import asyncio
import json
import logging
import re
from typing import Any

from livekit import rtc
from livekit.agents import AgentSession, JobContext

logger = logging.getLogger(__name__)


def sanitize_json_data(data: Any) -> dict[str, Any]:
    """Sanitize data to prevent ParseIntError in WebRTC layer"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Ensure keys are clean strings
            clean_key = str(key).strip()
            # Remove any non-printable characters from keys
            clean_key = re.sub(r"[^\w\s\-_.]", "", clean_key)

            if isinstance(value, str):
                # Clean string values - remove problematic characters
                clean_value = value.strip()
                # Remove control characters and invalid Unicode
                clean_value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean_value)
                # Replace problematic quotes and characters
                clean_value = clean_value.replace('\\"', '"').replace("\\'", "'")
                sanitized[clean_key] = clean_value
            elif isinstance(value, (int, float)):
                # Ensure numeric values are valid
                if isinstance(value, float) and (
                    value != value or value == float("inf") or value == float("-inf")
                ):
                    sanitized[clean_key] = 0  # Replace NaN/Inf with 0
                else:
                    sanitized[clean_key] = value
            elif isinstance(value, bool):
                sanitized[clean_key] = value
            elif isinstance(value, list):
                # Recursively clean list items
                sanitized[clean_key] = [
                    (
                        sanitize_json_data(item)
                        if isinstance(item, dict)
                        else clean_item(item)
                    )
                    for item in value
                ]
            elif isinstance(value, dict):
                # Recursively clean nested dictionaries
                sanitized[clean_key] = sanitize_json_data(value)
            elif value is None:
                sanitized[clean_key] = None
            else:
                # Convert other types to clean strings
                sanitized[clean_key] = clean_item(value)
        return sanitized
    else:
        return clean_item(data)


def clean_item(item: Any) -> Any:
    """Clean individual items"""
    if isinstance(item, str):
        clean_str = item.strip()
        # Remove control characters
        clean_str = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean_str)
        return clean_str
    elif isinstance(item, (int, float)):
        if isinstance(item, float) and (
            item != item or item == float("inf") or item == float("-inf")
        ):
            return 0
        return item
    else:
        return str(item) if item is not None else ""


class PerJobState:
    """Holds everything that must be isolated per livekit job / room."""

    def __init__(
        self,
        room: rtc.Room,
        session: AgentSession,
        website_name: str,
        database_name: str,
        base_url: str,
        website_description: str,
        pages: list[dict],
        categories: list[dict],
        preferred_language: str,
        currency: str,
        job_context: JobContext = None
    ):
        self.room: rtc.Room = room
        self.session: AgentSession = session
        self.website_name = website_name
        self.database_name = database_name
        self.website_description = website_description
        self.pages = pages or []
        self.categories = categories or []
        self.preferred_language = preferred_language
        self.currency = currency
        self.base_url = base_url
        self.job_context = job_context

    async def send_data_to_participants(self, data):
        """Enhanced send function with ParseIntError prevention"""
        if not self.room:
            logger.warning("No current room available for data sending")
            return False

        try:
            # Step 1: Sanitize the input data thoroughly
            if isinstance(data, dict):
                sanitized_data = sanitize_json_data(data)
                # Use very strict JSON serialization
                message = json.dumps(
                    sanitized_data,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                    default=str,  # Convert any remaining problematic types to strings
                )
            elif isinstance(data, str):
                # Clean string data thoroughly
                message = str(data).strip()
                # Remove control characters that might cause parsing issues
                message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)
                # Remove any potential numeric parsing issues
                message = re.sub(r'[^\w\s\-_.,:;!?()[\]{}"\']', "", message)
            else:
                # Convert to string and clean
                message = str(data) if data is not None else ""
                message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)

            # Step 2: Validate message
            if not message or len(message.strip()) == 0:
                logger.warning("Message is empty after sanitization, skipping")
                return False

            # Step 3: Size validation (reduce size for extra safety)
            max_size = 16384  # 16KB for extra safety
            if len(message) > max_size:
                logger.warning(f"Message too large ({len(message)} bytes), truncating")
                message = message[: max_size - 20] + "...[TRUNCATED]"

            # Step 4: Final encoding validation
            try:
                # Test JSON parsing if it looks like JSON
                if message.strip().startswith(("{", "[")):
                    json.loads(message)  # Validate JSON structure

                # Encode with strict error handling
                message_bytes = message.encode("utf-8", errors="replace")

                # Additional validation - ensure no null bytes
                if b"\x00" in message_bytes:
                    message_bytes = message_bytes.replace(b"\x00", b"")

            except (json.JSONDecodeError, UnicodeEncodeError) as encode_error:
                logger.error(f"Failed to validate/encode message: {encode_error}")
                return False

            # Step 5: Send with enhanced retry logic
            max_retries = 2  # Reduced retries to fail faster
            base_delay = 0.05  # Shorter delays

            for attempt in range(max_retries):
                try:
                    # Add small delay before each attempt to avoid race conditions
                    if attempt > 0:
                        await asyncio.sleep(base_delay * attempt)

                    await self.room.local_participant.publish_data(message_bytes)

                    # Success logging
                    log_msg = message[:80] + "..." if len(message) > 80 else message
                    logger.info(f"📤 Data sent successfully: {log_msg}")
                    return True

                except Exception as send_error:
                    error_msg = str(send_error).lower()

                    # Check for specific WebRTC parsing errors
                    if any(
                        keyword in error_msg
                        for keyword in ["parseint", "invalid digit", "number format"]
                    ):
                        logger.error(f"WebRTC parsing error detected: {send_error}")
                        # Don't retry parsing errors - they won't succeed
                        return False

                    if attempt == max_retries - 1:
                        logger.error(
                            f"Failed to send data after {max_retries} attempts: {send_error}"
                        )
                        return False
                    else:
                        logger.warning(
                            f"Send attempt {attempt + 1} failed, retrying: {send_error}"
                        )

        except Exception as e:
            logger.error(f"Critical error in send_data_to_participants: {e}")
            import traceback

            traceback.print_exc()
            return False

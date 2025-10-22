import logging
import re
from typing import Any

from livekit import rtc
from livekit.agents import AgentSession, JobContext

from src.devaito.db.models.products import Category

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
        categories: list[Category],
        preferred_language: str,
        currency: str,
        job_context: JobContext = None,
        pending_product: dict[str, Any] | None = None,
        current_mode: str = "text",
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
        self.pending_product = pending_product
        self.current_mode = current_mode

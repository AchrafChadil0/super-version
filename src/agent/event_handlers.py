import asyncio
import logging
from typing import TYPE_CHECKING

from livekit.agents import MetricsCollectedEvent

from src.agent.metrics import MetricsProcessor

if TYPE_CHECKING:
    from state_manager import PerJobState

logger = logging.getLogger(__name__)


class EventHandlers:
    """Manages all LiveKit event handlers"""

    def __init__(self, state: "PerJobState"):
        self.state = state

    def setup_room_handlers(self, room):
        """Setup room-level event handlers"""

        @room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(f"👋 Participant joined: {participant.identity}")
            pass

        @room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            pass

        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            pass

        @room.on("data_received")
        def on_data_received(data_packet):
            pass

    def setup_session_handlers(self, session, start_time: float):
        """Setup session-level event handlers"""

        @session.on("metrics_collected")
        def on_metrics_collected(event: MetricsCollectedEvent):
            metrics_processor = MetricsProcessor(start_time=start_time)
            asyncio.create_task(metrics_processor.process_metrics(event))

        @session.on("user_input_transcribed")
        def on_user_input_transcribed(evt):
            """Handle user speech transcription"""
            pass

        @session.on("conversation_item_added")
        def on_conversation_item_added(evt):
            """Handle when conversation items are added"""
            pass

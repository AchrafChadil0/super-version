import asyncio
import logging
from typing import TYPE_CHECKING

from livekit import rtc
from livekit.agents import MetricsCollectedEvent, AgentSession, UserStateChangedEvent, UserInputTranscribedEvent, \
    ConversationItemAddedEvent
from livekit.agents.llm import AudioContent
from livekit.rtc import TranscriptionSegment, Participant, TrackPublication

from src.agent.metrics import MetricsProcessor
from src.utils.tools import log_to_file

if TYPE_CHECKING:
    from state_manager import PerJobState

logger = logging.getLogger(__name__)


class EventHandlers:
    """Manages all LiveKit event handlers"""

    def __init__(self, state: "PerJobState"):
        self.state = state

    def setup_room_handlers(self, room: rtc.Room):
        """Setup room-level event handlers"""

        @room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(f"👋 Participant joined: {participant.identity}")
            pass

        @room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            logger.info(f"👋 Participant disconnected: {participant.identity}")

        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            pass

        @room.on("data_received")
        def on_data_received(data_packet):
            pass

    def setup_session_handlers(self, session: AgentSession, start_time: float):
        """Setup session-level event handlers"""
        inactivity_task: asyncio.Task | None = None
        @session.on("metrics_collected")
        def on_metrics_collected(event: MetricsCollectedEvent):
            metrics_processor = MetricsProcessor(start_time=start_time)
            asyncio.create_task(metrics_processor.process_metrics(event))

        async def send_user_input(text:str):
            await self.state.room.local_participant.send_text(text=text, topic="user_input")
        async def send_assistant_transcription(text:str):
            await self.state.room.local_participant.send_text(text=text, topic="assistant_transcription")

        @session.on("conversation_item_added")
        def on_conversation_item_added(event: ConversationItemAddedEvent):
            log_to_file(
                f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}", 111)
            if event.item.role == "assistant":
                asyncio.create_task(send_assistant_transcription(event.item.text_content))
            else:
                asyncio.create_task(send_user_input(event.item.text_content))

        async def user_presence_task():
            for _ in range(2):
                await session.generate_reply(
                    instructions=(
                        "The user has been inactive. Politely check if the user is still present."
                    )
                )
                await asyncio.sleep(15)
            await session.generate_reply(
                instructions=(
                    "The user is away, we going to shutdown the session right now, say goodbye!"
                )
            )
            await session.aclose()



        #@session.on("user_state_changed")
        """
        def _user_state_changed(ev: UserStateChangedEvent):
            nonlocal inactivity_task
            if ev.new_state == "away":
                inactivity_task = asyncio.create_task(user_presence_task())
                return

            # ev.new_state: listening, speaking, ..
            if inactivity_task is not None:
                inactivity_task.cancel()
        """






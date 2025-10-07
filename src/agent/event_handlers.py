import asyncio
import logging
from typing import TYPE_CHECKING

from livekit.agents import MetricsCollectedEvent, AgentSession, UserStateChangedEvent

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

    def setup_session_handlers(self, session: AgentSession, start_time: float):
        """Setup session-level event handlers"""
        inactivity_task: asyncio.Task | None = None
        @session.on("metrics_collected")
        def on_metrics_collected(event: MetricsCollectedEvent):
            metrics_processor = MetricsProcessor(start_time=start_time)
            asyncio.create_task(metrics_processor.process_metrics(event))

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
            session.shutdown()

        @session.on("user_state_changed")
        def _user_state_changed(ev: UserStateChangedEvent):
            nonlocal inactivity_task
            if ev.new_state == "away":
                inactivity_task = asyncio.create_task(user_presence_task())
                return

            # ev.new_state: listening, speaking, ..
            if inactivity_task is not None:
                inactivity_task.cancel()






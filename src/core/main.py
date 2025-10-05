import json
import time

from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import noise_cancellation, openai, silero

from src.agent.assistant import Assistant
from src.agent.event_handlers import EventHandlers
from src.agent.state_manager import PerJobState
from src.core.config import Config


async def entrypoint(ctx: agents.JobContext):
    metadata = ctx.job.metadata or "{}"
    parsed_metadata = json.loads(metadata)
    currency = "$"
    website_name = parsed_metadata.get("website_name", Config.DEFAULT_WEBSITE_NAME)
    website_description = parsed_metadata.get(
        "description_website", Config.DEFAULT_WEBSITE_DESCRIPTION
    )
    # hostname = parsed_metadata.get("host")
    preferred_language = parsed_metadata.get("language", "en")

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(model="gpt-4o-mini-realtime-preview"),
        tts=openai.TTS(
            voice="alloy",
        ),
    )

    state = PerJobState(
        room=ctx.room,
        session=session,
        website_name=website_name,
        website_description=website_description,
        preferred_language=preferred_language,
        currency=currency,
        categories=[],
        pages=[],
    )
    agent = Assistant()
    agent.website_name = website_name
    agent.website_description = website_description
    agent.preferred_language = preferred_language
    start_time = time.time()

    event_handlers = EventHandlers(state)
    # Setup room event handlers
    event_handlers.setup_room_handlers(ctx.room)
    event_handlers.setup_session_handlers(session, start_time)

    session.userdata = state
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(), close_on_disconnect=False
        ),
    )

    await session.generate_reply(
        instructions=f"""Always start by saying 'Welcome to {website_name}! How can I assist you today? in user's preferred language.'
               Communicate to the users in their preferred language (here is the 2 letter language ISO 639): {preferred_language}
               """,
    )


def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


def main():
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm)
    )


if __name__ == "__main__":
    main()

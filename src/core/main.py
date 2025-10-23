import base64
import json
import logging
import os
import time

from livekit import agents
from livekit.agents import AgentSession, RoomInputOptions, RoomOutputOptions, MetricsCollectedEvent, metrics
from livekit.plugins import noise_cancellation, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.telemetry import set_tracer_provider

from src.agent.agents.assistant import Assistant
from src.agent.event_handlers import EventHandlers
from src.agent.state_manager import PerJobState
from src.context_logger import setup_logging
from src.core.agent_session_config import (
    AgentIntimeSessionConfig,
)
from src.core.config import Config
from src.data.db_to_vector import sync_products_to_vector_store
from src.data.vector_store import VectorStore
from src.devaito.services.products import get_tenant_categories
from src.utils.tools import add_https_to_hostname, log_to_file

setup_logging(log_level="INFO", log_dir="logs")
logger = logging.getLogger(__name__)


def setup_langfuse(
    host: str | None = None, public_key: str | None = None, secret_key: str | None = None
):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    host = host or os.getenv("LANGFUSE_HOST")

    if not public_key or not secret_key or not host:
        raise ValueError("LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST must be set")

    langfuse_auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{host.rstrip('/')}/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    trace_provider = TracerProvider()
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    set_tracer_provider(trace_provider)




async def entrypoint(ctx: agents.JobContext):
    # setup_langfuse()
    await ctx.connect()
    metadata = ctx.job.metadata or "{}"
    parsed_metadata = json.loads(metadata)
    currency = "$"
    website_name = parsed_metadata.get("website_name", Config.DEFAULT_WEBSITE_NAME)
    website_description = parsed_metadata.get(
        "description_website", Config.DEFAULT_WEBSITE_DESCRIPTION
    )
    hostname = parsed_metadata.get("host", "picksssss.devaito.com")
    preferred_language = parsed_metadata.get("language", "en")
    database_name = parsed_metadata.get("database_name", "picksssss")
    mode = parsed_metadata.get("mode", "text")
    logger.info("parsed_metadata", extra={"parsed_metadata": parsed_metadata})

    try:
        # Ingest if there is no products
        vector_store = VectorStore(
            collection_name=Config.CHROMA_COLLECTION_NAME,
            persist_directory=f"vdbs/{database_name}",
            openai_api_key=Config.OPENAI_API_KEY,
        )
        stats = vector_store.get_statistics()

        if stats["total_products"] == 0:
            # we ingest data if we don't find anything
            logger.warning(
                "⚠️ Vector database is empty! Running ingestion automatically...",
                extra={"database_name": database_name, "base_url": hostname},
            )
            await sync_products_to_vector_store(
                database_name=database_name, hostname=hostname, clear_existing=False
            )
        else:
            logger.info(
                f"✅ Vector database ready with {stats['total_products']} products",
                extra={"database_name": database_name, "base_url": hostname},
            )
    except Exception:
        logger.exception(
            "something went wrong while trying to ingest data into vector db"
        )

    # session_config = AgentRealtimeSessionConfig()
    session_config = AgentIntimeSessionConfig()
    session = AgentSession(
        llm=openai.LLM(model=session_config.model_name),
        tts=openai.TTS(model=session_config.tts_model, voice=session_config.voice),
        stt=openai.STT(model=session_config.stt_model),
        vad=ctx.proc.userdata["vad"],
        turn_detection=MultilingualModel(),
    )
    base_url = add_https_to_hostname(hostname)
    try:
        categories = await get_tenant_categories(database_name)
    except Exception as e:
        logger.error(f"Failed to fetch categories for DB '{database_name}': {e}")
        categories = []
    state = PerJobState(
        room=ctx.room,
        session=session,
        website_name=website_name,
        database_name=database_name,
        base_url=base_url,
        website_description=website_description,
        preferred_language=preferred_language,
        job_context=ctx,
        currency=currency,
        categories=categories,
        pages=[],
    )
    agent = Assistant(state=state)

    start_time = time.time()

    event_handlers = EventHandlers(state)
    # Setup room event handlers
    event_handlers.setup_room_handlers(ctx.room)
    event_handlers.setup_session_handlers(session, start_time)

    session.userdata = state

    # by default, we disable the audio
    session.input.set_audio_enabled(False)
    session.output.set_audio_enabled(False)

    available_modes = ["text", "voice"]

    if mode not in available_modes:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of {available_modes}")

    # if the mode is voice we will activate the audio
    if mode == "voice":
        session.input.set_audio_enabled(True)
        session.output.set_audio_enabled(True)
        state.current_mode = "voice"


    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        usage_collector.collect(event.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        log_to_file("Usage:------", summary)

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(), close_on_disconnect=False
        ),
        room_output_options=RoomOutputOptions(sync_transcription=False),
    )

    await session.generate_reply(
        instructions=f"""Always start by saying 'Welcome to {website_name}! How can I assist you today? in user's preferred language. {preferred_language}'
               adapt naturally to the user's language and speaking style, if the user want to speak another lang other then preferred lang speak it.
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

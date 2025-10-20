from dataclasses import dataclass


@dataclass
class AgentRealtimeSessionConfig:
    """Configuration for AgentSession initialization."""

    model_name: str = "gpt-4o-mini-realtime-preview-2024-12-17"
    voice: str = "alloy"


@dataclass
class AgentIntimeSessionConfig:
    model_name: str = "gpt-4o-mini-2024-07-18"
    stt_model: str = "gpt-4o-transcribe"
    tts_model: str = "gpt-4o-mini-tts"
    voice: str = "alloy"

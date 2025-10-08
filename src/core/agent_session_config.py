from dataclasses import dataclass

@dataclass
class AgentRealtimeSessionConfig:
    """Configuration for AgentSession initialization."""
    model_name: str = "gpt-4o-mini-realtime-preview-2024-12-17"
    voice: str = "alloy"

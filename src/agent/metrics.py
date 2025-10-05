import time
from datetime import datetime

from livekit.agents import MetricsCollectedEvent
from livekit.agents.metrics import AgentMetrics, RealtimeModelMetrics
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()

# --- Pricing (USD per 1,000,000 tokens) ---
# GPT-4o mini
P_AUDIO_IN = 10.00
P_AUDIO_CACHED = 0.30
P_AUDIO_OUT = 20.00

P_TEXT_IN = 0.60
P_TEXT_CACHED = 0.30
P_TEXT_OUT = 2.40

# Images are unused / free per your note
P_IMAGE_IN = 0.00
P_IMAGE_CACHED = 0.00
P_IMAGE_OUT = 0.00


def _usd(x: float) -> str:
    # Show small costs with more precision so they don’t round to $0.00
    return f"${x:.6f}" if x < 0.01 else f"${x:.4f}"


class MetricsProcessor:
    start_time: float

    def __init__(self, start_time: float):
        self.start_time = start_time

    async def process_metrics(self, metrics_event: MetricsCollectedEvent):
        metrics: AgentMetrics = metrics_event.metrics
        if isinstance(metrics, RealtimeModelMetrics):
            self.metrics_to_table(metrics, self.start_time)

    def metrics_to_table(self, metrics: RealtimeModelMetrics, start_time: float):
        # console = Console()

        table = Table(
            title="[bold blue]Realtime Model Metrics[/bold blue]",
            box=box.ROUNDED,
            highlight=True,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Metric", style="bold green")
        table.add_column("Value", style="yellow")

        # ----- Format timestamp
        timestamp = datetime.fromtimestamp(metrics.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----- Top-level metrics
        table.add_row("Type", str(metrics.type))
        table.add_row("Label", str(metrics.label))
        if metrics.request_id is not None:
            table.add_row("Request ID", str(metrics.request_id))
        table.add_row("Timestamp", timestamp)
        table.add_row("Duration", f"[white]{metrics.duration:.4f}[/white]s")
        table.add_row("Time to First Token", f"[white]{metrics.ttft:.4f}[/white]s")
        table.add_row("Cancelled", "✓" if metrics.cancelled else "✗")
        table.add_row("Input Tokens (total)", str(metrics.input_tokens))
        table.add_row("Output Tokens (total)", str(metrics.output_tokens))
        table.add_row("Total Tokens", str(metrics.total_tokens))
        table.add_row("Tokens/Second", f"{metrics.tokens_per_second:.2f}")

        # ----- Input token details
        it = metrics.input_token_details
        table.add_row("--- Input Token Details ---", "")
        table.add_row("Text Tokens (Input)", str(it.text_tokens))
        table.add_row("Audio Tokens (Input)", str(it.audio_tokens))
        table.add_row("Image Tokens (Input)", str(it.image_tokens))
        table.add_row("Cached Tokens (total)", str(it.cached_tokens))

        cached_text = cached_audio = cached_image = 0
        if it.cached_tokens_details:
            c = it.cached_tokens_details
            cached_text = int(c.text_tokens or 0)
            cached_audio = int(c.audio_tokens or 0)
            cached_image = int(c.image_tokens or 0)
            table.add_row("   └─ Cached Text Tokens", str(cached_text))
            table.add_row("   └─ Cached Audio Tokens", str(cached_audio))
            table.add_row("   └─ Cached Image Tokens", str(cached_image))

        # ----- Output token details
        ot = metrics.output_token_details
        table.add_row("--- Output Token Details ---", "")
        table.add_row("Text Tokens (Output)", str(ot.text_tokens))
        table.add_row("Audio Tokens (Output)", str(ot.audio_tokens))
        table.add_row("Image Tokens (Output)", str(ot.image_tokens))

        # ======== COST CALCULATION ========
        # Billable input = input - cached (never negative)
        billable_text_in = max(it.text_tokens - cached_text, 0)
        billable_audio_in = max(it.audio_tokens - cached_audio, 0)
        billable_image_in = max(it.image_tokens - cached_image, 0)

        # Costs (per 1e6)
        cost_input_text = billable_text_in * (P_TEXT_IN / 1_000_000)
        cost_input_audio = billable_audio_in * (P_AUDIO_IN / 1_000_000)
        cost_input_image = billable_image_in * (P_IMAGE_IN / 1_000_000)

        cost_cached_text = cached_text * (P_TEXT_CACHED / 1_000_000)
        cost_cached_audio = cached_audio * (P_AUDIO_CACHED / 1_000_000)
        cost_cached_image = cached_image * (P_IMAGE_CACHED / 1_000_000)

        cost_output_text = ot.text_tokens * (P_TEXT_OUT / 1_000_000)
        cost_output_audio = ot.audio_tokens * (P_AUDIO_OUT / 1_000_000)
        cost_output_image = ot.image_tokens * (P_IMAGE_OUT / 1_000_000)

        total_input_cost = cost_input_text + cost_input_audio + cost_input_image
        total_cached_cost = cost_cached_text + cost_cached_audio + cost_cached_image
        total_output_cost = cost_output_text + cost_output_audio + cost_output_image
        grand_total_cost = total_input_cost + total_cached_cost + total_output_cost

        # ----- Session duration & cost per minute
        elapsed_seconds = time.time() - start_time
        elapsed_minutes = elapsed_seconds / 60
        cost_per_minute = (
            grand_total_cost / elapsed_minutes if elapsed_minutes > 0 else 0
        )

        # ----- Cost breakdown section
        table.add_row("— Cost Breakdown (USD) —", "")
        table.add_row(
            "Input (Text) — Billable", f"{billable_text_in} → {_usd(cost_input_text)}"
        )
        table.add_row(
            "Input (Audio) — Billable",
            f"{billable_audio_in} → {_usd(cost_input_audio)}",
        )
        if billable_image_in:
            table.add_row(
                "Input (Image) — Billable",
                f"{billable_image_in} → {_usd(cost_input_image)}",
            )

        table.add_row("Cached (Text)", f"{cached_text} → {_usd(cost_cached_text)}")
        table.add_row("Cached (Audio)", f"{cached_audio} → {_usd(cost_cached_audio)}")
        if cached_image:
            table.add_row(
                "Cached (Image)", f"{cached_image} → {_usd(cost_cached_image)}"
            )

        table.add_row("Output (Text)", f"{ot.text_tokens} → {_usd(cost_output_text)}")
        table.add_row(
            "Output (Audio)", f"{ot.audio_tokens} → {_usd(cost_output_audio)}"
        )
        if ot.image_tokens:
            table.add_row(
                "Output (Image)", f"{ot.image_tokens} → {_usd(cost_output_image)}"
            )

        # Totals
        table.add_row("— Subtotal: Input", _usd(total_input_cost))
        table.add_row("— Subtotal: Cached", _usd(total_cached_cost))
        table.add_row("— Subtotal: Output", _usd(total_output_cost))
        table.add_row(
            "[bold]Estimated Cost (Total)[/bold]",
            f"[bold]{_usd(grand_total_cost)}[/bold]",
        )

        # Session stats
        table.add_row("Session Time", f"{elapsed_minutes:.2f} min")
        table.add_row("Estimated Cost/Minute", _usd(cost_per_minute))

        with open("metrics_output.txt", "a", encoding="utf-8") as f:
            file_console = Console(file=f, width=120)  # Adjust width as needed
            file_console.print("\n")
            file_console.print(table)
            file_console.print("\n")

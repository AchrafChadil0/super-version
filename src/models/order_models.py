import logging
from dataclasses import dataclass
from datetime import datetime

from src.models.product_models import ProductOptionGroup, parse_option

logger = logging.getLogger(__name__)


class OrderState:
    def __init__(self):
        self.product_name = "Product Name"
        self.total_price = 0
        self.quantity = 1
        self.option_groups: list[ProductOptionGroup] = []
        self.currency_code = "USD"
        self.currency_symbol = "$"
        self.last_sync: datetime | None = None

    def to_dict(self) -> dict:
        """Convert OrderState instance to dictionary representation."""
        return {
            "product_name": self.product_name,
            "total_price": self.total_price,
            "quantity": self.quantity,
            "option_groups": [
                {
                    "id": group.id,
                    "name": group.name,
                    "min_options": group.min_options,
                    "max_options": group.max_options,
                    "options": [
                        {
                            "id": option.id,
                            "name": option.name,
                            "price": option.price,
                            "stock": option.stock,
                            "qty_max": option.qty_max,
                            "qty": option.qty,
                        }
                        for option in group.options
                    ],
                }
                for group in self.option_groups
            ],
            "currency_code": self.currency_code,
            "currency_symbol": self.currency_symbol,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
        }

    @classmethod
    def from_sync_response(cls, sync_data) -> "OrderState":
        """Create OrderState from sync response data."""

        state = cls()
        state.product_name = sync_data.get("product_name")
        state.currency_code = sync_data.get("currency_code", "EUR")
        state.currency_symbol = sync_data.get("currency_symbol", "€")
        state.quantity = sync_data.get("current_quantity", 1)
        state.total_price = sync_data.get("price", 0)
        state.last_sync = datetime.now()

        if sync_data.get("options_groups", []):
            for group_data in sync_data.get("options_groups", []):
                group = ProductOptionGroup(
                    id=group_data["id"],
                    name=group_data["group_name"],
                    min_options=group_data["min_options"],
                    max_options=group_data["max_options"],
                )
                for option_data in group_data["options"]:
                    option = parse_option(option_data)
                    group.add_option(option)
                state.option_groups.append(group)
        return state

    def to_summary(self) -> str:
        """Generate a concise, human-readable summary of the order state."""
        qty_text = f" (x{self.quantity})" if self.quantity > 1 else ""
        lines = [
            f"This Order Summary for: {self.product_name}{qty_text}",
            f"Total Price: {self.total_price:.2f}{self.currency_symbol}",
        ]

        if self.option_groups:
            lines.append("Selected Options:")
            for group in self.option_groups:
                group_line = f"  - {group.name} (choose {group.min_options}-{group.max_options}):"
                lines.append(group_line)
                for option in group.options:
                    lines.append(
                        f"    * {option.name} - {option.price:.2f}{self.currency_symbol} "
                        f"(Qty: {option.qty}/{option.qty_max}, Stock: {option.stock})"
                    )
        else:
            lines.append("No options selected.")

        if self.last_sync:
            lines.append(f"Last synced: {self.last_sync.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)


@dataclass
class OrderResult:
    """
    The result returned by the OrderTask upon completion.
    """

    message: str
    product_name: None | str = None

from typing import TypedDict


class ProductOption:
    def __init__(
        self, id: int, name: str, price: float, stock: int, qty_max: int, qty: int = 0
    ):
        self.id = id
        self.name = name
        self.price = price
        self.stock = stock
        self.qty_max = qty_max
        self.qty = qty

    def to_dict(self) -> dict:
        try:
            price = f"{self.price:.2f}"
        except (TypeError, ValueError):
            price = "0.00"
        return {
            "id": self.id,
            "option_name": self.name,
            "price": price,
            "stock": self.stock,
            "qty_max": self.qty_max,
            "qty": self.qty,
        }


class ProductOptionGroup:
    def __init__(self, id: int, name: str, min_options: int, max_options: int):
        self.id = id
        self.name = name
        self.min_options = min_options
        self.max_options = max_options
        self.options: list[ProductOption] = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "min_options": self.min_options,
            "max_options": self.max_options,
            "options": [opt.to_dict() for opt in self.options],
        }

    def add_option(self, option: ProductOption):
        if not isinstance(option, ProductOption):
            raise TypeError("option must be ProductOption")
        self.options.append(option)


class ApiOption(TypedDict):
    id: int
    option_name: str
    price: str
    stock: int
    qty_max: int


def parse_option(option_data: ApiOption) -> ProductOption:
    try:
        price = float(option_data["price"])
    except (ValueError, TypeError):
        price = 0.0
    return ProductOption(
        id=option_data.get("id", 0),
        name=option_data.get("option_name", ""),
        price=price,
        stock=option_data.get("stock", 0),
        qty_max=option_data.get("qty_max", 0),
    )

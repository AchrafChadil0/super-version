from typing import Literal, TypedDict

ProductType = Literal["basic", "variant", "customizable"]


class VectorProductMetadata(TypedDict):
    categories: list[str]
    brand: str
    product_type: ProductType
    redirect_url: str


class VectorProductFormat(TypedDict):
    id: str
    document: str
    metadata: VectorProductMetadata


class VectorProductSearchResult(TypedDict):
    id: str
    document: str
    metadata: VectorProductMetadata
    similarity_score: float
    search_rank: int


class SyncOption(TypedDict):
    option_name: str
    price: str
    stock: int
    qty_max: int
    id: int
    qty: int


class SyncOptionsGroup(TypedDict):
    id: int
    min_options: int
    max_options: int
    options: list[SyncOption]
    group_name: str


class SyncResponse(TypedDict):
    options_groups: list[SyncOptionsGroup]
    current_quantity: int
    currency_code: str
    currency_symbol: str
    price: float
    product_name: str

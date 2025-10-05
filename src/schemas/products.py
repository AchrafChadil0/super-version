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

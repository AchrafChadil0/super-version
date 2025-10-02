from typing import TypedDict


class BrandDict(TypedDict):
    id: int
    name: str
    is_active: int


class ColorDict(TypedDict):
    id: int
    name: str


class CategoryDict(TypedDict):
    id: int
    name: str
    permalink: str


class ProductDict(TypedDict):
    id: int
    name: str
    brand: int
    has_options: bool
    has_variants: bool
    colors: list[ColorDict]
    categories: list[CategoryDict]


class CategoryDictOld(TypedDict):
    id: int
    name: str


class BasicSingleProductDetailDict(TypedDict):
    product_id: int
    product_name: str
    product_description: str
    product_permalink: str
    brand_id: int | None
    brand_name: str | None
    categories: list[CategoryDictOld]
    price: float | None
    quantity: int | None
    has_discount: int | None
    discount_type_name: str | None
    discount_label: str | None
    discount_amount: float | None
    has_variant: int


class VariantOptionDict(TypedDict):
    option_id: int
    option_name: str


class VariantGroupDict(TypedDict):
    group_id: int
    group_name: str
    options: list[VariantOptionDict]


class BasicVariantProductDetailDict(TypedDict):
    product_id: int
    product_name: str
    product_description: str
    product_permalink: str
    brand_id: int | None
    brand_name: str | None
    categories: list[CategoryDictOld]
    variant: str | None
    price: float | None
    quantity: int | None
    has_discount: int | None
    discount_type_name: str | None
    discount_label: str | None
    discount_amount: float | None
    colors: list[ColorDict] | None
    has_variant: int
    variants: list[VariantGroupDict] | None


class CustomizableOptionDict(TypedDict):
    id: int
    option_name: str
    price: float
    stock: int
    qty_max: int


class OptionsGroupDict(TypedDict):
    group_id: int
    group_name: str
    min_options: int
    max_options: int
    options: list[CustomizableOptionDict]


class CustomizableProductDetailDict(TypedDict):
    product_id: int
    product_name: str
    product_description: str
    product_permalink: str
    brand_id: int | None
    brand_name: str | None
    categories: list[CategoryDictOld]
    price: float | None
    quantity: int | None
    has_discount: int | None
    discount_type_name: str | None
    discount_label: str | None
    discount_amount: float | None
    options_groups: list[OptionsGroupDict] | None

class ProductForVectorDict(TypedDict):
    product_id: int
    product_name: str
    product_description: str
    product_permalink: str
    has_options: int
    has_variant: int
    brand_id: int | None
    brand_name: str | None
    categories: list[CategoryDictOld]

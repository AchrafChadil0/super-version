import datetime

from src.devaito.schemas.products import (
    BasicSingleProductDetailDict,
    BasicVariantProductDetailDict,
    CustomizableProductDetailDict,
)
from src.devaito.utils.tools import clean_html
from src.schemas.products import VectorProductSearchResult


def log_to_file(hint: str, variable, file_path: str = "logs/debug_logs.txt"):
    """
    Logs a hint and a variable to a txt file with a timestamp.

    :param hint: A string hint or marker (e.g., "❌❌❌❌")
    :param variable: The variable to log (can be any type)
    :param file_path: Path to the log file
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {hint}\n")
        f.write(f"{variable}\n")
        f.write("-" * 50 + "\n")  # separator for readability


def format_search_results_for_llm(results: list[VectorProductSearchResult]) -> str:
    """
    Format search results into a clean, LLM-friendly string.

    Args:
        results: List of search results

    Returns:
        Formatted string ready for LLM consumption
    """
    if not results:
        return "No search results found."

    formatted_parts = [f"Found {len(results)} relevant results:\n"]

    for result in results:
        # Extract metadata
        meta = result["metadata"]
        # Format each result
        result_text = f"""
Result #{result['search_rank']} (Relevance: {result['similarity_score']:.2%})
---
Product: {result['document'].strip()}
product_id: {result['id']}
product_type: {meta['product_type']}
redirect_url: {meta['redirect_url']}
"""
        formatted_parts.append(result_text)

    return "\n".join(formatted_parts)


def format_customizable_product_for_llm(
    product_details: CustomizableProductDetailDict, currency: str
) -> str:
    """Format product dict into LLM-friendly markdown text."""
    lines = [
        f"# {product_details['product_name']}",
        f"**Product ID:** {product_details['product_id']}",
    ]

    if product_details.get("brand_name"):
        lines.append(f"**Brand:** {product_details['brand_name']}")

    # Price formatting
    if product_details.get("price") is not None:
        lines.append("\n## Pricing")
        lines.append(f"- **Base Price:** {product_details['price']:.2f} {currency}")

        if product_details.get("has_discount") and product_details.get(
            "discount_amount"
        ):
            if product_details["discount_type_name"] == "Flat":
                final_price = (
                    product_details["price"] - product_details["discount_amount"]
                )
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount Amount:** {product_details['discount_amount']:.2f} {currency} off"
                )

            if product_details["discount_type_name"] == "Percentage":
                discount_value = (
                    product_details["price"] * product_details["discount_amount"]
                ) / 100
                final_price = product_details["price"] - discount_value
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount:** {product_details['discount_amount']:.0f}% off ({discount_value:.2f} {currency})"
                )

            if product_details.get("discount_label"):
                lines.append(
                    f"- **Discount Label:** {product_details['discount_label']}"
                )

    # Description with safety check
    if product_details.get("product_description"):
        description = product_details["product_description"]
        lines.append("\n## Description")
        lines.append(clean_html(description))

    # Categories
    if product_details.get("categories"):
        category_names = [cat["name"] for cat in product_details["categories"]]
        lines.append("\n## Categories")
        lines.append(", ".join(category_names))

    # Customization options with better safety checks
    if product_details.get("options_groups"):
        lines.append("\n## Customization Options")
        for group in product_details["options_groups"]:
            if not group.get("options"):  # Safety check
                continue

            lines.append(f"\n### {group['group_name']}")
            lines.append(f"*group_id: {group['group_id']}*")
            lines.append("")  # Empty line for better formatting

            for opt in group["options"]:
                price_str = (
                    f"{opt['price']:.2f} {currency}"
                    if opt.get("price") is not None
                    else "N/A"
                )
                lines.append(
                    f"- **{opt['option_name']}** (option_id: {opt['id']}) - {price_str}"
                )

    return "\n".join(lines)


def format_basic_variant_product_for_llm(
    product_details: BasicVariantProductDetailDict, currency: str
) -> str:
    """Format basic variant product dict into LLM-friendly markdown text."""
    lines = [
        f"# {product_details['product_name']}",
        f"**Product ID:** {product_details['product_id']}",
    ]

    if product_details.get("brand_name"):
        lines.append(f"**Brand:** {product_details['brand_name']}")

    # Current variant if applicable
    if product_details.get("variant"):
        lines.append(f"**Current Variant:** {product_details['variant']}")

    # Price formatting
    if product_details.get("price") is not None:
        lines.append("\n## Pricing")
        lines.append(f"- **Base Price:** {product_details['price']:.2f} {currency}")

        if product_details.get("has_discount") and product_details.get(
            "discount_amount"
        ):
            if product_details["discount_type_name"] == "Flat":
                final_price = (
                    product_details["price"] - product_details["discount_amount"]
                )
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount Amount:** {product_details['discount_amount']:.2f} {currency} off"
                )

            elif product_details["discount_type_name"] == "Percentage":
                discount_value = (
                    product_details["price"] * product_details["discount_amount"]
                ) / 100
                final_price = product_details["price"] - discount_value
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount:** {product_details['discount_amount']:.0f}% off ({discount_value:.2f} {currency})"
                )

            if product_details.get("discount_label"):
                lines.append(
                    f"- **Discount Label:** {product_details['discount_label']}"
                )

    # Description with safety check
    if product_details.get("product_description"):
        description = product_details["product_description"]
        lines.append("\n## Description")
        lines.append(clean_html(description))  # Assuming clean_html is available

    # Categories
    if product_details.get("categories"):
        category_names = [cat["name"] for cat in product_details["categories"]]
        lines.append("\n## Categories")
        lines.append(", ".join(category_names))

    # Available colors
    if product_details.get("colors"):
        lines.append("\n## Available Colors")
        lines.append("*group_id: -1*")
        color_list = []
        for color in product_details["colors"]:
            # Assuming ColorDict has 'name' and possibly 'hex' or 'code' fields
            if isinstance(color, dict) and "name" in color:
                color_list.append(f"- **{color['name']}**  (option_id: {color['id']})")
            elif isinstance(color, str):
                color_list.append(f"- {color}")
        lines.extend(color_list)

    # Variant options (similar to customization but for variants like sizes)
    if product_details.get("has_variant") and product_details.get("variants"):
        lines.append("\n## Available Variants")
        for group in product_details["variants"]:
            if not group.get("options"):  # Safety check
                continue

            lines.append(f"\n### {group['group_name']}")
            lines.append(f"*group_id: {group['group_id']}*")
            lines.append("")  # Empty line for better formatting

            for opt in group["options"]:
                lines.append(
                    f"- **{opt['option_name']}** (option_id: {opt['option_id']})"
                )

    # Stock information if available
    if product_details.get("quantity") is not None:
        lines.append("\n## Stock")
        lines.append(f"- **Available Quantity:** {product_details['quantity']}")

    return "\n".join(lines)


def format_basic_single_product_for_llm(
    product_details: BasicSingleProductDetailDict, currency: str
) -> str:
    """Format basic single product dict into LLM-friendly markdown text."""
    lines = [
        f"# {product_details['product_name']}",
        f"**Product ID:** {product_details['product_id']}",
    ]

    if product_details.get("brand_name"):
        lines.append(f"**Brand:** {product_details['brand_name']}")

    # Price formatting
    if product_details.get("price") is not None:
        lines.append("\n## Pricing")
        lines.append(f"- **Base Price:** {product_details['price']:.2f} {currency}")

        if product_details.get("has_discount") and product_details.get(
            "discount_amount"
        ):
            if product_details["discount_type_name"] == "Flat":
                final_price = (
                    product_details["price"] - product_details["discount_amount"]
                )
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount Amount:** {product_details['discount_amount']:.2f} {currency} off"
                )

            elif product_details["discount_type_name"] == "Percentage":
                discount_value = (
                    product_details["price"] * product_details["discount_amount"]
                ) / 100
                final_price = product_details["price"] - discount_value
                lines.append(f"- **Discount Price:** {final_price:.2f} {currency}")
                lines.append(
                    f"- **Discount:** {product_details['discount_amount']:.0f}% off ({discount_value:.2f} {currency})"
                )

            if product_details.get("discount_label"):
                lines.append(
                    f"- **Discount Label:** {product_details['discount_label']}"
                )

    # Description with safety check
    if product_details.get("product_description"):
        description = product_details["product_description"]
        lines.append("\n## Description")
        lines.append(clean_html(description))

    # Categories
    if product_details.get("categories"):
        category_names = [cat["name"] for cat in product_details["categories"]]
        lines.append("\n## Categories")
        lines.append(", ".join(category_names))

    # Stock information if available
    if product_details.get("quantity") is not None:
        lines.append("\n## Stock")
        lines.append(f"- **Available Quantity:** {product_details['quantity']}")

    # Note about variants if applicable
    if product_details.get("has_variant"):
        lines.append("\n## Note")
        lines.append("*This product has variants available and no options to add, it's a stand alone product*")

    return "\n".join(lines)

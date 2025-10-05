import json

from livekit.agents import RunContext, ToolError, function_tool, get_job_context
from livekit.rtc import RpcError

from src.devaito.services.products import (
    get_basic_single_product_detail,
    get_basic_variant_product_detail,
    get_customizable_product_detail,
)
from src.schemas.products import ProductType

from ...core.config import Config
from ...data.vector_store import VectorStore
from ...utils.tools import (
    format_customizable_product_for_llm,
    format_search_results_for_llm,
    log_to_file,
)
from ..state_manager import PerJobState
from .configs import REDIRECT_TO_PRODUCT_PAGE, REDIRECT_TO_WEBSITE_PAGE, SEARCH_PRODUCTS


@function_tool(name=SEARCH_PRODUCTS.name, description=SEARCH_PRODUCTS.to_description())
async def search_products(
    context: RunContext,
    query: str,
):

    state: PerJobState = context.userdata
    website_name = state.website_name

    vector_store = VectorStore(
        collection_name="products",
        persist_directory=f"vdbs/{website_name}",
        openai_api_key=Config.OPENAI_API_KEY,
    )
    # Perform semantic search
    products = vector_store.search_products(query=query, n_results=2)
    log_to_file("products[0]", format_search_results_for_llm(products))

    return products


@function_tool(
    name=REDIRECT_TO_PRODUCT_PAGE.name,
    description=REDIRECT_TO_PRODUCT_PAGE.to_description(),
)
async def redirect_to_product_page(
    context: RunContext, redirect_url: str, product_id: int, product_type: ProductType
) -> dict[str, any]:
    try:
        state: PerJobState = context.userdata
        website_name = state.website_name
        room = get_job_context().room

        if not room.remote_participants:
            raise ToolError("No participants to redirect")

        participant_identity = next(iter(room.remote_participants))

        try:
            await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="redirectToPage",
                payload=json.dumps({"url": redirect_url}),
            )
        except RpcError as e:
            raise ToolError("Failed to redirect to product page") from e

        if product_type == "basic":
            product_details = await get_basic_single_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_customizable_product_for_llm(
                product_details, currency=state.currency
            )
        elif product_type == "variant":
            product_details = await get_basic_variant_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_customizable_product_for_llm(
                product_details, currency=state.currency
            )
        elif product_type == "customizable":
            product_details = await get_customizable_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_customizable_product_for_llm(
                product_details=product_details, currency=state.currency
            )
        else:
            raise ValueError(f"Invalid product type: {product_type}")

        log_to_file("7alim", formated_details)

        return {
            "success": True,
            "redirected_to": redirect_url,
            "product_details": formated_details,
        }

    except ToolError:
        raise
    except Exception as e:
        raise ToolError("Product page redirect failed") from e


@function_tool(
    name=REDIRECT_TO_WEBSITE_PAGE.name,
    description=REDIRECT_TO_WEBSITE_PAGE.to_description(),
)
async def redirect_to_website_page(
    context: RunContext,
    redirect_url: str,
) -> dict[str, any]:
    try:
        room = get_job_context().room

        if not room.remote_participants:
            raise ToolError("No participants to redirect")

        participant_identity = next(iter(room.remote_participants))

        try:
            await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="redirectToPage",
                payload=json.dumps({"url": redirect_url}),
            )
        except RpcError as e:
            raise ToolError("Failed to redirect to page") from e

        return {"success": True, "redirected_to": redirect_url}

    except ToolError:
        raise
    except Exception as e:
        raise ToolError("Page redirect failed") from e

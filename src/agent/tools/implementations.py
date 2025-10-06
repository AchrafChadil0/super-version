import json

from livekit.agents import RunContext, ToolError, function_tool, get_job_context
from livekit.rtc import RpcError

from ...core.config import Config
from ...data.vector_store import VectorStore
from ...utils.tools import (
    format_search_results_for_llm,
    log_to_file,
)
from ..state_manager import PerJobState
from .configs import REDIRECT_TO_WEBSITE_PAGE, SEARCH_PRODUCTS


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

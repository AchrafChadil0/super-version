import json
from typing import Any

from livekit.agents import (
    ChatContext,
    RunContext,
    ToolError,
    function_tool,
    get_job_context,
)
from livekit.rtc import RpcError

from ..agents.basic_order_task import BasicOrderTask
from ...core.config import Config
from ...data.vector_store import VectorStore
from ...devaito.services.products import (
    get_basic_single_product_detail,
    get_basic_variant_product_detail,
    get_customizable_product_detail,
)
from ...schemas.products import ProductType, SyncResponse
from ...utils.tools import (
    format_basic_single_product_for_llm,
    format_basic_variant_product_for_llm,
    format_customizable_product_for_llm,
    log_to_file,
)
from ..state_manager import PerJobState
from .configs import REDIRECT_TO_WEBSITE_PAGE


async def search_products_impl(
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


async def redirect_to_product_page_impl(
    chat_ctx: ChatContext,
    context: RunContext,
    redirect_url: str,
    product_id: int,
    product_type: ProductType,
):
    try:
        from src.agent.agents.order_task import OrderTask

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

        if product_type == ProductType.BASIC:
            product_details = await get_basic_single_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_basic_single_product_for_llm(
                product_details, currency=state.currency
            )
        elif product_type == ProductType.VARIANT:
            product_details = await get_basic_variant_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_basic_variant_product_for_llm(
                product_details, currency=state.currency
            )
        elif product_type == ProductType.CUSTOMIZABLE:
            product_details = await get_customizable_product_detail(
                tenant_id=website_name, product_id=product_id
            )
            formated_details = format_customizable_product_for_llm(
                product_details=product_details, currency=state.currency
            )
        else:
            raise ValueError(f"Invalid product type: {product_type}")
        log_to_file("7ALIM", formated_details)
        if product_type == ProductType.BASIC:
            return BasicOrderTask(
                product_name=product_details.get("product_name", "Product Name"),
                product_details_summary=formated_details,
                chat_ctx=chat_ctx,  # Pass the current chat context for continuity
                product_type=product_type,
                website_name=state.website_name,
                website_description=state.website_description,
                preferred_language=state.preferred_language,
            )
        else:
            return OrderTask(
                product_name=product_details.get("product_name", "Product Name"),
                product_details_summary=formated_details,
                chat_ctx=chat_ctx,  # Pass the current chat context for continuity
                product_type=product_type,
                website_name=state.website_name,
                website_description=state.website_description,
                preferred_language=state.preferred_language,
            )

    except ToolError:
        raise
    except Exception as e:
        raise ToolError("Product page redirect failed") from e


# ============================================
# ORDER TASK TOOLS IMPLEMENTATIONS (used inside OrderTask agent)
# ============================================


async def sync_order_options_impl(context: RunContext):
    from ...models.order_models import OrderState

    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants to redirect")
    participant_identity = next(iter(room.remote_participants))
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="syncProductOptions",
            payload=json.dumps({}),
            response_timeout=15.0,
        )
    except RpcError as e:
        raise ToolError("Failed to sync order options") from e

    if not response:
        return {"success": False, "error": "Empty RPC response"}
    order_data: SyncResponse = json.loads(response)
    current_order = OrderState.from_sync_response(order_data)
    log_to_file(
        "OrderTask.sync_order_options(), self.current_order.to_summary()",
        current_order.to_summary(),
    )
    return {"success": True, "summary": current_order.to_summary()}


async def increase_product_quantity_impl(
    product_type: ProductType, context: RunContext
) -> dict[str, Any]:
    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants is present")

    participant_identity = next(iter(room.remote_participants))
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="increaseProductQuantity",
            payload=json.dumps(
                {
                    "product_type": (
                        "basic" if product_type == ProductType.VARIANT else product_type
                    )
                }
            ),
            response_timeout=10.0,
        )
    except RpcError as e:
        raise ToolError("Failed to increase product quantity") from e

    log_to_file("OrderTask.increase_product_quantity(): response", response)
    if not response:
        raise ToolError("Failed to increase product quantity")
    # Sync to update local state
    # await self.sync_order_options(context)
    return {"message": response}


# --------


async def decrease_product_quantity_impl(
    product_type: ProductType, context: RunContext
) -> dict[str, any]:
    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants is present")

    participant_identity = next(iter(room.remote_participants))
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="decreaseProductQuantity",
            payload=json.dumps(
                {
                    "product_type": (
                        "basic" if product_type == ProductType.VARIANT else product_type
                    )
                }
            ),
            response_timeout=10.0,
        )
    except RpcError as e:
        raise ToolError("Failed to decrease product quantity") from e

    log_to_file("OrderTask.decrease_product_quantity(): response", response)
    if not response:
        raise ToolError("Failed to decrease product quantity")

    # Sync to update local state
    # await self.sync_order_options(context)
    return {"message": response}


# --------
async def select_option_impl(
    product_type: ProductType,
    group_id: int,
    option_id: int,
    context: RunContext,
) -> dict[str, Any]:

    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants is present")
    participant_identity = next(iter(room.remote_participants))
    payload = json.dumps(
        {
            "group_id": group_id,
            "option_id": option_id,
            "action": "select",
            "product_type": (
                "basic" if product_type == ProductType.VARIANT else product_type
            ),
        }
    )
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="toggleOptionSelection",
            payload=payload,
            response_timeout=10.0,
        )
    except RpcError as e:
        raise ToolError("Failed to select option") from e
    log_to_file("OrderTask.select_option(): response", response)
    if not response:
        raise ToolError("Failed to select option")
    # Sync to update local state
    # await self.sync_order_options(context)
    return {"message": response, "group_id": group_id, "option_id": option_id}


# --------
async def unselect_option_impl(
    product_type: ProductType, group_id: int, option_id: int, context: RunContext
) -> dict[str, Any]:

    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants is present")
    participant_identity = next(iter(room.remote_participants))
    payload = json.dumps(
        {
            "group_id": group_id,
            "option_id": option_id,
            "action": "unselect",
            "product_type": product_type,
        }
    )
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="toggleOptionSelection",
            payload=payload,
            response_timeout=15.0,
        )
    except RpcError as e:
        raise ToolError("Failed to unselect option") from e

    log_to_file("OrderTask.unselect_option(): response", response)
    if not response:
        raise ToolError("Failed to unselect option")
    # Sync to update local state
    # await self.sync_order_options(context)
    return {"message": response, "group_id": group_id, "option_id": option_id}


async def complete_order_impl(
    chat_ctx: ChatContext, product_name: str, context: RunContext
):
    from src.agent.agents.assistant import Assistant
    room = get_job_context().room
    if not room.remote_participants:
        raise ToolError("No participants available")

    participant_identity = next(iter(room.remote_participants))
    try:
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="addToCart",
            payload=json.dumps({}),
            response_timeout=10.0,
        )
        if not response:
            raise ToolError("Failed to add item to cart")

        return (
            Assistant(chat_ctx=chat_ctx),
            f"the order has been successfully completed for {product_name},",
        )

    except Exception as e:
        raise ToolError(
            "An error occurred while attempting to add the item to cart"
        ) from e


async def exit_ordering_task_impl(
    chat_ctx: ChatContext, product_name: str, exist_reason: str
):
    from src.agent.agents.assistant import Assistant

    # Complete the task with the cancellation result
    return (
        Assistant(chat_ctx=chat_ctx),
        f"User exited customization for {product_name}, reason fot the user's exit {exist_reason}",
    )



async def end_session_impl(context: RunContext):
    try:
        await context.session.generate_reply(
            instructions=(
                "We are ending the session right now, say goodbye!"
            )
        )
        context.session.shutdown()
    except Exception as e:
        raise ToolError("Failed to shutdown") from e
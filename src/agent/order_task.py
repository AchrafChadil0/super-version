import json
import logging
from typing import Any

from livekit.agents import AgentTask, RunContext, function_tool, get_job_context

from src.models.order_models import OrderResult, OrderState
from src.schemas.products import SyncResponse
from src.utils.tools import log_to_file

logger = logging.getLogger(__name__)


class OrderTask(AgentTask[OrderResult]):
    """
    A focused task for handling product customization and adding to cart.
    This task is designed to be handed control after the user has been
    redirected to a product page and its details have been fetched.
    """

    def __init__(
        self,
        product_type: str,
        product_name: str,
        product_details_summary: str,
        website_name: str,
        website_description: str,
        preferred_language: str,
        chat_ctx=None,
    ):
        """
        Initialize the OrderTask with the product details.
        """
        self.product_details_summary = product_details_summary
        self.product_type = product_type
        self.current_order: OrderState | None = None
        self.product_name: str = product_name
        self.website_name: str = website_name
        self.website_description: str = website_description
        self.preferred_language: str = preferred_language

        # Generate a dynamic, product-specific instruction for the LLM
        instructions = self._generate_instructions()

        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
        )

    def _generate_instructions(self) -> str:
        """
        Generate dynamic instructions for the LLM based on the product details.
        This is crucial for guiding the LML through the customization process.
        """
        base_instructions = f"""
You are a smart voice assistant for {self.website_name}
Language: ALWAYS respond in user's preferred_language {self.preferred_language} (ISO 639: {self.preferred_language}), if preferred_language was specified, just speak in the user's language, adapt with what ever language he speaks
Website: {self.website_description}

You are now in a temporary, focused ordering task for the product: **{self.product_name}**.
Your ONLY job is to help the user customize this specific product and add it to their cart.
Do NOT handle navigation, search, or unrelated requests. If the user asks to go back, look for something else, or seems unsure, use the `exit_ordering_task` tool.

Here are the product's customization options:
{self.product_details_summary}

YOUR TASK:
1.  Guide the user through customizing their product using the tools provided.
2.  Start by summarizing the product and its base price.
3.  Then, go through each option group one by one.
    - For each group, present 2-3 popular or default options first.
    - Ask the user what they would like for that group.
    - If they ask for "more options," list additional ones.
    - If they say "skip" or "next," move to the next group.
    - Always respect the min/max constraints for each group.
4.  After all groups are processed, summarize the user's selections and the total price.
5.  Ask the user to confirm if they want to add this customized item to their cart.
6.  If at ANY POINT the user indicates they want to stop, go back, or look for something else, use the `exit_ordering_task` tool.

AVAILABLE TOOLS (USE THEM AS NEEDED):
- `sync_order_options()`: ALWAYS call this first to get the user's current selections from the frontend. Call it again after any change.
- `select_option(group_id, option_id)`: Use when the user wants to add a specific option.
- `unselect_option(group_id, option_id)`: Use when the user wants to remove a specific option.
- `increase_product_quantity()`: Use when the user wants more of this item.
- `decrease_product_quantity()`: Use when the user wants less of this item.
- `complete_order()`: Call this tool ONLY when the user explicitly confirms they want to add the item to their cart. This will end the task.
- `exit_ordering_task(exist_reason)`: Call this tool when the user wants to STOP and return to the main assistant (e.g., "never mind", "go back", "look for something else"). This will cancel the order and return control.

CRITICAL RULES:
- NEVER list all options in a group if there are more than 3-4. Start with the most popular.
- ALWAYS mention the price for paid options.
- ALWAYS call `sync_order_options()` before answering any question about the user's current selections.
- Be conversational and patient. Let the user control the pace.
- YOU HAVE NO MEMORY OF PREVIOUS SELECTIONS. ALWAYS sync before describing.
- Once the order is confirmed via `complete_order()`, OR if the user cancels via `exit_ordering_task`, the task will end and control will return to the main assistant.
- If the user asks ANYTHING unrelated to customizing THIS product (e.g., "where is the contact page?", "do you have pizza?", "what's your return policy?"), use `exit_ordering_task` immediately.
"""

        return base_instructions

    async def on_enter(self) -> None:
        """
        Called when the task starts. Begin the customization dialogue.
        """
        await self.session.generate_reply(
            instructions=f"Start by welcoming the user to customize the '{self.product_name}'. Summarize its base details and begin guiding them through the first option group."
        )

    @function_tool()
    async def sync_order_options(self, context: RunContext):
        """ALWAYS call this before answering questions about user's selected options."""
        room = get_job_context().room
        if not room.remote_participants:
            return {"success": False, "error": "No participants to redirect"}
        participant_identity = next(iter(room.remote_participants))
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="syncProductOptions",
            payload=json.dumps({}),
            response_timeout=15.0,
        )
        if not response:
            return {"success": False, "error": "Empty RPC response"}
        order_data: SyncResponse = json.loads(response)
        self.current_order = OrderState.from_sync_response(order_data)
        log_to_file(
            "OrderTask.sync_order_options(), self.current_order.to_summary()",
            self.current_order.to_summary(),
        )
        return {"success": True, "summary": self.current_order.to_summary()}

    @function_tool()
    async def increase_product_quantity(self, context: RunContext) -> dict[str, Any]:
        """Call when the user wants to increase the quantity."""
        room = get_job_context().room
        if not room.remote_participants:
            return {
                "success": False,
                "error": "No participants available to update quantity",
            }
        participant_identity = next(iter(room.remote_participants))
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="increaseProductQuantity",
            payload=json.dumps(
                {
                    "product_type": (
                        "basic" if self.product_type == "variant" else self.product_type
                    )
                }
            ),
            response_timeout=10.0,
        )
        log_to_file("OrderTask.increase_product_quantity(): response", response)
        if not response:
            return {"success": False, "error": "Failed to update product quantity"}
        # Sync to update local state
        # await self.sync_order_options(context)
        return {"message": response}

    @function_tool()
    async def decrease_product_quantity(self, context: RunContext) -> dict[str, Any]:
        """Call when the user wants to decrease the quantity."""
        room = get_job_context().room
        if not room.remote_participants:
            return {
                "success": False,
                "error": "No participants available to update quantity",
            }
        participant_identity = next(iter(room.remote_participants))
        response = await room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="decreaseProductQuantity",
            payload=json.dumps(
                {
                    "product_type": (
                        "basic" if self.product_type == "variant" else self.product_type
                    )
                }
            ),
            response_timeout=10.0,
        )
        log_to_file("OrderTask.decrease_product_quantity(): response", response)
        if not response:
            return {"success": False, "error": "Failed to update product quantity"}
        # Sync to update local state
        # await self.sync_order_options(context)
        return {"message": response}

    @function_tool()
    async def select_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
        """Select an option in the current product customization."""
        try:
            room = get_job_context().room
            if not room.remote_participants:
                return {"success": False, "error": "No participants available"}
            participant_identity = next(iter(room.remote_participants))
            payload = json.dumps(
                {
                    "group_id": group_id,
                    "option_id": option_id,
                    "action": "select",
                    "product_type": (
                        "basic" if self.product_type == "variant" else self.product_type
                    ),
                }
            )
            response = await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="toggleOptionSelection",
                payload=payload,
                response_timeout=10.0,
            )
            log_to_file("OrderTask.select_option(): response", response)
            if not response:
                return {"success": False, "error": "No response from frontend"}
            # Sync to update local state
            # await self.sync_order_options(context)
            return {"message": response, "group_id": group_id, "option_id": option_id}
        except Exception as e:
            return {"success": False, "error": f"Failed to select option: {str(e)}"}

    @function_tool()
    async def unselect_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
        """Unselect an option in the current product customization."""
        try:
            room = get_job_context().room
            if not room.remote_participants:
                return {"success": False, "error": "No participants available"}
            participant_identity = next(iter(room.remote_participants))
            payload = json.dumps(
                {
                    "group_id": group_id,
                    "option_id": option_id,
                    "action": "unselect",
                    "product_type": self.product_type,
                }
            )
            response = await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="toggleOptionSelection",
                payload=payload,
                response_timeout=15.0,
            )
            log_to_file("OrderTask.unselect_option(): response", response)
            if not response:
                return {"success": False, "error": "No response from frontend"}
            # Sync to update local state
            # await self.sync_order_options(context)
            return {"message": response, "group_id": group_id, "option_id": option_id}
        except Exception as e:
            return {"success": False, "error": f"Failed to unselect option: {str(e)}"}

    @function_tool()
    async def complete_order(self, context: RunContext) -> None:
        """
        Call this tool when the user confirms they want to add the item to their cart.
        This will finalize the task and return control to the main agent.
        """
        room = get_job_context().room
        if not room.remote_participants:
            self.complete(
                OrderResult(message="No participants available to add to cart")
            )
            return

        participant_identity = next(iter(room.remote_participants))
        try:
            response = await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="addToCart",
                payload=json.dumps({}),
                response_timeout=10.0,
            )
            if not response:
                self.complete(
                    OrderResult(
                        message="Failed to add item to cart",
                        product_name=self.product_name,
                    )
                )
                return

            result = OrderResult(
                message=response,  # You can parse this for a user-friendly message
                product_name=self.product_name,
            )
            self.complete(result)

        except Exception as e:
            logger.error(f"Error in complete_order: {e}")
            self.complete(
                OrderResult(
                    message="An error occurred while attempting to add the item to cart",
                    product_name=self.product_name,
                )
            )

    # Inside your OrderTask class in order_task.py

    @function_tool()
    async def exit_ordering_task(self, exist_reason: str) -> None:
        """
        Args:
            exist_reason (str): the reason why the user want to exit the ordering task
        Use this tool when the user wants to STOP customizing this product and return to the main assistant.
        Call this when the user says things like:
        - "Never mind"
        - "I changed my mind"
        - "Go back"
        - "I want to look for something else"
        - "Cancel this"
        - "Take me back"
        - "I'm not ready to order this"
        - "Actually, I have a question about something else"
        Effect:
          1. Gracefully exits this ordering task.
          2. Returns control to the main SimpleAssistant agent.
          3. Does NOT add anything to the cart.
        Important: Always confirm with the user before calling this tool if their intent is ambiguous.
        Example:
          User: "Actually, I want to see if you have a veggie burger instead."
          You: "Sure, I'll take you back so you can search for other options." → [exit_ordering_task]
        """
        # Create a cancellation result
        result = OrderResult(
            message=f"User exited customization for {self.product_name} without adding to cart.",
            product_name=self.product_name,
            # You can add a field like `cancelled=True` to your OrderResult dataclass if you want to track this explicitly
        )
        # Complete the task with the cancellation result
        self.complete(result)

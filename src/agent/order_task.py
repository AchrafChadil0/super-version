import json
import logging
from typing import Any

from livekit.agents import AgentTask, RunContext, function_tool, get_job_context, Agent, ToolError

from src.agent.tools import SYNC_ORDER_OPTIONS, INCREASE_PRODUCT_QUANTITY, DECREASE_PRODUCT_QUANTITY, SELECT_OPTION, \
    UNSELECT_OPTION, COMPLETE_ORDER
from src.agent.tools.configs import EXIT_ORDERING_TASK
from src.models.order_models import OrderResult, OrderState
from src.schemas.products import SyncResponse, ProductType
from src.utils.tools import log_to_file

logger = logging.getLogger(__name__)


class OrderTask(Agent):
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
You are a focused, friendly voice assistant for **{self.website_name}**, currently helping the user customize one specific product:  
**“{self.product_name}”**.

---

### Language & Tone
- Always respond in the user’s language (detected or specified as `{self.preferred_language}`).
- Use a warm, patient, conversational tone—like a helpful store associate.
- Avoid robotic, formal, or repetitive phrasing.

---

### Your Role (Strict Scope)
Your only job is to:
1. Guide the user through customizing this exact product.
2. Help them select options (including “no X” choices like “SANS FROMAGE” or “without cheese”), adjust quantity, and confirm adding it to their cart.

Never:
- Answer general questions (e.g., “What’s your return policy?”).
- Handle navigation (“Take me to contact”), search (“Do you have pizza?”), or unrelated topics.
- Suggest other products or alternatives.

If the user says anything off-topic, wants to go back, or seems unsure (e.g., “never mind”, “I changed my mind”, “show me something else”), immediately call `exit_ordering_task` with a clear reason.

---

### Customization Flow

#### Step 1: Warm Welcome
“Great choice! You’re customizing the **{self.product_name}**. It starts at [base price]. Let’s personalize it together!”

#### Step 2: Walk Through Option Groups
For each customization group (e.g., Toppings, Size, Add-ons):
- Present 2–3 most popular or default options first.
- Always include price impact for paid options (e.g., “+ $1.50”).
- Ask: “What would you like for [group name]?”

User says:
- “More options” → List 2–3 additional choices.
- “Skip” or “Next” → Move to the next group.
- “I want it without cheese”, “SANS OIGNON”, “no bacon” → Treat this as selecting a “no X” option (e.g., “SANS FROMAGE”) → use `select_option`.
- “Remove bacon”, “take off the onions”, “I don’t want cheese anymore” → Only if X was already selected → use `unselect_option`.

Respect min/max rules (e.g., “Choose 1 size”, “Pick up to 3 toppings”).

Key distinction:  
- “Without X” = select the “no X” option (it’s a valid choice in the UI).  
- “Remove X” = unselect X (only if it was previously added).

#### Step 3: Final Summary
“You’ve selected: [Option A], [Option B]… Total: $X.XX for [quantity] item(s).”  
“Would you like to add this to your cart?”

#### Step 4: Final Action
- User confirms (e.g., “Yes, add it”) → Call `complete_order()`.
- User hesitates, declines, or changes mind → Call `exit_ordering_task`.

---

### Tool Usage Rules (Non-Negotiable)

| Tool | When to Use |
|------|-------------|
| `sync_order_options()` | ALWAYS call first on entry, and before describing current selections. You have no memory—sync every time! |
| `select_option(group_id, option_id)` | When user chooses any visible option—including “no cheese”, “SANS FROMAGE”, “large size”, etc. |
| `unselect_option(group_id, option_id)` | Only when user wants to remove an option that was already selected (e.g., “take off the bacon”). |
| `increase_product_quantity()` | On clear request: “two of these”, “I want more”. |
| `decrease_product_quantity()` | On clear request: “just one”, “reduce to one”. |
| `complete_order()` | ONLY after explicit confirmation like “Go ahead” or “Add to cart”. |
| `exit_ordering_task(exit_reason)` | For any off-topic, cancellation, or navigation request. |

---

### Critical Guardrails
- Never list more than 4 options at once—start with top picks.
- Always sync before summarizing—never assume state.
- Never ask “Would you like to see options?”—you’re already in the product!
- Never suggest or prompt customizations for products that are not listed in product_details. Only the customizations explicitly mentioned in product_details are allowed 
- If in doubt, exit gracefully—don’t force the flow.

---

### Product Details
{self.product_details_summary}

---

Now begin by welcoming the user and summarizing the base product.
"""

        return base_instructions

    async def on_enter(self) -> None:
        """
        Called when the task starts. Begin the customization dialogue.
        """
        await self.session.generate_reply(
            instructions=f"Start by welcoming the user to customize the '{self.product_name}'. Summarize its base details and begin guiding them through the first option group."
        )

    @function_tool(
        name=SYNC_ORDER_OPTIONS.name,
        description=SYNC_ORDER_OPTIONS.to_description()
    )
    async def sync_order_options(self, context: RunContext):
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

    @function_tool(
        name=INCREASE_PRODUCT_QUANTITY.name,
        description=INCREASE_PRODUCT_QUANTITY.to_description(),
    )
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
                        "basic" if self.product_type ==  ProductType.VARIANT else self.product_type
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

    @function_tool(
        name=DECREASE_PRODUCT_QUANTITY.name,
        description=DECREASE_PRODUCT_QUANTITY.to_description(),
    )
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
                        "basic" if self.product_type == ProductType.VARIANT else self.product_type
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

    @function_tool(
        name=SELECT_OPTION.name,
        description=SELECT_OPTION.to_description(),
    )
    async def select_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
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
                        "basic" if self.product_type == ProductType.VARIANT else self.product_type
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

    @function_tool(
        name=UNSELECT_OPTION.name,
        description=UNSELECT_OPTION.to_description(),
    )
    async def unselect_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
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

    @function_tool(
        name=COMPLETE_ORDER.name,
        description=COMPLETE_ORDER.to_description(),
    )
    async def complete_order(self, context: RunContext):
        from src.agent.assistant import Assistant
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

            return Assistant(chat_ctx=self.chat_ctx), f"the order has been successfully completed for {self.product_name},"

        except Exception as e:
            logger.error(f"Error in complete_order: {e}")
            raise ToolError("An error occurred while attempting to add the item to cart")

    # Inside your OrderTask class in order_task.py

    @function_tool(
        name=EXIT_ORDERING_TASK.name,
        description=EXIT_ORDERING_TASK.to_description(),
    )
    async def exit_ordering_task(self, exist_reason: str):
        from src.agent.assistant import Assistant
        # Complete the task with the cancellation result
        return Assistant(chat_ctx=self.chat_ctx), f"User exited customization for {self.product_name}, reason fot the user's exit {exist_reason}"

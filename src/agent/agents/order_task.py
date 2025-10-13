import logging
from pprint import pprint
from typing import Any

from livekit.agents import Agent, RunContext, function_tool

from src.agent.state_manager import PerJobState
from src.agent.tools import (
    COMPLETE_ORDER,
    DECREASE_PRODUCT_QUANTITY,
    EXIT_ORDERING_TASK,
    INCREASE_PRODUCT_QUANTITY,
    SELECT_OPTION,
    SYNC_ORDER_OPTIONS,
    UNSELECT_OPTION,
    complete_order_impl,
    decrease_product_quantity_impl,
    exit_ordering_task_impl,
    increase_product_quantity_impl,
    select_option_impl,
    unselect_option_impl, END_SESSION,
)
from src.agent.tools.implementations import sync_order_options_impl
from src.schemas.products import ProductType

logger = logging.getLogger(__name__)


class OrderTask(Agent):
    """
    A focused task for handling product customization and adding to cart.
    This task is designed to be handed control after the user has been
    redirected to a product page and its details have been fetched.
    """

    def __init__(
        self,
        product_type: ProductType,
        product_name: str,
        product_details_summary: str,
        website_name: str,
        website_description: str,
        preferred_language: str,
        state: PerJobState,
        chat_ctx=None,
    ):
        """
        Initialize the OrderTask with the product details.
        """
        self.product_details_summary = product_details_summary
        self.product_type: ProductType = product_type
        self.product_name: str = product_name
        self.website_name: str = website_name
        self.website_description: str = website_description
        self.preferred_language: str = preferred_language
        self.state: PerJobState = state

        # Generate a dynamic, product-specific instruction for the LLM
        instructions = self._generate_instructions()

        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        """
        Called when the task starts. Begin the customization dialogue.
        """
        await self.session.generate_reply(
            instructions=f"assist the user his product {self.product_name},  details: {self.product_details_summary}"
        )

    @function_tool(
        name=SYNC_ORDER_OPTIONS.name, description=SYNC_ORDER_OPTIONS.to_description()
    )
    async def sync_order_options(self, context: RunContext):
        return await sync_order_options_impl(context=context)

    @function_tool(
        name=INCREASE_PRODUCT_QUANTITY.name,
        description=INCREASE_PRODUCT_QUANTITY.to_description(),
    )
    async def increase_product_quantity(self, context: RunContext) -> dict[str, Any]:
        return await increase_product_quantity_impl(
            product_type=self.product_type, context=context
        )

    @function_tool(
        name=DECREASE_PRODUCT_QUANTITY.name,
        description=DECREASE_PRODUCT_QUANTITY.to_description(),
    )
    async def decrease_product_quantity(self, context: RunContext) -> dict[str, Any]:
        return await decrease_product_quantity_impl(
            product_type=self.product_type, context=context
        )

    # -----
    @function_tool(
        name=SELECT_OPTION.name,
        description=SELECT_OPTION.to_description(),
    )
    async def select_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
        return await select_option_impl(
            product_type=self.product_type,
            group_id=group_id,
            option_id=option_id,
            context=context,
        )

    @function_tool(
        name=UNSELECT_OPTION.name,
        description=UNSELECT_OPTION.to_description(),
    )
    async def unselect_option(
        self, context: RunContext, group_id: int, option_id: int
    ) -> dict[str, Any]:
        return await unselect_option_impl(
            product_type=self.product_type,
            group_id=group_id,
            option_id=option_id,
            context=context,
        )

    @function_tool(
        name=COMPLETE_ORDER.name,
        description=COMPLETE_ORDER.to_description(),
    )
    async def complete_order(self, context: RunContext):
        return await complete_order_impl(
            chat_ctx=self.chat_ctx, product_name=self.product_name, context=context
        )

    @function_tool(
        name=EXIT_ORDERING_TASK.name,
        description=EXIT_ORDERING_TASK.to_description(),
    )
    async def exit_ordering_task(self, exist_reason: str):
        return await exit_ordering_task_impl(
            chat_ctx=self.chat_ctx,
            product_name=self.product_name,
            exist_reason=exist_reason,
            state=self.state
        )

    @function_tool(
        name=END_SESSION.name,
        description=END_SESSION.to_description(),
    )
    async def end_session(self, context: RunContext):
        from src.agent.tools.implementations import end_session_impl
        return await end_session_impl(context=context, job_context=self.state.job_context)
    def _generate_instructions(self) -> str:
        """
        Generate dynamic instructions for the LLM based on the product details.
        This is crucial for guiding the LML through the customization process.
        """
        base_instructions = f"""
    You are a focused, friendly voice assistant for **{self.website_name}**, currently helping the user customize one specific product:
    **“{self.product_name}”**.


    CRITICAL: The user ALREADY SELECTED this product. Don't second-guess their choice!
    
    If they originally said "I want a burger" and you're now on "PICKS BRGR" - THAT'S THE BURGER THEY WANTED!
    Don't exit thinking they want a different burger. This IS their burger.
    
    ONLY exit if they give you a NEW instruction like:
    - "Actually, show me pizza"  
    - "Cancel this"
    - "I changed my mind"
    
    NEVER exit because their original request seems "general" - it was already resolved by selecting THIS product.
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

    If the user says anything off-topic, wants to go back, or seems unsure (e.g., “never mind”, “I changed my mind”, “show me something else”),
    immediately call `exit_ordering_task` with a clear reason.

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
    - Never suggest or prompt customizations for products that are not listed in product_details.
    Only the customizations explicitly mentioned in product_details are allowed
    - If in doubt, exit gracefully—don’t force the flow.

    ---

    ### Product Details
    {self.product_details_summary}

    ---

    Now begin by welcoming the user and summarizing the base product.
    """

        return base_instructions

import logging
from typing import Any

from livekit.agents import Agent, RunContext, function_tool
from livekit.plugins import openai

from src.agent.state_manager import PerJobState
from src.agent.tools import (
    COMPLETE_ORDER,
    DECREASE_PRODUCT_QUANTITY,
    EXIT_ORDERING_TASK,
    INCREASE_PRODUCT_QUANTITY, END_SESSION
)
from src.schemas.products import ProductType

logger = logging.getLogger(__name__)


class BasicOrderTask(Agent):
    """
    A focused task for handling basic products that cannot be customized.
    This task handles quantity selection and adding to cart for products
    without customization options.
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
        Initialize the BasicOrderTask with the product details.
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
        Called when the task starts. Begin the order dialogue.
        """
        await self.session.generate_reply(
            instructions=f"Help the user order {self.product_name}. Details: {self.product_details_summary}"
        )

    @function_tool(
        name=INCREASE_PRODUCT_QUANTITY.name,
        description=INCREASE_PRODUCT_QUANTITY.to_description(),
    )
    async def increase_product_quantity(self, context: RunContext) -> dict[str, Any]:
        from src.agent.tools.implementations import increase_product_quantity_impl
        return await increase_product_quantity_impl(
            product_type=self.product_type, context=context
        )

    @function_tool(
        name=DECREASE_PRODUCT_QUANTITY.name,
        description=DECREASE_PRODUCT_QUANTITY.to_description(),
    )
    async def decrease_product_quantity(self, context: RunContext) -> dict[str, Any]:
        from src.agent.tools.implementations import decrease_product_quantity_impl
        return await decrease_product_quantity_impl(
            product_type=self.product_type, context=context
        )

    @function_tool(
        name=COMPLETE_ORDER.name,
        description=COMPLETE_ORDER.to_description(),
    )
    async def complete_order(self, context: RunContext):
        from src.agent.tools.implementations import complete_order_impl
        return await complete_order_impl(
            chat_ctx=self.chat_ctx, product_name=self.product_name, context=context
        )

    @function_tool(
        name=EXIT_ORDERING_TASK.name,
        description=EXIT_ORDERING_TASK.to_description(),
    )
    async def exit_ordering_task(self, exit_reason: str):
        from src.agent.tools.implementations import exit_ordering_task_impl
        return await exit_ordering_task_impl(
            chat_ctx=self.chat_ctx,
            product_name=self.product_name,
            exist_reason=exit_reason,
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
        """
        base_instructions = f"""
    You are a focused, friendly voice assistant for **{self.website_name}**, currently helping the user customize one specific product:
    **“{self.product_name}”**.


    CRITICAL: The user ALREADY SELECTED this product. Don't second-guess their choice!
    
    If they originally said "I want a PEPSI" and you're now on "PEPSI" - THAT'S THE PEPSI THEY WANTED!
    Don't exit thinking they want a different Product. This IS their product.
    
    ONLY exit if they give you a NEW instruction like:
    - "Actually, show me pizza"  
    - "Cancel this"
    - "I changed my mind"
    
    NEVER exit because their original request seems "general" - it was already resolved by selecting THIS product.
---

### Language & Tone
- Always respond in the user's language (detected or specified as `{self.preferred_language}`).
- Use a warm, efficient, conversational tone—like a helpful store associate.
- Avoid robotic, formal, or repetitive phrasing.

---

### Your Role (Strict Scope)
Your only job is to:
1. Confirm the product selection with the user.
2. Help them choose the quantity.
3. Add the item to their cart upon confirmation.

Never:
- Answer general questions (e.g., "What's your return policy?").
- Handle navigation ("Take me to contact"), search ("Do you have pizza?"), or unrelated topics.
- Suggest other products or alternatives.
- Offer or discuss customization options—this product comes as-is.

If the user says anything off-topic, wants to go back, or seems unsure (e.g., "never mind", "I changed my mind", "show me something else"),
immediately call `exit_ordering_task` with a clear reason.

---

### Order Flow

#### Step 1: Warm Welcome & Confirmation
"Great choice! You've selected the **{self.product_name}** at [price]. How many would you like?"

#### Step 2: Quantity Selection
- Default to 1 item.
- If user requests more: "two of these", "I want three" → Call `increase_product_quantity()`.
- If user wants fewer: "just one", "reduce to one" → Call `decrease_product_quantity()`.

#### Step 3: Final Summary
"Perfect! That's [quantity] x **{self.product_name}** for a total of $X.XX."
"Ready to add this to your cart?"

#### Step 4: Final Action
- User confirms (e.g., "Yes", "Add it", "Go ahead") → Call `complete_order()`.
- User hesitates, declines, or changes mind → Call `exit_ordering_task` with reason.

---

### Tool Usage Rules (Non-Negotiable)

| Tool | When to Use |
|------|-------------|
| `increase_product_quantity()` | On clear request: "two of these", "I want more", "make it three". |
| `decrease_product_quantity()` | On clear request: "just one", "reduce to one", "only one". |
| `complete_order()` | ONLY after explicit confirmation like "Yes", "Add to cart", "Go ahead". |
| `exit_ordering_task(exit_reason)` | For any off-topic, cancellation, or navigation request. |

---

### Critical Guardrails
- Keep it simple and fast—this is a basic product with no customization.
- Never mention or offer customization options.
- Never ask about size, toppings, or any modifications.
- Focus only on quantity and confirmation.
- If user asks about customization, politely explain: "This item comes as-is, but I can help you choose how many you'd like!"
- If in doubt, exit gracefully—don't force the flow.

---

### Product Details
{self.product_details_summary}

---

Now begin by welcoming the user and asking about quantity.
"""

        return base_instructions
"""
All tool configurations for the Agent.
Add new tools here
"""

from . import ToolConfig

# ============================================
# PRODUCT SEARCH TOOLS
# ============================================

SEARCH_PRODUCTS = ToolConfig(
    name="search_products",
    purpose="Search for products in the database using semantic matching.",
    when_to_use="Call immediately when user mentions any product name, brand, category, or makes a product-related request.",
    parameters={
        "query": "The user's exact search terms (e.g., 'nike shoes', 'burger', 'laptop')",
        "max_results": "Always set to 2 (default)",
    },
    execution_notes=[
        "Tool takes 2-3 seconds to execute",
        "Say to user: 'One moment while I search for [their request]'",
        "Maintain conversational tone during wait",
    ],
    behavior_steps=[
        "Performs semantic search against product database",
        "Returns products ranked by similarity_score (0.0 = no match, 1.0 = perfect match)",
        "Each result includes: name, id, redirect_url, similarity_score",
    ],
    critical_rules=[
        "If highest similarity_score >= 0.4: Immediately redirect to that product WITHOUT asking",
        "If highest similarity_score < 0.4: Tell user no close match found, suggest trying different keywords",
        "NEVER present multiple options for user to choose between",
        "NEVER ask for confirmation before redirecting",
    ],
    examples=[
        'User: "I want Adidas sneakers"\n→ Call: search_products(query="Adidas sneakers", max_results=2)\n→ If score >= 0.4: '
        '"I found [name]. Taking you there now!"\n→ Then redirect immediately',
        'User: "Show me burgers"\n→ Call: search_products(query="burgers", max_results=2)\n→ Redirect to highest-scoring result',
        'User: "Looking for a laptop"\n→ Call: search_products(query="laptop", max_results=2)\n→ If score < 0.4: "I couldn\'t find a close match. '
        "Try 'gaming laptop' or 'business laptop'?\"",
    ],
)

# ============================================
# NAVIGATION TOOLS
# ============================================

# configs.py

REDIRECT_TO_PRODUCT_PAGE = ToolConfig(
    name="redirect_to_product_page",
    purpose="Navigate the user to a product page and fetch its complete details.",
    when_to_use=(
        "Call immediately after search_products returns a product with redirect_url, "
        "product_id, and product_type. Use this ONLY for products, NOT for general website pages."
    ),
    parameters={
        "redirect_url": "Exact product page URL from search_products results",
        "product_id": "Unique product identifier (integer) from search_products",
        "product_type": "Product type enum: 'basic', 'variant', or 'customizable' (from search results)",
    },
    execution_notes=[
        "Tool takes 2-3 seconds (redirect + API fetch)",
        "Say to user: 'Taking you to [product name] now!' or 'Opening [product name]!'",
        "Product details are automatically fetched based on product_type",
        "Different product types return different detail structures",
    ],
    behavior_steps=[
        "Validates that remote participants exist in the room",
        "Sends RPC command 'redirectToPage' to user's browser",
        "Browser navigates to the product page",
        "Fetches product details from API based on product_type:",
        "Returns success with URL and full product details",
    ],
    response_format={
        "success": "boolean - True if redirect and fetch succeeded",
        "redirected_to": "string - Full product page URL",
        "product_details": "dict - Complete product data (structure varies by product_type)",
    },
    critical_rules=[
        "NEVER ask 'Would you like to see this product?' - redirect immediately",
        "MUST pass all three parameters: redirect_url, product_id, AND product_type",
        "Product_type MUST be one of: 'basic', 'variant', 'customizable' (case-sensitive)",
        "Use exact values from search_products - don't guess or modify them",
        "This tool is ONLY for products - use redirect_to_website_page for other pages",
        "If no participants in room, raises ToolError automatically",
        "If invalid product_type passed, raises ValueError",
    ],
    examples=[
        'User: "Show me Nike shoes"\n'
        '→ search_products(query="Nike shoes") returns:\n'
        '   {redirect_url: "https://site.com/nike", product_id: 123, product_type: "basic"}\n'
        "→ redirect_to_product_page(\n"
        '     redirect_url="https://site.com/nike",\n'
        "     product_id=123,\n"
        '     product_type="basic"\n'
        "   )\n"
        '→ Say: "Taking you to Nike Air Max now!"\n'
        "→ Product details automatically loaded",
        "After search finds variant product:\n"
        "→ redirect_to_product_page(\n"
        "     redirect_url=<from_search>,\n"
        "     product_id=<from_search>,\n"
        '     product_type="variant"  ← Note: different type\n'
        "   )\n"
        "→ Fetches variant-specific details (sizes, colors, etc.)",
        "After search finds customizable product:\n"
        "→ redirect_to_product_page(\n"
        "     redirect_url=<from_search>,\n"
        "     product_id=<from_search>,\n"
        '     product_type="customizable"  ← Custom options\n'
        "   )\n"
        "→ Fetches customization options (toppings, add-ons, etc.)",
        "Standard product flow:\n"
        "1. User mentions product\n"
        "2. search_products() returns {redirect_url, product_id, product_type}\n"
        "3. redirect_to_product_page() with ALL THREE parameters\n"
        "4. User sees page + you get full product details to discuss",
    ],
)

REDIRECT_TO_WEBSITE_PAGE = ToolConfig(
    name="redirect_to_website_page",
    purpose="Navigate the user to a general website page (menu, about, contact, etc.).",
    when_to_use=(
        "Call immediately after find_website_page returns a page URL, or when user "
        "requests navigation to non-product pages (home, menu, categories, about, contact)."
    ),
    parameters={
        "redirect_url": "Exact page URL of the page that the user want's",
    },
    execution_notes=[
        "Redirect happens instantly via RPC call",
        "Say to user: 'Opening the [page name] now!' or 'Taking you to [page]!'",
        "No additional data fetch needed after redirect",
        "Tool takes ~1 second to execute",
    ],
    behavior_steps=[
        "Validates that remote participants exist in the room",
        "Sends RPC command 'redirectToPage' to user's browser",
        "Browser navigates to the specified page",
        "Returns success confirmation with final URL",
    ],
    response_format={
        "success": "boolean - True if redirect sent",
        "redirected_to": "string - Full page URL",
    },
    critical_rules=[
        "NEVER ask 'Would you like to go there?' - redirect immediately",
        "Use this for ALL non-product pages (menu, categories, about, contact, home)",
        "For products, use redirect_to_product_page instead",
        "If no participants in room, raises ToolError automatically",
    ],
    examples=[
        'User: "Show me the menu"\n'
        '→ find_website_page(query="menu") returns redirect_url\n'
        '→ redirect_to_website_page(redirect_url)\n'
        '→ Say: "Opening the menu now!"',
        'User: "Take me to the about page"\n'
        '→ redirect_to_website_page(redirect_url)\n'
        '→ Say: "Taking you to our About page!"',
        'User: "Go back to home"\n'
        '→ redirect_to_website_page(redirect_url)\n'
        '→ Say: "Heading to the homepage!"',
    ],
)


"""
All tool configurations for the Agent.
Add new tools here
"""


# ============================================
# ORDER TASK TOOLS (used inside OrderTask agent)
# ============================================

SYNC_ORDER_OPTIONS = ToolConfig(
    name="sync_order_options",
    purpose="Fetch the user's current product customization selections from the frontend.",
    when_to_use=(
        "call this when the user ask any question about the user's current selections, total price, or chosen options."
    ),
    parameters={},
    execution_notes=[
        "Takes ~1 second to sync state from browser",
        "Updates internal order state with real-time selections",
        "Required before summarizing or confirming order",
    ],
    behavior_steps=[
        "Sends RPC 'syncProductOptions' to frontend",
        "Receives current selections, quantity, and total price",
        "Parses response into structured OrderState",
        "Returns human-readable summary of current configuration",
    ],
    response_format={
        "success": "boolean - True if sync succeeded",
        "summary": "string - Natural language summary of current selections and total",
    },
    critical_rules=[
        "MUST be called before describing user's current choices",
        "Never assume prior state — always sync first",
        "If sync fails, inform user and retry once",
    ],
    examples=[
        "On task start: → sync_order_options() → 'You currently have: Classic Burger, no onions, extra cheese. Total: $12.50'",
        "User: 'What did I pick so far?' → sync_order_options() → respond with summary",
    ],
)

SELECT_OPTION = ToolConfig(
    name="select_option",
    purpose="Add a specific customization option to the user's product — including 'no X' options like 'SANS FROMAGE', 'NO CHEESE', etc.",
    when_to_use=(
        "When the user explicitly chooses ANY option — positive (e.g., 'add bacon') OR negative (e.g., 'without cheese', 'SANS OIGNION'). "
        "Treat all visible options in the UI as valid selections, even if they mean exclusion."
    ),
    parameters={
        "group_id": "Integer ID of the option group (e.g., 1 for 'Toppings', 2 for 'Size')",
        "option_id": "Integer ID of the specific option within the group — including 'no X' options",
    },
    execution_notes=[
        "Sends selection to frontend via 'toggleOptionSelection'",
        "Frontend updates UI and recalculates price",
        "Does NOT auto-sync — call sync_order_options afterward if needed",
    ],
    behavior_steps=[
        "Validates group_id and option_id exist in product schema",
        "Sends RPC with action='select'",
        "Confirms selection was applied",
    ],
    response_format={
        "message": "string - Confirmation from frontend (e.g., 'Option added')",
        "group_id": "int - The group ID selected",
        "option_id": "int - The option ID selected",
    },
    critical_rules=[
        "Only call when user makes a clear selection — whether adding or excluding",
        "Never guess group_id/option_id — rely on product details from earlier",
        "Do not call if user says 'maybe' or is undecided",
        "If user says 'without X', find the corresponding 'no X' option in the group and select it — do NOT unselect unless X was already selected",
    ],
    examples=[
        'User: "Add extra cheese"\n→ select_option(group_id=3, option_id=12)\n→ "Added extra cheese (+$1.00)"',
        'User: "I want the spicy sauce"\n→ select_option(group_id=5, option_id=8)',
        'User: "I want it without cheese"\n→ select_option(group_id=3, option_id=15) ← where option_id=15 = "SANS FROMAGE"',
        'User: "SANS OIGNION please"\n→ select_option(group_id=3, option_id=17) ← assuming "SANS OIGNION" is option 17',
    ],
)
UNSELECT_OPTION = ToolConfig(
    name="unselect_option",
    purpose="Remove a previously selected customization option that the user now wants to cancel.",
    when_to_use=(
        "When the user wants to remove an option that was ALREADY selected (e.g., 'remove bacon', 'I don’t want that anymore', 'take off the onions')."
    ),
    parameters={
        "group_id": "Integer ID of the option group",
        "option_id": "Integer ID of the option to remove — must have been previously selected",
    },
    execution_notes=[
        "Sends 'unselect' action to frontend",
        "Useful for correcting mistakes or changing mind",
    ],
    behavior_steps=[
        "Sends RPC with action='unselect'",
        "Frontend removes option and updates total",
    ],
    response_format={
        "message": "string - Confirmation from frontend",
        "group_id": "int",
        "option_id": "int",
    },
    critical_rules=[
        "Only unselect if user explicitly requests removal AND the option was previously selected",
        "Do NOT unselect options just because user picks a different one in same group — let frontend handle exclusivity",
        "NEVER use unselect for 'I want without X' if X was never selected — use select_option with the 'no X' option instead",
    ],
    examples=[
        'User: "Actually, no bacon" ← if bacon was previously selected\n→ unselect_option(group_id=3, option_id=7)',
        'User: "I dont want cheese anymore" ← if cheese was selected\n→ unselect_option(group_id=3, option_id=12)',
        'User: "Take off the onions" ← if onions were selected\n→ unselect_option(group_id=3, option_id=9)',
    ],
)

INCREASE_PRODUCT_QUANTITY = ToolConfig(
    name="increase_product_quantity",
    purpose="Increase the quantity of the current product to be added to cart.",
    when_to_use="When user says 'two of these', 'make it three', 'I want more', etc.",
    parameters={},
    execution_notes=[
        "Sends 'increaseProductQuantity' RPC",
        "Frontend handles min/max validation",
    ],
    behavior_steps=[
        "Triggers +1 quantity increment in browser",
        "Updates displayed total",
    ],
    response_format={
        "message": "string - Frontend confirmation (e.g., 'Quantity: 2')",
    },
    critical_rules=[
        "Do not allow quantity to exceed frontend limits",
        "Always sync or ask frontend for new total if discussing price after change",
    ],
    examples=[
        'User: "I’ll take two"\n→ increase_product_quantity()',
    ],
)

DECREASE_PRODUCT_QUANTITY = ToolConfig(
    name="decrease_product_quantity",
    purpose="Decrease the quantity of the current product.",
    when_to_use="When user says 'just one', 'cancel one', 'reduce to one', etc.",
    parameters={},
    execution_notes=[
        "Sends 'decreaseProductQuantity' RPC",
        "Prevents quantity from going below 1",
    ],
    behavior_steps=[
        "Triggers -1 quantity decrement (min 1)",
    ],
    response_format={
        "message": "string - Updated quantity confirmation",
    },
    critical_rules=[
        "Never let quantity drop below 1",
    ],
    examples=[
        'User: "Actually, just one"\n→ decrease_product_quantity()',
    ],
)

COMPLETE_ORDER = ToolConfig(
    name="complete_order",
    purpose="Finalize and add the customized product to the user's cart.",
    when_to_use=(
        "ONLY when the user explicitly confirms they want to add the item to cart "
        "(e.g., 'Yes, add it', 'Go ahead', 'I’m ready to order')."
    ),
    parameters={},
    execution_notes=[
        "Sends 'addToCart' RPC to frontend",
        "Ends the OrderTask and returns control to main assistant",
        "Irreversible action — requires clear user intent",
    ],
    behavior_steps=[
        "Validates all required groups have selections (if applicable)",
        "Adds item to cart",
        "Returns success message",
    ],
    response_format={
        "status": "'success'",
        "action": "'added_to_cart'",
        "product": "string - Product name that was added",
    },
    critical_rules=[
        "NEVER call without explicit user confirmation",
        "Do not assume 'sounds good' or 'okay' is confirmation — ask: 'Shall I add it to your cart?'",
        "After this, the task ends and main assistant resumes",
    ],
    examples=[
        'User: "Yes, add it to my cart"\n→ complete_order()\n→ Task ends, main agent takes over',
    ],
)

EXIT_ORDERING_TASK = ToolConfig(
    name="exit_ordering_task",
    purpose="Cancel the current ordering task and return to the main assistant ONLY after user confirmation.",
    when_to_use=(
        "When user CLEARLY wants a completely different product after confirmation. "
        "Be aware of potential STT errors - if something seems out of context, clarify first. "
        "ALWAYS ASK FOR CONFIRMATION FIRST."
    ),
    parameters={
        "exit_reason": "Brief string explaining why user exited (for logging/analytics)",
    },
    execution_notes=[
        "This is a two-step process: ASK first, then EXIT only if confirmed",
        "Consider if request seems contextually odd before assuming user wants to leave",
        "Never exit without explicit user confirmation",
    ],
    behavior_steps=[
        "1. EVALUATE if request fits current customization context",
        "2. If request seems unrelated to current product, CLARIFY intent",
        "3. Check if mentioned item could be an option/variant vs completely different product",
        "4. ALWAYS CONFIRM before exiting",
        "5. Continue customization if user clarifies they meant an option",
    ],
    response_format={
        "status": "'cancelled'",
        "reason": "string - User-provided or inferred reason",
        "product": "string - Product name that was being customized",
    },
    critical_rules=[
        "If request seems out of context for current product:",
        "  - First CLARIFY what user meant",
        "  - Don't assume it's a different product",
        "  - Could be STT error or misunderstanding",
        "Pattern for clarification:",
        "  - 'I heard [X] - is that something you want to add to this [product], or did you want to look for something else?'",
        "  - 'Did you mean [X] as an option for your [current product]?'",
        "  - 'Just to clarify - are you customizing your [current product] or looking for a different item?'",
        "NEVER auto-exit on ambiguous requests",
        "ALWAYS require explicit confirmation to exit",
        "Single words out of context are often STT errors - always clarify",
    ],
    contextual_awareness=[
        "Consider if the request makes sense for the current product type",
        "Single unexpected words are often misrecognitions - clarify don't exit",
        "Check product's available options before assuming user wants different product",
        "If user mentions something that COULD be an option, ask if they meant it as customization",
    ],
    examples=[
        # Out of context word - Clarify
        'User (customizing product): "I want extra [unexpected word]"\n'
        '→ CLARIFY: "I heard [unexpected word] - could you clarify what you\'d like to add?"\n'
        '→ User clarifies their intent\n'
        '→ Proceed based on clarification',

        # Ambiguous request
        'User (customizing laptop): "Actually blue"\n'
        '→ CLARIFY: "Did you want the blue color option for this laptop?"\n'
        '→ User: "Yes, blue color"\n'
        '→ DO NOT EXIT - select blue option',

        # Clear different product
        'User (customizing shirt): "Forget this, show me pants"\n'
        '→ CONFIRM: "Would you like to cancel this shirt and look at pants instead?"\n'
        '→ User: "Yes please"\n'
        '→ exit_ordering_task(exit_reason="switching to pants")',

        # Unclear single word
        'User (customizing): Says single word that doesn\'t match any option\n'
        '→ CLARIFY: "Could you tell me more about what you\'d like?"\n'
        '→ Get clarification before considering exit',

        # Never assume
        '❌ WRONG: Auto-exit because word seems unrelated\n'
        '✓ RIGHT: Ask "I heard [word] - what would you like to do with your current order?"',

        # Context check
        'User customizing any product: "[word that could be option or new product]"\n'
        '→ ASK: "Is that something you want for your [current product], or were you looking for something else?"\n'
        '→ Let user clarify their intent',
    ],
)


# ============================================
# END SESSION TOOL
# ============================================
END_SESSION = ToolConfig(
    name="end_session",
    purpose="End the conversation session when the user wants to completely stop interacting with the assistant.",
    when_to_use=(
        "Call when user explicitly wants to end the entire conversation, not just exit a task. "
        "Examples: 'goodbye', 'I'm done', 'end chat', 'stop talking', 'close this', 'that's all', "
        "'I don't need anything else', 'thanks, bye', 'see you later'."
    ),
    parameters={
        "farewell_message": "Brief, friendly goodbye message to send before ending session (optional)",
    },
    execution_notes=[
        "This is a terminal action - session cannot be resumed",
        "Always send a polite farewell before shutting down",
        "Distinguish from exit_ordering_task (which returns to main assistant)",
        "Tool takes ~1 second to execute graceful shutdown",
    ],
    behavior_steps=[
        "Validates user intent to end entire session (not just current task)",
        "Sends farewell message to user",
    ],
    critical_rules=[
        "NEVER call for ambiguous phrases like 'ok' or 'thanks' without clear goodbye intent",
        "If user says 'goodbye' while in OrderTask, confirm: 'Do you want to end the order or end our chat entirely?'",
        "Always be polite - this is the user's last interaction",
        "Distinguish between: (1) exiting a task, (2) going back to browse, (3) ending session",
        "Do NOT call if user just finished an order and might want to order more",
    ],
    examples=[
        'User: "Goodbye"\n→ end_session(farewell_message="Goodbye! Thanks for shopping with us today!")',
        'User: "That\'s all I need, thanks"\n→ end_session(farewell_message="You\'re welcome! Have a great day!")',
        'User: "I\'m done here"\n→ end_session(farewell_message="Thanks for visiting! See you next time!")',
        'User: "Close this"\n→ end_session(farewell_message="Closing now. Have a wonderful day!")',
        'User: "Thanks, bye!" (after completing order)\n→ end_session(farewell_message="Thank you for your order! Goodbye!")',
        '❌ WRONG - User: "Thanks" (after adding to cart)\n→ DO NOT end session - user might want to order more\n→ Instead say: "You\'re welcome! Anything else I can help you find?"',
        '❌ WRONG - User in OrderTask: "I want to leave"\n→ DO NOT immediately end session\n→ First clarify: "Would you like to cancel this order, or end our conversation entirely?"',
    ],
)

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
        "redirect_url": "Exact page URL from find_website_page or known site structure",
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
        '→ redirect_to_website_page(redirect_url="https://site.com/menu")\n'
        '→ Say: "Opening the menu now!"',
        'User: "Take me to the about page"\n'
        '→ redirect_to_website_page(redirect_url="https://site.com/about")\n'
        '→ Say: "Taking you to our About page!"',
        'User: "Go back to home"\n'
        '→ redirect_to_website_page(redirect_url="https://site.com")\n'
        '→ Say: "Heading to the homepage!"',
    ],
)

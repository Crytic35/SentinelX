from typing import Dict, Any, List, Optional, Tuple

CAPABILITY_SEARCH_PRODUCTS = "search_products"
CAPABILITY_CART_MANAGEMENT = "cart_management"
CAPABILITY_INITIATE_PAYMENT = "initiate_merchant_payments"
CAPABILITY_VIEW_ORDERS = "view_orders"

KNOWN_CAPABILITIES = {
    CAPABILITY_SEARCH_PRODUCTS: "Search and retrieve products from catalog",
    CAPABILITY_CART_MANAGEMENT: "Add/remove items in user shopping cart",
    CAPABILITY_INITIATE_PAYMENT: "Submit payment intents for merchant transactions",
    CAPABILITY_VIEW_ORDERS: "Check historical order status and shipping"
}

def validate_agent_capabilities(capabilities: List[str]) -> Tuple[bool, List[str]]:
    """
    Validates whether all requested capabilities are recognized in SentinelX registry.
    """
    invalid = [c for c in capabilities if c not in KNOWN_CAPABILITIES]
    if invalid:
        return False, invalid
    return True, []

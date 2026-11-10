from typing import Dict, Any, Optional, Tuple, List

# Pre-seeded known trusted merchants in sandbox environment
TRUSTED_MERCHANTS: Dict[str, Dict[str, Any]] = {
    "merch_bestbuy_01": {
        "id": "merch_bestbuy_01",
        "name": "Best Buy Official",
        "domain": "bestbuy.com",
        "country": "US",
        "category": "electronics",
        "trust_score": 98.0,
        "is_verified": True
    },
    "merch_newegg_02": {
        "id": "merch_newegg_02",
        "name": "Newegg Electronics",
        "domain": "newegg.com",
        "country": "US",
        "category": "electronics",
        "trust_score": 96.0,
        "is_verified": True
    },
    "merch_barnesnoble_03": {
        "id": "merch_barnesnoble_03",
        "name": "Barnes & Noble",
        "domain": "barnesandnoble.com",
        "country": "US",
        "category": "books",
        "trust_score": 99.0,
        "is_verified": True
    },
    "merch_amazon_04": {
        "id": "merch_amazon_04",
        "name": "Amazon Marketplace",
        "domain": "amazon.com",
        "country": "US",
        "category": "electronics",
        "trust_score": 97.0,
        "is_verified": True
    }
}

class MerchantSecurityService:
    @staticmethod
    def verify_merchant(
        merchant_id: str,
        merchant_name: str,
        category: str,
        expected_merchant_id: Optional[str] = None
    ) -> Tuple[bool, bool, float, List[Dict[str, Any]]]:
        """
        Evaluates merchant identity, destination binding, category alignment, and novelty.
        Returns:
            (is_valid_destination, is_new_merchant, merchant_trust_score, anomalies)
        """
        anomalies: List[Dict[str, Any]] = []

        # 1. Payment Destination Binding Check
        if expected_merchant_id and merchant_id != expected_merchant_id:
            anomalies.append({
                "signal": "destination_substitution",
                "severity": "CRITICAL",
                "expected": expected_merchant_id,
                "actual": merchant_id,
                "message": f"Payment destination substitution detected! Expected '{expected_merchant_id}', received '{merchant_id}'"
            })
            return False, False, 10.0, anomalies

        # 2. Lookup known merchant
        known = TRUSTED_MERCHANTS.get(merchant_id)
        if not known:
            # New/unrecognized merchant
            anomalies.append({
                "signal": "new_merchant",
                "severity": "MEDIUM",
                "merchant_id": merchant_id,
                "message": f"Merchant '{merchant_name}' ({merchant_id}) has no prior transaction history with SentinelX"
            })
            return True, True, 60.0, anomalies

        # 3. Category Mismatch Detection
        expected_cat = known.get("category", "").lower()
        if expected_cat and expected_cat != category.lower():
            anomalies.append({
                "signal": "merchant_category_mismatch",
                "severity": "HIGH",
                "expected_category": expected_cat,
                "actual_category": category,
                "message": f"Merchant '{known['name']}' usually operates in '{expected_cat}' but request specifies '{category}'"
            })
            return True, False, 50.0, anomalies

        return True, False, known.get("trust_score", 95.0), anomalies

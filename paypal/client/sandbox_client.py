import os
import base64
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

class PayPalSandboxClient:
    """
    Client for PayPal REST API v2 in PayPal Sandbox environment.
    Handles OAuth2 token acquisition, order creation, and capture.
    Strictly isolated behind SentinelX deterministic authorization layer.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = "https://api-m.sandbox.paypal.com"
    ):
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.client_id != "placeholder_client_id")

    async def get_access_token(self) -> str:
        """
        Retrieves OAuth2 Bearer token from PayPal Sandbox endpoint.
        """
        if not self.is_configured:
            return "simulated_sandbox_token"

        if self._access_token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._access_token

        auth_str = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                data={"grant_type": "client_credentials"}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"PayPal Sandbox OAuth failed: HTTP {resp.status_code} - {resp.text}")

            data = resp.json()
            self._access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow()
            return self._access_token

    async def create_order(
        self,
        amount: float,
        currency: str,
        reference_id: str,
        custom_id: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order via /v2/checkout/orders.
        Passes SentinelX trace/intent ID in reference_id and custom_id for PayPal traceability.
        """
        if not self.is_configured:
            # Deterministic sandbox simulation mode with authentic PayPal schema
            sim_order_id = f"PAYPAL-SANDBOX-ORDER-{uuid.uuid4().hex[:10].upper()}"
            return {
                "id": sim_order_id,
                "status": "CREATED",
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": reference_id,
                    "custom_id": custom_id,
                    "description": description,
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    }
                }],
                "links": [
                    {
                        "href": f"https://www.sandbox.paypal.com/checkoutnow?token={sim_order_id}",
                        "rel": "approve",
                        "method": "GET"
                    },
                    {
                        "href": f"{self.base_url}/v2/checkout/orders/{sim_order_id}/capture",
                        "rel": "capture",
                        "method": "POST"
                    }
                ]
            }

        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(uuid.uuid4())
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "custom_id": custom_id,
                    "description": description[:120],
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    }
                }
            ],
            "application_context": {
                "brand_name": "SentinelX Autonomous Commerce Guard",
                "user_action": "PAY_NOW",
                "return_url": "https://sentinelx.local/checkout/success",
                "cancel_url": "https://sentinelx.local/checkout/cancel"
            }
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=payload
            )
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"PayPal Order creation failed: HTTP {resp.status_code} - {resp.text}")
            return resp.json()

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Captures an approved PayPal order via /v2/checkout/orders/{order_id}/capture.
        """
        if not self.is_configured:
            sim_capture_id = f"CAPTURE-{uuid.uuid4().hex[:12].upper()}"
            return {
                "id": order_id,
                "status": "COMPLETED",
                "purchase_units": [{
                    "payments": {
                        "captures": [{
                            "id": sim_capture_id,
                            "status": "COMPLETED",
                            "amount": {"currency_code": "USD", "value": "100.00"},
                            "final_capture": True,
                            "create_time": datetime.utcnow().isoformat()
                        }]
                    }
                }]
            }

        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(uuid.uuid4())
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                json={}
            )
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"PayPal Order capture failed: HTTP {resp.status_code} - {resp.text}")
            return resp.json()


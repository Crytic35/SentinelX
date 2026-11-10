import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from security.identity.crypto import sign_payload, verify_signature

class DelegatedCapabilityToken(BaseModel):
    token_id: str = Field(default_factory=lambda: f"del_{uuid.uuid4().hex[:12]}")
    source_agent_id: str
    target_agent_id: str
    capability: str
    max_amount: float
    currency: str = "USD"
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    signature: Optional[str] = None

    def payload_to_sign(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "capability": self.capability,
            "max_amount": self.max_amount,
            "currency": self.currency,
            "expires_at": self.expires_at,
            "created_at": self.created_at
        }

    def sign(self, source_private_key_hex: str) -> None:
        self.signature = sign_payload(self.payload_to_sign(), source_private_key_hex)

    def verify(self, source_public_key_hex: str) -> Tuple[bool, str]:
        if not self.signature:
            return False, "Missing cryptographic signature on delegation token"
        
        # Check expiration
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00")).replace(tzinfo=None)
            if datetime.utcnow() > exp:
                return False, f"Delegation token expired at {self.expires_at}"
        except Exception:
            return False, "Malformed token expiration timestamp"

        if not verify_signature(self.payload_to_sign(), self.signature, source_public_key_hex):
            return False, "Invalid signature on delegation token: failed cryptographic verification against source agent key"

        return True, "Valid"


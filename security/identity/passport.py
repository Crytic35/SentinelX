import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from security.identity.crypto import canonical_json, sign_payload, verify_signature, hash_content

class TrustState:
    NEW = "NEW"
    UNVERIFIED = "UNVERIFIED"
    TRUSTED = "TRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    RESTRICTED = "RESTRICTED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"

    VALID_STATES = {NEW, UNVERIFIED, TRUSTED, SUSPICIOUS, RESTRICTED, QUARANTINED, REVOKED}

class AgentPassportModel(BaseModel):
    passport_id: str = Field(default_factory=lambda: f"psp_{uuid.uuid4().hex[:12]}")
    agent_id: str
    owner_id: str
    version: int = 1
    capabilities: List[str]
    per_transaction_limit: float
    daily_limit: float
    allowed_categories: List[str]
    blocked_categories: List[str]
    allowed_countries: List[str]
    approval_threshold: float
    require_approval_new_merchant: bool = True
    require_approval_recurring: bool = True
    public_key: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    signature: Optional[str] = None

    def payload_to_sign(self) -> Dict[str, Any]:
        return {
            "passport_id": self.passport_id,
            "agent_id": self.agent_id,
            "owner_id": self.owner_id,
            "version": self.version,
            "capabilities": sorted(self.capabilities),
            "per_transaction_limit": float(self.per_transaction_limit),
            "daily_limit": float(self.daily_limit),
            "allowed_categories": sorted(self.allowed_categories),
            "blocked_categories": sorted(self.blocked_categories),
            "allowed_countries": sorted(self.allowed_countries),
            "approval_threshold": float(self.approval_threshold),
            "require_approval_new_merchant": self.require_approval_new_merchant,
            "require_approval_recurring": self.require_approval_recurring,
            "public_key": self.public_key,
            "created_at": self.created_at,
        }

    def sign(self, private_key_hex: str) -> None:
        self.signature = sign_payload(self.payload_to_sign(), private_key_hex)

    def verify(self) -> bool:
        if not self.signature:
            return False
        return verify_signature(self.payload_to_sign(), self.signature, self.public_key)

    def fingerprint(self) -> str:
        return hash_content(self.payload_to_sign())


from typing import Tuple
from security.identity.passport import TrustState

class TrustStateMachine:
    """
    Manages continuous agent trust lifecycle transitions.
    Transitions:
    NEW -> UNVERIFIED -> TRUSTED -> SUSPICIOUS -> RESTRICTED -> QUARANTINED -> REVOKED
    """

    ALLOWED_TRANSITIONS = {
        TrustState.NEW: {TrustState.UNVERIFIED, TrustState.TRUSTED},
        TrustState.UNVERIFIED: {TrustState.TRUSTED, TrustState.RESTRICTED, TrustState.REVOKED},
        TrustState.TRUSTED: {TrustState.SUSPICIOUS, TrustState.RESTRICTED, TrustState.QUARANTINED, TrustState.REVOKED},
        TrustState.SUSPICIOUS: {TrustState.TRUSTED, TrustState.RESTRICTED, TrustState.QUARANTINED, TrustState.REVOKED},
        TrustState.RESTRICTED: {TrustState.TRUSTED, TrustState.QUARANTINED, TrustState.REVOKED},
        TrustState.QUARANTINED: {TrustState.RESTRICTED, TrustState.TRUSTED, TrustState.REVOKED},
        TrustState.REVOKED: set()  # Terminal state
    }

    @classmethod
    def can_transition(cls, current_state: str, new_state: str) -> bool:
        if current_state == new_state:
            return True
        return new_state in cls.ALLOWED_TRANSITIONS.get(current_state, set())

    @classmethod
    def transition(cls, current_state: str, new_state: str) -> Tuple[bool, str]:
        if not cls.can_transition(current_state, new_state):
            return False, f"Illegal trust transition from '{current_state}' to '{new_state}'"
        return True, "Success"


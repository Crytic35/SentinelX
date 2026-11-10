from datetime import datetime, timedelta
import threading
from typing import Dict, Optional, Tuple

class NonceStore:
    """
    Thread-safe store for nonces, request IDs, and idempotency tracking.
    Prevents replay attacks, duplicate submissions, and accepts only non-expired requests.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NonceStore, cls).__new__(cls)
                cls._instance._seen_nonces = {}  # nonce -> expiry_datetime
                cls._instance._idempotency_keys = {}  # idempotency_key -> cached_result
                cls._instance._agent_last_request = {}  # agent_id -> list of request timestamps for velocity
        return cls._instance

    def validate_and_record_nonce(self, nonce: str, timestamp_iso: str, max_age_seconds: int = 300) -> Tuple[bool, str]:
        """
        Validates nonce uniqueness and timestamp freshness within tolerance.
        """
        now = datetime.utcnow()
        try:
            req_time = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return False, "Malformed request timestamp"

        # Check clock skew / expiry
        age = (now - req_time).total_seconds()
        if age > max_age_seconds:
            return False, f"Request expired (age: {age:.1f}s > {max_age_seconds}s limit)"
        if age < -60:  # More than 60s in the future
            return False, "Request timestamp is in the future"

        with self._lock:
            # Purge expired nonces
            expired = [n for n, exp in self._seen_nonces.items() if exp < now]
            for n in expired:
                del self._seen_nonces[n]

            if nonce in self._seen_nonces:
                return False, f"Replay attack detected: Nonce '{nonce}' has already been used"

            # Record nonce with expiration
            self._seen_nonces[nonce] = now + timedelta(seconds=max_age_seconds * 2)
            return True, "Valid"

    def record_agent_request(self, agent_id: str) -> int:
        """
        Records an agent request and returns count of requests in the last 60 seconds (for velocity tracking).
        """
        now = datetime.utcnow()
        one_min_ago = now - timedelta(seconds=60)
        with self._lock:
            history = self._agent_last_request.get(agent_id, [])
            history = [t for t in history if t > one_min_ago]
            history.append(now)
            self._agent_last_request[agent_id] = history
            return len(history)

    def clear(self):
        with self._lock:
            self._seen_nonces.clear()
            self._idempotency_keys.clear()
            self._agent_last_request.clear()

nonce_store = NonceStore()


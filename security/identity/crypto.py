import json
import base64
import hashlib
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_agent_keypair() -> Tuple[str, str]:
    """
    Generates a cryptographically secure Ed25519 keypair for an agent.
    Returns (public_key_hex, private_key_hex).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return pub_bytes.hex(), priv_bytes.hex()


def canonical_json(data: Dict[str, Any]) -> bytes:
    """
    Converts a Python dictionary to deterministic canonical JSON bytes
    (sorted keys, compact separators, UTF-8 encoded).
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def sign_payload(payload: Dict[str, Any], private_key_hex: str) -> str:
    """
    Signs canonical JSON representation of payload using Ed25519 private key.
    Returns hex signature.
    """
    priv_bytes = bytes.fromhex(private_key_hex)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    message = canonical_json(payload)
    signature = private_key.sign(message)
    return signature.hex()


def verify_signature(payload: Dict[str, Any], signature_hex: str, public_key_hex: str) -> bool:
    """
    Verifies Ed25519 signature over canonical JSON of payload using public key.
    """
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        message = canonical_json(payload)
        public_key.verify(sig_bytes, message)
        return True
    except Exception:
        return False


def hash_content(data: Any) -> str:
    """
    SHA-256 hash of canonical JSON data or string.
    """
    if isinstance(data, dict) or isinstance(data, list):
        encoded = canonical_json(data)
    elif isinstance(data, str):
        encoded = data.encode('utf-8')
    elif isinstance(data, bytes):
        encoded = data
    else:
        encoded = str(data).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


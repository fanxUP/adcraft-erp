"""API Key encryption/decryption using Fernet symmetric encryption.

The encryption key is derived from the app's SECRET_KEY so no
additional configuration is needed. Keys are stored as encrypted
blobs in the database - the frontend can only see the last 4 chars.
"""
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings

_SALT = b"adcraft-ai-secret-store-v1"


def _derive_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from SECRET_KEY."""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_SALT, iterations=100_000)
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key and return the encrypted token string."""
    if not api_key:
        return ""
    fernet = Fernet(_derive_fernet_key())
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an encrypted API key token."""
    if not encrypted:
        return ""
    fernet = Fernet(_derive_fernet_key())
    return fernet.decrypt(encrypted.encode()).decode()


def mask_api_key(encrypted_or_raw: str) -> str:
    """Show only last 4 chars for display."""
    try:
        decrypted = decrypt_api_key(encrypted_or_raw)
    except Exception:
        decrypted = encrypted_or_raw
    if len(decrypted) <= 8:
        return "****" + decrypted[-4:] if len(decrypted) > 4 else "****"
    return decrypted[:4] + "****" + decrypted[-4:]

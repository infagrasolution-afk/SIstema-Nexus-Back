"""
Implementación pura en Python de RFC 6238 (TOTP - Time-based One-Time Password).
100% compatible con Google Authenticator, Authy y Microsoft Authenticator.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_totp_secret(length: int = 20) -> str:
    """Genera un secreto Base32 criptográficamente seguro de 160 bits."""
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _totp_at(secret: str, counter: int, digits: int = 6) -> str:
    padded = secret.strip().upper()
    padding = (-len(padded)) % 8
    key = base64.b32decode(padded + ("=" * padding), casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code_int).zfill(digits)


def verify_totp_code(secret: str, code: str, window: int = 1, period: int = 30) -> bool:
    """Valida un código TOTP de 6 dígitos con tolerancia de ±1 ventana de 30s."""
    if not secret or not code:
        return False
    clean_code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(clean_code) != 6:
        return False

    current_counter = int(time.time() // period)
    for offset in range(-window, window + 1):
        expected = _totp_at(secret, current_counter + offset)
        if hmac.compare_digest(clean_code, expected):
            return True
    return False


def build_otpauth_uri(username: str, secret: str, issuer: str = "APEX ERP") -> str:
    """Construye la URI estándar otpauth:// para escanear con código QR."""
    label = quote(f"{issuer}:{username}")
    issuer_q = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer_q}&algorithm=SHA1&digits=6&period=30"


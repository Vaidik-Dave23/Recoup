from datetime import datetime, timedelta, timezone

import hashlib
import bcrypt

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    # Hash password with SHA-256 first to support passwords of arbitrary length safely
    # (keeps the bcrypt input within the 72-byte limit).
    password_hash = hashlib.sha256(password.encode("utf-8")).digest()
    # Hashing with bcrypt.gensalt() (defaults to 12 rounds)
    hashed_bytes = bcrypt.hashpw(password_hash, bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")

        # 1. Try checking assuming SHA-256 pre-hashing (new scheme)
        sha256_digest = hashlib.sha256(password_bytes).digest()
        if bcrypt.checkpw(sha256_digest, hashed_bytes):
            return True

        # 2. Try checking assuming direct raw password hashing (legacy scheme fallback)
        # Catch/guard if length of raw password is > 72 to avoid ValueError from bcrypt
        if len(password_bytes) <= 72:
            if bcrypt.checkpw(password_bytes, hashed_bytes):
                return True

        return False
    except Exception:
        # Any format/parsing/value exception should return False instead of bubbling up as 500
        return False


def create_access_token(
    user_id: str,
    merchant_id: str,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": user_id,
        "merchant_id": merchant_id,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
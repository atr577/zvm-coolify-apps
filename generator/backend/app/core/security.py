from datetime import datetime, timedelta
from typing import Optional
import hashlib
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# bcrypt cost factor (12 is a good balance of security and speed)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def _is_sha256_hash(hashed_password: str) -> bool:
    """Check if hash is legacy SHA256 (64 hex chars)."""
    return len(hashed_password) == 64 and all(c in '0123456789abcdef' for c in hashed_password)


def _verify_sha256(plain_password: str, hashed_password: str) -> bool:
    """Verify against legacy SHA256 hash."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def _verify_bcrypt(plain_password: str, hashed_password: str) -> bool:
    """Verify against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except (ValueError, TypeError):
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Supports both bcrypt (new) and SHA256 (legacy) for backward compatibility.
    """
    if _is_sha256_hash(hashed_password):
        return _verify_sha256(plain_password, hashed_password)
    return _verify_bcrypt(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """Check if password needs to be rehashed (e.g., legacy SHA256 → bcrypt)."""
    return _is_sha256_hash(hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

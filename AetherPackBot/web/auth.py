"""
JWT 认证工具
JWT authentication utilities.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import jwt

SECRET_KEY = "AetherPackBot_secret"
ALGORITHM = "HS256"
TOKEN_EXPIRY = 86400  # 24小时


def create_token(username: str) -> str:
    """创建 JWT Token / Create a JWT token."""
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    """验证 JWT Token / Verify a JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def hash_password(password: str) -> str:
    """密码哈希 / Hash password."""
    return hashlib.sha256(password.encode()).hexdigest()

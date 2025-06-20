# app/security.py

"""
JWT (JSON Web Token) validation and security scheme configuration.

This module handles bearer token parsing and signature verification using HS256.

Used for:
- Validating authentication headers on protected endpoints
- Enforcing token expiry
- Attaching identity (`sub`) to the request lifecycle

Requires a shared secret key, configured via `.env` as `JWT_SECRET_KEY`.

🛡️ This is used alongside the `/v1/token` route that issues short-lived tokens
based on an API key. All core endpoints (chat, embed) require a valid JWT.
"""

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

# Ensure the app is configured correctly at startup
if not settings.jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY not set in environment")

# HTTPBearer ensures the Authorization header is present and formatted properly
bearer_scheme = HTTPBearer(auto_error=True)


async def verify_jwt(
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Verifies a JWT provided in the Authorization header.

    Args:
        creds (HTTPAuthorizationCredentials): Contains the raw Bearer token.

    Returns:
        dict: The decoded JWT payload if valid.

    Raises:
        HTTPException(403): If the token is invalid, malformed, or expired.
    """
    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )
    except jwt.PyJWTError:
        raise HTTPException(403, detail="Invalid or expired token")

    return payload

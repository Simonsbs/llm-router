from app.config import settings
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

if not settings.jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY not set in environment")

bearer_scheme = HTTPBearer(auto_error=True)

async def verify_jwt(
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    token = creds.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, 
            algorithms=["HS256"]
        )
    except jwt.PyJWTError:
        raise HTTPException(403, detail="Invalid or expired token")
    return payload

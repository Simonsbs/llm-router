import os
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load .env at startup
load_dotenv()

SECRET = os.getenv("JWT_SECRET_KEY")
if not SECRET:
    raise RuntimeError("JWT_SECRET_KEY not set in environment")

bearer_scheme = HTTPBearer(auto_error=True)

async def verify_jwt(
    creds: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(403, detail="Invalid or expired token")
    return payload

import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

# Load .env at start-up
load_dotenv()

API_KEY = os.getenv("LLM_ROUTER_API_KEY")
if not API_KEY:
    raise RuntimeError("LLM_ROUTER_API_KEY not set in environment")

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_scheme)):
    if api_key != API_KEY:
        raise HTTPException(403, detail="Invalid or missing API Key")
    return api_key

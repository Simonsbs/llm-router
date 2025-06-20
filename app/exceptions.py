# app/exceptions.py

"""
Custom exception classes for the SimonGPT LLM Router.

This module currently defines a single custom exception type used
to represent errors that occur within an LLM adapter during routing
or execution (e.g., network failures, invalid responses, internal logic bugs).

This structured exception is caught by FastAPI's global exception handler
to return consistent JSON error responses to the client.

🧠 Why use custom exceptions?
- Provide additional metadata like status codes
- Enable centralized error handling
- Improve traceability in logs and client responses
"""


class AdapterError(Exception):
    """
    Exception raised for adapter-specific errors.

    This is a catch-all for runtime errors inside adapter logic
    (e.g., failed API call, unsupported model, parsing error, etc.)

    Args:
        detail (str): Human-readable description of the error.
        status_code (int): HTTP status code to be returned to the client.

    Example:
        raise AdapterError("Provider not available", status_code=503)
    """
    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

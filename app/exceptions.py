# app/exceptions.py

class AdapterError(Exception):
    """
    A catch-all for errors inside adapters.
    Carries both an HTTP status code and a message.
    """
    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

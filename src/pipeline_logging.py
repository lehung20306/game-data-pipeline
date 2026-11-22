import requests


class AdsAPIError(RuntimeError):
    def __init__(self, platform, code):
        self.platform = platform
        self.code = code if type(code) is int else None
        super().__init__(f"{platform} API error | api_code={self.code}")


def error_context(error):
    """Report allowlisted error metadata without printing raw exceptions."""
    context = f"error_type={type(error).__name__}"
    if isinstance(error, AdsAPIError) and error.code is not None:
        context += f" api_code={error.code}"
    if isinstance(error, requests.RequestException) and error.response is not None:
        status = error.response.status_code
        if type(status) is int:
            context += f" http_status={status}"
    return context

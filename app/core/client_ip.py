"""Work out which IP address a request really came from."""

from starlette.requests import Request

from app.config import settings


def get_client_ip(request: Request) -> str:
    """Return the caller's IP address.

    Behind Railway's proxy the socket address is the proxy's, not the user's.
    When TRUST_PROXY_HEADERS is on we use the first X-Forwarded-For entry, which
    Railway's edge sets to the real client. Never turn that on when the app is
    directly exposed to the internet, because clients could then fake the header.
    """
    if settings.trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first = forwarded_for.split(",")[0].strip()
            if first:
                return first
    return request.client.host if request.client else "unknown"

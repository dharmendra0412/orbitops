"""ASGI request-body limits to bound multipart parsing and disk spooling."""
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.responses import JSONResponse

ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[dict[str, Any]]], Callable[..., Awaitable[None]]], Awaitable[None]]

MIB = 1024 * 1024
DEFAULT_REQUEST_BODY_BYTES = 10 * MIB
CHECKSUM_REQUEST_BODY_BYTES = 101 * MIB
PDS4_REQUEST_BODY_BYTES = 6 * MIB
SPICE_ARTIFACT_REQUEST_BODY_BYTES = 1025 * MIB


class RequestBodyTooLarge(Exception):
    """Raised when an incoming ASGI request exceeds its endpoint body budget."""


class RequestBodyLimitMiddleware:
    """Enforce endpoint-specific body budgets before Starlette parses multipart data."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_limit_bytes: int = DEFAULT_REQUEST_BODY_BYTES,
        checksum_limit_bytes: int = CHECKSUM_REQUEST_BODY_BYTES,
        pds4_limit_bytes: int = PDS4_REQUEST_BODY_BYTES,
        spice_artifact_limit_bytes: int = SPICE_ARTIFACT_REQUEST_BODY_BYTES,
    ) -> None:
        self.app = app
        self.default_limit_bytes = default_limit_bytes
        self.checksum_limit_bytes = checksum_limit_bytes
        self.pds4_limit_bytes = pds4_limit_bytes
        self.spice_artifact_limit_bytes = spice_artifact_limit_bytes

    def _limit_for(self, path: str) -> int:
        if path == "/api/v1/datasets/checksum":
            return self.checksum_limit_bytes
        if path == "/api/v1/datasets/pds4/inspect":
            return self.pds4_limit_bytes
        parts = path.split("/")
        if (
            len(parts) == 7
            and parts[:5] == ["", "api", "v1", "ephemeris", "spice"]
            and parts[5] == "kernels"
            and parts[6].endswith("/artifact")
        ):
            return self.spice_artifact_limit_bytes
        if path.startswith("/api/v1/ephemeris/spice/kernels/") and path.endswith("/artifact"):
            return self.spice_artifact_limit_bytes
        return self.default_limit_bytes

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        limit = self._limit_for(scope.get("path", ""))
        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > limit:
                    await JSONResponse(
                        {"detail": f"Request body exceeds the {limit}-byte limit"},
                        status_code=413,
                    )(scope, receive, send)
                    return
            except ValueError:
                pass

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > limit:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await JSONResponse(
                {"detail": f"Request body exceeds the {limit}-byte limit"},
                status_code=413,
            )(scope, receive, send)

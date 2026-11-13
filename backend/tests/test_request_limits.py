from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.request_limits import RequestBodyLimitMiddleware


def _limited_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RequestBodyLimitMiddleware,
        default_limit_bytes=16,
        checksum_limit_bytes=32,
        pds4_limit_bytes=8,
        spice_artifact_limit_bytes=64,
    )

    @app.post("/{path:path}")
    async def echo_body(request: Request):
        return {"size": len(await request.body())}

    return app


def test_request_body_limit_rejects_oversized_default_endpoint():
    client = TestClient(_limited_test_app())
    response = client.post("/api/v1/missions/projects", content=b"x" * 17)
    assert response.status_code == 413


def test_checksum_endpoint_uses_its_larger_upload_budget():
    client = TestClient(_limited_test_app())
    response = client.post("/api/v1/datasets/checksum", content=b"x" * 32)
    assert response.status_code == 200
    assert response.json()["size"] == 32


def test_pds4_endpoint_has_a_smaller_request_budget():
    client = TestClient(_limited_test_app())
    response = client.post("/api/v1/datasets/pds4/inspect", content=b"x" * 9)
    assert response.status_code == 413


def test_spice_artifact_endpoint_gets_the_largest_upload_budget():
    client = TestClient(_limited_test_app())
    response = client.post(
        "/api/v1/ephemeris/spice/kernels/demo/artifact",
        content=b"x" * 64,
    )
    assert response.status_code == 200
    assert response.json()["size"] == 64


def test_chunked_request_body_is_counted_without_content_length():
    client = TestClient(_limited_test_app())
    response = client.post(
        "/api/v1/missions/projects",
        content=iter([b"x" * 10, b"x" * 7]),
    )
    assert response.status_code == 413

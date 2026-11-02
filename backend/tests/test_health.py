from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "x-request-id" in res.headers


def test_request_id_is_echoed(client: TestClient) -> None:
    res = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert res.headers["x-request-id"] == "abc-123"


def test_unknown_route_uses_fastapi_404(client: TestClient) -> None:
    assert client.get("/nope").status_code == 404


def test_unhandled_error_uses_envelope_with_request_id(client: TestClient) -> None:
    async def boom() -> None:
        raise RuntimeError("kaboom")

    client.app.add_api_route("/boom", boom)  # type: ignore[attr-defined]
    res = client.get("/boom", headers={"X-Request-ID": "rid-500"})
    assert res.status_code == 500
    body = res.json()["error"]
    assert body["code"] == "internal_error"
    assert body["message"] == "Internal server error"  # no traceback leaks to the client
    assert body["request_id"] == "rid-500"

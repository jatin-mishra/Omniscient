import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/documents", {"text": "hello world", "source": "notes.txt"}),
        ("/v1/query", {"question": "what is in my notes?"}),
    ],
)
def test_stub_endpoints_return_501_envelope(
    client: TestClient, path: str, payload: dict[str, str]
) -> None:
    res = client.post(path, json=payload, headers={"X-Request-ID": "rid-501"})
    assert res.status_code == 501
    body = res.json()["error"]
    assert body["code"] == "not_implemented"
    assert body["request_id"] == "rid-501"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/documents", {"text": "", "source": "notes.txt"}),  # empty text
        ("/v1/documents", {"text": "hello"}),  # missing source
        ("/v1/query", {"question": ""}),  # empty question
        ("/v1/query", {"question": "q", "top_k": 0}),  # top_k below range
        ("/v1/query", {"question": "q", "top_k": 51}),  # top_k above range
    ],
)
def test_invalid_payloads_are_rejected(
    client: TestClient, path: str, payload: dict[str, object]
) -> None:
    assert client.post(path, json=payload).status_code == 422

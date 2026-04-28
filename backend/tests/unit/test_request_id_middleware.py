import pytest


@pytest.mark.asyncio
async def test_request_id_middleware_generates_id_when_missing(client):
    resp = await client.get("/")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_request_id_middleware_passes_through_client_id(client):
    resp = await client.get("/", headers={"X-Request-ID": "my-trace-123"})
    assert resp.headers["X-Request-ID"] == "my-trace-123"


@pytest.mark.asyncio
async def test_request_id_middleware_present_on_error(client):
    resp = await client.get("/api/v1/items/not-a-uuid")
    assert resp.status_code in (405, 422)
    assert "X-Request-ID" in resp.headers
    body = resp.json()
    assert "detail" in body

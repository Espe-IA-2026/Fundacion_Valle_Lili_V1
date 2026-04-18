from __future__ import annotations

from fastapi.testclient import TestClient

from semantic_layer_fvl.api.app import create_app


def test_search_endpoint_returns_results() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/search", params={"q": "cardiologia", "limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_search_endpoint_requires_query() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/search")
    assert response.status_code == 422  # Validation error


def test_stats_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_indexed_chunks" in data
    assert "categories" in data

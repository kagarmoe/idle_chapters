from fastapi.testclient import TestClient


def test_sessions_flow() -> None:
    from app.main import app

    client = TestClient(app)

    create_response = client.post("/sessions")
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    step_response = client.post(f"/sessions/{session_id}/step", json={"command": "enter"})
    assert step_response.status_code == 200
    payload = step_response.json()

    assert "journal_page" in payload
    assert "choices" in payload


def test_world_endpoints() -> None:
    from app.main import app

    client = TestClient(app)

    for path in ["/world/places", "/world/npcs", "/world/items"]:
        response = client.get(path)
        assert response.status_code == 200

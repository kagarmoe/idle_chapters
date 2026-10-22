"""Every error, fatal or not, becomes one JSON line in the logs (monitoring design §1)."""

import json

from fastapi.testclient import TestClient

from idle_chapters.api.server import create_app


def _events(captured: str) -> list[dict]:
    lines = [json.loads(line) for line in captured.splitlines() if line.startswith("{")]
    return [e for e in lines if e.get("event") == "error"]


def test_a_handled_error_is_logged_as_a_warning_without_the_raw_id(capsys) -> None:
    response = TestClient(create_app()).get("/v1/sessions/secret-session-id")

    assert response.status_code == 404
    [event] = _events(capsys.readouterr().err)
    assert event["level"] == "warning" and event["source"] == "api"
    assert event["status"] == 404 and event["kind"] == "session_not_found"
    assert event["method"] == "GET" and event["path"] == "/v1/sessions/{session_id}"
    assert "secret-session-id" not in json.dumps(event)


def test_an_unhandled_error_is_a_500_problem_and_logged_with_its_stack(capsys) -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kettle cracked")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json()["status"] == 500 and "kettle" not in response.text
    [event] = _events(capsys.readouterr().err)
    assert event["level"] == "error" and event["kind"] == "RuntimeError"
    assert "kettle cracked" in event["message"] and "boom" in event["stack"]


def test_browser_errors_are_logged_and_bad_reports_are_refused(capsys) -> None:
    client = TestClient(create_app())
    report = {"level": "warning", "kind": "ApiError", "message": "Something went quiet (503)",
              "path": "/play/idle-chapters", "stack": "at handleError"}

    assert client.post("/v1/client-errors", json=report).status_code == 204
    [event] = _events(capsys.readouterr().err)
    assert event["source"] == "browser" and event["message"] == report["message"]
    assert event["user_agent"].startswith("testclient")

    assert client.post("/v1/client-errors", json={**report, "message": "x" * 501}).status_code == 422
    assert client.post("/v1/client-errors", json={**report, "level": "fatal"}).status_code == 422
    assert client.post("/v1/client-errors", json={**report, "stack": "y" * 4001}).status_code == 422
    assert client.post("/v1/client-errors", json={**report, "player_text": "hi"}).status_code == 422
    assert _events(capsys.readouterr().err) == []

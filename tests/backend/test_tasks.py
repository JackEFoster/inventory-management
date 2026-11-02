"""
Tests for the /api/tasks endpoints behind the header Tasks modal.

Tasks live in an in-memory list on the server module, so each test clears it
(and the ID counter) to stay independent of execution order.
"""
import pytest

import main

VALID = {"title": "Check stock levels", "priority": "high", "dueDate": "2025-10-10"}


@pytest.fixture(autouse=True)
def clear_tasks():
    main.tasks.clear()
    main._task_seq = 0
    yield
    main.tasks.clear()


def test_list_starts_empty(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_returns_pending_task_with_string_id(client):
    response = client.post("/api/tasks", json=VALID)
    assert response.status_code == 201
    task = response.json()
    assert task == {**VALID, "id": "task-1", "status": "pending"}


def test_list_is_newest_first(client):
    client.post("/api/tasks", json={**VALID, "title": "first"})
    client.post("/api/tasks", json={**VALID, "title": "second"})
    assert [t["title"] for t in client.get("/api/tasks").json()] == ["second", "first"]


def test_toggle_flips_status_both_ways(client):
    tid = client.post("/api/tasks", json=VALID).json()["id"]
    assert client.patch(f"/api/tasks/{tid}").json()["status"] == "completed"
    assert client.patch(f"/api/tasks/{tid}").json()["status"] == "pending"


def test_delete_removes_task_and_ids_are_not_reused(client):
    tid = client.post("/api/tasks", json=VALID).json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 200
    assert client.get("/api/tasks").json() == []
    assert client.post("/api/tasks", json=VALID).json()["id"] == "task-2"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_task_is_404(client, method):
    assert getattr(client, method)("/api/tasks/task-999").status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {**VALID, "title": ""},
        {**VALID, "priority": "urgent"},
        {**VALID, "dueDate": "10/10/2025"},
        {"title": "missing due date"},
    ],
)
def test_invalid_input_is_rejected(client, bad):
    assert client.post("/api/tasks", json=bad).status_code == 422

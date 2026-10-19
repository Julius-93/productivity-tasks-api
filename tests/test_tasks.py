"""CRUD, pagination, validation, isolation, and authorization tests."""


def signup(client, username, password="SecurePass123!"):
    response = client.post("/signup", json={
        "username": username,
        "password": password,
        "password_confirmation": password,
    })
    assert response.status_code == 201
    return response


def make_task(client, title="Write tests", **other_fields):
    return client.post("/tasks", json={"title": title, **other_fields})


def test_all_task_routes_require_authentication(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"title": "Protected"}).status_code == 401
    assert client.get("/tasks/1").status_code == 401
    assert client.patch("/tasks/1", json={"title": "X"}).status_code == 401
    assert client.delete("/tasks/1").status_code == 401


def test_create_task_returns_201_and_authenticated_owner(client):
    signup(client, "julius")
    response = make_task(client, "Read book", description="Chapter 1")
    assert response.status_code == 201
    assert response.json["title"] == "Read book"
    assert response.json["description"] == "Chapter 1"
    assert response.json["is_completed"] is False
    assert response.json["user_id"] == 1
    assert response.json["created_at"] is not None


def test_get_task_returns_owned_record(client):
    signup(client, "julius")
    task_id = make_task(client).json["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json["id"] == task_id


def test_patch_changes_only_supplied_fields(client):
    signup(client, "julius")
    task_id = make_task(client, description="Keep me").json["id"]
    response = client.patch(f"/tasks/{task_id}", json={"is_completed": True})
    assert response.status_code == 200
    assert response.json["is_completed"] is True
    assert response.json["description"] == "Keep me"


def test_delete_task_returns_204_then_404(client):
    signup(client, "julius")
    task_id = make_task(client).json["id"]
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_missing_task_returns_404(client):
    signup(client, "julius")
    assert client.get("/tasks/999").status_code == 404
    assert client.patch("/tasks/999", json={"title": "Test"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404


def test_empty_list_is_paginated(client):
    signup(client, "julius")
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json["items"] == []
    assert response.json["total"] == 0
    assert response.json["page"] == 1
    assert response.json["per_page"] == 10


def test_pagination_reports_page_counts_and_next_page(client):
    signup(client, "julius")
    for index in range(12):
        assert make_task(client, f"Task {index}").status_code == 201
    first = client.get("/tasks?page=1&per_page=5").json
    second = client.get("/tasks?page=2&per_page=5").json
    third = client.get("/tasks?page=3&per_page=5").json
    assert [len(x["items"]) for x in (first, second, third)] == [5, 5, 2]
    assert first["total"] == 12
    assert first["pages"] == 3
    assert first["has_next"] is True
    assert third["has_next"] is False
    assert len({task["id"] for page in (first, second, third) for task in page["items"]}) == 12


def test_invalid_pagination_returns_400(client):
    signup(client, "julius")
    for query in ("?page=0", "?page=x", "?per_page=-1", "?per_page=101"):
        assert client.get(f"/tasks{query}").status_code == 400


def test_cannot_set_owner_or_unknown_fields(client):
    signup(client, "julius")
    assert make_task(client, user_id=123).status_code == 400
    assert make_task(client, arbitrary="x").status_code == 400


def test_create_rejects_missing_or_invalid_fields(client):
    signup(client, "julius")
    assert client.post("/tasks", json={"description": "missing title"}).status_code == 400
    assert make_task(client, title="  ").status_code == 400
    assert make_task(client, title="A" * 121).status_code == 400
    assert make_task(client, is_completed="yes").status_code == 400
    assert make_task(client, description=123).status_code == 400


def test_patch_rejects_empty_payload(client):
    signup(client, "julius")
    task_id = make_task(client).json["id"]
    assert client.patch(f"/tasks/{task_id}", json={}).status_code == 400


def test_other_users_cannot_read_patch_or_delete_tasks(client):
    signup(client, "alice")
    alice_task_id = make_task(client, "Alice private task").json["id"]
    client.delete("/logout")
    signup(client, "bob")

    assert client.get(f"/tasks/{alice_task_id}").status_code == 404
    assert client.patch(f"/tasks/{alice_task_id}", json={"title": "Hijack"}).status_code == 404
    assert client.delete(f"/tasks/{alice_task_id}").status_code == 404
    assert client.get("/tasks").json["items"] == []

    # A different user may create and only see their own tasks.
    bob_task = make_task(client, "Bob task")
    assert bob_task.status_code == 201
    assert [t["title"] for t in client.get("/tasks").json["items"]] == ["Bob task"]

    client.delete("/logout")
    response = client.post("/login", json={
        "username": "alice", "password": "SecurePass123!",
    })
    assert response.status_code == 200
    assert client.get(f"/tasks/{alice_task_id}").status_code == 200
    assert client.get(f"/tasks/{bob_task.json['id']}").status_code == 404

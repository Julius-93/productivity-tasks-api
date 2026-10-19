"""Auth flow, password protection, status codes, and session persistence."""

from app.extensions import db
from app.models import User


def signup(client, username="julius", password="SecurePass123!"):
    return client.post("/signup", json={
        "username": username,
        "password": password,
        "password_confirmation": password,
    })


def test_health_route(client):
    assert client.get("/").status_code == 200


def test_signup_creates_user_and_logs_them_in(client):
    response = signup(client)
    assert response.status_code == 201
    assert response.json == {"id": 1, "username": "julius"}
    assert client.get("/check_session").json == response.json


def test_signup_password_is_hashed_and_hidden(app, client):
    signup(client)
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.password_hash != "SecurePass123!"
        assert user.password_hash.startswith("$2")
        assert user.check_password("SecurePass123!")
        assert "password_hash" not in user.to_dict()


def test_password_property_cannot_be_read(app, client):
    signup(client)
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        try:
            _ = user.password
        except AttributeError:
            pass
        else:
            raise AssertionError("Password unexpectedly readable")


def test_duplicate_username_returns_409(client):
    assert signup(client).status_code == 201
    assert signup(client).status_code == 409


def test_signup_requires_matching_confirmation(client):
    response = client.post("/signup", json={
        "username": "julius", "password": "SecurePass123!",
        "password_confirmation": "different",
    })
    assert response.status_code == 400


def test_signup_rejects_too_short_password(client):
    response = signup(client, password="short")
    assert response.status_code == 400


def test_signup_rejects_password_longer_than_bcrypt_limit(client):
    assert signup(client, password="a" * 73).status_code == 400


def test_signup_rejects_bad_username(client):
    assert signup(client, username="  x  ").status_code == 400


def test_signup_rejects_non_json_body(client):
    assert client.post("/signup", data="bad", content_type="text/plain").status_code == 400


def test_signup_rejects_invalid_json_types(client):
    assert client.post("/signup", json=[1, 2]).status_code == 400


def test_login_succeeds_with_correct_credentials(client):
    signup(client)
    client.delete("/logout")
    response = client.post("/login", json={
        "username": "julius", "password": "SecurePass123!",
    })
    assert response.status_code == 200
    assert response.json["username"] == "julius"
    assert client.get("/check_session").status_code == 200


def test_login_rejects_invalid_password(client):
    signup(client)
    client.delete("/logout")
    response = client.post("/login", json={
        "username": "julius", "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert client.get("/check_session").status_code == 401


def test_login_rejects_unknown_user(client):
    response = client.post("/login", json={
        "username": "nobody", "password": "SecurePass123!",
    })
    assert response.status_code == 401


def test_login_requires_json_fields(client):
    assert client.post("/login", json={"username": "julius"}).status_code == 400


def test_anonymous_check_session_returns_401_and_empty_object(client):
    response = client.get("/check_session")
    assert response.status_code == 401
    assert response.json == {}


def test_session_persists_across_requests_and_logout_clears_it(client):
    signup(client)
    assert client.get("/check_session").status_code == 200
    assert client.get("/check_session").status_code == 200
    response = client.delete("/logout")
    assert response.status_code == 200
    assert response.json == {}
    assert client.get("/check_session").status_code == 401


def test_session_for_deleted_user_is_rejected(app, client):
    signup(client)
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        db.session.delete(user)
        db.session.commit()
    assert client.get("/check_session").status_code == 401

import pytest


def test_register_login_logout(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    me = api.register("alice", email="alice@example.org")
    assert me["user"]["username"] == "alice"
    assert me["team"] is None
    assert api.get("/api/auth/me").json()["user"]["username"] == "alice"

    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/auth/me").json() is None

    response = api.post("/api/auth/login", {"username": "ALICE", "password": "motdepasse-solide"})
    assert response.status_code == 200
    assert api.get("/api/auth/me").json()["user"]["username"] == "alice"


def test_session_cookie_flags(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    response = api.post(
        "/api/auth/register", {"username": "alice", "password": "motdepasse-solide"}
    )
    cookie = response.headers["set-cookie"]
    assert "jq_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_username_is_unique_case_insensitive(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    new_client().register("Alice")
    response = new_client().post(
        "/api/auth/register", {"username": "alice", "password": "motdepasse-solide"}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("username", ["ab", "a" * 33, "nom avec espaces", "<script>"])
def test_invalid_usernames(new_client, sync, username: str) -> None:  # type: ignore[no-untyped-def]
    sync()
    response = new_client().post(
        "/api/auth/register", {"username": username, "password": "motdepasse-solide"}
    )
    assert response.status_code == 422


def test_short_password_is_rejected(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    response = new_client().post("/api/auth/register", {"username": "alice", "password": "court"})
    assert response.status_code == 422


def test_wrong_password_and_unknown_user_look_the_same(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    new_client().register("alice")
    api = new_client()
    wrong = api.post("/api/auth/login", {"username": "alice", "password": "mauvais-mot"})
    unknown = api.post("/api/auth/login", {"username": "personne", "password": "mauvais-mot"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_is_rate_limited(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    new_client().register("alice")
    api = new_client()
    for _ in range(10):
        assert (
            api.post(
                "/api/auth/login", {"username": "alice", "password": "mauvais-mot"}
            ).status_code
            == 401
        )
    response = api.post("/api/auth/login", {"username": "alice", "password": "motdepasse-solide"})
    assert response.status_code == 429


def test_login_failures_expire(new_client, sync, clock) -> None:  # type: ignore[no-untyped-def]
    from datetime import timedelta

    sync()
    new_client().register("alice")
    api = new_client()
    for _ in range(10):
        api.post("/api/auth/login", {"username": "alice", "password": "mauvais-mot"})
    clock.set(clock.now + timedelta(minutes=16))
    assert (
        api.post(
            "/api/auth/login", {"username": "alice", "password": "motdepasse-solide"}
        ).status_code
        == 200
    )


def test_csrf_token_is_required(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    response = api.client.post(
        "/api/auth/register", json={"username": "alice", "password": "motdepasse-solide"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf"

    response = api.client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "motdepasse-solide"},
        headers={"X-CSRF-Token": "faux"},
    )
    assert response.status_code == 403


def test_expired_session_is_rejected(new_client, sync, clock) -> None:  # type: ignore[no-untyped-def]
    from datetime import timedelta

    sync()
    api = new_client()
    api.register("alice")
    clock.set(clock.now + timedelta(hours=73))
    assert api.get("/api/auth/me").json() is None


def test_closed_registration(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    sync(make_pack(participation={"registration": "closed"}))
    response = new_client().post(
        "/api/auth/register", {"username": "alice", "password": "motdepasse-solide"}
    )
    assert response.status_code == 403


def test_invite_code_registration(new_client, sync, make_pack, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from pydantic import SecretStr

    from jacquard.config import get_settings

    sync(make_pack(participation={"registration": "invite_code"}))
    monkeypatch.setattr(get_settings(), "registration_code", SecretStr("CODE-EPITA"))
    api = new_client()
    body = {"username": "alice", "password": "motdepasse-solide"}
    assert api.post("/api/auth/register", body).status_code == 403
    assert api.post("/api/auth/register", {**body, "registration_code": "faux"}).status_code == 403
    assert (
        api.post("/api/auth/register", {**body, "registration_code": "CODE-EPITA"}).status_code
        == 201
    )


def test_solo_mode_creates_personal_team(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    sync(make_pack(participation={"mode": "solo"}))
    api = new_client()
    me = api.register("alice")
    assert me["team"]["name"] == "alice"
    assert api.post("/api/teams", {"name": "Autre"}).status_code == 403


def test_no_event_returns_503(new_client) -> None:  # type: ignore[no-untyped-def]
    response = new_client().get("/api/event")
    assert response.status_code == 503


def test_security_headers(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    response = new_client().get("/api/event")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]

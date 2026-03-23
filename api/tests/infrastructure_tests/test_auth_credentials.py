from infrastructure.auth.auth_credentials import try_login, try_register
from infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher
from apps_api.test_auth_router import FakeRepo, _row

_HASHER = BcryptPasswordHasher()


def test_try_login_success() -> None:
    alice = _row()
    repo = FakeRepo({"alice": alice})
    ok, msg, user = try_login(repo, "alice", "secret123", password_hasher=_HASHER)
    assert ok and user
    assert user["user_id"] == "u1"
    assert "successful" in msg.lower()


def test_try_register_creates_user() -> None:
    repo = FakeRepo({})
    ok, msg, user = try_register(
        repo,
        username="bob",
        password="password1",
        confirm_password="password1",
        display_name="Bob",
        password_hasher=_HASHER,
    )
    assert ok and user
    assert user["username"] == "bob"
    assert repo.username_exists("bob")

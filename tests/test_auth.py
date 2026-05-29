import pytest

from app.core.auth import create_access_token, decode_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = hash_password("test123456")
        assert isinstance(h, str)
        assert h.startswith("$2b$")

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("mypassword")
        assert verify_password("wrong", h) is False

    def test_verify_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True

    def test_hash_is_deterministic_for_verify(self):
        h = hash_password("abc")
        # Same password should verify against its own hash
        assert verify_password("abc", h) is True

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("password")
        h2 = hash_password("password")
        # bcrypt uses random salt, so hashes differ
        assert h1 != h2
        # But both verify correctly
        assert verify_password("password", h1)
        assert verify_password("password", h2)


class TestJWTToken:
    def test_create_and_decode_token(self):
        token = create_access_token(42)
        uid = decode_token(token)
        assert uid == 42

    def test_decode_invalid_token(self):
        assert decode_token("not.a.valid.token") is None

    def test_decode_empty_token(self):
        assert decode_token("") is None

    def test_decode_none(self):
        assert decode_token(None) is None

    def test_decode_garbage(self):
        assert decode_token("asdfasdfasdf") is None

    def test_token_for_different_users(self):
        t1 = decode_token(create_access_token(1))
        t2 = decode_token(create_access_token(999))
        assert t1 == 1
        assert t2 == 999

    @pytest.mark.parametrize("user_id", [1, 100, 9999])
    def test_roundtrip_various_ids(self, user_id):
        token = create_access_token(user_id)
        assert decode_token(token) == user_id

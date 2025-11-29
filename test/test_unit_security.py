from bs.src.auth import security


def test_password_hash_and_verify():
    pw = "s3cr3t-pass"
    hashed = security.get_password_hash(pw)
    assert hashed != pw
    assert security.verify_password(pw, hashed) is True
    assert security.verify_password("wrong-pass", hashed) is False


def test_create_and_decode_token_contains_expected_fields():
    data = {"sub": "unittest-user"}
    token = security.create_access_token(data)
    payload = security.decode_token(token)
    assert payload.get("sub") == "unittest-user"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_create_access_token_with_custom_jti_and_uniqueness():
    custom_jti = security.create_jti()
    token = security.create_access_token({"sub": "x"}, jti=custom_jti)
    payload = security.decode_token(token)
    assert payload.get("jti") == custom_jti

    # ensure create_jti produces unique values
    a = security.create_jti()
    b = security.create_jti()
    assert a != b

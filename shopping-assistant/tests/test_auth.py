import pytest
from fastapi import HTTPException
from backend.main import (
    hash_password,
    verify_password,
    ensure_bcrypt_safe,
    normalize_code,
    hash_recovery_code,
    verify_recovery_code,
)


def test_correct_password():
    # Arrange
    password = "SecurePassword123"
    hashed = hash_password(password)

    # Act
    result = verify_password(password, hashed)

    # Assert
    assert result is True


def test_incorrect_password():
    hashed = hash_password("CorrectPassword123")

    result = verify_password("WrongPassword123", hashed)

    assert result is False


def test_password_hash_is_not_plaintext():
    password = "SecurePassword123"

    hashed = hash_password(password)

    assert hashed != password.encode()


def test_password_within_bcrypt_limit():
    ensure_bcrypt_safe("a" * 72)


def test_password_exceeds_bcrypt_limit():
    with pytest.raises(HTTPException) as error:
        ensure_bcrypt_safe("a" * 73)

    assert error.value.status_code == 422


def test_unicode_password_exceeds_byte_limit():
    with pytest.raises(HTTPException) as error:
        ensure_bcrypt_safe("😀" * 19)

    assert error.value.status_code == 422


def test_recovery_code_normalization():
    result = normalize_code("ab12-cd34 ef56")

    assert result == "AB12CD34EF56"


def test_correct_recovery_code():
    code = "ABCD-EFGH-JKLM-NPQR"
    hashed = hash_recovery_code(code)

    assert verify_recovery_code("abcd efgh jklm npqr", hashed) is True


def test_incorrect_recovery_code():
    hashed = hash_recovery_code("ABCD-EFGH-JKLM-NPQR")

    assert verify_recovery_code("WRONG-CODE", hashed) is False

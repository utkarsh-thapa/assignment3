from app.models import User


def test_password_is_hashed_and_checked():
    user = User()

    user.set_password("SecurePassword123!")

    assert user.password_hash != "SecurePassword123!"
    assert user.check_password("SecurePassword123!") is True
    assert user.check_password("WrongPassword") is False
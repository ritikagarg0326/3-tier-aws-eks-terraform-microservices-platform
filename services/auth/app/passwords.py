import bcrypt

from .config import get_settings

_DUMMY = None


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    """Constant-ish time: always performs a bcrypt comparison, even for unknown users."""
    global _DUMMY
    if hashed is None:
        if _DUMMY is None:
            _DUMMY = hash_password("dummy-password-for-timing")
        bcrypt.checkpw(plain.encode()[:72], _DUMMY.encode())
        return False
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False

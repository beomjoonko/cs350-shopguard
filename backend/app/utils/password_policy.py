"""Password complexity — SRS §4.3 REQ-6."""
import re

_MIN_LENGTH = 8
_HAS_DIGIT = re.compile(r"\d")
_HAS_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def validate_password_complexity(password: str) -> str | None:
    """Return an error message if the password fails policy, else None."""
    errors: list[str] = []
    if len(password) < _MIN_LENGTH:
        errors.append("at least 8 characters")
    if not _HAS_DIGIT.search(password):
        errors.append("at least one number")
    if not _HAS_SPECIAL.search(password):
        errors.append("at least one special character")
    if errors:
        return "Password must include " + ", ".join(errors) + "."
    return None

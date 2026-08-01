"""
Validation-error helpers shared by routers that hand-roll their own form
re-render on failure (login, reflection, ...).

Pydantic v2 prefixes a `ValueError` raised inside a `@field_validator` with
"Value error, " in the resulting error message — these strip that prefix so
users see the message we actually wrote.
"""

from pydantic import ValidationError

_PREFIX = "Value error, "


def _clean(error: dict) -> str:
    msg = error["msg"]
    return msg[len(_PREFIX) :] if msg.startswith(_PREFIX) else msg


def first_error_message(exc: ValidationError) -> str:
    return _clean(exc.errors()[0])


def field_errors(exc: ValidationError) -> dict[str, str]:
    return {err["loc"][0]: _clean(err) for err in exc.errors()}

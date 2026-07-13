"""User-facing bot errors."""


class PluralityError(Exception):
    """Base error with a user-friendly message."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NoSystemError(PluralityError):
    def __init__(self):
        super().__init__(
            "You don't have a system registered yet. Use `pl!system new` or `/system new` to create one!"
        )


class PermissionError(PluralityError):
    def __init__(self, message: str = "You don't have permission to do that."):
        super().__init__(message)


class SyntaxError(PluralityError):
    pass


def proxy_name_too_short(name: str) -> PluralityError:
    return PluralityError(f"Proxy name `{name}` is too short (minimum 2 characters).")


def proxy_name_too_long(name: str) -> PluralityError:
    return PluralityError(f"Proxy name `{name}` is too long (maximum 80 characters).")


def member_not_found(name: str) -> PluralityError:
    return PluralityError(f"Couldn't find a member matching `{name}` in that system.")


def system_not_found() -> PluralityError:
    return PluralityError("Couldn't find a system matching that query.")


def attachment_too_large() -> PluralityError:
    return PluralityError(
        "One of your attachments is too large to proxy (max 8MB per message chunk)."
    )
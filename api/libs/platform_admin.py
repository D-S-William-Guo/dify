"""Platform-administrator identity helpers and request guards.

Authorization is fail-closed: only an authenticated, active account whose
normalized email appears in the configured allowlist is accepted. The
allowlist is never cached or exposed by this module.
"""

from collections.abc import Callable
from functools import wraps
from typing import Protocol

from configs import dify_config
from libs.exception import BaseHTTPException
from libs.login import current_user
from models.account import Account, AccountStatus


class _AccountIdentity(Protocol):
    email: str
    status: AccountStatus


class PlatformAdminHTTPError(BaseHTTPException):
    """Stable platform-admin error response."""

    def __init__(self, error_code: str, description: str, status_code: int) -> None:
        self.error_code = error_code
        self.code = status_code
        super().__init__(description=description)


def normalize_platform_admin_email(email: str | None) -> str | None:
    """Return a lowercase, trimmed email or ``None`` for an empty value."""
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def parse_platform_admin_emails(configured_emails: str | None) -> frozenset[str]:
    """Parse a comma-separated allowlist into normalized unique emails."""
    if not configured_emails:
        return frozenset()
    return frozenset(
        normalized
        for item in configured_emails.split(",")
        if (normalized := normalize_platform_admin_email(item)) is not None
    )


def is_platform_admin_account(account: _AccountIdentity | None, configured_emails: str | None = None) -> bool:
    """Return whether an active account is present in the configured allowlist."""
    if account is None or account.status != AccountStatus.ACTIVE:
        return False
    normalized_email = normalize_platform_admin_email(account.email)
    if normalized_email is None:
        return False
    allowlist = parse_platform_admin_emails(
        dify_config.PLATFORM_ADMIN_EMAILS if configured_emails is None else configured_emails
    )
    return normalized_email in allowlist


def _resolved_current_account() -> Account | None:
    user_proxy = current_user
    get_current_object = getattr(user_proxy, "_get_current_object", None)
    user = get_current_object() if callable(get_current_object) else user_proxy
    return user if isinstance(user, Account) else None


def platform_admin_required[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    """Reject callers whose authenticated account is not a configured administrator."""

    @wraps(view)
    def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
        if not is_platform_admin_account(_resolved_current_account()):
            raise PlatformAdminHTTPError("platform_admin_required", "Platform administrator access required.", 403)
        return view(*args, **kwargs)

    return decorated


def platform_admin_current_tenant_required[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    """Return a stable conflict before the official initialization guard asserts."""

    @wraps(view)
    def decorated(*args: P.args, **kwargs: P.kwargs) -> R:
        account = _resolved_current_account()
        if account is None or account.current_tenant_id is None:
            raise PlatformAdminHTTPError(
                "current_tenant_required",
                "A current workspace is required for platform administration.",
                409,
            )
        return view(*args, **kwargs)

    return decorated

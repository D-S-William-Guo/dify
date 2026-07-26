from unittest.mock import Mock, patch

import pytest

from libs.platform_admin import (
    PlatformAdminHTTPError,
    is_platform_admin_account,
    normalize_platform_admin_email,
    parse_platform_admin_emails,
    platform_admin_current_tenant_required,
    platform_admin_required,
)
from models.account import AccountStatus


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        (" Admin@Example.COM ", "admin@example.com"),
    ],
)
def test_normalize_platform_admin_email(value: str | None, expected: str | None) -> None:
    assert normalize_platform_admin_email(value) == expected


def test_parse_platform_admin_emails_normalizes_deduplicates_and_drops_blanks() -> None:
    assert parse_platform_admin_emails(" Admin@Example.com,admin@example.COM, , Ops@Example.com ") == frozenset(
        {"admin@example.com", "ops@example.com"}
    )


@pytest.mark.parametrize("status", [AccountStatus.PENDING, AccountStatus.UNINITIALIZED, AccountStatus.BANNED])
def test_is_platform_admin_account_requires_active_status(status: AccountStatus) -> None:
    account = Mock(email="admin@example.com", status=status)

    assert not is_platform_admin_account(account, "admin@example.com")


def test_is_platform_admin_account_matches_normalized_active_email() -> None:
    account = Mock(email=" Admin@Example.COM ", status=AccountStatus.ACTIVE)

    assert is_platform_admin_account(account, "admin@example.com")


def test_platform_admin_required_short_circuits_before_view() -> None:
    view = Mock()
    decorated = platform_admin_required(view)

    with patch("libs.platform_admin._resolved_current_account", return_value=None):
        with pytest.raises(PlatformAdminHTTPError) as exc_info:
            decorated()

    assert exc_info.value.error_code == "platform_admin_required"
    assert exc_info.value.code == 403
    view.assert_not_called()


def test_platform_admin_current_tenant_required_returns_stable_conflict() -> None:
    account = Mock(current_tenant_id=None)
    view = Mock()
    decorated = platform_admin_current_tenant_required(view)

    with patch("libs.platform_admin._resolved_current_account", return_value=account):
        with pytest.raises(PlatformAdminHTTPError) as exc_info:
            decorated()

    assert exc_info.value.error_code == "current_tenant_required"
    assert exc_info.value.code == 409
    assert exc_info.value.data == {
        "code": "current_tenant_required",
        "message": "A current workspace is required for platform administration.",
        "status": 409,
    }
    view.assert_not_called()

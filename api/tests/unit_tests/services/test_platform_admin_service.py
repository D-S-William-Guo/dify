import json
import logging
from contextlib import AbstractContextManager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from redis.exceptions import LockError, RedisError
from sqlalchemy.exc import IntegrityError

from libs.platform_admin import PlatformAdminHTTPError
from models.account import Account, AccountStatus, Tenant, TenantAccountJoin, TenantAccountRole, TenantStatus
from services.account_service import RegisterService
from services.platform_admin_service import (
    LOCK_BLOCKING_TIMEOUT_SECONDS,
    LOCK_TTL_SECONDS,
    InviteBatchResult,
    InviteResult,
    PlatformAdminService,
    _Dispatch,
)


def _result(values: list[object]) -> Mock:
    result = Mock()
    result.all.return_value = values
    return result


def _account(email: str, status: AccountStatus) -> Account:
    return Account(
        name=email.split("@")[0],
        email=email,
        password=None,
        password_salt=None,
        interface_language="en-US",
        interface_theme="light",
        timezone="UTC",
        status=status,
        initialized_at=None,
    )


def _tenant() -> Tenant:
    return Tenant(name="Workspace", status=TenantStatus.NORMAL)


def _readable_tenant(*, status: TenantStatus = TenantStatus.NORMAL) -> Tenant:
    tenant = Tenant(name="Workspace", status=status)
    tenant.created_at = datetime(2026, 1, 1)
    tenant.updated_at = datetime(2026, 1, 2)
    return tenant


def _join(tenant: Tenant, account: Account, role: TenantAccountRole = TenantAccountRole.NORMAL) -> TenantAccountJoin:
    return TenantAccountJoin(
        tenant_id=tenant.id,
        account_id=account.id,
        current=False,
        role=role,
        invited_by=None,
    )


def _integrity_error() -> IntegrityError:
    return IntegrityError("statement", {}, RuntimeError("constraint"))


def test_platform_admin_service_exposes_exact_public_methods() -> None:
    expected = {
        "get_workspace",
        "invite_members",
        "list_members",
        "list_workspaces",
        "rename_workspace",
        "update_member_role",
    }
    public_methods = {
        name for name, value in vars(PlatformAdminService).items() if callable(value) and not name.startswith("_")
    }

    assert public_methods == expected
    assert "remove_member" not in vars(PlatformAdminService)


@pytest.mark.parametrize(
    ("page", "limit", "total", "expected_has_more"),
    [(1, 50, 0, False), (1, 50, 50, False), (2, 50, 120, True)],
)
def test_list_workspaces_pagination(page: int, limit: int, total: int, expected_has_more: bool) -> None:
    session = MagicMock()
    session.scalar.return_value = total
    session.scalars.return_value = _result([])

    result = PlatformAdminService(session).list_workspaces(
        page=page,
        limit=limit,
        keyword=None,
        status="normal",
    )

    assert (result.page, result.limit, result.total, result.has_more) == (
        page,
        limit,
        total,
        expected_has_more,
    )


@pytest.mark.parametrize(
    ("status", "keyword", "expected_values"),
    [
        ("normal", None, {TenantStatus.NORMAL}),
        ("archive", "  archived  ", {TenantStatus.ARCHIVE, "%  archived  %"}),
        ("all", "alpha", {"%alpha%"}),
    ],
)
def test_list_workspaces_applies_status_and_keyword(
    status: str,
    keyword: str | None,
    expected_values: set[object],
) -> None:
    session = MagicMock()
    session.scalar.return_value = 0
    session.scalars.return_value = _result([])

    PlatformAdminService(session).list_workspaces(page=1, limit=50, keyword=keyword, status=status)

    count_statement = session.scalar.call_args.args[0]
    assert expected_values <= set(count_statement.compile().params.values())


def test_get_workspace_not_found() -> None:
    session = MagicMock()
    session.scalar.return_value = None

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).get_workspace("missing")

    assert (exc_info.value.error_code, exc_info.value.code) == ("workspace_not_found", 404)


def test_archived_workspace_is_readable() -> None:
    tenant = _readable_tenant(status=TenantStatus.ARCHIVE)
    owner = _account("owner@example.com", AccountStatus.ACTIVE)
    session = MagicMock()
    session.scalar.side_effect = [tenant, 1]
    session.execute.return_value.scalar_one_or_none.return_value = owner

    result = PlatformAdminService(session).get_workspace(tenant.id)

    assert result.status == "archive"
    assert result.owner is not None
    assert result.owner.email == owner.email


def test_rename_workspace_success() -> None:
    tenant = _readable_tenant()
    owner = _account("owner@example.com", AccountStatus.ACTIVE)
    session = MagicMock()
    events: list[str] = []
    session.begin.return_value = _RecordingTransaction(events)
    session.scalar.side_effect = [tenant, 1]
    session.execute.return_value.scalar_one_or_none.return_value = owner

    result = PlatformAdminService(session).rename_workspace(
        workspace_id=tenant.id,
        name="Renamed",
        operator_account_id="operator-id",
    )

    assert result.name == "Renamed"
    session.begin.assert_called_once_with()
    session.flush.assert_called_once_with()
    assert events == ["begin", "commit"]


@pytest.mark.parametrize(
    ("tenant", "expected_code"),
    [(None, "workspace_not_found"), (_readable_tenant(status=TenantStatus.ARCHIVE), "workspace_unavailable")],
)
def test_rename_workspace_rejections(tenant: Tenant | None, expected_code: str) -> None:
    session = MagicMock()
    session.scalar.return_value = tenant

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).rename_workspace(
            workspace_id="workspace-id",
            name="Renamed",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == expected_code
    session.flush.assert_not_called()


def test_rename_integrity_error_maps_conflict_without_success_log(caplog) -> None:
    tenant = _readable_tenant()
    session = MagicMock()
    events: list[str] = []
    session.begin.return_value = _RecordingTransaction(events)
    session.scalar.return_value = tenant
    session.flush.side_effect = _integrity_error()

    with caplog.at_level(logging.INFO), pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).rename_workspace(
            workspace_id=tenant.id,
            name="Renamed",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == "concurrent_operation"
    assert events == ["begin", "rollback"]
    assert "platform_admin.workspace_renamed" not in caplog.text


@pytest.mark.parametrize(
    ("status", "has_join", "expected_action", "requires_setup", "expected_new_joins"),
    [
        (None, False, "account_created", True, 1),
        (AccountStatus.PENDING, False, "membership_created", True, 1),
        (AccountStatus.PENDING, True, "invitation_resent", True, 0),
        (AccountStatus.ACTIVE, False, "invitation_queued", False, 0),
        (AccountStatus.ACTIVE, True, "already_member", None, 0),
    ],
)
def test_invitation_state_matrix(
    monkeypatch,
    status: AccountStatus | None,
    has_join: bool,
    expected_action: str,
    requires_setup: bool | None,
    expected_new_joins: int,
) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", status) if status else None
    join = (
        TenantAccountJoin(
            tenant_id=tenant.id,
            account_id=account.id,
            current=True,
            role=TenantAccountRole.NORMAL,
            invited_by=None,
        )
        if account and has_join
        else None
    )
    session = MagicMock()
    session.scalar.return_value = tenant
    session.scalars.side_effect = [
        _result([account] if account else []),
        _result([join] if join else []),
    ]
    service = PlatformAdminService(session)

    with patch.object(service, "_check_capacity"):
        batch, dispatches, _, _ = service._persist_invitations(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role=TenantAccountRole.NORMAL,
            language="en-US",
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert batch.results[0].action == expected_action
    assert [item.requires_setup for item in dispatches] == ([] if requires_setup is None else [requires_setup])
    added_joins = [
        item for item in (item.args[0] for item in session.add.call_args_list) if isinstance(item, TenantAccountJoin)
    ]
    assert len(added_joins) == expected_new_joins
    if status == AccountStatus.PENDING and not has_join:
        assert added_joins[0].current is False
    if status is None:
        assert added_joins[0].current is True
    if join is not None:
        assert join.current is True


def test_invite_dispatches_explicit_requires_setup_and_revokes_correct_token(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult("member@example.com", "invitation_resent", "failed")],
    )
    session = MagicMock()
    service = PlatformAdminService(session)

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(
            service,
            "_persist_invitations",
            return_value=(batch, [_Dispatch(0, account, True)], 0, tenant),
        ),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            return_value="sensitive-token",
        ) as generate,
        patch(
            "services.platform_admin_service.send_invite_member_mail_task.delay",
            side_effect=RuntimeError("broker"),
        ),
        patch("services.platform_admin_service.RegisterService.revoke_token") as revoke,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=operator,
        )

    assert generate.call_args.kwargs == {"requires_setup": True}
    revoke.assert_called_once_with(None, None, "sensitive-token")
    assert result.results[0].email_delivery == "failed"


@pytest.mark.parametrize(
    ("action", "requires_setup"),
    [
        ("account_created", True),
        ("membership_created", True),
        ("invitation_resent", True),
        ("invitation_queued", False),
    ],
)
def test_final_dispatch_uses_explicit_requires_setup(
    monkeypatch,
    action: str,
    requires_setup: bool,
) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult(account.email, action, "failed")],
    )
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(
            service,
            "_persist_invitations",
            return_value=(batch, [_Dispatch(0, account, requires_setup)], 0, tenant),
        ),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            return_value="token",
        ) as generate,
        patch("services.platform_admin_service.send_invite_member_mail_task.delay") as delay,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=(account.email,),
            role="normal",
            language=None,
            operator=operator,
        )

    generate.assert_called_once_with(tenant, account, "normal", requires_setup=requires_setup)
    delay.assert_called_once()
    assert result.results[0].email_delivery == "queued"


def test_active_existing_member_does_not_generate_token_or_task(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult("member@example.com", "already_member", "not_applicable")],
    )
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(service, "_persist_invitations", return_value=(batch, [], 0, tenant)),
        patch("services.platform_admin_service.RegisterService.generate_invite_token") as generate,
        patch("services.platform_admin_service.send_invite_member_mail_task.delay") as delay,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=operator,
        )

    generate.assert_not_called()
    delay.assert_not_called()
    assert result.results[0].email_delivery == "not_applicable"


def test_token_generation_failure_returns_failed_without_task_or_revoke(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult(account.email, "invitation_resent", "failed")],
    )
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(service, "_persist_invitations", return_value=(batch, [_Dispatch(0, account, True)], 0, tenant)),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            side_effect=RedisError("secret detail"),
        ),
        patch("services.platform_admin_service.RegisterService.revoke_token") as revoke,
        patch("services.platform_admin_service.send_invite_member_mail_task.delay") as delay,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=(account.email,),
            role="normal",
            language=None,
            operator=operator,
        )

    assert result.results[0].email_delivery == "failed"
    revoke.assert_not_called()
    delay.assert_not_called()


def test_token_revoke_failure_is_suppressed_and_sanitized(monkeypatch, caplog) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult(account.email, "invitation_resent", "failed")],
    )
    service = PlatformAdminService(MagicMock())

    with (
        caplog.at_level(logging.WARNING),
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(service, "_persist_invitations", return_value=(batch, [_Dispatch(0, account, True)], 0, tenant)),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            return_value="sensitive-token",
        ),
        patch(
            "services.platform_admin_service.send_invite_member_mail_task.delay",
            side_effect=RuntimeError("full sensitive exception"),
        ),
        patch(
            "services.platform_admin_service.RegisterService.revoke_token",
            side_effect=RedisError("revoke secret"),
        ) as revoke,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=(account.email,),
            role="normal",
            language=None,
            operator=operator,
        )

    revoke.assert_called_once_with(None, None, "sensitive-token")
    assert result.results[0].email_delivery == "failed"
    assert account.email not in caplog.text
    assert "sensitive-token" not in caplog.text
    assert "full sensitive exception" not in caplog.text
    assert "revoke secret" not in caplog.text


@pytest.mark.parametrize("requires_setup", [True, False])
def test_invitation_token_redis_payload_contains_explicit_requires_setup(monkeypatch, requires_setup: bool) -> None:
    monkeypatch.setattr("services.account_service.dify_config.INVITE_EXPIRY_HOURS", 24)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)

    with patch("services.account_service.redis_client.setex") as setex:
        token = RegisterService.generate_invite_token(
            tenant,
            account,
            "normal",
            requires_setup=requires_setup,
        )

    key, expiry, raw_payload = setex.call_args.args
    assert key == f"member_invite:token:{token}"
    assert expiry == 24 * 60 * 60
    assert json.loads(raw_payload)["requires_setup"] is requires_setup


class _RecordingLock(AbstractContextManager["_RecordingLock"]):
    def __init__(self, key: str, events: list[str]) -> None:
        self.key = key
        self.events = events

    def __enter__(self) -> "_RecordingLock":
        self.events.append(f"enter:{self.key}")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.events.append(f"exit:{self.key}")


class _RecordingTransaction(AbstractContextManager["_RecordingTransaction"]):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def __enter__(self) -> "_RecordingTransaction":
        self.events.append("begin")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.events.append("commit" if exc_type is None else "rollback")


def test_invite_lock_order_ttl_timeout_and_reverse_release(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    events: list[str] = []
    tenant = _tenant()
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    service = PlatformAdminService(MagicMock())
    batch = InviteBatchResult(workspace_id=tenant.id, results=[])

    def lock_factory(key: str, **kwargs: int) -> _RecordingLock:
        assert kwargs == {"timeout": LOCK_TTL_SECONDS, "blocking_timeout": LOCK_BLOCKING_TIMEOUT_SECONDS}
        return _RecordingLock(key, events)

    with (
        patch("services.platform_admin_service.redis_client.lock", side_effect=lock_factory),
        patch.object(service, "_persist_invitations", return_value=(batch, [], 0, tenant)),
    ):
        service.invite_members(
            workspace_id=tenant.id,
            emails=("z@example.com", "a@example.com"),
            role="normal",
            language=None,
            operator=operator,
        )

    entered = [event.removeprefix("enter:") for event in events if event.startswith("enter:")]
    exited = [event.removeprefix("exit:") for event in events if event.startswith("exit:")]
    assert entered[:2] == [f"platform_admin:invite:tenant:{tenant.id}", "platform_admin:invite:seats"]
    assert entered[2:] == sorted(entered[2:])
    assert exited == list(reversed(entered))
    assert all("a@example.com" not in key and "z@example.com" not in key for key in entered)


class _FailingLock(AbstractContextManager["_FailingLock"]):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def __enter__(self) -> "_FailingLock":
        raise self.error

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


@pytest.mark.parametrize("error", [LockError("timeout"), RedisError("unavailable")])
def test_lock_failures_map_to_concurrent_operation(monkeypatch, error: Exception) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=_FailingLock(error)),
        patch.object(service, "_persist_invitations") as persist,
        pytest.raises(PlatformAdminHTTPError) as exc_info,
    ):
        service.invite_members(
            workspace_id="workspace-id",
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert (exc_info.value.error_code, exc_info.value.code) == ("concurrent_operation", 409)
    persist.assert_not_called()


def test_partial_lock_failure_releases_acquired_locks_in_reverse_order(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    events: list[str] = []
    calls = 0

    def lock_factory(key: str, **kwargs: int) -> AbstractContextManager:
        nonlocal calls
        del kwargs
        calls += 1
        if calls == 3:
            return _FailingLock(LockError("timeout"))
        return _RecordingLock(key, events)

    with (
        patch("services.platform_admin_service.redis_client.lock", side_effect=lock_factory),
        pytest.raises(PlatformAdminHTTPError),
    ):
        PlatformAdminService(MagicMock()).invite_members(
            workspace_id="workspace-id",
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    entered = [event.removeprefix("enter:") for event in events if event.startswith("enter:")]
    exited = [event.removeprefix("exit:") for event in events if event.startswith("exit:")]
    assert exited == list(reversed(entered))


def test_rbac_invite_fails_before_lock_or_database(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", True)
    session = MagicMock()
    service = PlatformAdminService(session)

    with patch("services.platform_admin_service.redis_client.lock") as lock:
        with pytest.raises(PlatformAdminHTTPError) as exc_info:
            service.invite_members(
                workspace_id="workspace-id",
                emails=("member@example.com",),
                role="normal",
                language=None,
                operator=_account("operator@example.com", AccountStatus.ACTIVE),
            )

    assert exc_info.value.error_code == "rbac_mode_not_supported"
    lock.assert_not_called()
    assert session.mock_calls == []


def test_billing_freeze_rejects_new_account_before_database_write_or_dispatch(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", True)
    tenant = _tenant()
    session = MagicMock()
    session.scalar.return_value = tenant
    session.scalars.side_effect = [_result([]), _result([])]
    service = PlatformAdminService(session)

    with (
        patch.object(service, "_check_capacity"),
        patch("services.platform_admin_service.BillingService.is_email_in_freeze", return_value=True),
        pytest.raises(PlatformAdminHTTPError) as exc_info,
    ):
        service._persist_invitations(
            workspace_id=tenant.id,
            emails=("frozen@example.com",),
            role=TenantAccountRole.NORMAL,
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert exc_info.value.error_code == "email_in_freeze"
    session.add.assert_not_called()


def test_invitation_begins_transaction_before_first_injected_session_query(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    events: list[str] = []
    tenant = _tenant()
    session = MagicMock()
    session.begin.return_value = _RecordingTransaction(events)

    def scalar(*args, **kwargs):
        del args, kwargs
        events.append("query")
        return tenant

    session.scalar.side_effect = scalar
    session.scalars.return_value = _result([])
    service = PlatformAdminService(session)

    with patch.object(service, "_check_capacity"):
        service._persist_invitations(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role=TenantAccountRole.NORMAL,
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert events[0:2] == ["begin", "query"]
    assert events[-1] == "commit"


def test_token_and_task_run_only_after_transaction_commit(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", False)
    events: list[str] = []
    tenant = _tenant()
    session = MagicMock()
    session.begin.return_value = _RecordingTransaction(events)
    session.scalar.return_value = tenant
    session.scalars.return_value = _result([])
    service = PlatformAdminService(session)

    def generate(*args, **kwargs) -> str:
        del args, kwargs
        events.append("token")
        return "token"

    def delay(**kwargs) -> None:
        del kwargs
        events.append("task")

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(service, "_check_capacity"),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            side_effect=generate,
        ),
        patch("services.platform_admin_service.send_invite_member_mail_task.delay", side_effect=delay),
    ):
        service.invite_members(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert events == ["begin", "commit", "token", "task"]


@pytest.mark.parametrize("failure_point", ["feature", "billing", "flush"])
def test_invitation_transaction_failures_do_not_dispatch_or_report_success(
    monkeypatch,
    failure_point: str,
    caplog,
) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr(
        "services.platform_admin_service.dify_config.BILLING_ENABLED",
        failure_point == "billing",
    )
    tenant = _tenant()
    session = MagicMock()
    session.scalar.return_value = tenant
    session.scalars.return_value = _result([])
    events: list[str] = []
    session.begin.return_value = _RecordingTransaction(events)
    if failure_point == "flush":
        session.flush.side_effect = _integrity_error()
    service = PlatformAdminService(session)

    def get_features(*args, **kwargs):
        del args, kwargs
        if failure_point == "feature":
            raise RuntimeError("feature sensitive")
        return SimpleNamespace(
            workspace_members=SimpleNamespace(enabled=False),
            billing=SimpleNamespace(enabled=False),
        )

    def is_frozen(*args, **kwargs) -> bool:
        del args, kwargs
        if failure_point == "billing":
            raise RuntimeError("billing sensitive")
        return False

    expected_exception = PlatformAdminHTTPError if failure_point == "flush" else RuntimeError

    with (
        caplog.at_level(logging.INFO),
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch("services.platform_admin_service.FeatureService.get_features", side_effect=get_features),
        patch(
            "services.platform_admin_service.BillingService.is_email_in_freeze",
            side_effect=is_frozen,
        ),
        patch("services.platform_admin_service.RegisterService.generate_invite_token") as generate,
        patch("services.platform_admin_service.send_invite_member_mail_task.delay") as delay,
        pytest.raises(expected_exception),
    ):
        service.invite_members(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert events[-1] == "rollback"
    generate.assert_not_called()
    delay.assert_not_called()
    assert "platform_admin.members_invited" not in caplog.text


def test_billing_cache_failure_is_post_commit_best_effort_and_dispatch_continues(monkeypatch, caplog) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", True)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.PENDING)
    operator = _account("operator@example.com", AccountStatus.ACTIVE)
    batch = InviteBatchResult(
        workspace_id=tenant.id,
        results=[InviteResult(account.email, "membership_created", "failed")],
    )
    service = PlatformAdminService(MagicMock())
    events: list[str] = []

    def persisted(**kwargs):
        del kwargs
        events.append("committed")
        return batch, [_Dispatch(0, account, True)], 1, tenant

    def cache_failure(tenant_id: str) -> None:
        assert tenant_id == tenant.id
        events.append("cache")
        raise RuntimeError("sensitive external failure")

    def generate(*args, **kwargs) -> str:
        del args, kwargs
        events.append("token")
        return "sensitive-token"

    with (
        caplog.at_level(logging.WARNING),
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(service, "_persist_invitations", side_effect=persisted),
        patch(
            "services.platform_admin_service.BillingService.clean_billing_info_cache",
            side_effect=cache_failure,
        ),
        patch(
            "services.platform_admin_service.RegisterService.generate_invite_token",
            side_effect=generate,
        ),
        patch("services.platform_admin_service.send_invite_member_mail_task.delay") as delay,
    ):
        result = service.invite_members(
            workspace_id=tenant.id,
            emails=(account.email,),
            role="normal",
            language=None,
            operator=operator,
        )

    assert events == ["committed", "cache", "token"]
    delay.assert_called_once()
    assert result.results[0].email_delivery == "queued"
    assert account.email not in caplog.text
    assert "sensitive-token" not in caplog.text
    assert "sensitive external failure" not in caplog.text


@pytest.mark.parametrize(
    ("billing_enabled", "immediate_join_count", "expected_calls"),
    [(False, 1, 0), (True, 0, 0), (True, 1, 1)],
)
def test_billing_cache_only_runs_for_immediate_join_when_billing_enabled(
    monkeypatch,
    billing_enabled: bool,
    immediate_join_count: int,
    expected_calls: int,
) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", billing_enabled)
    tenant = _tenant()
    service = PlatformAdminService(MagicMock())
    batch = InviteBatchResult(workspace_id=tenant.id, results=[])

    with (
        patch("services.platform_admin_service.redis_client.lock", return_value=MagicMock()),
        patch.object(
            service,
            "_persist_invitations",
            return_value=(batch, [], immediate_join_count, tenant),
        ),
        patch("services.platform_admin_service.BillingService.clean_billing_info_cache") as clean,
    ):
        service.invite_members(
            workspace_id=tenant.id,
            emails=("member@example.com",),
            role="normal",
            language=None,
            operator=_account("operator@example.com", AccountStatus.ACTIVE),
        )

    assert clean.call_count == expected_calls


def test_capacity_zero_increment_skips_all_external_and_database_calls() -> None:
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.FeatureService.get_features") as features,
        patch("services.platform_admin_service.FeatureService.get_system_features") as system_features,
    ):
        service._check_capacity(tenant_id="workspace-id", required_memberships=0, new_account_count=0)

    features.assert_not_called()
    system_features.assert_not_called()
    service._session.scalar.assert_not_called()


def test_enterprise_capacity_checks_workspace_but_skips_seats_for_existing_accounts(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", True)
    features = SimpleNamespace(workspace_members=SimpleNamespace(enabled=True, is_available=Mock(return_value=True)))
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.FeatureService.get_features", return_value=features),
        patch("services.platform_admin_service.FeatureService.get_system_features") as system_features,
    ):
        service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=0)

    features.workspace_members.is_available.assert_called_once_with(1)
    system_features.assert_not_called()


def test_enterprise_workspace_unavailable_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", True)
    features = SimpleNamespace(workspace_members=SimpleNamespace(enabled=True, is_available=Mock(return_value=False)))
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.FeatureService.get_features", return_value=features),
        patch("services.platform_admin_service.FeatureService.get_system_features") as system_features,
        pytest.raises(PlatformAdminHTTPError) as exc_info,
    ):
        service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=1)

    assert exc_info.value.error_code == "workspace_member_limit_exceeded"
    system_features.assert_not_called()


def test_enterprise_seat_unavailable_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", True)
    features = SimpleNamespace(workspace_members=SimpleNamespace(enabled=True, is_available=Mock(return_value=True)))
    seats = SimpleNamespace(is_available=Mock(return_value=False))
    system_features = SimpleNamespace(license=SimpleNamespace(seats=seats))
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.FeatureService.get_features", return_value=features),
        patch(
            "services.platform_admin_service.FeatureService.get_system_features",
            return_value=system_features,
        ),
        pytest.raises(PlatformAdminHTTPError) as exc_info,
    ):
        service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=1)

    assert exc_info.value.error_code == "seat_limit_exceeded"
    seats.is_available.assert_called_once_with(1)


def test_enterprise_capacity_does_not_apply_billing_count(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", True)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", True)
    features = SimpleNamespace(
        workspace_members=SimpleNamespace(enabled=True, is_available=Mock(return_value=True)),
        billing=SimpleNamespace(enabled=True),
        members=SimpleNamespace(limit=1),
    )
    service = PlatformAdminService(MagicMock())

    with (
        patch("services.platform_admin_service.FeatureService.get_features", return_value=features),
        patch("services.platform_admin_service.FeatureService.get_system_features") as system_features,
    ):
        service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=0)

    system_features.assert_not_called()
    service._session.scalar.assert_not_called()


@pytest.mark.parametrize(("limit", "current", "raises"), [(0, 100, False), (2, 1, False), (1, 1, True)])
def test_billing_capacity_unlimited_equal_and_exceeded(monkeypatch, limit: int, current: int, raises: bool) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", True)
    features = SimpleNamespace(
        billing=SimpleNamespace(enabled=True),
        members=SimpleNamespace(limit=limit),
    )
    session = MagicMock()
    session.scalar.return_value = current
    service = PlatformAdminService(session)

    with patch("services.platform_admin_service.FeatureService.get_features", return_value=features):
        if raises:
            with pytest.raises(PlatformAdminHTTPError) as exc_info:
                service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=1)
            assert exc_info.value.error_code == "workspace_member_limit_exceeded"
        else:
            service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=1)


def test_billing_disabled_feature_does_not_query_member_count(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.ENTERPRISE_ENABLED", False)
    monkeypatch.setattr("services.platform_admin_service.dify_config.BILLING_ENABLED", True)
    features = SimpleNamespace(billing=SimpleNamespace(enabled=False))
    service = PlatformAdminService(MagicMock())

    with patch("services.platform_admin_service.FeatureService.get_features", return_value=features):
        service._check_capacity(tenant_id="workspace-id", required_memberships=1, new_account_count=1)

    service._session.scalar.assert_not_called()


def test_rbac_member_read_hides_legacy_role(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", True)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.ACTIVE)
    join = TenantAccountJoin(
        tenant_id=tenant.id,
        account_id=account.id,
        current=True,
        role=TenantAccountRole.ADMIN,
        invited_by=None,
    )
    join.created_at = MagicMock()
    account.last_active_at = MagicMock()
    session = MagicMock()
    session.scalar.return_value = tenant
    session.execute.return_value.all.return_value = [(account, join)]

    result = PlatformAdminService(session).list_members(tenant.id)

    assert result[0].role is None
    assert result[0].role_source == "rbac_unavailable"
    assert result[0].mutation_supported is False


@pytest.mark.parametrize("status", [AccountStatus.ACTIVE, AccountStatus.PENDING])
def test_role_update_allows_active_and_pending(monkeypatch, status: AccountStatus) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", status)
    join = _join(tenant, account)
    session = MagicMock()
    session.scalar.side_effect = [tenant, join, account]

    result = PlatformAdminService(session).update_member_role(
        workspace_id=tenant.id,
        member_id=account.id,
        new_role="admin",
        operator_account_id="operator-id",
    )

    assert result.result == "success"
    assert join.role == TenantAccountRole.ADMIN
    session.begin.assert_called_once_with()
    session.flush.assert_called_once_with()


def test_role_update_member_not_found(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    tenant = _tenant()
    session = MagicMock()
    session.scalar.side_effect = [tenant, None]

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).update_member_role(
            workspace_id=tenant.id,
            member_id="missing",
            new_role="admin",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == "member_not_found"
    session.flush.assert_not_called()


def test_role_update_rejects_owner_and_already_assigned(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.ACTIVE)

    for role, new_role, expected_code in [
        (TenantAccountRole.OWNER, "admin", "owner_operation_deferred"),
        (TenantAccountRole.ADMIN, "admin", "role_already_assigned"),
    ]:
        session = MagicMock()
        session.scalar.side_effect = [tenant, _join(tenant, account, role), account]
        with pytest.raises(PlatformAdminHTTPError) as exc_info:
            PlatformAdminService(session).update_member_role(
                workspace_id=tenant.id,
                member_id=account.id,
                new_role=new_role,
                operator_account_id="operator-id",
            )
        assert exc_info.value.error_code == expected_code
        session.flush.assert_not_called()


def test_rbac_role_update_fails_before_database(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", True)
    session = MagicMock()

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).update_member_role(
            workspace_id="workspace-id",
            member_id="member-id",
            new_role="admin",
            operator_account_id="operator-id",
        )

    assert (exc_info.value.error_code, exc_info.value.code) == ("rbac_mode_not_supported", 503)
    assert session.mock_calls == []


def test_owner_role_update_is_rejected_before_database(monkeypatch) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    session = MagicMock()

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).update_member_role(
            workspace_id="workspace-id",
            member_id="member-id",
            new_role="owner",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == "owner_assignment_deferred"
    assert session.mock_calls == []


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (AccountStatus.UNINITIALIZED, "account_uninitialized"),
        (AccountStatus.BANNED, "account_disabled"),
        (AccountStatus.CLOSED, "account_disabled"),
    ],
)
def test_role_update_rejects_disallowed_account_status(
    monkeypatch,
    status: AccountStatus,
    expected_code: str,
) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", status)
    join = _join(tenant, account)
    session = MagicMock()
    session.scalar.side_effect = [tenant, join, account]

    with pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).update_member_role(
            workspace_id=tenant.id,
            member_id=account.id,
            new_role="admin",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == expected_code
    session.begin.assert_called_once_with()
    session.flush.assert_not_called()


def test_role_update_integrity_error_has_no_success_log(monkeypatch, caplog) -> None:
    monkeypatch.setattr("services.platform_admin_service.dify_config.RBAC_ENABLED", False)
    tenant = _tenant()
    account = _account("member@example.com", AccountStatus.ACTIVE)
    join = _join(tenant, account)
    session = MagicMock()
    events: list[str] = []
    session.begin.return_value = _RecordingTransaction(events)
    session.scalar.side_effect = [tenant, join, account]
    session.flush.side_effect = _integrity_error()

    with caplog.at_level(logging.INFO), pytest.raises(PlatformAdminHTTPError) as exc_info:
        PlatformAdminService(session).update_member_role(
            workspace_id=tenant.id,
            member_id=account.id,
            new_role="admin",
            operator_account_id="operator-id",
        )

    assert exc_info.value.error_code == "concurrent_operation"
    assert events == ["begin", "rollback"]
    assert "platform_admin.member_role_updated" not in caplog.text

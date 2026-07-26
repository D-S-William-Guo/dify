import ast
import inspect
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from controllers.console import platform_admin
from libs.platform_admin import PlatformAdminHTTPError
from models.account import Account, AccountStatus


def _account(email: str, status: AccountStatus) -> Account:
    return Account(
        name="Admin",
        email=email,
        password=None,
        password_salt=None,
        interface_language="en-US",
        interface_theme="light",
        timezone="UTC",
        status=status,
        initialized_at=None,
    )


def _innermost(method):
    while hasattr(method, "__wrapped__"):
        method = method.__wrapped__
    return method


def test_platform_admin_controller_defines_exact_seven_method_route_pairs() -> None:
    expected = {
        ("GET", "/account/platform-admin-status"),
        ("GET", "/platform-admin/workspaces"),
        ("GET", "/platform-admin/workspaces/<uuid:workspace_id>"),
        ("PATCH", "/platform-admin/workspaces/<uuid:workspace_id>"),
        ("GET", "/platform-admin/workspaces/<uuid:workspace_id>/members"),
        ("POST", "/platform-admin/workspaces/<uuid:workspace_id>/members/invitations"),
        ("PATCH", "/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role"),
    }
    tree = ast.parse(inspect.getsource(platform_admin))
    actual = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        route = None
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "route"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
            ):
                route = decorator.args[0].value
        if route is None:
            continue
        actual.update(
            (method.name.upper(), route)
            for method in node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            and method.name in {"get", "post", "patch", "delete"}
        )

    assert actual == expected


def test_platform_admin_defines_exact_fourteen_dtos() -> None:
    dto_names = {
        name
        for name, value in vars(platform_admin).items()
        if inspect.isclass(value)
        and name.startswith("PlatformAdmin")
        and name.endswith(("Payload", "Query", "Response"))
    }

    assert len(dto_names) == 14


def test_invite_payload_normalizes_and_rejects_duplicates() -> None:
    payload = platform_admin.PlatformAdminMemberInvitePayload.model_validate(
        {"emails": [" Admin@Example.com "], "role": "normal"}
    )
    assert payload.emails == ["admin@example.com"]

    with pytest.raises(ValidationError, match="duplicate_email"):
        platform_admin.PlatformAdminMemberInvitePayload.model_validate(
            {"emails": ["Admin@example.com", " admin@EXAMPLE.com "], "role": "normal"}
        )


def test_owner_cannot_enter_invite_or_role_payload() -> None:
    with pytest.raises(ValidationError):
        platform_admin.PlatformAdminMemberInvitePayload.model_validate(
            {"emails": ["member@example.com"], "role": "owner"}
        )
    with pytest.raises(ValidationError):
        platform_admin.PlatformAdminMemberRoleUpdatePayload.model_validate({"role": "owner"})


def test_invite_response_has_no_sensitive_fields() -> None:
    fields = platform_admin.PlatformAdminMemberInviteResultResponse.model_fields

    assert set(fields) == {"email", "action", "email_delivery"}
    assert "token" not in fields
    assert "activation_url" not in fields


@pytest.mark.parametrize(
    ("email", "status", "configured", "expected"),
    [
        ("admin@example.com", AccountStatus.ACTIVE, "admin@example.com", True),
        ("user@example.com", AccountStatus.ACTIVE, "admin@example.com", False),
        ("admin@example.com", AccountStatus.PENDING, "admin@example.com", False),
    ],
)
def test_status_returns_actual_platform_admin_result(
    monkeypatch,
    email: str,
    status: AccountStatus,
    configured: str,
    expected: bool,
) -> None:
    monkeypatch.setattr(platform_admin, "current_user", _account(email, status))
    monkeypatch.setattr("libs.platform_admin.dify_config.PLATFORM_ADMIN_EMAILS", configured)
    monkeypatch.setattr(platform_admin.dify_config, "RBAC_ENABLED", False)

    result = _innermost(platform_admin.PlatformAdminStatusApi.get)(platform_admin.PlatformAdminStatusApi())

    assert result == {"is_platform_admin": expected, "mutation_supported": expected}


def test_platform_admin_http_error_data_contract() -> None:
    error = PlatformAdminHTTPError("current_tenant_required", "Current workspace required.", 409)

    assert error.data == {
        "code": "current_tenant_required",
        "message": "Current workspace required.",
        "status": 409,
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (platform_admin.PlatformAdminWorkspaceListQuery, {"unexpected": True}),
        (platform_admin.PlatformAdminWorkspaceRenamePayload, {"name": "Name", "unexpected": True}),
        (
            platform_admin.PlatformAdminMemberInvitePayload,
            {"emails": ["member@example.com"], "role": "normal", "unexpected": True},
        ),
        (platform_admin.PlatformAdminMemberRoleUpdatePayload, {"role": "normal", "unexpected": True}),
    ],
)
def test_request_models_forbid_extra_fields(model, payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate(payload)


def test_response_serialization_failure_is_not_hidden() -> None:
    with pytest.raises(ValidationError):
        platform_admin._response(
            platform_admin.PlatformAdminWorkspaceResponse,
            {
                "id": "workspace-id",
                "name": "Workspace",
                "plan": "basic",
                "status": "normal",
                "created_at": "invalid",
                "updated_at": "invalid",
                "member_count": 1,
                "owner": None,
            },
        )


def test_with_session_wrapper_commit_is_not_a_second_business_transaction() -> None:
    session = MagicMock()
    session.begin.return_value = nullcontext()
    session_context = MagicMock()
    session_context.__enter__.return_value = session

    class Handler:
        @platform_admin.with_session
        def patch(self, injected_session):
            with injected_session.begin():
                injected_session.flush()
            return {"result": "success"}

    with patch(
        "controllers.common.session.session_factory.create_session",
        return_value=session_context,
    ):
        result = Handler().patch()

    assert result == {"result": "success"}
    session.begin.assert_called_once_with()
    session.flush.assert_called_once_with()
    session.commit.assert_called_once_with()


def test_management_decorator_order() -> None:
    method = platform_admin.PlatformAdminWorkspaceListApi.get
    wrappers = []
    while hasattr(method, "__wrapped__"):
        wrappers.append(method.__code__.co_qualname.partition(".<locals>")[0])
        method = method.__wrapped__

    expected = [
        "setup_required",
        "login_required",
        "platform_admin_required",
        "platform_admin_current_tenant_required",
        "account_initialization_required",
        "with_session",
    ]
    assert [name for name in wrappers if name in expected] == expected


def test_status_endpoint_does_not_require_current_tenant_or_initialization() -> None:
    method = platform_admin.PlatformAdminStatusApi.get
    wrappers = []
    while hasattr(method, "__wrapped__"):
        wrappers.append(method.__code__.co_qualname.partition(".<locals>")[0])
        method = method.__wrapped__

    assert "setup_required" in wrappers
    assert "login_required" in wrappers
    assert "account_initialization_required" not in wrappers
    assert "platform_admin_current_tenant_required" not in wrappers

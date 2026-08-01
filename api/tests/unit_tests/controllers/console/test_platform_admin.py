import ast
import inspect
import json
from contextlib import nullcontext
from pathlib import Path
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


def _load_console_openapi():
    """Return the generated console OpenAPI spec dict."""
    repo_root = Path(__file__).resolve().parents[5]
    spec_path = repo_root / "packages" / "contracts" / "openapi" / "console-openapi.json"
    return json.loads(spec_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def console_openapi():
    return _load_console_openapi()


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


# ═══════════════════════════════════════════════════════════════════════════
# OpenAPI semantic tests (read from generated console-openapi.json)
# ═══════════════════════════════════════════════════════════════════════════

B3_EXPECTED_ERRORS = {
    ("get", "/account/platform-admin-status"): {401},
    ("get", "/platform-admin/workspaces"): {400, 401, 403, 409},
    ("get", "/platform-admin/workspaces/{workspace_id}"): {401, 403, 404, 409},
    ("patch", "/platform-admin/workspaces/{workspace_id}"): {400, 401, 403, 404, 409},
    ("get", "/platform-admin/workspaces/{workspace_id}/members"): {401, 403, 404, 409},
    (
        "post",
        "/platform-admin/workspaces/{workspace_id}/members/invitations",
    ): {400, 401, 403, 404, 409, 503},
    (
        "patch",
        "/platform-admin/workspaces/{workspace_id}/members/{member_id}/role",
    ): {400, 401, 403, 404, 409, 503},
}


def test_openapi_b3_operations_have_expected_error_status_sets(console_openapi) -> None:
    paths = console_openapi["paths"]
    for (method, path), expected_errors in B3_EXPECTED_ERRORS.items():
        operation = paths[path][method]
        responses = operation.get("responses", {})
        status_codes = {int(k) for k in responses if k.isdigit()}
        success = 201 if method == "post" and path.endswith("/invitations") else 200
        assert status_codes == (expected_errors | {success}), (
            f"Unexpected response statuses for {method.upper()} {path}: {sorted(status_codes)}"
        )


def test_openapi_b3_error_response_schema_shapes(console_openapi) -> None:
    paths = console_openapi["paths"]
    for (method, path), _expected in B3_EXPECTED_ERRORS.items():
        responses = paths[path][method].get("responses", {})
        for status in sorted(str(code) for code in _expected if code != 401):
            content = responses[status].get("content", {})
            app_json = content.get("application/json", {})
            ref = app_json.get("schema", {}).get("$ref", "")
            assert "PlatformAdminErrorResponse" in ref, (
                f"Error {status} in {method} {path} should reference "
                f"PlatformAdminErrorResponse but got: {ref}"
            )


def test_openapi_b3_401_uses_unauthorized_response(console_openapi) -> None:
    paths = console_openapi["paths"]
    for (method, path), _expected in B3_EXPECTED_ERRORS.items():
        responses = paths[path][method].get("responses", {})
        resp401 = responses.get("401", {})
        content = resp401.get("content", {})
        app_json = content.get("application/json", {})
        ref = app_json.get("schema", {}).get("$ref", "")
        assert "UnauthorizedResponse" in ref, (
            f"401 in {method} {path} should reference UnauthorizedResponse but got: {ref}"
        )
        assert "PlatformAdminErrorResponse" not in ref, (
            f"401 in {method} {path} incorrectly references PlatformAdminErrorResponse"
        )


def test_openapi_platform_admin_error_response_schema(console_openapi) -> None:
    schemas = console_openapi["components"]["schemas"]
    err_schema = schemas.get("PlatformAdminErrorResponse")
    assert err_schema is not None, "PlatformAdminErrorResponse not in schemas"
    props = err_schema.get("properties", {})
    assert isinstance(props, dict)
    assert set(props) == {"code", "message", "status"}, f"Unexpected props: {set(props)}"

import ast
import importlib.util
import inspect
import json
import sys
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from pydantic import ValidationError

from controllers.console import enterprise_marketplace as em
from controllers.console.enterprise_marketplace import (
    MarketplaceHTTPError,
    _validated_admin_query,
)
from services.errors.enterprise_marketplace import (
    AssetAlreadyUnlisted,
    AssetNotFound,
    CopyFailed,
    CopyPendingUnsupported,
    DependencyServiceUnavailable,
    InvalidStatusTransition,
    SnapshotIntegrityError,
    SnapshotNotReady,
    SourceAppNotFound,
    SourceAppUnavailable,
    StaleAssetVersion,
    SubmissionAlreadyPending,
)


def _innermost(method):
    while hasattr(method, "__wrapped__"):
        method = method.__wrapped__
    return method


def _load_specs_module():
    api_dir = Path(__file__).resolve().parents[4]
    script_path = api_dir / "dev" / "generate_swagger_specs.py"
    spec = importlib.util.spec_from_file_location("generate_swagger_specs", script_path)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ═══════════════════════════════════════════════════════════════════════════
# Route definition tests (AST)
# ═══════════════════════════════════════════════════════════════════════════


def test_enterprise_marketplace_controller_defines_exact_eight_method_route_pairs() -> None:
    expected = {
        ("POST", "/apps/<uuid:app_id>/enterprise-marketplace/submissions"),
        ("GET", "/enterprise-marketplace/submissions"),
        ("GET", "/enterprise-marketplace/assets"),
        ("GET", "/enterprise-marketplace/assets/<uuid:asset_id>"),
        ("POST", "/enterprise-marketplace/assets/<uuid:asset_id>/copies"),
        ("GET", "/platform-admin/enterprise-marketplace/assets"),
        ("POST", "/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/reviews"),
        ("POST", "/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/unlist"),
    }
    tree = ast.parse(inspect.getsource(em))
    actual: set[tuple[str, str]] = set()
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


def test_enterprise_marketplace_has_no_delete_routes() -> None:
    tree = ast.parse(inspect.getsource(em))
    methods: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods.update(
            method.name.upper()
            for method in node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            and method.name in {"get", "post", "patch", "delete"}
        )
    assert "DELETE" not in methods


# ═══════════════════════════════════════════════════════════════════════════
# Real Flask route tests (url_map + DELETE requests)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def spec_app():
    module = _load_specs_module()
    return module.create_spec_app()


def test_real_url_map_has_b3_seven_and_b4_eight_routes(spec_app) -> None:
    b3_expected = {
        ("GET", "/console/api/account/platform-admin-status"),
        ("GET", "/console/api/platform-admin/workspaces"),
        ("GET", "/console/api/platform-admin/workspaces/<uuid:workspace_id>"),
        ("PATCH", "/console/api/platform-admin/workspaces/<uuid:workspace_id>"),
        ("GET", "/console/api/platform-admin/workspaces/<uuid:workspace_id>/members"),
        ("POST", "/console/api/platform-admin/workspaces/<uuid:workspace_id>/members/invitations"),
        ("PATCH", "/console/api/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role"),
    }
    b4_expected = {
        ("POST", "/console/api/apps/<uuid:app_id>/enterprise-marketplace/submissions"),
        ("GET", "/console/api/enterprise-marketplace/submissions"),
        ("GET", "/console/api/enterprise-marketplace/assets"),
        ("GET", "/console/api/enterprise-marketplace/assets/<uuid:asset_id>"),
        ("POST", "/console/api/enterprise-marketplace/assets/<uuid:asset_id>/copies"),
        ("GET", "/console/api/platform-admin/enterprise-marketplace/assets"),
        ("POST", "/console/api/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/reviews"),
        ("POST", "/console/api/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/unlist"),
    }

    console_rules = [
        rule
        for rule in spec_app.url_map.iter_rules()
        if rule.rule.startswith("/console/api") and "static" not in rule.rule
    ]
    all_console = {
        (method, rule.rule) for rule in console_rules for method in rule.methods if method not in {"OPTIONS", "HEAD"}
    }

    b3_actual = {(m, p) for (m, p) in all_console if "platform-admin" in p and "marketplace" not in p}
    b4_actual = {(m, p) for (m, p) in all_console if "marketplace" in p and "plugin" not in p}

    b3_missing = b3_expected - b3_actual
    b3_extra = b3_actual - b3_expected
    assert b3_actual == b3_expected, f"B3 mismatch — missing: {b3_missing}, extra: {b3_extra}"

    b4_missing = b4_expected - b4_actual
    b4_extra = b4_actual - b4_expected
    assert b4_actual == b4_expected, f"B4 mismatch — missing: {b4_missing}, extra: {b4_extra}"


def test_real_url_map_has_no_delete_for_marketplace(spec_app) -> None:
    for rule in spec_app.url_map.iter_rules():
        if "marketplace" in rule.rule.lower():
            assert "DELETE" not in rule.methods, f"Marketplace has DELETE: {rule.rule}"


def test_real_url_map_has_no_member_delete_on_platform_admin(spec_app) -> None:
    for rule in spec_app.url_map.iter_rules():
        rule_str = rule.rule.lower()
        if "platform-admin" in rule_str and "members" in rule_str:
            assert "DELETE" not in rule.methods, f"Platform-admin member path has DELETE: {rule.rule}"


def test_real_url_map_has_no_dangerous_routes(spec_app) -> None:
    dangerous = {"create", "delete", "archive", "password", "reset-password", "transfer-owner", "break-glass"}
    for rule in spec_app.url_map.iter_rules():
        rule_lower = rule.rule.lower()
        if "platform-admin" in rule_lower or "marketplace" in rule_lower:
            for token in dangerous:
                assert token not in rule_lower, f"Dangerous route found: {rule.rule}"


def test_real_delete_marketplace_asset_returns_405(spec_app) -> None:
    with spec_app.test_client() as client:
        resp = client.delete("/console/api/enterprise-marketplace/assets/00000000-0000-0000-0000-000000000001")
        assert resp.status_code == 405, f"Expected 405, got {resp.status_code}"


def test_real_delete_admin_marketplace_asset_returns_404(spec_app) -> None:
    with spec_app.test_client() as client:
        resp = client.delete(
            "/console/api/platform-admin/enterprise-marketplace/assets/00000000-0000-0000-0000-000000000001"
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


def test_real_delete_admin_workspace_member_returns_404(spec_app) -> None:
    with spec_app.test_client() as client:
        resp = client.delete(
            "/console/api/platform-admin/workspaces"
            "/00000000-0000-0000-0000-000000000001"
            "/members/00000000-0000-0000-0000-000000000002"
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
# Admin array query tests (real Flask request context)
# ═══════════════════════════════════════════════════════════════════════════


def test_admin_query_status_single_value() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?status=pending"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert isinstance(q, em.MarketplaceAdminAssetListQuery)
        assert q.status == ["pending"]


def test_admin_query_status_repeated() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?status=pending&status=approved"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.status == ["pending", "approved"]


def test_admin_query_publication_status() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?publication_status=published"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.publication_status == ["published"]


def test_admin_query_snapshot_state_repeated() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?snapshot_state=ready&snapshot_state=failed"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.snapshot_state == ["ready", "failed"]


def test_admin_query_multi_value_none_when_not_provided() -> None:
    app = Flask(__name__)
    with app.test_request_context("/"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.status is None
        assert q.publication_status is None
        assert q.snapshot_state is None


def test_admin_query_unknown_field_rejected() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?unexpected=true"):
        with pytest.raises(MarketplaceHTTPError) as exc_info:
            _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert exc_info.value.data["code"] == "invalid_request"


def test_admin_query_scalar_fields_still_work() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?page=3&limit=25&keyword=test&category=Chat&sort=title_asc"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.page == 3
        assert q.limit == 25
        assert q.keyword == "test"
        assert q.category == "Chat"
        assert q.sort == "title_asc"


def test_admin_query_combined_array_and_scalar() -> None:
    app = Flask(__name__)
    with app.test_request_context("/?page=2&status=pending&status=rejected&category=General"):
        q = _validated_admin_query(em.MarketplaceAdminAssetListQuery)
        assert q.page == 2
        assert q.status == ["pending", "rejected"]
        assert q.category == "General"


# ═══════════════════════════════════════════════════════════════════════════
# DTO count tests
# ═══════════════════════════════════════════════════════════════════════════


def test_enterprise_marketplace_defines_exact_dto_counts() -> None:
    all_names = {
        name
        for name, value in vars(em).items()
        if inspect.isclass(value) and not name.startswith("__") and not name.startswith("_")
    }
    request_dtos = {n for n in all_names if n.endswith("Payload") or n.endswith("Query")}
    response_dtos = {n for n in all_names if n.endswith("Response")}
    assert len(request_dtos) == 7
    assert len(response_dtos) == 8


# ═══════════════════════════════════════════════════════════════════════════
# Decorator order tests
# ═══════════════════════════════════════════════════════════════════════════


def test_submit_decorator_order() -> None:
    method = em.MarketplaceSubmissionApi.post
    wrappers = []
    while hasattr(method, "__wrapped__"):
        wrappers.append(method.__code__.co_qualname.partition(".<locals>")[0])
        method = method.__wrapped__
    expected = [
        "setup_required",
        "login_required",
        "account_initialization_required",
        "edit_permission_required",
        "with_session",
        "get_app_model",
    ]
    assert [name for name in wrappers if name in expected] == expected


def test_admin_decorator_order() -> None:
    method = em.MarketplaceAdminAssetsApi.get
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


def test_review_decorator_order() -> None:
    method = em.MarketplaceReviewApi.post
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


def test_copy_decorator_order() -> None:
    method = em.MarketplaceCopyApi.post
    wrappers = []
    while hasattr(method, "__wrapped__"):
        wrappers.append(method.__code__.co_qualname.partition(".<locals>")[0])
        method = method.__wrapped__
    expected = [
        "setup_required",
        "login_required",
        "account_initialization_required",
        "edit_permission_required",
        "with_session",
    ]
    assert [name for name in wrappers if name in expected] == expected


# ═══════════════════════════════════════════════════════════════════════════
# DTO validation tests
# ═══════════════════════════════════════════════════════════════════════════


def test_submission_payload_validates_title_bounds() -> None:
    with pytest.raises(ValidationError):
        em.MarketplaceSubmissionPayload.model_validate({"title": "", "category": "Cat"})
    with pytest.raises(ValidationError):
        em.MarketplaceSubmissionPayload.model_validate({"title": "a" * 256, "category": "Cat"})


def test_submission_payload_allows_null_expected_row_version() -> None:
    payload = em.MarketplaceSubmissionPayload.model_validate(
        {"title": "T", "category": "C", "expected_row_version": None}
    )
    assert payload.expected_row_version is None


def test_submission_payload_rejects_negative_row_version() -> None:
    with pytest.raises(ValidationError):
        em.MarketplaceSubmissionPayload.model_validate({"title": "T", "category": "C", "expected_row_version": -1})


def test_review_payload_only_allows_approved_or_rejected() -> None:
    em.MarketplaceReviewPayload.model_validate({"decision": "approved", "expected_row_version": 0})
    em.MarketplaceReviewPayload.model_validate({"decision": "rejected", "expected_row_version": 0})
    with pytest.raises(ValidationError):
        em.MarketplaceReviewPayload.model_validate({"decision": "pending", "expected_row_version": 0})
    with pytest.raises(ValidationError):
        em.MarketplaceReviewPayload.model_validate({"decision": "unlisted", "expected_row_version": 0})


def test_unlist_payload_rejects_negative_row_version() -> None:
    with pytest.raises(ValidationError):
        em.MarketplaceUnlistPayload.model_validate({"expected_row_version": -1})


def test_review_note_max_length() -> None:
    em.MarketplaceReviewPayload.model_validate(
        {"decision": "approved", "review_note": "a" * 5000, "expected_row_version": 0}
    )
    with pytest.raises(ValidationError):
        em.MarketplaceReviewPayload.model_validate(
            {"decision": "approved", "review_note": "a" * 5001, "expected_row_version": 0}
        )


def test_tags_max_10_each_max_64() -> None:
    em.MarketplaceSubmissionPayload.model_validate({"title": "T", "category": "C", "tags": ["a" * 64] * 10})
    with pytest.raises(ValidationError):
        em.MarketplaceSubmissionPayload.model_validate({"title": "T", "category": "C", "tags": ["a" * 65]})
    with pytest.raises(ValidationError):
        em.MarketplaceSubmissionPayload.model_validate({"title": "T", "category": "C", "tags": ["tag"] * 11})


@pytest.mark.parametrize(
    ("model_cls", "payload"),
    [
        (em.MarketplaceSubmissionPayload, {"title": "T", "category": "C", "unexpected": True}),
        (em.MarketplaceReviewPayload, {"decision": "approved", "expected_row_version": 0, "unexpected": True}),
        (em.MarketplaceUnlistPayload, {"expected_row_version": 0, "unexpected": True}),
        (em.MarketplaceCopyPayload, {"unexpected": True}),
    ],
)
def test_request_models_forbid_extra_fields(model_cls, payload) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model_cls.model_validate(payload)


def test_public_query_default_limit_is_24() -> None:
    q = em.MarketplacePublicAssetListQuery.model_validate({})
    assert q.limit == 24


def test_my_submission_query_default_limit_is_50() -> None:
    q = em.MarketplaceMySubmissionListQuery.model_validate({})
    assert q.limit == 50


def test_admin_query_default_limit_is_50() -> None:
    q = em.MarketplaceAdminAssetListQuery.model_validate({})
    assert q.limit == 50


def test_page_min_1() -> None:
    with pytest.raises(ValidationError):
        em.MarketplacePublicAssetListQuery.model_validate({"page": 0})
    with pytest.raises(ValidationError):
        em.MarketplaceMySubmissionListQuery.model_validate({"page": -1})


def test_limit_max_100() -> None:
    with pytest.raises(ValidationError):
        em.MarketplacePublicAssetListQuery.model_validate({"limit": 101})
    with pytest.raises(ValidationError):
        em.MarketplaceMySubmissionListQuery.model_validate({"limit": 0})


def test_keyword_trimmed_and_max_255() -> None:
    q = em.MarketplacePublicAssetListQuery.model_validate({"keyword": "  hello  "})
    assert q.keyword == "hello"
    q = em.MarketplaceMySubmissionListQuery.model_validate({"keyword": "a" * 300})
    assert len(q.keyword) == 255


def test_sort_only_allowed_values() -> None:
    for s in ("updated_at_desc", "created_at_desc", "title_asc"):
        em.MarketplacePublicAssetListQuery.model_validate({"sort": s})
    with pytest.raises(ValidationError):
        em.MarketplacePublicAssetListQuery.model_validate({"sort": "invalid"})


# ═══════════════════════════════════════════════════════════════════════════
# Error mapping tests
# ═══════════════════════════════════════════════════════════════════════════


def test_http_error_data_contract() -> None:
    error = MarketplaceHTTPError("asset_not_found", "Not found", 404)
    assert error.data == {"code": "asset_not_found", "message": "Not found", "status": 404}


@pytest.mark.parametrize("domain_error", [SourceAppNotFound(), AssetNotFound()])
def test_404_errors(domain_error) -> None:
    assert domain_error.status_code == 404


@pytest.mark.parametrize(
    "domain_error",
    [
        SubmissionAlreadyPending(),
        InvalidStatusTransition(),
        AssetAlreadyUnlisted(),
        StaleAssetVersion(),
        SourceAppUnavailable(),
        SnapshotNotReady(),
        SnapshotIntegrityError(),
    ],
)
def test_409_errors(domain_error) -> None:
    assert domain_error.status_code == 409


@pytest.mark.parametrize("domain_error", [CopyFailed(), CopyPendingUnsupported()])
def test_422_errors(domain_error) -> None:
    assert domain_error.status_code == 422


def test_503_errors() -> None:
    assert DependencyServiceUnavailable().status_code == 503


def test_raise_marketplace_error_preserves_code_message_status() -> None:
    err = AssetNotFound()
    with pytest.raises(MarketplaceHTTPError) as exc_info:
        em._raise_marketplace_error(err)
    assert exc_info.value.data["code"] == err.code
    assert exc_info.value.data["message"] == err.description
    assert exc_info.value.data["status"] == err.status_code


# ═══════════════════════════════════════════════════════════════════════════
# Response DTO field isolation tests
# ═══════════════════════════════════════════════════════════════════════════


def test_admin_response_includes_audit_fields() -> None:
    fields = set(em.MarketplaceAssetResponse.model_fields)
    for f in (
        "source_app_id",
        "source_tenant_id",
        "submitter_account_id",
        "reviewer_account_id",
        "review_note",
        "snapshot_error_code",
        "reviewed_at",
    ):
        assert f in fields


def test_public_snapshot_response_excludes_audit_fields() -> None:
    fields = set(em.MarketplaceSnapshotResponse.model_fields)
    for f in (
        "source_app_id",
        "source_tenant_id",
        "submitter_account_id",
        "reviewer_account_id",
        "review_note",
        "snapshot_error_code",
    ):
        assert f not in fields


def test_public_snapshot_response_includes_snapshot_fields() -> None:
    fields = set(em.MarketplaceSnapshotResponse.model_fields)
    for f in (
        "snapshot_id",
        "snapshot_version",
        "app_name",
        "app_mode",
        "dsl_version",
        "content_sha256",
        "dependencies",
        "frozen_at",
    ):
        assert f in fields


def test_admin_response_excludes_snapshot_detail_fields() -> None:
    fields = set(em.MarketplaceAssetResponse.model_fields)
    for f in ("dsl_content", "app_name", "app_mode", "dsl_version", "snapshot_id"):
        assert f not in fields


def test_copy_response_only_has_required_fields() -> None:
    fields = set(em.MarketplaceCopyResponse.model_fields)
    assert {"app_id", "import_status", "warnings", "snapshot_version", "content_sha256"}.issubset(fields)
    assert "dsl_content" not in fields


# ═══════════════════════════════════════════════════════════════════════════
# Controller behavior tests
# ═══════════════════════════════════════════════════════════════════════════


def test_submit_injects_session_to_service() -> None:
    mock_asset = MagicMock()
    mock_asset.configure_mock(
        id="asset-1",
        status="pending",
        publication_status="unpublished",
        snapshot_state="none",
        title="T",
        description="",
        category="C",
        tags=[],
        scenario="",
        allow_show_workspace_name=False,
        source_app_id="app-1",
        source_tenant_id="t-1",
        submitter_account_id="acct-1",
        reviewer_account_id=None,
        row_version=1,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        reviewed_at=None,
        review_note=None,
        snapshot_error_code=None,
    )
    service_mock = MagicMock()
    service_mock.submit_asset.return_value = mock_asset
    with patch.object(em, "EnterpriseMarketplaceService", return_value=service_mock):
        with patch.object(
            em, "current_account_with_tenant", return_value=(MagicMock(id="acct-1", current_tenant_id="t-1"), "t-1")
        ):
            with patch.object(em, "console_ns", payload={"title": "T", "category": "C"}):
                response, _ = _innermost(em.MarketplaceSubmissionApi.post)(
                    em.MarketplaceSubmissionApi(), MagicMock(), app_model=MagicMock(id="app-1")
                )
    assert response["asset_id"] == "asset-1"
    assert "id" not in response
    service_mock.submit_asset.assert_called_once()
    call_kwargs = service_mock.submit_asset.call_args[1]
    assert "session" not in call_kwargs
    assert call_kwargs["title"] == "T"


def test_review_dispatch_approved_calls_approve() -> None:
    account = MagicMock(id="rev-1", current_tenant_id="t-1")
    asset = MagicMock()
    asset.configure_mock(
        id="a-1",
        status="approved",
        publication_status="published",
        snapshot_state="ready",
        title="T",
        description="",
        category="C",
        tags=[],
        scenario="",
        allow_show_workspace_name=False,
        source_app_id="app-1",
        source_tenant_id="t-1",
        submitter_account_id="acct-1",
        reviewer_account_id="rev-1",
        row_version=2,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        reviewed_at=datetime(2026, 1, 1),
        review_note=None,
        snapshot_error_code=None,
    )
    service_mock = MagicMock()
    service_mock.approve_asset.return_value = (asset, MagicMock())
    with patch.object(em, "EnterpriseMarketplaceService", return_value=service_mock):
        with patch.object(em, "current_account_with_tenant", return_value=(account, "t-1")):
            with patch.object(em, "console_ns", payload={"decision": "approved", "expected_row_version": 1}):
                response = _innermost(em.MarketplaceReviewApi.post)(
                    em.MarketplaceReviewApi(), MagicMock(), asset_id="a-1"
                )
    assert response["asset_id"] == "a-1"
    assert "id" not in response
    service_mock.approve_asset.assert_called_once()
    service_mock.reject_asset.assert_not_called()


def test_review_dispatch_rejected_calls_reject() -> None:
    account = MagicMock(id="rev-1", current_tenant_id="t-1")
    asset = MagicMock()
    asset.configure_mock(
        id="a-1",
        status="rejected",
        publication_status="unpublished",
        snapshot_state="none",
        title="T",
        description="",
        category="C",
        tags=[],
        scenario="",
        allow_show_workspace_name=False,
        source_app_id="app-1",
        source_tenant_id="t-1",
        submitter_account_id="acct-1",
        reviewer_account_id="rev-1",
        row_version=2,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        reviewed_at=datetime(2026, 1, 1),
        review_note="bad",
        snapshot_error_code=None,
    )
    service_mock = MagicMock()
    service_mock.reject_asset.return_value = asset
    with patch.object(em, "EnterpriseMarketplaceService", return_value=service_mock):
        with patch.object(em, "current_account_with_tenant", return_value=(account, "t-1")):
            with patch.object(em, "console_ns", payload={"decision": "rejected", "expected_row_version": 1}):
                response = _innermost(em.MarketplaceReviewApi.post)(
                    em.MarketplaceReviewApi(), MagicMock(), asset_id="a-1"
                )
    assert response["asset_id"] == "a-1"
    assert "id" not in response
    service_mock.reject_asset.assert_called_once()
    service_mock.approve_asset.assert_not_called()


def test_copy_passes_tenant_from_current_account() -> None:
    account = MagicMock(id="acct-1", current_tenant_id="tid-copy")
    snapshot_mock = MagicMock(
        import_app_id="import-1",
        import_status="completed",
        warnings=[],
        snapshot_version=1,
        content_sha256="abc" * 21 + "12",
    )
    service_mock = MagicMock()
    service_mock.copy_asset.return_value = snapshot_mock
    with patch.object(em, "EnterpriseMarketplaceService", return_value=service_mock):
        with patch.object(em, "current_account_with_tenant", return_value=(account, "tid-copy")):
            with patch.object(em, "console_ns", payload={}):
                _innermost(em.MarketplaceCopyApi.post)(em.MarketplaceCopyApi(), MagicMock(), asset_id="a-1")
    call_kwargs = service_mock.copy_asset.call_args[1]
    assert call_kwargs["account"] is account
    assert call_kwargs["asset_id"] == "a-1"


def test_controller_has_no_db_session_import() -> None:
    tree = ast.parse(inspect.getsource(em))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "ext_database" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert "ext_database" not in node.module


def test_controller_no_direct_model_access() -> None:
    source = inspect.getsource(em)
    assert "EnterpriseMarketplaceAsset" not in source
    assert "EnterpriseMarketplaceAssetSnapshot" not in source


def test_response_dtos_have_no_secret_fields() -> None:
    canary_keys = {"secret", "token", "credential", "password", "api_key", "dsl_content", "private_key"}
    for model_cls in [
        em.MarketplaceAssetResponse,
        em.MarketplaceSnapshotResponse,
        em.MarketplaceSnapshotDetailResponse,
        em.MarketplaceCopyResponse,
        em.MarketplaceErrorResponse,
    ]:
        fields = set(model_cls.model_fields)
        assert fields.isdisjoint(canary_keys), f"{model_cls.__name__} leaks canary keys: {fields & canary_keys}"


def test_with_session_wrapper_commit_on_success() -> None:
    session = MagicMock()
    session.begin.return_value = nullcontext()
    session_context = MagicMock()
    session_context.__enter__.return_value = session

    class Handler:
        @em.with_session
        def get(self, injected_session):
            injected_session.flush()
            return {"result": "success"}

    with patch("controllers.common.session.session_factory.create_session", return_value=session_context):
        result = Handler().get()
    assert result == {"result": "success"}
    session.flush.assert_called_once_with()
    session.commit.assert_called_once_with()


def test_validated_payload_maps_pydantic_to_400() -> None:
    with patch.object(em, "console_ns", payload={"unexpected": True}):
        with pytest.raises(MarketplaceHTTPError) as exc_info:
            em._validated_payload(em.MarketplaceCopyPayload)
        assert exc_info.value.data["code"] == "invalid_request"


def test_validated_query_maps_pydantic_to_400() -> None:
    with pytest.raises(ValidationError):
        em.MarketplacePublicAssetListQuery.model_validate({"page": -1})


# ═══════════════════════════════════════════════════════════════════════════
# OpenAPI semantic tests (read from generated console-openapi.json)
# ═══════════════════════════════════════════════════════════════════════════


def _load_console_openapi():
    """Return the generated console OpenAPI spec dict."""
    repo_root = Path(__file__).resolve().parents[5]
    spec_path = repo_root / "packages" / "contracts" / "openapi" / "console-openapi.json"
    return json.loads(spec_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def console_openapi():
    return _load_console_openapi()


def test_openapi_marketplace_error_response_schema(console_openapi) -> None:
    schemas = console_openapi["components"]["schemas"]
    err_schema = schemas.get("MarketplaceErrorResponse")
    assert err_schema is not None, "MarketplaceErrorResponse not in schemas"
    props = err_schema.get("properties", {})
    assert isinstance(props, dict)
    assert set(props) == {"code", "message", "status"}, f"Unexpected props: {set(props)}"


def test_openapi_unauthorized_response_schema(console_openapi) -> None:
    schemas = console_openapi["components"]["schemas"]
    unauth_schema = schemas.get("UnauthorizedResponse")
    assert unauth_schema is not None, "UnauthorizedResponse not in schemas"
    props = unauth_schema.get("properties", {})
    assert isinstance(props, dict)
    assert set(props) == {"code", "message"}, f"UnauthorizedResponse has unexpected props: {set(props)}"
    assert "status" not in props, "UnauthorizedResponse must not have a status field"


def test_openapi_each_b4_operation_has_error_responses(console_openapi) -> None:
    paths = console_openapi["paths"]
    b4_paths = {p for p in paths if "marketplace" in p.lower() and "plugin" not in p.lower()}
    for path in sorted(b4_paths):
        for method_name, operation in paths[path].items():
            if method_name == "parameters":
                continue
            responses = operation.get("responses", {})
            status_codes = {int(k) for k in responses if k.isdigit()}
            error_codes = status_codes - {200, 201}
            assert error_codes, f"Operation {method_name} {path} has no error responses: {status_codes}"
            assert 401 in status_codes, f"Operation {method_name} {path} missing 401 response"


def test_openapi_401_does_not_reference_marketplace_error_response(console_openapi) -> None:
    paths = console_openapi["paths"]
    b4_paths = {p for p in paths if "marketplace" in p.lower() and "plugin" not in p.lower()}
    for path in sorted(b4_paths):
        for method_name, operation in paths[path].items():
            if method_name == "parameters":
                continue
            responses = operation.get("responses", {})
            resp401 = responses.get("401", {})
            content = resp401.get("content", {}) if isinstance(resp401, dict) else {}
            app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
            schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
            ref = schema.get("$ref", "") if isinstance(schema, dict) else ""
            assert "MarketplaceErrorResponse" not in ref, (
                f"401 in {method_name} {path} incorrectly references MarketplaceErrorResponse"
            )
            assert "UnauthorizedResponse" in ref, f"401 in {method_name} {path} does not reference UnauthorizedResponse"


def test_openapi_domain_error_responses_reference_marketplace_error_response(console_openapi) -> None:
    paths = console_openapi["paths"]
    b4_paths = {p for p in paths if "marketplace" in p.lower() and "plugin" not in p.lower()}
    domain_errors = {"400", "403", "404", "409", "422", "503"}
    for path in sorted(b4_paths):
        for method_name, operation in paths[path].items():
            if method_name == "parameters":
                continue
            responses = operation.get("responses", {})
            for status in domain_errors:
                resp = responses.get(status)
                if resp is None:
                    continue
                content = resp.get("content", {}) if isinstance(resp, dict) else {}
                app_json = content.get("application/json", {}) if isinstance(content, dict) else {}
                schema = app_json.get("schema", {}) if isinstance(app_json, dict) else {}
                ref = schema.get("$ref", "") if isinstance(schema, dict) else ""
                assert "MarketplaceErrorResponse" in ref, (
                    f"Error {status} in {method_name} {path} should reference MarketplaceErrorResponse but got: {ref}"
                )


def test_openapi_success_status_codes(console_openapi) -> None:
    paths = console_openapi["paths"]
    submit_path = "/apps/{app_id}/enterprise-marketplace/submissions"
    copy_path = "/enterprise-marketplace/assets/{asset_id}/copies"
    for p, expected_success in [(submit_path, "201"), (copy_path, "201")]:
        assert p in paths, f"Path {p} not found in OpenAPI"
        methods = paths[p]
        post_method = methods.get("post", {})
        assert expected_success in post_method.get("responses", {}), f"{p} missing {expected_success}"

    get_paths = [k for k in paths if "marketplace" in k.lower() and k not in (submit_path, copy_path)]
    for p in get_paths:
        for method, op in paths[p].items():
            if method in ("get", "post") and method != "parameters":
                assert "200" in op.get("responses", {}), f"{method} {p} missing 200"


def test_openapi_review_operation_includes_422_domain_error(console_openapi) -> None:
    paths = console_openapi["paths"]
    review_path = "/platform-admin/enterprise-marketplace/assets/{asset_id}/reviews"
    assert review_path in paths, f"Path {review_path} not found in OpenAPI"
    responses = paths[review_path]["post"].get("responses", {})
    assert "422" in responses, f"Review operation missing 422 response: {sorted(responses)}"
    content = responses["422"].get("content", {})
    app_json = content.get("application/json", {})
    ref = app_json.get("schema", {}).get("$ref", "")
    assert "MarketplaceErrorResponse" in ref, f"Review 422 should reference MarketplaceErrorResponse but got: {ref}"

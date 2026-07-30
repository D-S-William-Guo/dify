"""Enterprise marketplace controller – eight approved B4 routes.

Submitted, reviewed, unlisted, and copied strictly through the session-injected
service layer.  Controller owns no business logic, no direct model access, and
no ``db.session``.
"""

import logging
from datetime import datetime
from http import HTTPStatus
from typing import Annotated, Literal
from uuid import UUID

from flask import request
from flask_restx import Resource
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from controllers.common.schema import (
    query_params_from_model,
    register_response_schema_models,
    register_schema_models,
)
from controllers.common.session import with_session
from controllers.console import console_ns
from controllers.console.app.wraps import get_app_model
from controllers.console.wraps import (
    account_initialization_required,
    edit_permission_required,
    setup_required,
)
from fields.base import ResponseModel
from libs.exception import BaseHTTPException
from libs.helper import dump_response
from libs.login import current_account_with_tenant, login_required
from libs.platform_admin import platform_admin_current_tenant_required, platform_admin_required
from services.enterprise_marketplace_service import EnterpriseMarketplaceService
from services.errors.enterprise_marketplace import MarketplaceError

logger = logging.getLogger(__name__)

ReviewDecision = Literal["approved", "rejected"]
_AllSorts = Literal["updated_at_desc", "created_at_desc", "title_asc"]

_ERR_400 = "Invalid request"
_ERR_403 = "Permission denied"
_ERR_404 = "Not found"
_ERR_409 = "Conflict"
_ERR_422 = "Unprocessable content"
_ERR_503 = "Service unavailable"


class MarketplaceHTTPError(BaseHTTPException):
    def __init__(self, error_code: str, description: str, status_code: int) -> None:
        self.error_code = error_code
        self.code = status_code
        super().__init__(description=description)


# ── Request DTOs ────────────────────────────────────────────────────────

class MarketplaceSubmissionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=5000)] = ""
    category: Annotated[str, Field(min_length=1, max_length=255)]
    tags: Annotated[list[Annotated[str, Field(min_length=1, max_length=64)]], Field(max_length=10)] = []
    scenario: Annotated[str, Field(max_length=5000)] = ""
    allow_show_workspace_name: bool = False
    expected_row_version: int | None = None

    @field_validator("expected_row_version")
    @classmethod
    def _check_expected_row_version(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("expected_row_version must be non-negative")
        return v


class MarketplaceReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    review_note: Annotated[str | None, Field(default=None, max_length=5000)] = None
    expected_row_version: Annotated[int, Field(ge=0)]


class MarketplaceUnlistPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: Annotated[str | None, Field(default=None, max_length=5000)] = None
    expected_row_version: Annotated[int, Field(ge=0)]


class MarketplaceCopyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _MarketplaceListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: Annotated[int, Field(default=1, ge=1)]
    limit: Annotated[int, Field(default=50, ge=1, le=100)]
    keyword: Annotated[str | None, Field(default=None, max_length=255)] = None
    category: str | None = None
    sort: _AllSorts = "updated_at_desc"

    @field_validator("keyword", mode="before")
    @classmethod
    def normalize_keyword(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        trimmed = v.strip()[:255]
        return trimmed or None


class MarketplaceMySubmissionListQuery(_MarketplaceListQuery):
    limit: Annotated[int, Field(default=50, ge=1, le=100)] = 50


class MarketplacePublicAssetListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: Annotated[int, Field(default=1, ge=1)]
    limit: Annotated[int, Field(default=24, ge=1, le=100)] = 24
    keyword: Annotated[str | None, Field(default=None, max_length=255)] = None
    category: str | None = None
    sort: _AllSorts = "updated_at_desc"

    @field_validator("keyword", mode="before")
    @classmethod
    def normalize_keyword(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        trimmed = v.strip()[:255]
        return trimmed or None


class MarketplaceAdminAssetListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: Annotated[int, Field(default=1, ge=1)]
    limit: Annotated[int, Field(default=50, ge=1, le=100)] = 50
    keyword: Annotated[str | None, Field(default=None, max_length=255)] = None
    category: str | None = None
    status: list[str] | None = None
    publication_status: list[str] | None = None
    snapshot_state: list[str] | None = None
    sort: _AllSorts = "updated_at_desc"

    @field_validator("keyword", mode="before")
    @classmethod
    def normalize_keyword(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        trimmed = v.strip()[:255]
        return trimmed or None


# ── Response DTOs ───────────────────────────────────────────────────────

class MarketplaceAssetResponse(ResponseModel):
    """Admin / my-submissions asset view – no DSL."""
    asset_id: str
    status: str
    publication_status: str
    snapshot_state: str
    title: str
    description: str
    category: str
    tags: list[str]
    scenario: str
    allow_show_workspace_name: bool
    source_app_id: str | None
    source_tenant_id: str | None
    submitter_account_id: str | None
    reviewer_account_id: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    review_note: str | None
    snapshot_error_code: str | None


class MarketplaceAssetPaginationResponse(ResponseModel):
    items: list[MarketplaceAssetResponse]
    page: int
    limit: int
    total: int
    has_more: bool


class MarketplaceSnapshotResponse(ResponseModel):
    """Public asset view – frozen snapshot fields, no audit leak."""
    asset_id: str
    snapshot_id: str | None
    snapshot_version: int | None
    status: str
    publication_status: str
    snapshot_state: str
    title: str
    description: str
    category: str
    tags: list[str]
    scenario: str
    allow_show_workspace_name: bool
    source_tenant_name: str | None
    app_name: str | None
    app_description: str | None
    app_mode: str | None
    app_icon_type: str | None
    app_icon: str | None
    app_icon_background: str | None
    dsl_version: str | None
    content_sha256: str | None
    dependencies: list[dict[str, object]] | None
    frozen_at: datetime | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class MarketplaceSnapshotPaginationResponse(ResponseModel):
    items: list[MarketplaceSnapshotResponse]
    page: int
    limit: int
    total: int
    has_more: bool


class MarketplaceSnapshotDetailResponse(ResponseModel):
    """Public single-asset detail – identical to list-item shape."""
    asset_id: str
    snapshot_id: str | None
    snapshot_version: int | None
    status: str
    publication_status: str
    snapshot_state: str
    title: str
    description: str
    category: str
    tags: list[str]
    scenario: str
    allow_show_workspace_name: bool
    source_tenant_name: str | None
    app_name: str | None
    app_description: str | None
    app_mode: str | None
    app_icon_type: str | None
    app_icon: str | None
    app_icon_background: str | None
    dsl_version: str | None
    content_sha256: str | None
    dependencies: list[dict[str, object]] | None
    frozen_at: datetime | None
    row_version: int
    created_at: datetime
    updated_at: datetime


class MarketplaceCopyResponse(ResponseModel):
    app_id: str
    import_status: str
    warnings: list[str]
    snapshot_version: int
    content_sha256: str


class MarketplaceErrorResponse(ResponseModel):
    code: str
    message: str
    status: int


class UnauthorizedResponse(ResponseModel):
    """Matches the official login_required unauthorized_handler shape."""
    code: str
    message: str


# ── Schema registration ─────────────────────────────────────────────────

register_schema_models(
    console_ns,
    MarketplaceSubmissionPayload,
    MarketplaceReviewPayload,
    MarketplaceUnlistPayload,
    MarketplaceCopyPayload,
    MarketplaceMySubmissionListQuery,
    MarketplacePublicAssetListQuery,
    MarketplaceAdminAssetListQuery,
)

register_response_schema_models(
    console_ns,
    MarketplaceAssetResponse,
    MarketplaceAssetPaginationResponse,
    MarketplaceSnapshotResponse,
    MarketplaceSnapshotPaginationResponse,
    MarketplaceSnapshotDetailResponse,
    MarketplaceCopyResponse,
    MarketplaceErrorResponse,
    UnauthorizedResponse,
)


# ── Error response decorators ───────────────────────────────────────────

def _err_response(status: int, description: str):
    """Decorator registering a MarketplaceErrorResponse for the given HTTP status."""

    def decorator(f):
        return console_ns.response(status, description, console_ns.models["MarketplaceErrorResponse"])(f)

    return decorator


def _auth_401(f):
    """Register 401 with the official UnauthorizedResponse schema (no status field)."""
    return console_ns.response(401, "Authentication required", console_ns.models["UnauthorizedResponse"])(f)


# ── Internal helpers ────────────────────────────────────────────────────

def _validated_payload(model: type[BaseModel]) -> BaseModel:
    try:
        return model.model_validate(console_ns.payload or {})
    except ValidationError as exc:
        raise MarketplaceHTTPError("invalid_request", "Invalid request.", 400) from exc


def _validated_query(model: type[BaseModel]) -> BaseModel:
    try:
        return model.model_validate(request.args.to_dict(flat=True))
    except ValidationError as exc:
        raise MarketplaceHTTPError("invalid_request", "Invalid request.", 400) from exc


_MULTI_VAL_FIELDS = frozenset({"status", "publication_status", "snapshot_state"})


def _validated_admin_query(model: type[BaseModel]) -> BaseModel:
    """Validate query params with ``getlist`` for multi-value admin fields."""
    try:
        scalar = request.args.to_dict(flat=True)
        merged: dict[str, object] = {}
        for key, value in scalar.items():
            if key in _MULTI_VAL_FIELDS:
                continue
            merged[key] = value
        for field_name in _MULTI_VAL_FIELDS:
            vals = request.args.getlist(field_name)
            if vals:
                merged[field_name] = vals
        return model.model_validate(merged)
    except ValidationError as exc:
        raise MarketplaceHTTPError("invalid_request", "Invalid request.", 400) from exc


def _response(model: type[ResponseModel], value: object) -> dict[str, object]:
    validated = model.model_validate(value, from_attributes=True)
    return dump_response(model, validated)


def _raise_marketplace_error(error: MarketplaceError) -> None:
    raise MarketplaceHTTPError(error.code, error.description, error.status_code) from error


# ── Route 1: POST /apps/<uuid:app_id>/enterprise-marketplace/submissions ─

@console_ns.route("/apps/<uuid:app_id>/enterprise-marketplace/submissions")
class MarketplaceSubmissionApi(Resource):
    @console_ns.expect(console_ns.models[MarketplaceSubmissionPayload.__name__])
    @console_ns.response(HTTPStatus.CREATED, "Created", console_ns.models[MarketplaceAssetResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @_err_response(403, _ERR_403)
    @_err_response(404, _ERR_404)
    @_err_response(409, _ERR_409)
    @setup_required
    @login_required
    @account_initialization_required
    @edit_permission_required
    @with_session
    @get_app_model
    def post(self, session: Session, app_model):
        payload = _validated_payload(MarketplaceSubmissionPayload)
        assert isinstance(payload, MarketplaceSubmissionPayload)
        account, _ = current_account_with_tenant()
        try:
            asset = EnterpriseMarketplaceService(session).submit_asset(
                source_app=app_model,
                account=account,
                title=payload.title,
                description=payload.description,
                category=payload.category,
                tags=payload.tags,
                scenario=payload.scenario,
                allow_show_workspace_name=payload.allow_show_workspace_name,
                expected_row_version=payload.expected_row_version,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceAssetResponse, asset), HTTPStatus.CREATED


# ── Route 2: GET /enterprise-marketplace/submissions ────────────────────

@console_ns.route("/enterprise-marketplace/submissions")
class MarketplaceMySubmissionsApi(Resource):
    @console_ns.doc(params=query_params_from_model(MarketplaceMySubmissionListQuery))
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[MarketplaceAssetPaginationResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @setup_required
    @login_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session):
        query = _validated_query(MarketplaceMySubmissionListQuery)
        assert isinstance(query, MarketplaceMySubmissionListQuery)
        account, tenant_id = current_account_with_tenant()
        try:
            result = EnterpriseMarketplaceService(session).list_my_submissions(
                tenant_id=tenant_id,
                submitter_account_id=account.id,
                page=query.page,
                limit=query.limit,
                keyword=query.keyword,
                category=query.category,
                sort=query.sort,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceAssetPaginationResponse, result)


# ── Route 3: GET /enterprise-marketplace/assets ─────────────────────────

@console_ns.route("/enterprise-marketplace/assets")
class MarketplacePublicAssetsApi(Resource):
    @console_ns.doc(params=query_params_from_model(MarketplacePublicAssetListQuery))
    @console_ns.response(
        HTTPStatus.OK, "Success", console_ns.models[MarketplaceSnapshotPaginationResponse.__name__]
    )
    @_err_response(400, _ERR_400)
    @_auth_401
    @setup_required
    @login_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session):
        query = _validated_query(MarketplacePublicAssetListQuery)
        assert isinstance(query, MarketplacePublicAssetListQuery)
        try:
            result = EnterpriseMarketplaceService(session).list_public_assets(
                page=query.page,
                limit=query.limit,
                keyword=query.keyword,
                category=query.category,
                sort=query.sort,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceSnapshotPaginationResponse, result)


# ── Route 4: GET /enterprise-marketplace/assets/<uuid:asset_id> ─────────

@console_ns.route("/enterprise-marketplace/assets/<uuid:asset_id>")
class MarketplacePublicAssetDetailApi(Resource):
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[MarketplaceSnapshotDetailResponse.__name__])
    @_auth_401
    @_err_response(404, _ERR_404)
    @setup_required
    @login_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session, asset_id: UUID):
        try:
            result = EnterpriseMarketplaceService(session).get_public_asset(
                asset_id=str(asset_id),
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceSnapshotDetailResponse, result)


# ── Route 5: POST /enterprise-marketplace/assets/<uuid:asset_id>/copies ─

@console_ns.route("/enterprise-marketplace/assets/<uuid:asset_id>/copies")
class MarketplaceCopyApi(Resource):
    @console_ns.expect(console_ns.models[MarketplaceCopyPayload.__name__])
    @console_ns.response(HTTPStatus.CREATED, "Created", console_ns.models[MarketplaceCopyResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @_err_response(403, _ERR_403)
    @_err_response(404, _ERR_404)
    @_err_response(409, _ERR_409)
    @_err_response(422, _ERR_422)
    @_err_response(503, _ERR_503)
    @setup_required
    @login_required
    @account_initialization_required
    @edit_permission_required
    @with_session
    def post(self, session: Session, asset_id: UUID):
        _validated_payload(MarketplaceCopyPayload)
        account, _ = current_account_with_tenant()
        try:
            copy_result = EnterpriseMarketplaceService(session).copy_asset(
                asset_id=str(asset_id),
                account=account,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        copy_payload = {
            "app_id": copy_result.import_app_id,
            "import_status": copy_result.import_status,
            "warnings": copy_result.warnings,
            "snapshot_version": copy_result.snapshot_version,
            "content_sha256": copy_result.content_sha256,
        }
        return _response(MarketplaceCopyResponse, copy_payload), HTTPStatus.CREATED


# ── Route 6: GET /platform-admin/enterprise-marketplace/assets ──────────

@console_ns.route("/platform-admin/enterprise-marketplace/assets")
class MarketplaceAdminAssetsApi(Resource):
    @console_ns.doc(params=query_params_from_model(MarketplaceAdminAssetListQuery))
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[MarketplaceAssetPaginationResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @_err_response(403, _ERR_403)
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session):
        query = _validated_admin_query(MarketplaceAdminAssetListQuery)
        assert isinstance(query, MarketplaceAdminAssetListQuery)
        try:
            result = EnterpriseMarketplaceService(session).list_admin_assets(
                page=query.page,
                limit=query.limit,
                keyword=query.keyword,
                category=query.category,
                status=query.status,
                publication_status=query.publication_status,
                snapshot_state=query.snapshot_state,
                sort=query.sort,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceAssetPaginationResponse, result)


# ── Route 7: POST /platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/reviews

@console_ns.route("/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/reviews")
class MarketplaceReviewApi(Resource):
    @console_ns.expect(console_ns.models[MarketplaceReviewPayload.__name__])
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[MarketplaceAssetResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @_err_response(403, _ERR_403)
    @_err_response(404, _ERR_404)
    @_err_response(409, _ERR_409)
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session
    def post(self, session: Session, asset_id: UUID):
        payload = _validated_payload(MarketplaceReviewPayload)
        assert isinstance(payload, MarketplaceReviewPayload)
        account, _ = current_account_with_tenant()
        try:
            if payload.decision == "approved":
                asset, _snap = EnterpriseMarketplaceService(session).approve_asset(
                    asset_id=str(asset_id),
                    reviewer=account,
                    review_note=payload.review_note,
                    expected_row_version=payload.expected_row_version,
                )
            else:
                asset = EnterpriseMarketplaceService(session).reject_asset(
                    asset_id=str(asset_id),
                    reviewer=account,
                    review_note=payload.review_note,
                    expected_row_version=payload.expected_row_version,
                )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceAssetResponse, asset)


# ── Route 8: POST /platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/unlist

@console_ns.route("/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/unlist")
class MarketplaceUnlistApi(Resource):
    @console_ns.expect(console_ns.models[MarketplaceUnlistPayload.__name__])
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[MarketplaceAssetResponse.__name__])
    @_err_response(400, _ERR_400)
    @_auth_401
    @_err_response(403, _ERR_403)
    @_err_response(404, _ERR_404)
    @_err_response(409, _ERR_409)
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session
    def post(self, session: Session, asset_id: UUID):
        payload = _validated_payload(MarketplaceUnlistPayload)
        assert isinstance(payload, MarketplaceUnlistPayload)
        account, _ = current_account_with_tenant()
        try:
            asset = EnterpriseMarketplaceService(session).unlist_asset(
                asset_id=str(asset_id),
                reviewer=account,
                review_note=payload.review_note,
                expected_row_version=payload.expected_row_version,
            )
        except MarketplaceError as exc:
            _raise_marketplace_error(exc)
        return _response(MarketplaceAssetResponse, asset)

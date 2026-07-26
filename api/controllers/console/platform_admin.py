"""Unregistered B3 platform-administration controller.

B4 owns importing this module from the console package and generating the
contract. This module intentionally defines exactly seven approved routes.
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

from configs import dify_config
from controllers.common.schema import (
    query_params_from_model,
    register_response_schema_models,
    register_schema_models,
)
from controllers.common.session import with_session
from controllers.console import console_ns
from controllers.console.wraps import account_initialization_required, setup_required
from fields.base import ResponseModel
from libs.helper import EmailStr, dump_response
from libs.login import current_account_with_tenant, current_user, login_required
from libs.platform_admin import (
    PlatformAdminHTTPError,
    is_platform_admin_account,
    platform_admin_current_tenant_required,
    platform_admin_required,
)
from services.platform_admin_service import PlatformAdminService

logger = logging.getLogger(__name__)

NonOwnerRole = Literal["admin", "editor", "normal", "dataset_operator"]
MemberRole = Literal["owner", "admin", "editor", "normal", "dataset_operator"]


class PlatformAdminStatusResponse(ResponseModel):
    is_platform_admin: bool
    mutation_supported: bool


class PlatformAdminWorkspaceListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)
    keyword: str | None = Field(default=None, max_length=255)
    status: Literal["normal", "archive", "all"] = "normal"

    @field_validator("keyword", mode="before")
    @classmethod
    def normalize_keyword(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class PlatformAdminWorkspaceOwnerResponse(ResponseModel):
    id: str
    name: str
    email: str


class PlatformAdminWorkspaceResponse(ResponseModel):
    id: str
    name: str
    plan: str
    status: Literal["normal", "archive"]
    created_at: datetime
    updated_at: datetime
    member_count: int
    owner: PlatformAdminWorkspaceOwnerResponse


class PlatformAdminWorkspacePaginationResponse(ResponseModel):
    items: list[PlatformAdminWorkspaceResponse]
    page: int
    limit: int
    total: int
    has_more: bool


class PlatformAdminWorkspaceRenamePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PlatformAdminMemberResponse(ResponseModel):
    id: str
    name: str
    email: str
    status: str
    current: bool
    created_at: datetime
    last_login_at: datetime | None
    last_active_at: datetime | None
    role: MemberRole | None
    role_source: Literal["tenant_account_join", "rbac_unavailable"]
    mutation_supported: bool


class PlatformAdminMemberListResponse(ResponseModel):
    items: list[PlatformAdminMemberResponse]
    mutation_supported: bool


class PlatformAdminMemberInvitePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emails: Annotated[list[EmailStr], Field(min_length=1, max_length=50)]
    role: NonOwnerRole
    language: str | None = None

    @field_validator("emails", mode="before")
    @classmethod
    def normalize_emails(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized = [item.strip().lower() if isinstance(item, str) else item for item in value]
        string_emails = [item for item in normalized if isinstance(item, str)]
        if len(string_emails) != len(set(string_emails)):
            raise ValueError("duplicate_email")
        return normalized


class PlatformAdminMemberInviteResultResponse(ResponseModel):
    email: str
    action: Literal[
        "account_created",
        "membership_created",
        "invitation_queued",
        "invitation_resent",
        "already_member",
    ]
    email_delivery: Literal["queued", "failed", "not_applicable"]


class PlatformAdminMemberInviteResponse(ResponseModel):
    workspace_id: str
    results: list[PlatformAdminMemberInviteResultResponse]


class PlatformAdminMemberRoleUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: NonOwnerRole


class PlatformAdminMemberRoleUpdateResponse(ResponseModel):
    result: Literal["success"]
    workspace_id: str
    member_id: str


class PlatformAdminErrorResponse(ResponseModel):
    code: str
    message: str
    status: int


register_schema_models(
    console_ns,
    PlatformAdminWorkspaceListQuery,
    PlatformAdminWorkspaceRenamePayload,
    PlatformAdminMemberInvitePayload,
    PlatformAdminMemberRoleUpdatePayload,
)
register_response_schema_models(
    console_ns,
    PlatformAdminStatusResponse,
    PlatformAdminWorkspaceOwnerResponse,
    PlatformAdminWorkspaceResponse,
    PlatformAdminWorkspacePaginationResponse,
    PlatformAdminMemberResponse,
    PlatformAdminMemberListResponse,
    PlatformAdminMemberInviteResultResponse,
    PlatformAdminMemberInviteResponse,
    PlatformAdminMemberRoleUpdateResponse,
    PlatformAdminErrorResponse,
)


def _validated_payload(model: type[BaseModel]) -> BaseModel:
    try:
        return model.model_validate(console_ns.payload or {})
    except ValidationError as exc:
        error_code = "duplicate_email" if "duplicate_email" in str(exc) else "invalid_request"
        raise PlatformAdminHTTPError(error_code, "Invalid request.", 400) from exc


def _validated_query() -> PlatformAdminWorkspaceListQuery:
    try:
        return PlatformAdminWorkspaceListQuery.model_validate(request.args.to_dict(flat=True))
    except ValidationError as exc:
        raise PlatformAdminHTTPError("invalid_request", "Invalid request.", 400) from exc


def _response(model: type[ResponseModel], value: object) -> dict[str, object]:
    validated = model.model_validate(value, from_attributes=True)
    return dump_response(model, validated)


@console_ns.route("/account/platform-admin-status")
class PlatformAdminStatusApi(Resource):
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminStatusResponse.__name__])
    @setup_required
    @login_required
    def get(self):
        is_admin = is_platform_admin_account(current_user)
        logger.debug("platform_admin.identity_checked is_platform_admin=%s", is_admin)
        return _response(
            PlatformAdminStatusResponse,
            {
                "is_platform_admin": is_admin,
                "mutation_supported": is_admin and not dify_config.RBAC_ENABLED,
            },
        )


@console_ns.route("/platform-admin/workspaces")
class PlatformAdminWorkspaceListApi(Resource):
    @console_ns.doc(params=query_params_from_model(PlatformAdminWorkspaceListQuery))
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminWorkspacePaginationResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session):
        query = _validated_query()
        result = PlatformAdminService(session).list_workspaces(
            page=query.page,
            limit=query.limit,
            keyword=query.keyword,
            status=query.status,
        )
        response = _response(PlatformAdminWorkspacePaginationResponse, result)
        logger.debug("platform_admin.workspace_listed page=%s limit=%s", query.page, query.limit)
        return response


@console_ns.route("/platform-admin/workspaces/<uuid:workspace_id>")
class PlatformAdminWorkspaceApi(Resource):
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminWorkspaceResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session, workspace_id: UUID):
        result = PlatformAdminService(session).get_workspace(str(workspace_id))
        response = _response(PlatformAdminWorkspaceResponse, result)
        logger.debug("platform_admin.workspace_viewed workspace_id=%s", workspace_id)
        return response

    @console_ns.expect(console_ns.models[PlatformAdminWorkspaceRenamePayload.__name__])
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminWorkspaceResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session
    def patch(self, session: Session, workspace_id: UUID):
        payload = _validated_payload(PlatformAdminWorkspaceRenamePayload)
        assert isinstance(payload, PlatformAdminWorkspaceRenamePayload)
        account, _ = current_account_with_tenant()
        result = PlatformAdminService(session).rename_workspace(
            workspace_id=str(workspace_id),
            name=payload.name,
            operator_account_id=account.id,
        )
        return _response(PlatformAdminWorkspaceResponse, result)


@console_ns.route("/platform-admin/workspaces/<uuid:workspace_id>/members")
class PlatformAdminWorkspaceMembersApi(Resource):
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminMemberListResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session(write=False)
    def get(self, session: Session, workspace_id: UUID):
        result = {
            "items": PlatformAdminService(session).list_members(str(workspace_id)),
            "mutation_supported": not dify_config.RBAC_ENABLED,
        }
        response = _response(PlatformAdminMemberListResponse, result)
        logger.debug("platform_admin.members_listed workspace_id=%s", workspace_id)
        return response


@console_ns.route("/platform-admin/workspaces/<uuid:workspace_id>/members/invitations")
class PlatformAdminWorkspaceInvitationsApi(Resource):
    @console_ns.expect(console_ns.models[PlatformAdminMemberInvitePayload.__name__])
    @console_ns.response(HTTPStatus.CREATED, "Created", console_ns.models[PlatformAdminMemberInviteResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session
    def post(self, session: Session, workspace_id: UUID):
        payload = _validated_payload(PlatformAdminMemberInvitePayload)
        assert isinstance(payload, PlatformAdminMemberInvitePayload)
        account, _ = current_account_with_tenant()
        result = PlatformAdminService(session).invite_members(
            workspace_id=str(workspace_id),
            emails=tuple(payload.emails),
            role=payload.role,
            language=payload.language,
            operator=account,
        )
        return _response(PlatformAdminMemberInviteResponse, result), HTTPStatus.CREATED


@console_ns.route("/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role")
class PlatformAdminWorkspaceMemberRoleApi(Resource):
    @console_ns.expect(console_ns.models[PlatformAdminMemberRoleUpdatePayload.__name__])
    @console_ns.response(HTTPStatus.OK, "Success", console_ns.models[PlatformAdminMemberRoleUpdateResponse.__name__])
    @setup_required
    @login_required
    @platform_admin_required
    @platform_admin_current_tenant_required
    @account_initialization_required
    @with_session
    def patch(self, session: Session, workspace_id: UUID, member_id: UUID):
        payload = _validated_payload(PlatformAdminMemberRoleUpdatePayload)
        assert isinstance(payload, PlatformAdminMemberRoleUpdatePayload)
        account, _ = current_account_with_tenant()
        result = PlatformAdminService(session).update_member_role(
            workspace_id=str(workspace_id),
            member_id=str(member_id),
            new_role=payload.role,
            operator_account_id=account.id,
        )
        return _response(PlatformAdminMemberRoleUpdateResponse, result)

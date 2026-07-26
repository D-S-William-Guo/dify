"""Cross-workspace platform-administration service.

Write methods own one explicit database transaction on the controller-injected
session. Invitation tokens, cache invalidation, and mail dispatch happen only
after that transaction commits; their failures never masquerade as rollbacks.
"""

import contextlib
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from typing import Literal

from redis.exceptions import LockError, RedisError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from configs import dify_config
from constants.languages import get_valid_language, language_timezone_mapping
from extensions.ext_redis import redis_client
from libs.datetime_utils import naive_utc_now
from libs.platform_admin import PlatformAdminHTTPError
from models.account import Account, AccountStatus, Tenant, TenantAccountJoin, TenantAccountRole, TenantStatus
from services.account_service import RegisterService
from services.billing_service import BillingService
from services.feature_service import FeatureService
from tasks.mail_invite_member_task import send_invite_member_mail_task

logger = logging.getLogger(__name__)

LOCK_TTL_SECONDS = 60
LOCK_BLOCKING_TIMEOUT_SECONDS = 5

WorkspaceStatusFilter = Literal["normal", "archive", "all"]
InviteAction = Literal[
    "account_created",
    "membership_created",
    "invitation_queued",
    "invitation_resent",
    "already_member",
]
EmailDelivery = Literal["queued", "failed", "not_applicable"]


@dataclass(frozen=True)
class WorkspaceOwnerView:
    id: str
    name: str
    email: str


@dataclass(frozen=True)
class WorkspaceView:
    id: str
    name: str
    plan: str
    status: str
    created_at: datetime
    updated_at: datetime
    member_count: int
    owner: WorkspaceOwnerView | None


@dataclass(frozen=True)
class WorkspacePage:
    items: list[WorkspaceView]
    page: int
    limit: int
    total: int
    has_more: bool


@dataclass(frozen=True)
class MemberView:
    id: str
    name: str
    email: str
    status: str
    current: bool
    created_at: datetime
    last_login_at: datetime | None
    last_active_at: datetime | None
    role: str | None
    role_source: Literal["tenant_account_join", "rbac_unavailable"]
    mutation_supported: bool


@dataclass(frozen=True)
class InviteResult:
    email: str
    action: InviteAction
    email_delivery: EmailDelivery


@dataclass(frozen=True)
class InviteBatchResult:
    workspace_id: str
    results: list[InviteResult]


@dataclass(frozen=True)
class MemberRoleUpdateResult:
    result: Literal["success"]
    workspace_id: str
    member_id: str


@dataclass(frozen=True)
class _Dispatch:
    result_index: int
    account: Account
    requires_setup: bool


def _raise(error_code: str, message: str, status_code: int) -> None:
    raise PlatformAdminHTTPError(error_code, message, status_code)


class PlatformAdminService:
    """Perform approved platform-admin reads and low-risk mutations."""

    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_workspaces(
        self,
        *,
        page: int,
        limit: int,
        keyword: str | None,
        status: WorkspaceStatusFilter,
    ) -> WorkspacePage:
        """List normal or archived workspaces with owner and member summaries."""
        filters = []
        if status != "all":
            filters.append(Tenant.status == TenantStatus(status))
        if keyword:
            filters.append(Tenant.name.ilike(f"%{keyword}%"))

        total = self._session.scalar(select(func.count(Tenant.id)).where(*filters)) or 0
        tenants = list(
            self._session.scalars(
                select(Tenant)
                .where(*filters)
                .order_by(Tenant.created_at.desc(), Tenant.id.asc())
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
        )
        items = [self._workspace_view(tenant) for tenant in tenants]
        return WorkspacePage(
            items=items,
            page=page,
            limit=limit,
            total=total,
            has_more=page * limit < total,
        )

    def get_workspace(self, workspace_id: str) -> WorkspaceView:
        """Return one workspace irrespective of normal/archive status."""
        tenant = self._session.scalar(select(Tenant).where(Tenant.id == workspace_id).limit(1))
        if tenant is None:
            _raise("workspace_not_found", "Workspace not found.", 404)
        return self._workspace_view(tenant)

    def list_members(self, workspace_id: str) -> list[MemberView]:
        """List members; RBAC mode deliberately withholds non-authoritative roles."""
        tenant = self._session.scalar(select(Tenant).where(Tenant.id == workspace_id).limit(1))
        if tenant is None:
            _raise("workspace_not_found", "Workspace not found.", 404)

        rows = self._session.execute(
            select(Account, TenantAccountJoin)
            .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
            .where(TenantAccountJoin.tenant_id == workspace_id)
            .order_by(TenantAccountJoin.created_at.asc(), Account.id.asc())
        ).all()
        rbac_enabled = bool(dify_config.RBAC_ENABLED)
        return [
            MemberView(
                id=account.id,
                name=account.name,
                email=account.email,
                status=str(account.status),
                current=join.current,
                created_at=join.created_at,
                last_login_at=account.last_login_at,
                last_active_at=account.last_active_at,
                role=None if rbac_enabled else str(join.role),
                role_source="rbac_unavailable" if rbac_enabled else "tenant_account_join",
                mutation_supported=not rbac_enabled,
            )
            for account, join in rows
        ]

    def rename_workspace(self, *, workspace_id: str, name: str, operator_account_id: str) -> WorkspaceView:
        """Rename a normal workspace in one row-locked transaction."""
        try:
            with self._session.begin():
                tenant = self._session.scalar(
                    select(Tenant).where(Tenant.id == workspace_id).with_for_update().limit(1)
                )
                if tenant is None:
                    _raise("workspace_not_found", "Workspace not found.", 404)
                if tenant.status != TenantStatus.NORMAL:
                    _raise("workspace_unavailable", "Workspace is unavailable for mutation.", 409)
                tenant.name = name
                self._session.flush()
        except IntegrityError:
            _raise("concurrent_operation", "The workspace rename conflicted with another request.", 409)

        logger.info(
            "platform_admin.workspace_renamed workspace_id=%s operator_account_id=%s",
            workspace_id,
            operator_account_id,
        )
        return self._workspace_view(tenant)

    def invite_members(
        self,
        *,
        workspace_id: str,
        emails: tuple[str, ...],
        role: str,
        language: str | None,
        operator: Account,
    ) -> InviteBatchResult:
        """Atomically persist invitation state, then best-effort dispatch mail."""
        if dify_config.RBAC_ENABLED:
            _raise("rbac_mode_not_supported", "Member mutation is unavailable while RBAC is enabled.", 503)
        try:
            normalized_role = TenantAccountRole(role)
        except ValueError:
            _raise("invalid_role", "Invalid member role.", 400)
        if not TenantAccountRole.is_non_owner_role(normalized_role):
            _raise("owner_assignment_deferred", "Owner assignment is deferred.", 409)

        lock_keys = [
            f"platform_admin:invite:tenant:{workspace_id}",
            "platform_admin:invite:seats",
            *[
                f"platform_admin:invite:email:{digest}"
                for digest in sorted(sha256(email.encode()).hexdigest() for email in emails)
            ],
        ]

        try:
            with contextlib.ExitStack() as locks:
                for key in lock_keys:
                    lock = redis_client.lock(
                        key,
                        timeout=LOCK_TTL_SECONDS,
                        blocking_timeout=LOCK_BLOCKING_TIMEOUT_SECONDS,
                    )
                    locks.enter_context(lock)
                batch, dispatches, immediate_join_count, tenant = self._persist_invitations(
                    workspace_id=workspace_id,
                    emails=emails,
                    role=normalized_role,
                    language=language,
                    operator=operator,
                )
        except (LockError, RedisError):
            _raise("concurrent_operation", "The invitation operation could not acquire its locks.", 409)
        except IntegrityError:
            _raise("concurrent_operation", "The invitation operation conflicted with another request.", 409)

        if immediate_join_count > 0 and dify_config.BILLING_ENABLED:
            try:
                BillingService.clean_billing_info_cache(tenant.id)
            except Exception:
                logger.warning(
                    "platform_admin.billing_cache_invalidation_failed workspace_id=%s reason=external_error",
                    tenant.id,
                )

        results = list(batch.results)
        for dispatch in dispatches:
            delivery: EmailDelivery = "failed"
            token: str | None = None
            try:
                token = RegisterService.generate_invite_token(
                    tenant,
                    dispatch.account,
                    str(normalized_role),
                    requires_setup=dispatch.requires_setup,
                )
                send_invite_member_mail_task.delay(
                    language=dispatch.account.interface_language or "en-US",
                    to=dispatch.account.email,
                    token=token,
                    inviter_name=operator.name,
                    workspace_name=tenant.name,
                )
                delivery = "queued"
            except Exception:
                if token is not None:
                    with contextlib.suppress(Exception):
                        RegisterService.revoke_token(None, None, token)
                logger.warning(
                    "platform_admin.invitation_delivery_failed workspace_id=%s account_id=%s reason=dispatch_error",
                    tenant.id,
                    dispatch.account.id,
                )
            results[dispatch.result_index] = replace(results[dispatch.result_index], email_delivery=delivery)

        logger.info(
            "platform_admin.members_invited workspace_id=%s operator_account_id=%s result_count=%s",
            workspace_id,
            operator.id,
            len(results),
        )
        return InviteBatchResult(workspace_id=workspace_id, results=results)

    def update_member_role(
        self,
        *,
        workspace_id: str,
        member_id: str,
        new_role: str,
        operator_account_id: str,
    ) -> MemberRoleUpdateResult:
        """Update a fixed non-owner role in one row-locked transaction."""
        if dify_config.RBAC_ENABLED:
            _raise("rbac_mode_not_supported", "Member mutation is unavailable while RBAC is enabled.", 503)
        try:
            role = TenantAccountRole(new_role)
        except ValueError:
            _raise("invalid_role", "Invalid member role.", 400)
        if not TenantAccountRole.is_non_owner_role(role):
            _raise("owner_assignment_deferred", "Owner assignment is deferred.", 409)

        try:
            with self._session.begin():
                tenant = self._session.scalar(
                    select(Tenant).where(Tenant.id == workspace_id).with_for_update().limit(1)
                )
                if tenant is None:
                    _raise("workspace_not_found", "Workspace not found.", 404)
                if tenant.status != TenantStatus.NORMAL:
                    _raise("workspace_unavailable", "Workspace is unavailable for mutation.", 409)
                join = self._session.scalar(
                    select(TenantAccountJoin)
                    .where(
                        TenantAccountJoin.tenant_id == workspace_id,
                        TenantAccountJoin.account_id == member_id,
                    )
                    .with_for_update()
                    .limit(1)
                )
                if join is None:
                    _raise("member_not_found", "Member not found.", 404)
                account = self._session.scalar(
                    select(Account).where(Account.id == member_id).with_for_update().limit(1)
                )
                if account is None:
                    _raise("member_not_found", "Member not found.", 404)
                if account.status == AccountStatus.UNINITIALIZED:
                    _raise("account_uninitialized", "The account is uninitialized.", 409)
                if account.status not in {AccountStatus.ACTIVE, AccountStatus.PENDING}:
                    _raise("account_disabled", "The account is disabled.", 409)
                if join.role == TenantAccountRole.OWNER:
                    _raise("owner_operation_deferred", "Owner mutation is deferred.", 409)
                if join.role == role:
                    _raise("role_already_assigned", "The member already has this role.", 409)
                join.role = role
                self._session.flush()
        except IntegrityError:
            _raise("concurrent_operation", "The role update conflicted with another request.", 409)

        logger.info(
            "platform_admin.member_role_updated workspace_id=%s member_id=%s operator_account_id=%s",
            workspace_id,
            member_id,
            operator_account_id,
        )
        return MemberRoleUpdateResult(result="success", workspace_id=workspace_id, member_id=member_id)

    def _workspace_view(self, tenant: Tenant) -> WorkspaceView:
        member_count = (
            self._session.scalar(
                select(func.count(TenantAccountJoin.id)).where(TenantAccountJoin.tenant_id == tenant.id)
            )
            or 0
        )
        owner = self._session.execute(
            select(Account)
            .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
            .where(
                TenantAccountJoin.tenant_id == tenant.id,
                TenantAccountJoin.role == TenantAccountRole.OWNER,
            )
            .limit(1)
        ).scalar_one_or_none()
        return WorkspaceView(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan,
            status=str(tenant.status),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            member_count=member_count,
            owner=WorkspaceOwnerView(id=owner.id, name=owner.name, email=owner.email) if owner else None,
        )

    def _persist_invitations(
        self,
        *,
        workspace_id: str,
        emails: tuple[str, ...],
        role: TenantAccountRole,
        language: str | None,
        operator: Account,
    ) -> tuple[InviteBatchResult, list[_Dispatch], int, Tenant]:
        results: list[InviteResult] = []
        dispatches: list[_Dispatch] = []
        immediate_join_count = 0

        with self._session.begin():
            tenant = self._session.scalar(select(Tenant).where(Tenant.id == workspace_id).with_for_update().limit(1))
            if tenant is None:
                _raise("workspace_not_found", "Workspace not found.", 404)
            if tenant.status != TenantStatus.NORMAL:
                _raise("workspace_unavailable", "Workspace is unavailable for mutation.", 409)

            accounts = list(
                self._session.scalars(
                    select(Account).where(func.lower(Account.email).in_(emails)).with_for_update()
                ).all()
            )
            accounts_by_email: dict[str, list[Account]] = {}
            for account in accounts:
                accounts_by_email.setdefault(account.email.strip().lower(), []).append(account)
            if any(len(matches) > 1 for matches in accounts_by_email.values()):
                _raise("email_identity_ambiguous", "An email matches multiple accounts.", 409)

            account_by_email = {email: matches[0] for email, matches in accounts_by_email.items()}
            existing_account_ids = [account.id for account in accounts]
            joins = (
                list(
                    self._session.scalars(
                        select(TenantAccountJoin)
                        .where(
                            TenantAccountJoin.tenant_id == workspace_id,
                            TenantAccountJoin.account_id.in_(existing_account_ids),
                        )
                        .with_for_update()
                    ).all()
                )
                if existing_account_ids
                else []
            )
            join_by_account_id = {join.account_id: join for join in joins}

            new_account_count = 0
            pending_invitation_count = 0
            for email in emails:
                account = account_by_email.get(email)
                join = join_by_account_id.get(account.id) if account else None
                if account is None:
                    new_account_count += 1
                    immediate_join_count += 1
                elif account.status == AccountStatus.PENDING:
                    if join is None:
                        immediate_join_count += 1
                elif account.status == AccountStatus.ACTIVE:
                    if join is None:
                        pending_invitation_count += 1
                elif account.status == AccountStatus.UNINITIALIZED:
                    _raise("account_uninitialized", "The account is uninitialized.", 409)
                else:
                    _raise("account_disabled", "The account is disabled.", 409)

            required_memberships = immediate_join_count + pending_invitation_count
            self._check_capacity(
                tenant_id=workspace_id,
                required_memberships=required_memberships,
                new_account_count=new_account_count,
            )

            if dify_config.BILLING_ENABLED:
                for email in emails:
                    if email not in account_by_email and BillingService.is_email_in_freeze(email):
                        _raise("email_in_freeze", "An invited email is temporarily unavailable.", 409)

            interface_language = get_valid_language(language)
            for email in emails:
                account = account_by_email.get(email)
                join = join_by_account_id.get(account.id) if account else None
                result_index = len(results)
                if account is None:
                    account = Account(
                        name=email.split("@", 1)[0],
                        email=email,
                        password=None,
                        password_salt=None,
                        interface_language=interface_language,
                        interface_theme="light",
                        timezone=language_timezone_mapping.get(interface_language, "UTC"),
                        status=AccountStatus.PENDING,
                        initialized_at=naive_utc_now(),
                    )
                    self._session.add(account)
                    self._session.flush()
                    self._session.add(
                        TenantAccountJoin(
                            tenant_id=workspace_id,
                            account_id=account.id,
                            current=True,
                            role=role,
                            invited_by=operator.id,
                        )
                    )
                    action: InviteAction = "account_created"
                    requires_setup = True
                elif account.status == AccountStatus.PENDING and join is None:
                    self._session.add(
                        TenantAccountJoin(
                            tenant_id=workspace_id,
                            account_id=account.id,
                            current=False,
                            role=role,
                            invited_by=operator.id,
                        )
                    )
                    action = "membership_created"
                    requires_setup = True
                elif account.status == AccountStatus.PENDING:
                    action = "invitation_resent"
                    requires_setup = True
                elif join is None:
                    action = "invitation_queued"
                    requires_setup = False
                else:
                    results.append(InviteResult(email=email, action="already_member", email_delivery="not_applicable"))
                    continue

                results.append(InviteResult(email=email, action=action, email_delivery="failed"))
                dispatches.append(_Dispatch(result_index=result_index, account=account, requires_setup=requires_setup))

            self._session.flush()

        return (
            InviteBatchResult(workspace_id=workspace_id, results=results),
            dispatches,
            immediate_join_count,
            tenant,
        )

    def _check_capacity(self, *, tenant_id: str, required_memberships: int, new_account_count: int) -> None:
        if required_memberships <= 0:
            return

        features = FeatureService.get_features(tenant_id=tenant_id, exclude_vector_space=True)
        if dify_config.ENTERPRISE_ENABLED:
            workspace_members = features.workspace_members
            if workspace_members.enabled is True and not workspace_members.is_available(required_memberships):
                _raise("workspace_member_limit_exceeded", "Workspace member limit exceeded.", 403)
            if new_account_count > 0:
                seats = FeatureService.get_system_features(is_authenticated=True).license.seats
                if not seats.is_available(new_account_count):
                    _raise("seat_limit_exceeded", "Licensed seat limit exceeded.", 403)
            return

        if dify_config.BILLING_ENABLED and features.billing.enabled is True:
            current_member_count = (
                self._session.scalar(
                    select(func.count(TenantAccountJoin.id)).where(TenantAccountJoin.tenant_id == tenant_id)
                )
                or 0
            )
            if 0 < features.members.limit < current_member_count + required_memberships:
                _raise("workspace_member_limit_exceeded", "Workspace member limit exceeded.", 403)

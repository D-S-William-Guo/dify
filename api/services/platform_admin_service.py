from urllib import parse

from flask import abort
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from configs import dify_config
from constants.languages import get_valid_language
from extensions.ext_database import db
from models.account import Account, AccountStatus, Tenant, TenantAccountJoin, TenantAccountRole, TenantStatus
from services.account_service import AccountService, RegisterService, TenantService
from services.billing_service import BillingService
from services.errors.account import AccountAlreadyInTenantError, MemberNotInTenantError, RoleAlreadyAssignedError
from tasks.mail_invite_member_task import send_invite_member_mail_task


class PlatformAdminService:
    @staticmethod
    def get_workspace(workspace_id: str) -> Tenant:
        tenant = db.session.get(Tenant, workspace_id)
        if tenant is None or tenant.status != TenantStatus.NORMAL:
            abort(404)
        return tenant

    @staticmethod
    def list_workspaces(*, page: int = 1, limit: int = 50, keyword: str | None = None) -> tuple[list[dict], int]:
        stmt = select(Tenant).where(Tenant.status == TenantStatus.NORMAL)
        if keyword:
            stmt = stmt.where(Tenant.name.ilike(f"%{keyword.strip()}%"))

        pagination = db.paginate(select=stmt.order_by(Tenant.created_at.desc()), page=page, per_page=limit, error_out=False)
        items = [PlatformAdminService.serialize_workspace(tenant) for tenant in pagination.items]
        return items, pagination.total

    @staticmethod
    def serialize_workspace(tenant: Tenant) -> dict:
        owner = (
            db.session.query(Account)
            .join(TenantAccountJoin, Account.id == TenantAccountJoin.account_id)
            .where(TenantAccountJoin.tenant_id == tenant.id, TenantAccountJoin.role == TenantAccountRole.OWNER)
            .first()
        )
        member_count = (
            db.session.query(func.count(TenantAccountJoin.id))
            .where(TenantAccountJoin.tenant_id == tenant.id)
            .scalar()
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan,
            "status": tenant.status,
            "created_at": int(tenant.created_at.timestamp()),
            "member_count": int(member_count or 0),
            "owner": (
                {
                    "id": owner.id,
                    "name": owner.name,
                    "email": owner.email,
                }
                if owner
                else None
            ),
        }

    @staticmethod
    def create_workspace(
        *,
        name: str,
        owner_email: str | None,
        owner_name: str | None,
        inviter: Account,
        language: str | None,
    ) -> tuple[Tenant, str | None]:
        tenant = TenantService.create_tenant(name=name, is_from_dashboard=True)
        invitation_url = None

        if owner_email:
            invitation_url = PlatformAdminService.assign_workspace_owner(
                tenant=tenant,
                owner_email=owner_email,
                owner_name=owner_name,
                inviter=inviter,
                language=language,
            )

        return tenant, invitation_url

    @staticmethod
    def assign_workspace_owner(
        *,
        tenant: Tenant,
        owner_email: str,
        owner_name: str | None,
        inviter: Account,
        language: str | None,
    ) -> str | None:
        normalized_email = owner_email.lower()
        with Session(db.engine) as session:
            account = AccountService.get_account_by_email_with_case_fallback(normalized_email, session=session)

        should_send_invite = False
        if not account:
            account = RegisterService.register(
                email=normalized_email,
                name=owner_name or normalized_email.split("@")[0],
                language=get_valid_language(language),
                status=AccountStatus.PENDING,
                is_setup=True,
                create_workspace_required=False,
            )
            should_send_invite = True
        elif account.status in {AccountStatus.PENDING, AccountStatus.UNINITIALIZED}:
            should_send_invite = True

        if should_send_invite and owner_name:
            account.name = owner_name
            db.session.commit()

        TenantService.create_tenant_member(tenant, account, role=TenantAccountRole.OWNER)

        if should_send_invite:
            TenantService.switch_tenant(account, tenant.id)
            token = RegisterService.generate_invite_token(tenant, account)
            send_invite_member_mail_task.delay(
                language=account.interface_language or get_valid_language(language),
                to=account.email,
                token=token,
                inviter_name=inviter.name,
                workspace_name=tenant.name,
            )
            encoded_email = parse.quote(account.email.lower())
            return f"{dify_config.CONSOLE_WEB_URL}/activate?email={encoded_email}&token={token}"

        return None

    @staticmethod
    def get_workspace_members(tenant: Tenant) -> list[Account]:
        return TenantService.get_tenant_members(tenant)

    @staticmethod
    def invite_member(
        *,
        tenant: Tenant,
        email: str,
        language: str | None,
        role: str,
        inviter: Account,
    ) -> str:
        normalized_email = email.lower()

        with Session(db.engine) as session:
            account = AccountService.get_account_by_email_with_case_fallback(normalized_email, session=session)

        if not account:
            account = RegisterService.register(
                email=normalized_email,
                name=normalized_email.split("@")[0],
                language=get_valid_language(language),
                status=AccountStatus.PENDING,
                is_setup=True,
                create_workspace_required=False,
            )
            TenantService.create_tenant_member(tenant, account, role)
            TenantService.switch_tenant(account, tenant.id)
        else:
            tenant_join = db.session.query(TenantAccountJoin).filter_by(tenant_id=tenant.id, account_id=account.id).first()
            if not tenant_join:
                TenantService.create_tenant_member(tenant, account, role)

            if account.status == AccountStatus.ACTIVE:
                raise AccountAlreadyInTenantError("Account already in tenant.")

            if account.status not in {AccountStatus.PENDING, AccountStatus.UNINITIALIZED}:
                raise ValueError("Only active or pending accounts can be invited.")

            TenantService.switch_tenant(account, tenant.id)

        token = RegisterService.generate_invite_token(tenant, account)
        send_invite_member_mail_task.delay(
            language=account.interface_language or get_valid_language(language),
            to=account.email,
            token=token,
            inviter_name=inviter.name,
            workspace_name=tenant.name,
        )
        return token

    @staticmethod
    def update_member_role(*, tenant: Tenant, member: Account, new_role: str):
        target_member_join = db.session.query(TenantAccountJoin).filter_by(tenant_id=tenant.id, account_id=member.id).first()
        if not target_member_join:
            raise MemberNotInTenantError("Member not in tenant.")

        if target_member_join.role == new_role:
            raise RoleAlreadyAssignedError("The provided role is already assigned to the member.")

        target_member_join.role = TenantAccountRole(new_role)
        db.session.commit()

    @staticmethod
    def remove_member(*, tenant: Tenant, account: Account):
        tenant_join = db.session.query(TenantAccountJoin).filter_by(tenant_id=tenant.id, account_id=account.id).first()
        if not tenant_join:
            raise MemberNotInTenantError("Member not in tenant.")

        account_id = account.id
        account_email = account.email
        db.session.delete(tenant_join)

        should_delete_account = False
        if account.status == AccountStatus.PENDING:
            remaining_joins = db.session.query(TenantAccountJoin).filter_by(account_id=account_id).count()
            if remaining_joins == 0:
                db.session.delete(account)
                should_delete_account = True

        db.session.commit()

        if dify_config.BILLING_ENABLED:
            BillingService.clean_billing_info_cache(tenant.id)

        if should_delete_account:
            return {"deleted_pending_account_email": account_email}

        return None

    @staticmethod
    def rename_workspace(*, tenant: Tenant, name: str) -> Tenant:
        tenant.name = name
        db.session.commit()
        return tenant

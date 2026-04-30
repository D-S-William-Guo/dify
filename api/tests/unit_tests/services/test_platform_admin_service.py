from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models.account import AccountStatus, TenantAccountRole
from services.platform_admin_service import PlatformAdminService


def test_serialize_workspace_uses_supplied_owner_and_member_count():
    tenant = SimpleNamespace(
        id="tenant-1",
        name="Enterprise Workspace",
        plan="sandbox",
        status="normal",
        created_at=SimpleNamespace(timestamp=lambda: 1710000000),
    )
    owner = {"id": "account-1", "name": "Owner", "email": "owner@example.com"}

    result = PlatformAdminService.serialize_workspace(tenant, owner=owner, member_count=3)

    assert result == {
        "id": "tenant-1",
        "name": "Enterprise Workspace",
        "plan": "sandbox",
        "status": "normal",
        "created_at": 1710000000,
        "member_count": 3,
        "owner": owner,
    }


@patch("services.platform_admin_service.send_invite_member_mail_task")
@patch("services.platform_admin_service.RegisterService")
@patch("services.platform_admin_service.TenantService")
@patch("services.platform_admin_service.dify_config")
@patch(
    "services.platform_admin_service.PlatformAdminService._get_account_by_email_with_case_fallback",
    return_value=None,
)
def test_assign_workspace_owner_registers_pending_owner_and_returns_invite_url(
    mock_get_account,
    mock_dify_config,
    mock_tenant_service,
    mock_register_service,
    mock_mail_task,
):
    mock_dify_config.CONSOLE_WEB_URL = "http://localhost"
    tenant = SimpleNamespace(id="tenant-1", name="Managed Workspace")
    inviter = SimpleNamespace(name="Platform Admin")
    account = SimpleNamespace(
        email="owner@example.com",
        interface_language="en-US",
    )
    mock_register_service.register.return_value = account
    mock_register_service.generate_invite_token.return_value = "invite-token"

    result = PlatformAdminService.assign_workspace_owner(
        tenant=tenant,
        owner_email="Owner@Example.com",
        owner_name="Owner",
        inviter=inviter,
        language="en-US",
    )

    mock_get_account.assert_called_once_with("owner@example.com")
    mock_register_service.register.assert_called_once_with(
        email="owner@example.com",
        name="Owner",
        language="en-US",
        status=AccountStatus.PENDING,
        is_setup=True,
        create_workspace_required=False,
    )
    mock_tenant_service.create_tenant_member.assert_called_once_with(
        tenant,
        account,
        role=TenantAccountRole.OWNER,
    )
    mock_tenant_service.switch_tenant.assert_called_once_with(account, tenant.id)
    mock_mail_task.delay.assert_called_once_with(
        language="en-US",
        to="owner@example.com",
        token="invite-token",
        inviter_name="Platform Admin",
        workspace_name="Managed Workspace",
    )
    assert result == "http://localhost/activate?email=owner%40example.com&token=invite-token"


@patch("services.platform_admin_service.dify_config")
@patch("services.platform_admin_service.db")
def test_remove_member_deletes_pending_account_without_remaining_workspaces(mock_db, mock_dify_config):
    mock_dify_config.BILLING_ENABLED = False
    tenant = SimpleNamespace(id="tenant-1")
    account = SimpleNamespace(id="account-1", email="pending@example.com", status=AccountStatus.PENDING)
    tenant_join = SimpleNamespace(id="join-1")
    first_query = MagicMock()
    first_query.filter_by.return_value.first.return_value = tenant_join
    second_query = MagicMock()
    second_query.filter_by.return_value.count.return_value = 0
    mock_db.session.query.side_effect = [first_query, second_query]

    result = PlatformAdminService.remove_member(tenant=tenant, account=account)

    mock_db.session.delete.assert_any_call(tenant_join)
    mock_db.session.delete.assert_any_call(account)
    mock_db.session.commit.assert_called_once()
    assert result == {"deleted_pending_account_email": "pending@example.com"}

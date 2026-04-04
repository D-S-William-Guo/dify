from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call

from pytest_mock import MockerFixture

from services.platform_admin_service import PlatformAdminService, TenantStatus


def test_list_workspaces_should_serialize_with_prefetched_owner_and_member_count(
    mocker: MockerFixture,
) -> None:
    # Arrange
    tenant_a = SimpleNamespace(
        id="tenant-a",
        name="Workspace A",
        status=TenantStatus.NORMAL,
        plan="basic",
        created_at=datetime(2026, 4, 4, 10, 0, 0),
    )
    tenant_b = SimpleNamespace(
        id="tenant-b",
        name="Workspace B",
        status=TenantStatus.NORMAL,
        plan="pro",
        created_at=datetime(2026, 4, 4, 11, 0, 0),
    )
    pagination = SimpleNamespace(items=[tenant_a, tenant_b], total=2)

    mocked_db = mocker.patch("services.platform_admin_service.db")
    mocked_db.paginate.return_value = pagination
    mocked_db.session.execute.side_effect = [
        SimpleNamespace(
            all=lambda: [
                ("tenant-a", "owner-a", "Alice", "alice@example.com"),
                ("tenant-b", "owner-b", "Bob", "bob@example.com"),
            ]
        ),
        SimpleNamespace(
            all=lambda: [
                ("tenant-a", 3),
                ("tenant-b", 7),
            ]
        ),
    ]

    serialize_workspace = mocker.patch.object(
        PlatformAdminService,
        "serialize_workspace",
        side_effect=lambda tenant, *, owner=None, member_count=None: {
            "id": tenant.id,
            "owner": owner,
            "member_count": member_count,
        },
    )

    # Act
    items, total = PlatformAdminService.list_workspaces(keyword="Workspace")

    # Assert
    assert total == 2
    assert items == [
        {
            "id": "tenant-a",
            "owner": {
                "id": "owner-a",
                "name": "Alice",
                "email": "alice@example.com",
            },
            "member_count": 3,
        },
        {
            "id": "tenant-b",
            "owner": {
                "id": "owner-b",
                "name": "Bob",
                "email": "bob@example.com",
            },
            "member_count": 7,
        },
    ]
    assert mocked_db.session.execute.call_count == 2
    serialize_workspace.assert_has_calls(
        [
            call(
                tenant_a,
                owner={"id": "owner-a", "name": "Alice", "email": "alice@example.com"},
                member_count=3,
            ),
            call(
                tenant_b,
                owner={"id": "owner-b", "name": "Bob", "email": "bob@example.com"},
                member_count=7,
            ),
        ]
    )


def test_list_workspaces_should_skip_prefetch_queries_when_page_is_empty(
    mocker: MockerFixture,
) -> None:
    # Arrange
    mocked_db = mocker.patch("services.platform_admin_service.db")
    mocked_db.paginate.return_value = SimpleNamespace(items=[], total=0)
    mocked_db.session.execute = MagicMock()

    serialize_workspace = mocker.patch.object(PlatformAdminService, "serialize_workspace")

    # Act
    items, total = PlatformAdminService.list_workspaces()

    # Assert
    assert items == []
    assert total == 0
    mocked_db.session.execute.assert_not_called()
    serialize_workspace.assert_not_called()

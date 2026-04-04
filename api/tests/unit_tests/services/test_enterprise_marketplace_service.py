from types import SimpleNamespace
from unittest.mock import call

from pytest_mock import MockerFixture

from services.enterprise_marketplace_service import EnterpriseMarketplaceService


def test_serialize_asset_list_should_pass_prefetched_models_to_serializer(
    mocker: MockerFixture,
) -> None:
    # Arrange
    asset_a = SimpleNamespace(
        id="asset-a",
        source_app_id="app-a",
        submitter_account_id="account-a",
        source_tenant_id="tenant-a",
    )
    asset_b = SimpleNamespace(
        id="asset-b",
        source_app_id="app-b",
        submitter_account_id="account-b",
        source_tenant_id="tenant-b",
    )

    app_a = SimpleNamespace(id="app-a", status="normal")
    app_b = SimpleNamespace(id="app-b", status="normal")
    submitter_a = SimpleNamespace(id="account-a", name="Alice")
    submitter_b = SimpleNamespace(id="account-b", name="Bob")
    tenant_a = SimpleNamespace(id="tenant-a", name="Workspace A")
    tenant_b = SimpleNamespace(id="tenant-b", name="Workspace B")

    mocked_db = mocker.patch("services.enterprise_marketplace_service.db")
    mocked_db.session.scalars.side_effect = [
        SimpleNamespace(all=lambda: [app_a, app_b]),
        SimpleNamespace(all=lambda: [submitter_a, submitter_b]),
        SimpleNamespace(all=lambda: [tenant_a, tenant_b]),
    ]

    serialize_asset = mocker.patch.object(
        EnterpriseMarketplaceService,
        "serialize_asset",
        side_effect=lambda *, asset, include_workspace_name, source_app=None, submitter=None, source_tenant=None: {
            "asset_id": asset.id,
            "source_app_id": source_app.id if source_app else None,
            "submitter_id": submitter.id if submitter else None,
            "tenant_id": source_tenant.id if source_tenant else None,
            "include_workspace_name": include_workspace_name,
        },
    )

    # Act
    items = EnterpriseMarketplaceService.serialize_asset_list(
        assets=[asset_a, asset_b],
        include_workspace_name=True,
    )

    # Assert
    assert items == [
        {
            "asset_id": "asset-a",
            "source_app_id": "app-a",
            "submitter_id": "account-a",
            "tenant_id": "tenant-a",
            "include_workspace_name": True,
        },
        {
            "asset_id": "asset-b",
            "source_app_id": "app-b",
            "submitter_id": "account-b",
            "tenant_id": "tenant-b",
            "include_workspace_name": True,
        },
    ]
    assert mocked_db.session.scalars.call_count == 3
    serialize_asset.assert_has_calls(
        [
            call(
                asset=asset_a,
                include_workspace_name=True,
                source_app=app_a,
                submitter=submitter_a,
                source_tenant=tenant_a,
            ),
            call(
                asset=asset_b,
                include_workspace_name=True,
                source_app=app_b,
                submitter=submitter_b,
                source_tenant=tenant_b,
            ),
        ]
    )


def test_serialize_asset_list_should_skip_assets_without_normal_source_apps(
    mocker: MockerFixture,
) -> None:
    # Arrange
    asset = SimpleNamespace(
        id="asset-a",
        source_app_id="app-a",
        submitter_account_id="account-a",
        source_tenant_id="tenant-a",
    )
    archived_app = SimpleNamespace(id="app-a", status="archived")

    mocked_db = mocker.patch("services.enterprise_marketplace_service.db")
    mocked_db.session.scalars.side_effect = [
        SimpleNamespace(all=lambda: [archived_app]),
        SimpleNamespace(all=lambda: [SimpleNamespace(id="account-a")]),
        SimpleNamespace(all=lambda: [SimpleNamespace(id="tenant-a")]),
    ]

    serialize_asset = mocker.patch.object(EnterpriseMarketplaceService, "serialize_asset")

    # Act
    items = EnterpriseMarketplaceService.serialize_asset_list(
        assets=[asset],
        include_workspace_name=False,
    )

    # Assert
    assert items == []
    serialize_asset.assert_not_called()

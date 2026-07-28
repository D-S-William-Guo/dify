"""Unit tests for enterprise marketplace models."""

from __future__ import annotations

from enum import StrEnum
from typing import get_args, get_type_hints

import pytest
import sqlalchemy as sa
from sqlalchemy import CheckConstraint, UniqueConstraint

from models import (
    EnterpriseMarketplaceAsset,
    EnterpriseMarketplaceAssetPublicationStatus,
    EnterpriseMarketplaceAssetSnapshot,
    EnterpriseMarketplaceAssetSnapshotState,
)
from models.base import TypeBase


class TestPublicationStatusEnum:
    def test_publication_status_has_required_values(self) -> None:
        assert EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED.value == "unpublished"
        assert EnterpriseMarketplaceAssetPublicationStatus.PUBLISHED.value == "published"
        assert EnterpriseMarketplaceAssetPublicationStatus.UNLISTED.value == "unlisted"

    def test_publication_status_is_str_enum(self) -> None:
        assert issubclass(EnterpriseMarketplaceAssetPublicationStatus, StrEnum)


class TestSnapshotStateEnum:
    def test_snapshot_state_has_required_values(self) -> None:
        assert EnterpriseMarketplaceAssetSnapshotState.NONE.value == "none"
        assert EnterpriseMarketplaceAssetSnapshotState.READY.value == "ready"
        assert EnterpriseMarketplaceAssetSnapshotState.BACKFILL_PENDING.value == "backfill_pending"
        assert EnterpriseMarketplaceAssetSnapshotState.SOURCE_MISSING.value == "source_missing"
        assert EnterpriseMarketplaceAssetSnapshotState.FAILED.value == "failed"

    def test_snapshot_state_is_str_enum(self) -> None:
        assert issubclass(EnterpriseMarketplaceAssetSnapshotState, StrEnum)


class TestEnterpriseMarketplaceAssetTable:
    """Table metadata: name, columns, constraints, indexes."""

    @staticmethod
    def _table():
        t = EnterpriseMarketplaceAsset.__table__
        assert t is not None
        return t

    def test_table_name(self) -> None:
        assert EnterpriseMarketplaceAsset.__tablename__ == "enterprise_marketplace_assets"

    def test_inherits_type_base(self) -> None:
        assert issubclass(EnterpriseMarketplaceAsset, TypeBase)

    def test_all_legacy_columns_present(self) -> None:
        legacy = {
            "id", "source_tenant_id", "source_app_id", "submitter_account_id",
            "reviewer_account_id", "status", "title", "description", "category",
            "tags", "scenario", "allow_show_workspace_name", "review_note",
            "created_at", "updated_at", "reviewed_at",
        }
        actual = {c.name for c in self._table().columns}
        for col in legacy:
            assert col in actual, f"missing legacy column: {col}"

    def test_all_b4_columns_present(self) -> None:
        b4 = {
            "publication_status", "published_snapshot_id",
            "next_snapshot_version", "row_version",
            "snapshot_state", "snapshot_error_code",
        }
        actual = {c.name for c in self._table().columns}
        for col in b4:
            assert col in actual, f"missing B4 column: {col}"

    def test_tags_type_is_list(self) -> None:
        inst = EnterpriseMarketplaceAsset(
            source_tenant_id="t1",
            source_app_id="a1",
            submitter_account_id="acct1",
            title="test",
        )
        assert isinstance(inst.tags, list)
        assert inst.tags == []

    def test_tags_default_is_fresh_list_per_instance(self) -> None:
        a = EnterpriseMarketplaceAsset(
            source_tenant_id="t1", source_app_id="a1",
            submitter_account_id="acct1", title="test",
        )
        b = EnterpriseMarketplaceAsset(
            source_tenant_id="t2", source_app_id="a2",
            submitter_account_id="acct2", title="test2",
        )
        a.tags.append("shared")
        assert b.tags == []
        assert a.tags == ["shared"]

    # ── server_default vs python default ──

    def test_publication_status_server_default(self) -> None:
        col = self._table().columns["publication_status"]
        sd = col.server_default
        assert sd is not None
        assert sd.arg.text == "'unpublished'"

    def test_publication_status_python_default(self) -> None:
        col = self._table().columns["publication_status"]
        assert col.default is not None
        assert col.default.arg == EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED

    def test_snapshot_state_server_default(self) -> None:
        col = self._table().columns["snapshot_state"]
        sd = col.server_default
        assert sd is not None
        assert sd.arg.text == "'none'"

    def test_snapshot_state_python_default(self) -> None:
        col = self._table().columns["snapshot_state"]
        assert col.default is not None
        assert col.default.arg == EnterpriseMarketplaceAssetSnapshotState.NONE

    def test_next_snapshot_version_server_default_is_1(self) -> None:
        col = self._table().columns["next_snapshot_version"]
        sd = col.server_default
        assert sd is not None
        assert sd.arg.text == "1"

    def test_next_snapshot_version_python_default_is_1(self) -> None:
        col = self._table().columns["next_snapshot_version"]
        assert col.default is not None
        assert col.default.arg == 1

    def test_row_version_server_default_is_0(self) -> None:
        col = self._table().columns["row_version"]
        sd = col.server_default
        assert sd is not None
        assert sd.arg.text == "0"

    def test_row_version_python_default_is_0(self) -> None:
        col = self._table().columns["row_version"]
        assert col.default is not None
        assert col.default.arg == 0

    # ── nullable ──

    def test_publication_status_not_nullable(self) -> None:
        assert not self._table().columns["publication_status"].nullable

    def test_snapshot_state_not_nullable(self) -> None:
        assert not self._table().columns["snapshot_state"].nullable

    def test_published_snapshot_id_nullable(self) -> None:
        assert self._table().columns["published_snapshot_id"].nullable

    def test_snapshot_error_code_nullable(self) -> None:
        assert self._table().columns["snapshot_error_code"].nullable

    # ── Constraints ──

    def test_pk_is_id_with_correct_name(self) -> None:
        pk = self._table().primary_key
        assert pk.name == "enterprise_marketplace_asset_pkey"
        assert {c.name for c in pk.columns} == {"id"}

    def test_unique_source_app_with_correct_name(self) -> None:
        uniqs = [c for c in self._table().constraints if isinstance(c, UniqueConstraint)]
        source_uniq = [u for u in uniqs if u.name == "unique_enterprise_marketplace_source_app"]
        assert len(source_uniq) == 1
        assert {c.name for c in source_uniq[0].columns} == {"source_app_id"}

    def test_publication_status_check_exists_with_expected_sql(self) -> None:
        checks = [c for c in self._table().constraints if isinstance(c, CheckConstraint)]
        found = [c for c in checks if "publication_status" in str(c.sqltext)]
        assert len(found) == 1
        assert "published" in str(found[0].sqltext)
        assert "unpublished" in str(found[0].sqltext)
        assert "unlisted" in str(found[0].sqltext)

    def test_snapshot_state_check_exists_with_expected_sql(self) -> None:
        checks = [c for c in self._table().constraints if isinstance(c, CheckConstraint)]
        found = [c for c in checks if "snapshot_state" in str(c.sqltext)]
        assert len(found) == 1
        assert "none" in str(found[0].sqltext)
        assert "ready" in str(found[0].sqltext)
        assert "backfill_pending" in str(found[0].sqltext)

    def test_next_snapshot_version_check_exists_with_expected_sql(self) -> None:
        checks = [c for c in self._table().constraints if isinstance(c, CheckConstraint)]
        found = [c for c in checks if "next_snapshot_version" in str(c.sqltext)]
        assert len(found) == 1
        assert ">= 1" in str(found[0].sqltext)

    def test_no_legacy_status_check(self) -> None:
        for c in self._table().constraints:
            if isinstance(c, CheckConstraint):
                text = str(c.sqltext)
                is_legacy = (
                    "status" in text
                    and "publication_status" not in text
                    and "snapshot_state" not in text
                    and "next_snapshot_version" not in text
                )
                assert not is_legacy, f"unexpected legacy status CHECK: {text}"

    def test_no_physical_fks(self) -> None:
        for c in self._table().foreign_key_constraints:
            pytest.fail(f"unexpected FK: {c}")

    # ── Indexes ──

    def test_publication_idx_name_and_columns(self) -> None:
        idx = self._table().indexes
        found = [i for i in idx if i.name == "enterprise_marketplace_asset_publication_idx"]
        assert len(found) == 1
        col_names = [c.name for c in found[0].columns]
        assert col_names == ["publication_status", "updated_at", "id"]

    def test_submitter_idx_name_and_columns(self) -> None:
        idx = self._table().indexes
        found = [i for i in idx if i.name == "enterprise_marketplace_asset_submitter_idx"]
        assert len(found) == 1
        col_names = [c.name for c in found[0].columns]
        assert col_names == ["source_tenant_id", "submitter_account_id", "updated_at", "id"]

    # ── published_snapshot_id is a soft reference ──

    def test_published_snapshot_id_no_fk(self) -> None:
        col = self._table().columns["published_snapshot_id"]
        assert not col.foreign_keys


class TestEnterpriseMarketplaceAssetSnapshotTable:
    """Snapshot table metadata."""

    @staticmethod
    def _table():
        t = EnterpriseMarketplaceAssetSnapshot.__table__
        assert t is not None
        return t

    def test_table_name(self) -> None:
        assert EnterpriseMarketplaceAssetSnapshot.__tablename__ == "enterprise_marketplace_asset_snapshots"

    def test_inherits_type_base(self) -> None:
        assert issubclass(EnterpriseMarketplaceAssetSnapshot, TypeBase)

    def test_all_required_columns_present(self) -> None:
        required = {
            "id", "asset_id", "snapshot_version", "dsl_content", "dsl_version",
            "content_sha256", "frozen_at", "source_app_id", "source_tenant_id",
            "source_tenant_name", "submitter_account_id", "reviewer_account_id",
            "title", "description", "category", "tags", "scenario",
            "allow_show_workspace_name", "app_name", "app_description", "app_mode",
            "app_icon_type", "app_icon", "app_icon_background", "dependencies",
        }
        actual = {c.name for c in self._table().columns}
        for col in required:
            assert col in actual, f"missing snapshot column: {col}"

    def test_content_sha256_is_varchar_not_char(self) -> None:
        col = self._table().columns["content_sha256"]
        col_type = col.type
        assert not isinstance(col_type, sa.CHAR), "content_sha256 must not be CHAR"
        assert isinstance(col_type, sa.VARCHAR)
        assert col_type.length == 64

    # ── List-typed JSON defaults ──

    def test_tags_are_list(self) -> None:
        inst = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a1", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="a" * 64, frozen_at=None,
            source_app_id="app1", source_tenant_id="t1",
            submitter_account_id="acct1", reviewer_account_id="acct2",
            title="t", app_name="app", app_mode="chat",
        )
        assert isinstance(inst.tags, list)
        assert inst.tags == []

    def test_dependencies_are_list(self) -> None:
        inst = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a1", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="a" * 64, frozen_at=None,
            source_app_id="app1", source_tenant_id="t1",
            submitter_account_id="acct1", reviewer_account_id="acct2",
            title="t", app_name="app", app_mode="chat",
        )
        assert isinstance(inst.dependencies, list)
        assert inst.dependencies == []

    def test_tags_default_not_shared(self) -> None:
        a = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a1", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="a" * 64, frozen_at=None,
            source_app_id="app1", source_tenant_id="t1",
            submitter_account_id="acct1", reviewer_account_id="acct2",
            title="t", app_name="app", app_mode="chat",
        )
        b = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a2", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="b" * 64, frozen_at=None,
            source_app_id="app2", source_tenant_id="t2",
            submitter_account_id="acct3", reviewer_account_id="acct4",
            title="t2", app_name="app2", app_mode="workflow",
        )
        a.tags.append("shared")
        assert b.tags == []

    def test_dependencies_default_not_shared(self) -> None:
        a = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a1", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="a" * 64, frozen_at=None,
            source_app_id="app1", source_tenant_id="t1",
            submitter_account_id="acct1", reviewer_account_id="acct2",
            title="t", app_name="app", app_mode="chat",
        )
        b = EnterpriseMarketplaceAssetSnapshot(
            asset_id="a2", snapshot_version=1, dsl_content="", dsl_version="1",
            content_sha256="b" * 64, frozen_at=None,
            source_app_id="app2", source_tenant_id="t2",
            submitter_account_id="acct3", reviewer_account_id="acct4",
            title="t2", app_name="app2", app_mode="workflow",
        )
        a.dependencies.append({"plugin": "x"})
        assert b.dependencies == []

    # ── Nullable columns ──

    def test_non_null_columns(self) -> None:
        t = self._table()
        non_null = {"asset_id", "snapshot_version", "dsl_content", "dsl_version",
                     "content_sha256", "frozen_at", "source_app_id", "source_tenant_id",
                     "submitter_account_id", "reviewer_account_id", "title",
                     "category", "app_name", "app_mode", "dependencies"}
        for name in non_null:
            assert not t.columns[name].nullable, f"{name} must be NOT NULL"

    def test_nullable_columns(self) -> None:
        t = self._table()
        nullable = {"source_tenant_name", "app_icon_type", "app_icon", "app_icon_background"}
        for name in nullable:
            assert t.columns[name].nullable, f"{name} must be nullable"

    # ── Constraints ──

    def test_pk_name_and_column(self) -> None:
        pk = self._table().primary_key
        assert pk.name == "enterprise_marketplace_snapshot_pkey"
        assert {c.name for c in pk.columns} == {"id"}

    def test_asset_version_unique_name_and_columns(self) -> None:
        uniqs = [c for c in self._table().constraints if isinstance(c, UniqueConstraint)]
        found = [u for u in uniqs if u.name == "enterprise_marketplace_snapshot_asset_version_uq"]
        assert len(found) == 1
        assert {c.name for c in found[0].columns} == {"asset_id", "snapshot_version"}

    def test_snapshot_version_check_exists(self) -> None:
        checks = [c for c in self._table().constraints if isinstance(c, CheckConstraint)]
        found = [c for c in checks if "snapshot_version" in str(c.sqltext)]
        assert len(found) == 1
        assert ">= 1" in str(found[0].sqltext)

    def test_content_sha256_length_check_exists(self) -> None:
        checks = [c for c in self._table().constraints if isinstance(c, CheckConstraint)]
        found = [c for c in checks if "content_sha256" in str(c.sqltext)]
        assert len(found) == 1
        assert "64" in str(found[0].sqltext)

    def test_no_physical_fks(self) -> None:
        for c in self._table().foreign_key_constraints:
            pytest.fail(f"unexpected FK on snapshot: {c}")

    def test_asset_id_no_fk(self) -> None:
        col = self._table().columns["asset_id"]
        assert not col.foreign_keys

    # ── Indexes ──

    def test_asset_frozen_idx_name_and_columns(self) -> None:
        idx = self._table().indexes
        found = [i for i in idx if i.name == "enterprise_marketplace_snapshot_asset_frozen_idx"]
        assert len(found) == 1
        col_names = [c.name for c in found[0].columns]
        assert col_names == ["asset_id", "frozen_at", "id"]

    def test_sha256_idx_name_and_column(self) -> None:
        idx = self._table().indexes
        found = [i for i in idx if i.name == "enterprise_marketplace_snapshot_sha256_idx"]
        assert len(found) == 1
        col_names = [c.name for c in found[0].columns]
        assert col_names == ["content_sha256"]


class TestModelExportRegistration:
    def test_asset_model_in_all(self) -> None:
        from models import __all__ as models_all
        assert "EnterpriseMarketplaceAsset" in models_all

    def test_snapshot_model_in_all(self) -> None:
        from models import __all__ as models_all
        assert "EnterpriseMarketplaceAssetSnapshot" in models_all

    def test_publication_status_enum_in_all(self) -> None:
        from models import __all__ as models_all
        assert "EnterpriseMarketplaceAssetPublicationStatus" in models_all

    def test_snapshot_state_enum_in_all(self) -> None:
        from models import __all__ as models_all
        assert "EnterpriseMarketplaceAssetSnapshotState" in models_all


class TestModelTypeAnnotations:
    """Verify Mapped type parameters via get_type_hints."""

    def test_asset_tags_is_list_str(self) -> None:
        hints = get_type_hints(EnterpriseMarketplaceAsset, include_extras=False)
        inner = get_args(hints["tags"])[0]
        assert inner == list[str], f"expected list[str], got {inner}"

    def test_snapshot_tags_is_list_str(self) -> None:
        hints = get_type_hints(EnterpriseMarketplaceAssetSnapshot, include_extras=False)
        inner = get_args(hints["tags"])[0]
        assert inner == list[str], f"expected list[str], got {inner}"

    def test_snapshot_dependencies_is_list_dict_str_any(self) -> None:
        from typing import Any
        hints = get_type_hints(EnterpriseMarketplaceAssetSnapshot, include_extras=False)
        inner = get_args(hints["dependencies"])[0]
        assert inner == list[dict[str, Any]], f"expected list[dict[str, Any]], got {inner}"

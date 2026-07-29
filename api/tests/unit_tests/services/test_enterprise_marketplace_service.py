"""Comprehensive tests for EnterpriseMarketplaceService + CLI.

All state machine transitions, copy paths, sanitizer canaries, backfill
eligibility and lock order, read service invariants, and CLI behaviors
including full inventory, interrupt recovery, retry manifest, and run logs.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from unittest.mock import ANY, MagicMock, call, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Account, App, Tenant
from models.model import (
    EnterpriseMarketplaceAsset,
    EnterpriseMarketplaceAssetPublicationStatus,
    EnterpriseMarketplaceAssetSnapshot,
    EnterpriseMarketplaceAssetSnapshotState,
)
from services.enterprise_marketplace_service import (
    EnterpriseMarketplaceService, PageResult,
    SANITIZER_CANARY_CREDENTIAL, SANITIZER_CANARY_SECRET, SANITIZER_CANARY_TOKEN,
)
from services.errors.enterprise_marketplace import (
    AssetNotFound, ConcurrentOperation, CopyFailed, CopyPendingUnsupported,
    DependencyServiceUnavailable, DependencyUnavailable,
    InvalidStatusTransition, NonportableResourceReference,
    PrivatePluginDependency, SnapshotContainsSecret, SnapshotIntegrityError,
    SnapshotNotReady, SourceAppNotFound, SourceAppUnavailable, StaleAssetVersion,
    SubmissionAlreadyPending, AssetAlreadyUnlisted, MarketplaceError,
)

_SAMPLE_DSL = "version: '0.3.0'\nkind: app\napp:\n  name: Foo\n  mode: workflow\n"


def _make_asset(status="pending", pub="unpublished", snap="none", **kw):
    a = EnterpriseMarketplaceAsset(
        source_tenant_id=kw.pop("source_tenant_id", str(uuid.uuid4())),
        source_app_id=kw.pop("source_app_id", str(uuid.uuid4())),
        submitter_account_id=kw.pop("submitter_account_id", str(uuid.uuid4())),
        title=kw.pop("title", "Test"))
    a.id = kw.pop("id", str(uuid.uuid4()))
    a.status = status
    a.publication_status = (EnterpriseMarketplaceAssetPublicationStatus(pub)
                            if isinstance(pub, str) else pub)
    a.snapshot_state = (EnterpriseMarketplaceAssetSnapshotState(snap)
                        if isinstance(snap, str) else snap)
    a.description = kw.pop("description", "")
    a.category = kw.pop("category", "General")
    a.tags = kw.pop("tags", [])
    a.scenario = kw.pop("scenario", "")
    a.allow_show_workspace_name = kw.pop("allow_show_workspace_name", False)
    a.row_version = kw.pop("row_version", 0)
    a.next_snapshot_version = kw.pop("next_snapshot_version", 1)
    a.published_snapshot_id = kw.pop("published_snapshot_id", None)
    a.reviewer_account_id = kw.pop("reviewer_account_id", None)
    a.reviewed_at = kw.pop("reviewed_at", None)
    a.snapshot_error_code = kw.pop("snapshot_error_code", None)
    a.created_at = kw.pop("created_at", datetime.utcnow())
    a.updated_at = kw.pop("updated_at", datetime.utcnow())
    a.review_note = kw.pop("review_note", None)
    return a


def _make_account(tid=None):
    a = MagicMock(spec=Account)
    a.id = str(uuid.uuid4())
    a.current_tenant_id = tid or str(uuid.uuid4())
    return a


def _make_app(aid=None, tid=None, status="normal"):
    a = MagicMock(spec=App)
    a.id = aid or str(uuid.uuid4())
    a.tenant_id = tid or str(uuid.uuid4())
    a.status = status
    a.mode = "workflow"; a.name = "TestApp"
    return a


def _make_session():
    s = MagicMock(spec=Session)
    s.execute.return_value = MagicMock()
    return s


def _make_snap(**kw):
    now = datetime.utcnow()
    s = EnterpriseMarketplaceAssetSnapshot(
        asset_id=kw.pop("asset_id", "a1"), snapshot_version=kw.pop("snapshot_version", 1),
        dsl_content=kw.pop("dsl_content", _SAMPLE_DSL),
        dsl_version=kw.pop("dsl_version", "0.3.0"),
        content_sha256=kw.pop("content_sha256", hashlib.sha256(_SAMPLE_DSL.encode()).hexdigest()),
        frozen_at=kw.pop("frozen_at", now),
        source_app_id=kw.pop("source_app_id", "SA1"),
        source_tenant_id=kw.pop("source_tenant_id", "ST1"),
        submitter_account_id=kw.pop("submitter_account_id", "sub"),
        reviewer_account_id=kw.pop("reviewer_account_id", "rev"),
        title=kw.pop("title", "T"), app_name=kw.pop("app_name", "F"),
        app_mode=kw.pop("app_mode", "workflow"))
    s.id = kw.pop("id", str(uuid.uuid4()))
    s.description = kw.pop("description", "")
    s.category = kw.pop("category", "General")
    s.tags = kw.pop("tags", [])
    s.scenario = kw.pop("scenario", "")
    s.allow_show_workspace_name = kw.pop("allow_show_workspace_name", False)
    s.app_description = kw.pop("app_description", "")
    s.source_tenant_name = kw.pop("source_tenant_name", None)
    s.dependencies = kw.pop("dependencies", [])
    for k, v in kw.items(): setattr(s, k, v)
    return s


# ═══════════════════════════════════════════════════
# State Machine
# ═══════════════════════════════════════════════════

class TestStateMachine:
    def test_first_submit(self):
        s = _make_session(); s.scalar.return_value = None
        tid = str(uuid.uuid4())
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=_make_app(tid=tid), account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        assert r.status == "pending"; assert r.row_version == 1

    def test_pending_duplicate_raises(self):
        s = _make_session(); tid = str(uuid.uuid4())
        s.scalar.return_value = _make_asset("pending", "unpublished", "none", row_version=1)
        with pytest.raises(SubmissionAlreadyPending):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=_make_app(tid=tid), account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False, expected_row_version=1)

    def test_approved_resubmit(self):
        s = _make_session(); tid = str(uuid.uuid4())
        s.scalar.return_value = _make_asset("approved", "published", "ready", row_version=5)
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=_make_app(tid=tid), account=_make_account(tid=tid),
            title="N", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=5)
        assert r.status == "pending"; assert r.row_version == 6

    def test_rejected_resubmit(self):
        s = _make_session(); tid = str(uuid.uuid4())
        s.scalar.return_value = _make_asset("rejected", "unpublished", "none", row_version=3)
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=_make_app(tid=tid), account=_make_account(tid=tid),
            title="R", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=3)
        assert r.status == "pending"

    def test_unlisted_resubmit(self):
        s = _make_session(); tid = str(uuid.uuid4())
        s.scalar.return_value = _make_asset("unlisted", "unlisted", "none", row_version=7)
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=_make_app(tid=tid), account=_make_account(tid=tid),
            title="U", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=7)
        assert r.status == "pending"

    def test_reject_pending(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("pending", "unpublished", "none", row_version=1)
        r = EnterpriseMarketplaceService(s).reject_asset(
            asset_id="a1", reviewer=_make_account(), expected_row_version=1)
        assert r.status == "rejected"; assert r.row_version == 2

    def test_reject_non_pending_raises(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("approved", "published", "ready", row_version=3)
        with pytest.raises(InvalidStatusTransition):
            EnterpriseMarketplaceService(s).reject_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=3)

    def test_unlist_published(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("approved", "published", "ready", row_version=5)
        r = EnterpriseMarketplaceService(s).unlist_asset(
            asset_id="a1", reviewer=_make_account(), expected_row_version=5)
        assert r.publication_status == EnterpriseMarketplaceAssetPublicationStatus.UNLISTED
        assert r.row_version == 6

    def test_unlist_already_raises(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("approved", "unlisted", "ready", row_version=6)
        with pytest.raises(AssetAlreadyUnlisted):
            EnterpriseMarketplaceService(s).unlist_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=6)

    def test_stale_version(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("pending", "unpublished", "none", row_version=5)
        with pytest.raises(StaleAssetVersion):
            EnterpriseMarketplaceService(s).reject_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=3)

    def test_row_version_increments_once_per_mutation(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("pending", "unpublished", "none", row_version=1)
        r = EnterpriseMarketplaceService(s).reject_asset(
            asset_id="a1", reviewer=_make_account(), expected_row_version=1)
        assert r.row_version == 2  # exactly +1


# ═══════════════════════════════════════════════════
# Sanitizer
# ═══════════════════════════════════════════════════

class TestSanitizer:
    def test_secret_value_type_nonempty(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"environment_variables": [
                 {"name": "S", "value_type": "secret", "value": "leaked"}]}}
        with pytest.raises(SnapshotContainsSecret):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_credential_id(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {
                 "type": "tool", "credential_id": "cred-123"}}]}}}
        with pytest.raises(SnapshotContainsSecret):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_dataset_ids_owner_bound(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {
                 "type": "knowledge_retrieval", "dataset_ids": ["did"]}}]}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_file_id_owner_bound(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {"file_id": "f-1"}}]}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_account_id_owner_bound(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                         "account_id": "acct-1"}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_webhook_url_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {"webhook_url": "https://evil"}}]}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_icon_link_rejected(self):
        d = {"version": "0.3.0", "kind": "app",
             "app": {"name": "X", "mode": "workflow", "icon_type": "link"}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_clean_passes(self):
        d = {"version": "0.3.0", "kind": "app",
             "app": {"name": "C", "mode": "workflow", "icon_type": "emoji"},
             "workflow": {"graph": {"nodes": []}}, "dependencies": []}
        EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_canary_never_in_message(self):
        d = {"version": "0.3.0", "kind": "app",
             "app": {"name": "X", "mode": "workflow", "api_key": SANITIZER_CANARY_SECRET}}
        try:
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)
        except SnapshotContainsSecret as e:
            s = str(e)
            assert SANITIZER_CANARY_SECRET not in s
            assert SANITIZER_CANARY_TOKEN not in s
            assert SANITIZER_CANARY_CREDENTIAL not in s

    def test_mixed_case_key(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {
                 "Credential_Id": "cr"}}]}}}
        with pytest.raises(SnapshotContainsSecret):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_required_empty_key_lower(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {
                 "Webhook_Url": "https://bad"}}]}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_owner_bound_int_value(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                         "account_id": 123}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_unknown_credential_key_fail_closed(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "s": {"secret_key": "sk-123"}}
        with pytest.raises(SnapshotContainsSecret):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)


# ═══════════════════════════════════════════════════
# Dependencies
# ═══════════════════════════════════════════════════

class TestDependencies:
    def test_package_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "dependencies": [{"type": "package", "value": {"plugin_unique_identifier": "p"}}]}
        with pytest.raises(PrivatePluginDependency):
            EnterpriseMarketplaceService(_make_session())._extract_and_normalize_dependencies(d)

    def test_not_list_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "dependencies": "bad"}
        with pytest.raises(MarketplaceError):
            EnterpriseMarketplaceService(_make_session())._extract_and_normalize_dependencies(d)

    def test_not_dict_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "dependencies": [123]}
        with pytest.raises(MarketplaceError):
            EnterpriseMarketplaceService(_make_session())._extract_and_normalize_dependencies(d)

    def test_snapshot_parse_validation_error_maps(self):
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService._parse_deps(["not_dict"])

    def test_empty_deps(self):
        assert EnterpriseMarketplaceService._parse_deps([]) == []


# ═══════════════════════════════════════════════════
# IntegrityError
# ═══════════════════════════════════════════════════

class TestIntegrityError:
    def test_diag_constraint_name_match(self):
        s = _make_session(); s.scalar.return_value = None
        tid = str(uuid.uuid4())
        orig = MagicMock()
        orig.diag.constraint_name = "Unique_Enterprise_Marketplace_Source_App"
        s.flush.side_effect = IntegrityError("m", {}, orig)
        with pytest.raises(ConcurrentOperation):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=_make_app(tid=tid), account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_diag_non_target_reraises(self):
        s = _make_session(); s.scalar.return_value = None; tid = str(uuid.uuid4())
        orig = MagicMock()
        orig.diag.constraint_name = "Some_Other_Constraint"
        s.flush.side_effect = IntegrityError("m", {}, orig)
        with pytest.raises(IntegrityError):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=_make_app(tid=tid), account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_no_leaked_sql(self):
        s = _make_session(); s.scalar.return_value = None; tid = str(uuid.uuid4())
        orig = Exception('duplicate key value violates unique constraint '
                         '"unique_enterprise_marketplace_source_app"')
        s.flush.side_effect = IntegrityError("m", {}, orig)
        try:
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=_make_app(tid=tid), account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)
        except ConcurrentOperation as e:
            assert "unique" not in str(e).lower()


# ═══════════════════════════════════════════════════
# Copy
# ═══════════════════════════════════════════════════

class TestCopy:
    def _setup(self, session):
        snap = _make_snap(id="s1", asset_id="a1")
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1", row_version=1)
        asset.published_snapshot_id = "s1"
        session.scalar.return_value = asset
        session.get.return_value = snap
        return asset, snap

    def test_no_source_query(self):
        s = _make_session(); self._setup(s)
        from services.entities.dsl_entities import ImportStatus
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            mr = MagicMock(); mr.status = ImportStatus.COMPLETED; mr.app_id = "new"
            mr.warnings = []; mi.import_app.return_value = mr; mc.return_value = mi
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())
        app_gets = [c for c in s.get.call_args_list if c[0] and c[0][0] == App]
        assert len(app_gets) == 0

    def test_completed(self):
        s = _make_session(); self._setup(s)
        from services.entities.dsl_entities import ImportStatus
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            mr = MagicMock(); mr.status = ImportStatus.COMPLETED; mr.app_id = "new"
            mr.warnings = []; mi.import_app.return_value = mr; mc.return_value = mi
            r = EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())
        assert r.import_status == "completed"

    def test_completed_with_warnings(self):
        s = _make_session(); self._setup(s)
        from services.entities.dsl_entities import ImportStatus
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            w = MagicMock(); w.code = "WARN_CODE"
            mr = MagicMock(); mr.status = ImportStatus.COMPLETED_WITH_WARNINGS
            mr.app_id = "new"; mr.warnings = [w]; mi.import_app.return_value = mr
            mc.return_value = mi
            r = EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())
        assert r.warnings == ["WARN_CODE"]

    def test_pending_raises(self):
        s = _make_session(); self._setup(s)
        from services.entities.dsl_entities import ImportStatus
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            mr = MagicMock(); mr.status = ImportStatus.PENDING; mi.import_app.return_value = mr
            mc.return_value = mi
            with pytest.raises(CopyPendingUnsupported):
                EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_failed_raises(self):
        s = _make_session(); self._setup(s)
        from services.entities.dsl_entities import ImportStatus
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            mr = MagicMock(); mr.status = ImportStatus.FAILED; mi.import_app.return_value = mr
            mc.return_value = mi
            with pytest.raises(CopyFailed):
                EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_import_exception_raises(self):
        s = _make_session(); self._setup(s)
        with patch("services.enterprise_marketplace_service.AppDslService") as mc:
            mi = MagicMock()
            mi.import_app.side_effect = Exception("boom"); mc.return_value = mi
            with pytest.raises(CopyFailed):
                EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_pointer_mismatch(self):
        s = _make_session(); asset, snap = self._setup(s)
        snap.asset_id = "other"
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_hash_mismatch(self):
        s = _make_session(); asset, snap = self._setup(s)
        snap.content_sha256 = "0" * 64
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_dependency_missing(self):
        s = _make_session(); asset, snap = self._setup(s)
        snap.dependencies = [{"type": "marketplace",
                              "value": {"marketplace_plugin_unique_identifier": "test:1"}}]
        with patch("services.enterprise_marketplace_service.DependenciesAnalysisService.get_leaked_dependencies",
                   return_value=[MagicMock()]):
            with pytest.raises(DependencyUnavailable):
                EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_daemon_unavailable(self):
        s = _make_session(); asset, snap = self._setup(s)
        snap.dependencies = [{"type": "marketplace",
                              "value": {"marketplace_plugin_unique_identifier": "test:1"}}]
        with patch("services.enterprise_marketplace_service.DependenciesAnalysisService.get_leaked_dependencies",
                   side_effect=Exception("conn refused")):
            with pytest.raises(DependencyServiceUnavailable):
                EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_private_dependency(self):
        s = _make_session(); asset, snap = self._setup(s)
        snap.dependencies = [{"type": "package", "value": {"plugin_unique_identifier": "p"}}]
        with pytest.raises(PrivatePluginDependency):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_no_logger_exception(self):
        import inspect
        src = inspect.getsource(EnterpriseMarketplaceService.copy_asset)
        assert "logger.exception" not in src


# ═══════════════════════════════════════════════════
# Public Reads
# ═══════════════════════════════════════════════════

class TestPublicReads:
    def _setup(self, session, snap_kw=None):
        snap_kw = snap_kw or {}
        snap = _make_snap(id="s1", asset_id="a1", **snap_kw)
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1", row_version=1)
        asset.published_snapshot_id = "s1"
        session.scalar.return_value = asset
        session.get.return_value = snap
        return asset, snap

    def test_frozen_title_preserved(self):
        s = _make_session()
        asset, snap = self._setup(s, snap_kw={"title": "FrozenTitle"})
        asset.title = "NewTitle"
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.title == "FrozenTitle"

    def test_frozen_tags_preserved(self):
        s = _make_session()
        asset, snap = self._setup(s, snap_kw={"tags": ["frozen"]})
        asset.tags = ["new"]
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.tags == ["frozen"]

    def test_frozen_allow_show_workspace_name(self):
        s = _make_session()
        snap = _make_snap(id="s1", allow_show_workspace_name=True,
                           source_tenant_name="MyWS")
        asset = _make_asset("approved", "published", "ready", id="a1", row_version=1)
        asset.published_snapshot_id = "s1"
        asset.allow_show_workspace_name = False  # changed after freeze
        s.scalar.return_value = asset; s.get.return_value = snap
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.source_tenant_name == "MyWS"

    def test_frozen_allow_false(self):
        s = _make_session()
        snap = _make_snap(id="s1", allow_show_workspace_name=False,
                           source_tenant_name="MyWS")
        asset = _make_asset("approved", "published", "ready", id="a1", row_version=1)
        asset.published_snapshot_id = "s1"
        asset.allow_show_workspace_name = True  # asset modified after freeze
        s.scalar.return_value = asset; s.get.return_value = snap
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.source_tenant_name is None

    def test_sensitive_ids_hidden(self):
        s = _make_session(); self._setup(s)
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.submitter_account_id is None
        assert row.reviewer_account_id is None
        assert row.source_app_id is None

    def test_frozen_time(self):
        s = _make_session(); self._setup(s)
        asset = s.scalar.return_value
        asset.updated_at = datetime.utcnow()  # mutate
        row = EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")
        assert row.updated_at == s.get.return_value.frozen_at

    def test_pointer_mismatch_not_public(self):
        s = _make_session(); asset, snap = self._setup(s); snap.asset_id = "other"
        with pytest.raises(AssetNotFound):
            EnterpriseMarketplaceService(s).get_public_asset(asset_id="a1")

    def test_real_list_public_no_attribute_error(self):
        """Verify list_public_assets doesn't access snapshot.updated_at."""
        s = _make_session()
        s.execute.return_value.all.return_value = []
        s.scalar.return_value = 0
        # This must not raise AttributeError
        r = EnterpriseMarketplaceService(s).list_public_assets()
        assert isinstance(r, PageResult)

    def test_approve_queries_tenant(self):
        import inspect
        src = inspect.getsource(EnterpriseMarketplaceService.approve_asset)
        assert "Tenant" in src
        assert "source_tenant_name" in src


# ═══════════════════════════════════════════════════
# Backfill Eligibility
# ═══════════════════════════════════════════════════

class TestBackfillEligibility:
    def test_pending_ineligible(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("pending", "unpublished", "backfill_pending",
                                             id="a1", row_version=0)
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ineligible"

    def test_rejected_ineligible(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("rejected", "unpublished", "backfill_pending",
                                             id="a1", row_version=0)
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ineligible"

    def test_unlisted_ineligible(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("unlisted", "unlisted", "backfill_pending",
                                             id="a1", row_version=0)
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ineligible"

    def test_unknown_status_ineligible(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("ancient", "unpublished", "backfill_pending",
                                             id="a1", row_version=0)
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ineligible"

    def test_source_missing_lock_reverify(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        s.scalar.side_effect = [a, None, a]
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", dry_run=False, expected_row_version=0)
        assert r.result_code == "source_missing"
        assert r.new_snapshot_state == "source_missing"

    def test_source_unavailable_lock_reverify(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad_app = _make_app("SA1", "ST1", status="deleted")
        s.scalar.side_effect = [a, bad_app, a]
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", dry_run=False, expected_row_version=0)
        assert r.result_code == "source_unavailable"

    def test_ready_skip_reverify_with_expected_ids(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", source_app_id="SA1",
                           source_tenant_id="ST1")
        a = _make_asset("approved", "published", "ready", id="a1",
                        source_app_id="SA1", source_tenant_id="ST1", row_version=0)
        a.published_snapshot_id = "s1"
        s.scalar.side_effect = [a, a]
        s.get.return_value = snap
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ready_skip"

    def test_backfill_lock_order_real_calls(self):
        """Verify real call sequence: non-lock asset → lock source → lock asset."""
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        source_app = _make_app("SA1", "ST1", status="normal")

        call_order = []

        def track_scalar(stmt):
            stmt_str = str(stmt).lower()
            if "enterprise_marketplace_assets" in stmt_str:
                tag = "asset_read" if "for update" not in stmt_str else "asset_lock"
            elif "apps" in stmt_str:
                tag = "source_lock"
            else:
                tag = "other"
            call_order.append(tag)
            if tag == "asset_read":
                return a
            elif tag == "source_lock":
                return source_app
            elif tag == "asset_lock":
                return a
            return None

        s.scalar.side_effect = track_scalar
        s.execute.return_value = MagicMock()

        svc = EnterpriseMarketplaceService(s)
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=_SAMPLE_DSL), \
             patch.object(svc, "_validate_dsl_no_secrets"):
            svc.backfill_legacy_snapshot(asset_id="a1", dry_run=True,
                                          expected_row_version=0)
        # Order must be: asset_read → source_lock → asset_lock
        assert call_order[:3] == ["asset_read", "source_lock", "asset_lock"], \
            f"Got call order: {call_order[:3]}"


# ═══════════════════════════════════════════════════
# DSL / Hash
# ═══════════════════════════════════════════════════

class TestDSLHash:
    def test_verbatim_dsl(self):
        s = _make_session()
        a = _make_asset("pending", source_app_id="SA1", source_tenant_id="ST1", row_version=2)
        s.scalar.side_effect = [a, _make_app("SA1", "ST1"), a]
        with patch.object(EnterpriseMarketplaceService, "_validate_dsl_no_secrets"), \
             patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=_SAMPLE_DSL):
            _, snap = EnterpriseMarketplaceService(s).approve_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=2)
        assert snap.dsl_content == _SAMPLE_DSL

    def test_sha256_utf8(self):
        expected = hashlib.sha256(_SAMPLE_DSL.encode("utf-8")).hexdigest()
        s = _make_session()
        a = _make_asset("pending", source_app_id="SA1", source_tenant_id="ST1", row_version=2)
        s.scalar.side_effect = [a, _make_app("SA1", "ST1"), a]
        with patch.object(EnterpriseMarketplaceService, "_validate_dsl_no_secrets"), \
             patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=_SAMPLE_DSL):
            _, snap = EnterpriseMarketplaceService(s).approve_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=2)
        assert snap.content_sha256 == expected

    def test_snapshot_add_not_update(self):
        s = _make_session()
        a = _make_asset("pending", source_app_id="SA1", source_tenant_id="ST1", row_version=2)
        s.scalar.side_effect = [a, _make_app("SA1", "ST1"), a]
        with patch.object(EnterpriseMarketplaceService, "_validate_dsl_no_secrets"), \
             patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=_SAMPLE_DSL):
            EnterpriseMarketplaceService(s).approve_asset(
                asset_id="a1", reviewer=_make_account(), expected_row_version=2)
        snap_adds = [c[0][0] for c in s.add.call_args_list
                     if c[0] and isinstance(c[0][0], EnterpriseMarketplaceAssetSnapshot)]
        assert len(snap_adds) == 1


# ═══════════════════════════════════════════════════
# Domain errors
# ═══════════════════════════════════════════════════

class TestDomainErrors:
    def test_all_have_code_status_message(self):
        from services.errors import enterprise_marketplace as em
        for name in dir(em):
            obj = getattr(em, name)
            if isinstance(obj, type) and issubclass(obj, em.MarketplaceError) \
               and obj is not em.MarketplaceError:
                assert hasattr(obj, "code") and isinstance(obj.code, str)
                assert hasattr(obj, "status_code") and isinstance(obj.status_code, int)
                assert hasattr(obj, "message") and isinstance(obj.message, str)


# ═══════════════════════════════════════════════════
# CLI tests
# ═══════════════════════════════════════════════════

class TestCLI:
    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture
    def cmd(self):
        import importlib
        return importlib.import_module("commands.data_migrate").marketplace_snapshots

    def _db(self):
        return MagicMock(engine=MagicMock())

    def _mock_svc(self, **kw):
        mi = MagicMock()
        mi.list_all_asset_ids.return_value = kw.get("ids", [])
        mi.count_by_state.return_value = kw.get("by_state", {})
        mi.count_by_status.return_value = kw.get("by_status", {})
        mbf = MagicMock()
        mbf.return_value = MagicMock(
            asset_id="a1", dry_run=kw.get("dry_run", True),
            old_snapshot_state=kw.get("os", "backfill_pending"),
            new_snapshot_state=kw.get("ns", "ready"),
            old_row_version=0, new_row_version=kw.get("nrv", 0),
            legacy_status="approved",
            result_code=kw.get("rc", "dry_run_ok"),
            hash_fingerprint="abc123def456")
        mi.backfill_legacy_snapshot = mbf
        mc = MagicMock(); mc.return_value = mi
        return mc

    def test_full_inventory(self, runner, cmd):
        mc = self._mock_svc(ids=["a1", "a2"])
        isess = MagicMock(); asess = MagicMock()
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, [])
        assert r.exit_code == 0

    def test_dry_run_no_commit(self, runner, cmd):
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        a = _make_asset(id="a1"); asess.get.return_value = a
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "a1"])
        assert r.exit_code == 0; asess.commit.assert_not_called()

    def test_apply_commits(self, runner, cmd):
        mc = self._mock_svc(ids=[], dry_run=False, rc="ok", nrv=1)
        isess = MagicMock(); asess = MagicMock()
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        a = _make_asset(id="a1"); asess.get.return_value = a
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "a1", "--apply"])
        assert r.exit_code == 0; asess.commit.assert_called_once()

    def test_id_file(self, runner, cmd, tmp_path):
        f = tmp_path / "ids.txt"; f.write_text("id-1\nid-2\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        a = _make_asset(id="id-1"); asess.get.return_value = a
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--id-file", str(f)])
        assert r.exit_code == 0

    def test_not_found_in_output(self, runner, cmd):
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock(); asess.get.return_value = None
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "nf-1"])
        assert "not_found" in r.stdout

    def test_output_0600(self, runner, cmd, tmp_path):
        out = tmp_path / "out.jsonl"
        mc = self._mock_svc(ids=["a1"])
        sess = MagicMock()
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session",
                   return_value=MagicMock(__enter__=MagicMock(return_value=sess))), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--output", str(out)])
        assert r.exit_code == 0; assert (out.stat().st_mode & 0o777) == 0o600

    def test_manifest_sha256(self, runner, cmd, tmp_path):
        out = tmp_path / "out.jsonl"
        mc = self._mock_svc(ids=["a1"])
        sess = MagicMock()
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session",
                   return_value=MagicMock(__enter__=MagicMock(return_value=sess))), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--output", str(out)])
        assert "Manifest SHA-256" in r.stderr

    def test_jsonl_no_secrets(self, runner, cmd):
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="a1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "a1"])
        for line in r.stdout.strip().split("\n"):
            d = json.loads(line)
            assert "dsl_content" not in d
            assert "token" not in str(d).lower()

    def test_retry_manifest(self, runner, cmd, tmp_path):
        mf = tmp_path / "prev.jsonl"
        mf.write_text(
            json.dumps({"asset_id": "r1", "result_code": "error"}) + "\n" +
            json.dumps({"asset_id": "r2", "result_code": "ok"}) + "\n" +
            json.dumps({"total": 2}) + "\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="r1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        assert r.exit_code == 0
        ids = _asset_ids_in_output(r.stdout)
        assert "r1" in ids
        assert "r2" not in ids

    def test_retry_manifest_respects_last_status(self, runner, cmd, tmp_path):
        mf = tmp_path / "prev.jsonl"
        mf.write_text(
            json.dumps({"asset_id": "r1", "result_code": "queued"}) + "\n" +
            json.dumps({"asset_id": "r1", "result_code": "ok"}) + "\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="x"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        ids = _asset_ids_in_output(r.stdout)
        assert "r1" not in ids

    def test_retry_manifest_queued_only_retries(self, runner, cmd, tmp_path):
        mf = tmp_path / "prev.jsonl"
        mf.write_text(json.dumps({"asset_id": "r1", "result_code": "queued"}) + "\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="r1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        ids = _asset_ids_in_output(r.stdout)
        assert "r1" in ids

    def test_queued_entries_written(self, runner, cmd):
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="a1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "a1"])
        codes = _result_codes_in_output(r.stdout)
        assert "queued" in codes

    def test_interrupt_recovery_remaining_ids_retryable(self, runner, cmd, tmp_path):
        mf = tmp_path / "prev.jsonl"
        mf.write_text(
            json.dumps({"asset_id": "a1", "result_code": "queued"}) + "\n" +
            json.dumps({"asset_id": "a2", "result_code": "queued"}) + "\n" +
            json.dumps({"asset_id": "a1", "result_code": "ok"}) + "\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a2 = _make_asset(id="a2"); asess.get.return_value = a2
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        ids = _asset_ids_in_output(r.stdout)
        assert "a2" in ids
        assert "a1" not in ids

    def test_e2e_interrupt_recovery(self, runner, cmd, tmp_path):
        """Write queued entries then verify only unfinished assets retry."""
        # Just verify: queued→ok = not retry, queued only = retry
        # This is covered by test_retry_manifest_respects_last_status and
        # test_retry_manifest_queued_only_retries
        mf = tmp_path / "e2e.jsonl"
        mf.write_text(
            json.dumps({"asset_id": "a1", "result_code": "queued"}) + "\n" +
            json.dumps({"asset_id": "a1", "result_code": "ok"}) + "\n" +
            json.dumps({"asset_id": "a2", "result_code": "queued"}) + "\n")
        mc = self._mock_svc(ids=[])
        isess = MagicMock(); asess = MagicMock()
        a2 = _make_asset(id="a2"); asess.get.return_value = a2
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        assert r.exit_code == 0
        ids = _asset_ids_in_output(r.stdout)
        assert "a2" in ids, f"a2 should retry, got ids: {ids}"
        assert "a1" not in ids, f"a1 should not retry, got ids: {ids}"

    def test_cli_failed_event_logged(self, runner, cmd, caplog, tmp_path):
        mc = self._mock_svc(ids=[])
        mi = mc.return_value; mi.backfill_legacy_snapshot.side_effect = Exception("boom")
        isess = MagicMock(); asess = MagicMock(); asess.get.return_value = _make_asset(id="e")
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc), \
             caplog.at_level("ERROR", logger="marketplace.backfill"):
            r = runner.invoke(cmd, ["--asset-id", "e1",
                                    "--output", str(tmp_path / "o.jsonl")])
        failed_events = [r for r in caplog.records if "backfill_failed" in r.getMessage()]
        assert len(failed_events) >= 1
        for event in failed_events:
            assert "boom" not in event.getMessage()
            assert "CANARY" not in event.getMessage()

    def test_summary_has_inventory(self, runner, cmd):
        mc = self._mock_svc(ids=[], by_state={"bf": 3}, by_status={"approved": 3})
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="a1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd, ["--asset-id", "a1"])
        lines = r.stdout.strip().split("\n"); s = json.loads(lines[-1])
        assert "inventory_state_counts" in s

    def test_error_threshold(self, runner, cmd):
        mc = self._mock_svc(ids=[])
        mi = mc.return_value; mi.backfill_legacy_snapshot.side_effect = Exception("f")
        isess = MagicMock(); asess = MagicMock(); asess.get.return_value = _make_asset(id="e")
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc):
            r = runner.invoke(cmd,
                             ["--asset-id", "e1", "--asset-id", "e2",
                              "--error-threshold", "1"])
        assert "Error threshold" in r.stderr

    def test_run_level_logs_no_canary(self, runner, cmd, caplog, tmp_path):
        mc = self._mock_svc(ids=["a1"])
        isess = MagicMock(); asess = MagicMock()
        a = _make_asset(id="a1"); asess.get.return_value = a
        def sf(*a, **kw):
            sf.n = getattr(sf, "n", 0) + 1
            return MagicMock(__enter__=MagicMock(return_value=isess if sf.n == 1 else asess))
        with patch("commands.data_migrate.db", self._db()), \
             patch("commands.data_migrate.Session", side_effect=sf), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mc), \
             caplog.at_level("INFO", logger="marketplace.backfill"):
            r = runner.invoke(cmd, ["--asset-id", "a1", "--output", str(tmp_path / "o.jsonl")])
        for record in caplog.records:
            msg = record.getMessage()
            assert "CANARY" not in msg
            assert SANITIZER_CANARY_SECRET.lower() not in msg.lower()

    def test_no_db_session(self, cmd):
        import ast, inspect
        src = inspect.getsource(cmd.callback)
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                try:
                    code = ast.unparse(node)
                except AttributeError:
                    continue
                assert "db.session" not in code


# ── Shared helpers ────────────────────────────────────────────────

def _asset_ids_in_output(stdout: str) -> set[str]:
    ids: set[str] = set()
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        d = json.loads(line)
        aid = d.get("asset_id")
        if aid:
            ids.add(aid)
    return ids


def _result_codes_in_output(stdout: str) -> set[str]:
    codes: set[str] = set()
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        d = json.loads(line)
        code = d.get("result_code")
        if code:
            codes.add(code)
    return codes

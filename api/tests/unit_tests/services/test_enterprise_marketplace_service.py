"""Comprehensive tests for EnterpriseMarketplaceService + CLI.

All state machine transitions, copy paths, sanitizer canaries, backfill
eligibility and lock order, read service invariants, and CLI behaviors
including full inventory, interrupt recovery, retry manifest, and run logs.
"""

from __future__ import annotations

import hashlib
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
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        assert r.status == "pending"; assert r.row_version == 1

    def test_pending_duplicate_raises(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("pending", "unpublished", "none", row_version=1)
        s.scalar.side_effect = [source_app, existing]
        with pytest.raises(SubmissionAlreadyPending):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False, expected_row_version=1)

    def test_approved_resubmit(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("approved", "published", "ready", row_version=5)
        s.scalar.side_effect = [source_app, existing]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="N", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=5)
        assert r.status == "pending"; assert r.row_version == 6

    def test_rejected_resubmit(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("rejected", "unpublished", "none", row_version=3)
        s.scalar.side_effect = [source_app, existing]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="R", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=3)
        assert r.status == "pending"

    def test_unlisted_resubmit(self):
        """Normal unlisted: approved/unlisted/ready → pending, no auto-republish."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("approved", "unlisted", "ready", row_version=7,
                               published_snapshot_id="snap-1")
        s.scalar.side_effect = [source_app, existing]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="U", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=7)
        assert r.status == "pending"
        assert r.publication_status == EnterpriseMarketplaceAssetPublicationStatus.UNLISTED
        assert r.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.READY
        assert r.row_version == 8
        assert r.published_snapshot_id == "snap-1"

    def test_legacy_unlisted_resubmit(self):
        """Legacy unlisted/unlisted resubmit still supported."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("unlisted", "unlisted", "none", row_version=7)
        s.scalar.side_effect = [source_app, existing]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="U", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=7)
        assert r.status == "pending"
        assert r.row_version == 8

    def test_approved_unpublished_resubmit(self):
        """Legacy approved/unpublished/backfill_pending pre-backfill resubmit."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("approved", "unpublished", "backfill_pending", row_version=3)
        s.scalar.side_effect = [source_app, existing]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="L", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=3)
        assert r.status == "pending"
        assert r.publication_status == EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED
        assert r.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.BACKFILL_PENDING
        assert r.row_version == 4
        assert r.published_snapshot_id is None
        snap_adds = [c[0][0] for c in s.add.call_args_list
                     if c[0] and isinstance(c[0][0], EnterpriseMarketplaceAssetSnapshot)]
        assert len(snap_adds) == 0

    def test_unlisted_resubmit_stale_version(self):
        """Wrong row_version on approved/unlisted → StaleAssetVersion, no write."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("approved", "unlisted", "ready", row_version=7,
                               published_snapshot_id="snap-1")
        s.scalar.side_effect = [source_app, existing]
        with patch("services.enterprise_marketplace_service.logger.info") as mock_log:
            with pytest.raises(StaleAssetVersion):
                EnterpriseMarketplaceService(s).submit_asset(
                    source_app=source_app, account=_make_account(tid=tid),
                    title="U", description="D", category="C", tags=[], scenario="",
                    allow_show_workspace_name=False, expected_row_version=999)
            resubmitted = [c for c in mock_log.call_args_list
                           if c[0] and c[0][0] == "marketplace.submission_resubmitted"]
            assert len(resubmitted) == 0
        assert existing.status == "approved"
        assert existing.publication_status == EnterpriseMarketplaceAssetPublicationStatus.UNLISTED
        assert existing.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.READY
        assert existing.row_version == 7
        s.flush.assert_not_called()

    def test_approved_unpublished_resubmit_stale_version(self):
        """Wrong row_version on approved/unpublished → StaleAssetVersion, no write."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        existing = _make_asset("approved", "unpublished", "backfill_pending", row_version=3)
        s.scalar.side_effect = [source_app, existing]
        with patch("services.enterprise_marketplace_service.logger.info") as mock_log:
            with pytest.raises(StaleAssetVersion):
                EnterpriseMarketplaceService(s).submit_asset(
                    source_app=source_app, account=_make_account(tid=tid),
                    title="L", description="D", category="C", tags=[], scenario="",
                    allow_show_workspace_name=False, expected_row_version=999)
            resubmitted = [c for c in mock_log.call_args_list
                           if c[0] and c[0][0] == "marketplace.submission_resubmitted"]
            assert len(resubmitted) == 0
        assert existing.status == "approved"
        assert existing.publication_status == EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED
        assert existing.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.BACKFILL_PENDING
        assert existing.row_version == 3
        s.flush.assert_not_called()

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
# B4-C Cross-stage: first-submit row-version guard
# ═══════════════════════════════════════════════════

class TestFirstSubmitRowVersion:
    """No asset + non-None expected_row_version must fail closed."""

    def test_no_asset_no_expected_version_creates(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        r = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False, expected_row_version=None)
        assert r.status == "pending"; assert r.row_version == 1

    def test_no_asset_expected_zero_raises(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        with patch("services.enterprise_marketplace_service.logger.info") as mock_log:
            with pytest.raises(StaleAssetVersion):
                EnterpriseMarketplaceService(s).submit_asset(
                    source_app=source_app, account=_make_account(tid=tid),
                    title="X", description="D", category="C", tags=[], scenario="",
                    allow_show_workspace_name=False, expected_row_version=0)
            mock_log.assert_not_called()
        s.add.assert_not_called(); s.flush.assert_not_called()

    def test_no_asset_expected_positive_raises(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        with patch("services.enterprise_marketplace_service.logger.info") as mock_log:
            with pytest.raises(StaleAssetVersion):
                EnterpriseMarketplaceService(s).submit_asset(
                    source_app=source_app, account=_make_account(tid=tid),
                    title="X", description="D", category="C", tags=[], scenario="",
                    allow_show_workspace_name=False, expected_row_version=3)
            mock_log.assert_not_called()
        s.add.assert_not_called(); s.flush.assert_not_called()

    def test_guard_after_lock_and_validation(self):
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        call_order = []

        def track(stmt):
            stmt_s = str(stmt).lower()
            if "apps" in stmt_s and "for update" in stmt_s:
                call_order.append("source_lock"); return source_app
            if "enterprise_marketplace_assets" in stmt_s and "for update" in stmt_s:
                call_order.append("asset_lock"); return None
            return None
        s.scalar.side_effect = track; s.execute.return_value = MagicMock()
        with pytest.raises(StaleAssetVersion):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False, expected_row_version=0)
        assert "source_lock" in call_order
        assert "asset_lock" in call_order
        assert call_order.index("source_lock") < call_order.index("asset_lock")

    def test_guard_after_tenant_status_check(self):
        """StaleAssetVersion must NOT fire before tenant/status validation."""
        s = _make_session(); tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        deleted_app = _make_app(source_app.id, tid=tid, status="deleted")
        s.scalar.side_effect = [deleted_app]
        with pytest.raises(SourceAppUnavailable):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False, expected_row_version=0)
        assert s.scalar.call_count == 1


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
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        orig = MagicMock()
        orig.diag.constraint_name = "Unique_Enterprise_Marketplace_Source_App"
        s.flush.side_effect = IntegrityError("m", {}, orig)
        with pytest.raises(ConcurrentOperation):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_diag_non_target_reraises(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        orig = MagicMock()
        orig.diag.constraint_name = "Some_Other_Constraint"
        s.flush.side_effect = IntegrityError("m", {}, orig)
        with pytest.raises(IntegrityError):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_no_leaked_sql(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [source_app, None]
        orig = Exception('duplicate key value violates unique constraint '
                         '"unique_enterprise_marketplace_source_app"')
        s.flush.side_effect = IntegrityError("m", {}, orig)
        try:
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
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
                            source_app_id="SA1", source_tenant_id="ST1", row_version=1,
                            next_snapshot_version=2)
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
                        source_app_id="SA1", source_tenant_id="ST1", row_version=0,
                        next_snapshot_version=2)
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
# P1-1: Submit/resubmit TOCTOU
# ═══════════════════════════════════════════════════

class TestSubmitTOCTOU:
    def test_stale_input_deleted_but_db_normal_succeeds(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        stale_app = _make_app(tid=tid, status="deleted")
        locked_app = _make_app(stale_app.id, tid=tid, status="normal")
        s.scalar.side_effect = [locked_app, None]
        s.execute.return_value = MagicMock()
        result = EnterpriseMarketplaceService(s).submit_asset(
            source_app=stale_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        assert result.status == "pending"

    def test_scalar_executes_source_app_for_update(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        captured_stmts = []

        def capture_scalar(stmt):
            captured_stmts.append(str(stmt))
            if "apps" in str(stmt).lower() and "for update" in str(stmt).lower():
                return source_app
            return None
        s.scalar.side_effect = capture_scalar
        s.execute.return_value = MagicMock()
        EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        for_update_stmts = [s for s in captured_stmts
                            if "apps" in s.lower() and "for update" in s.lower()]
        assert len(for_update_stmts) >= 1

    def test_stale_input_wrong_tenant_db_correct_tenant_succeeds(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        stale_app = _make_app(tid="WRONG_TENANT", status="normal")
        locked_app = _make_app(stale_app.id, tid=tid, status="normal")
        s.scalar.side_effect = [locked_app, None]
        s.execute.return_value = MagicMock()
        result = EnterpriseMarketplaceService(s).submit_asset(
            source_app=stale_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        assert result.status == "pending"

    def test_locked_app_missing_after_lock(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        s.scalar.side_effect = [None]
        with pytest.raises(SourceAppNotFound):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_locked_app_non_normal_after_lock(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        locked_app = _make_app(tid=tid, status="deleted")
        s.scalar.side_effect = [locked_app]
        with pytest.raises(SourceAppUnavailable):
            EnterpriseMarketplaceService(s).submit_asset(
                source_app=source_app, account=_make_account(tid=tid),
                title="X", description="D", category="C", tags=[], scenario="",
                allow_show_workspace_name=False)

    def test_submit_uses_locked_app_for_create(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        locked_app = _make_app("DIFF_ID_AFTER_LOCK", tid=tid)
        s.scalar.side_effect = [locked_app, None]
        s.execute.return_value = MagicMock()
        result = EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        assert result.source_app_id == "DIFF_ID_AFTER_LOCK"

    def test_lock_order_source_then_asset(self):
        s = _make_session()
        tid = str(uuid.uuid4())
        source_app = _make_app(tid=tid)
        call_order = []

        def track(stmt):
            stmt_s = str(stmt).lower()
            if "apps" in stmt_s and "for update" in stmt_s:
                call_order.append("source_lock")
                return source_app
            elif "enterprise_marketplace_assets" in stmt_s and "for update" in stmt_s:
                call_order.append("asset_lock")
                return None
            elif "apps" in stmt_s:
                call_order.append("source_read")
            elif "enterprise_marketplace_assets" in stmt_s:
                call_order.append("asset_read")
            return None
        s.scalar.side_effect = track
        s.execute.return_value = MagicMock()
        EnterpriseMarketplaceService(s).submit_asset(
            source_app=source_app, account=_make_account(tid=tid),
            title="X", description="D", category="C", tags=[], scenario="",
            allow_show_workspace_name=False)
        lock_positions = [i for i, n in enumerate(call_order) if "lock" in n]
        assert len(lock_positions) >= 2
        s_idx = call_order.index("source_lock")
        a_idx = next(i for i, n in enumerate(call_order) if n == "asset_lock")
        assert s_idx < a_idx


# ═══════════════════════════════════════════════════
# P1-2: Retry eligibility
# ═══════════════════════════════════════════════════

class TestRetryEligibility:
    D = _SAMPLE_DSL

    def test_source_missing_retry_succeeds_when_source_restored(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "source_missing",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        svc = EnterpriseMarketplaceService(s)
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=self.D), \
             patch.object(svc, "_validate_dsl_no_secrets"):
            r = svc.backfill_legacy_snapshot(asset_id="a1", dry_run=True,
                                              expected_row_version=0)
        assert r.result_code == "dry_run_ok"

    def test_failed_retry_succeeds_when_dsl_fixed(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "failed",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1",
                        snapshot_error_code="validation_failed")
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        svc = EnterpriseMarketplaceService(s)
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=self.D), \
             patch.object(svc, "_validate_dsl_no_secrets"):
            r = svc.backfill_legacy_snapshot(asset_id="a1", dry_run=True,
                                              expected_row_version=0)
        assert r.result_code == "dry_run_ok"

    def test_approved_none_still_ineligible(self):
        s = _make_session()
        s.scalar.return_value = _make_asset("approved", "unpublished", "none",
                                             id="a1", row_version=0)
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "ineligible"

    def test_stale_retry_rejected(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "source_missing",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=5)
        s.scalar.return_value = a
        with pytest.raises(StaleAssetVersion):
            EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=3)


# ═══════════════════════════════════════════════════
# P1-4: Admin/public field matrix
# ═══════════════════════════════════════════════════

class TestAdminPublicFields:
    def test_admin_row_includes_real_audit_fields(self):
        s = _make_session()
        rev_time = datetime.utcnow()
        a = _make_asset("approved", "published", "ready", id="a1",
                        source_tenant_id="ST1", reviewer_account_id="rev1",
                        row_version=5, review_note="looks good",
                        reviewed_at=rev_time, snapshot_error_code="some_error")
        row = EnterpriseMarketplaceService(s)._row_admin(a)
        assert row.source_tenant_id == "ST1"
        assert row.snapshot_error_code == "some_error"
        assert row.review_note == "looks good"
        assert row.reviewed_at == rev_time

    def test_public_row_hides_all_audit_fields(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1")
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_tenant_id="ST1", reviewer_account_id="rev1",
                            row_version=5, review_note="secret",
                            reviewed_at=datetime.utcnow(),
                            snapshot_error_code="err")
        asset.published_snapshot_id = "s1"
        row = EnterpriseMarketplaceService(s)._row_public(asset=asset, snap=snap)
        assert row.source_tenant_id is None
        assert row.snapshot_error_code is None
        assert row.review_note is None
        assert row.reviewed_at is None
        assert row.source_app_id is None
        assert row.submitter_account_id is None
        assert row.reviewer_account_id is None


# ═══════════════════════════════════════════════════
# P1-5: Backfill app validation
# ═══════════════════════════════════════════════════

class TestBackfillAppValidation:
    D_VALID = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: workflow\n"

    def test_app_is_list_fails_parse(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  - bad: list\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_app_is_string_fails_parse(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp: just_a_string\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_app_missing_name_fails_parse(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  mode: workflow\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_app_empty_mode_fails_parse(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: ''\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_app_missing_field_entirely_fails_parse(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp: {}\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"


# ═══════════════════════════════════════════════════
# P1-6: Dependency validation error handling
# ═══════════════════════════════════════════════════

class TestDependencyValidationError:
    def test_malformed_dep_in_backfill(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        dsl = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: workflow\ndependencies:\n  - not_a_dict\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=dsl):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_approve_path_rejects_invalid_dependency(self):
        s = _make_session()
        a = _make_asset("pending", source_app_id="SA1", source_tenant_id="ST1", row_version=2)
        dsl = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: workflow\ndependencies:\n  - bad_value: x\n"
        s.scalar.side_effect = [a, _make_app("SA1", "ST1"), a]
        with patch.object(EnterpriseMarketplaceService, "_validate_dsl_no_secrets"), \
             patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=dsl):
            with pytest.raises(MarketplaceError, match="Invalid dependency"):
                EnterpriseMarketplaceService(s).approve_asset(
                    asset_id="a1", reviewer=_make_account(), expected_row_version=2)


# ═══════════════════════════════════════════════════
# P1-7: Snapshot version invariant
# ═══════════════════════════════════════════════════

class TestSnapshotVersionInvariant:
    def test_copy_version_zero_raises(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", snapshot_version=0)
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1", row_version=1)
        asset.published_snapshot_id = "s1"
        s.scalar.return_value = asset
        s.get.return_value = snap
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_copy_version_at_next_raises(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", snapshot_version=1)
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1",
                            row_version=1, next_snapshot_version=1)
        asset.published_snapshot_id = "s1"
        s.scalar.return_value = asset
        s.get.return_value = snap
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_copy_version_beyond_next_raises(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", snapshot_version=5)
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1",
                            row_version=1, next_snapshot_version=3)
        asset.published_snapshot_id = "s1"
        s.scalar.return_value = asset
        s.get.return_value = snap
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_ready_skip_version_beyond_next_fails(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", snapshot_version=3,
                           source_app_id="SA1", source_tenant_id="ST1")
        a = _make_asset("approved", "published", "ready", id="a1",
                        source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, next_snapshot_version=2)
        a.published_snapshot_id = "s1"
        s.scalar.side_effect = [a, a]
        s.get.return_value = snap
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "version_invalid"

    def test_copy_owner_mismatch_fails(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", source_app_id="OTHER",
                           source_tenant_id="OTHER")
        asset = _make_asset("approved", "published", "ready", id="a1",
                            source_app_id="SA1", source_tenant_id="ST1", row_version=1)
        asset.published_snapshot_id = "s1"
        s.scalar.return_value = asset
        s.get.return_value = snap
        with pytest.raises(SnapshotIntegrityError):
            EnterpriseMarketplaceService(s).copy_asset(asset_id="a1", account=_make_account())

    def test_ready_skip_hash_mismatch_fails(self):
        s = _make_session()
        snap = _make_snap(id="s1", asset_id="a1", source_app_id="SA1",
                           source_tenant_id="ST1", content_sha256="0" * 64)
        a = _make_asset("approved", "published", "ready", id="a1",
                        source_app_id="SA1", source_tenant_id="ST1", row_version=0,
                        next_snapshot_version=2)
        a.published_snapshot_id = "s1"
        s.scalar.side_effect = [a, a]
        s.get.return_value = snap
        r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
            asset_id="a1", expected_row_version=0)
        assert r.result_code == "hash_mismatch"


# ═══════════════════════════════════════════════════
# P2-4: Owner-bound key type handling
# ═══════════════════════════════════════════════════

class TestOwnerBoundKeyTypes:
    def test_int_zero_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": 0}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_bool_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": True}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_tuple_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": (1, 2)}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_none_passes(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": None}}
        EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_empty_string_passes(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": ""}}
        EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_empty_list_passes(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {"dataset_ids": []}}]}}}
        EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_empty_dict_passes(self):
        d = {"version": "0.3.0", "kind": "app",
             "app": {"name": "X", "mode": "workflow", "dataset_ids": {}}}
        EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_non_empty_str_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow",
                                                          "account_id": "a-1"}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_non_empty_list_rejected(self):
        d = {"version": "0.3.0", "kind": "app", "app": {"name": "X", "mode": "workflow"},
             "workflow": {"graph": {"nodes": [{"data": {"dataset_ids": ["id1"]}}]}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)

    def test_non_empty_dict_rejected(self):
        d = {"version": "0.3.0", "kind": "app",
             "app": {"name": "X", "mode": "workflow", "dataset_ids": {"k": "v"}}}
        with pytest.raises(NonportableResourceReference):
            EnterpriseMarketplaceService(_make_session())._validate_dsl_no_secrets(d)


# ═══════════════════════════════════════════════════
# P1-5+3: Strict app metadata validation
# ═══════════════════════════════════════════════════

class TestAppMetadataValidation:
    def test_name_list_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": [], "mode": "workflow"})

    def test_name_dict_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": {}, "mode": "workflow"})

    def test_name_int_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": 123, "mode": "workflow"})

    def test_name_bool_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": True, "mode": "workflow"})

    def test_name_none_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": None, "mode": "workflow"})

    def test_name_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": "   ", "mode": "workflow"})

    def test_mode_list_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": "F", "mode": []})

    def test_mode_bool_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": "F", "mode": True})

    def test_mode_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": "F", "mode": "   "})

    def test_mode_int_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EnterpriseMarketplaceService._validate_app_metadata(
                {"name": "F", "mode": 456})

    def test_valid_metadata_returns_stripped(self):
        aname, amode = EnterpriseMarketplaceService._validate_app_metadata(
            {"name": "  Foo  ", "mode": "  workflow  "})
        assert aname == "Foo"
        assert amode == "workflow"

    def test_not_dict_app_data_rejected(self):
        with pytest.raises(ValueError, match="must be mapping"):
            EnterpriseMarketplaceService._validate_app_metadata([1, 2, 3])

    def test_name_int_backfill_maps_to_parse_failed(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  name: 123\n  mode: workflow\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_mode_bool_backfill_maps_to_parse_failed(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: true\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"

    def test_whitespace_mode_backfill_maps_to_parse_failed(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "backfill_pending",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=0, reviewer_account_id="rev1")
        bad = "version: '0.3.0'\nkind: app\napp:\n  name: F\n  mode: '   '\n"
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=bad):
            r = EnterpriseMarketplaceService(s).backfill_legacy_snapshot(
                asset_id="a1", expected_row_version=0)
        assert r.result_code == "parse_failed"


# ═══════════════════════════════════════════════════
# Apply-mode retry recovery
# ═══════════════════════════════════════════════════

class TestApplyModeRetry:
    D = _SAMPLE_DSL

    def test_apply_retry_from_source_missing_to_ready(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "source_missing",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=1, reviewer_account_id="rev1",
                        next_snapshot_version=2)
        pre_next_v = a.next_snapshot_version
        pre_rv = a.row_version
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        svc = EnterpriseMarketplaceService(s)
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=self.D), \
             patch.object(svc, "_validate_dsl_no_secrets"):
            r = svc.backfill_legacy_snapshot(
                asset_id="a1", dry_run=False, expected_row_version=pre_rv)
        assert r.result_code == "ok"
        assert r.new_snapshot_state == "ready"
        # snapshot invariants
        snap_adds = [c[0][0] for c in s.add.call_args_list
                     if c[0] and isinstance(c[0][0], EnterpriseMarketplaceAssetSnapshot)]
        assert len(snap_adds) == 1
        snap = snap_adds[0]
        assert snap.asset_id == a.id
        assert snap.snapshot_version == pre_next_v
        assert a.next_snapshot_version == pre_next_v + 1
        assert a.published_snapshot_id == snap.id
        assert snap.source_app_id == a.source_app_id
        assert snap.source_tenant_id == a.source_tenant_id
        assert a.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.READY
        assert a.snapshot_error_code is None
        assert a.row_version == pre_rv + 1
        assert r.new_row_version == a.row_version

    def test_apply_retry_from_failed_to_ready(self):
        s = _make_session()
        a = _make_asset("approved", "unpublished", "failed",
                        id="a1", source_app_id="SA1", source_tenant_id="ST1",
                        row_version=2, reviewer_account_id="rev1",
                        snapshot_error_code="validation_failed",
                        next_snapshot_version=3)
        pre_next_v = a.next_snapshot_version
        pre_rv = a.row_version
        source_app = _make_app("SA1", "ST1", status="normal")
        s.scalar.side_effect = [a, source_app, a]
        svc = EnterpriseMarketplaceService(s)
        with patch("services.enterprise_marketplace_service.AppDslService.export_dsl",
                   return_value=self.D), \
             patch.object(svc, "_validate_dsl_no_secrets"):
            r = svc.backfill_legacy_snapshot(
                asset_id="a1", dry_run=False, expected_row_version=pre_rv)
        assert r.result_code == "ok"
        assert r.new_snapshot_state == "ready"
        # snapshot invariants
        snap_adds = [c[0][0] for c in s.add.call_args_list
                     if c[0] and isinstance(c[0][0], EnterpriseMarketplaceAssetSnapshot)]
        assert len(snap_adds) == 1
        snap = snap_adds[0]
        assert snap.asset_id == a.id
        assert snap.snapshot_version == pre_next_v
        assert a.next_snapshot_version == pre_next_v + 1
        assert a.published_snapshot_id == snap.id
        assert snap.source_app_id == a.source_app_id
        assert snap.source_tenant_id == a.source_tenant_id
        assert a.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.READY
        assert a.snapshot_error_code is None
        assert a.row_version == pre_rv + 1
        assert r.new_row_version == a.row_version

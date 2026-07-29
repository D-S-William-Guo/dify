"""Enterprise marketplace service – session-injected, lock-ordered, fail-closed."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, NamedTuple

import yaml
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from constants.dsl_version import CURRENT_APP_DSL_VERSION
from core.plugin.entities.plugin import PluginDependency, PluginDependencyType
from libs.datetime_utils import naive_utc_now
from models import Account, App, Tenant
from models.model import (
    EnterpriseMarketplaceAsset,
    EnterpriseMarketplaceAssetPublicationStatus,
    EnterpriseMarketplaceAssetSnapshot,
    EnterpriseMarketplaceAssetSnapshotState,
)
from services.app_dsl_service import AppDslService
from services.dsl_version import check_version_compatibility
from services.entities.dsl_entities import ImportMode, ImportStatus
from services.errors.enterprise_marketplace import (
    AssetAlreadyUnlisted,
    AssetNotFound,
    ConcurrentOperation,
    CopyFailed,
    CopyPendingUnsupported,
    DependencyServiceUnavailable,
    DependencyUnavailable,
    InvalidStatusTransition,
    MarketplaceError,
    NonportableResourceReference,
    PrivatePluginDependency,
    SnapshotContainsSecret,
    SnapshotIntegrityError,
    SnapshotNotReady,
    SourceAppNotFound,
    SourceAppUnavailable,
    StaleAssetVersion,
    SubmissionAlreadyPending,
)
from services.plugin.dependencies_analysis import DependenciesAnalysisService

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

_ALLOWED_TRANSITIONS = {
    (None, "unpublished"): frozenset({"pending"}),
    ("pending", "unpublished"): frozenset({"pending", "approved", "rejected"}),
    ("pending", "published"): frozenset({"pending", "approved", "rejected"}),
    ("approved", "published"): frozenset({"pending", "rejected", "approved"}),
    ("rejected", "unpublished"): frozenset({"pending"}),
    ("rejected", "published"): frozenset({"pending"}),
    ("unlisted", "unlisted"): frozenset({"pending"}),
}

_BACKFILL_ELIGIBLE_STATUSES = frozenset({"approved"})
_BACKFILL_ELIGIBLE_STATES = frozenset({"backfill_pending"})
_SOURCE_UNIQUE_CONSTRAINT = "unique_enterprise_marketplace_source_app"

SANITIZER_CANARY_SECRET = "CANARY_SECRET_VALUE_FOR_TESTING_ONLY"
SANITIZER_CANARY_TOKEN = "CANARY_TOKEN_VALUE_FOR_TESTING_ONLY"
SANITIZER_CANARY_CREDENTIAL = "CANARY_CREDENTIAL_ID_FOR_TESTING_ONLY"

_FORBIDDEN_KEY_PATTERNS = (
    "credential_id", "credentials", "api_key", "api-key",
    "bearer_token", "private_key", "private-key",
    "secret_key", "secret-key", "access_key", "access-key", "token",
)

_REQUIRED_EMPTY_KEYS = frozenset({
    "webhook_url", "webhook_debug_url", "subscription_id",
})

_OWNER_BOUND_KEY_PATTERNS = (
    "dataset_ids", "file_id", "upload_file_id",
    "tenant_id", "workspace_id", "account_id",
)

# Log events
_LOG_SUBMIT_CREATED = "marketplace.submission_created"
_LOG_SUBMIT_RESUBMITTED = "marketplace.submission_resubmitted"
_LOG_REVIEW_APPROVED = "marketplace.review_approved"
_LOG_REVIEW_REJECTED = "marketplace.review_rejected"
_LOG_ASSET_UNLISTED = "marketplace.asset_unlisted"
_LOG_ASSET_COPIED = "marketplace.asset_copied"
_LOG_COPY_FAILED = "marketplace.copy_failed"
_LOG_BACKFILL_STARTED = "marketplace.backfill_started"
_LOG_BACKFILL_COMPLETED = "marketplace.backfill_completed"
_LOG_BACKFILL_FAILED = "marketplace.backfill_failed"

# ── NamedTuples ────────────────────────────────────────────────────────

class BackfillResult(NamedTuple):
    asset_id: str; dry_run: bool
    old_snapshot_state: str; new_snapshot_state: str
    old_row_version: int; new_row_version: int
    legacy_status: str; result_code: str
    hash_fingerprint: str | None = None

class CopyResult(NamedTuple):
    import_app_id: str; import_status: str
    warnings: list[str]; snapshot_version: int; content_sha256: str

class IntegrityReport(NamedTuple):
    orphan_snapshot_count: int; missing_pointer_count: int; pointer_mismatch_count: int

class AssetSnapshotRow(NamedTuple):
    asset_id: str; snapshot_id: str | None; snapshot_version: int | None
    status: str; publication_status: str; snapshot_state: str
    title: str; description: str; category: str
    tags: list[str]; scenario: str; allow_show_workspace_name: bool
    source_app_id: str | None; source_tenant_name: str | None
    submitter_account_id: str | None; reviewer_account_id: str | None
    row_version: int
    created_at: datetime; updated_at: datetime
    app_name: str | None; app_description: str | None; app_mode: str | None
    app_icon_type: str | None; app_icon: str | None; app_icon_background: str | None
    dsl_version: str | None; content_sha256: str | None
    dependencies: list[dict[str, Any]] | None
    frozen_at: datetime | None

class PageResult(NamedTuple):
    items: list[AssetSnapshotRow]; page: int; limit: int; total: int; has_more: bool

# ── Service ────────────────────────────────────────────────────────────

class EnterpriseMarketplaceService:
    def __init__(self, session: Session):
        self._session = session

    # ── Submit ─────────────────────────────────────────────────────────

    def submit_asset(self, *, source_app, account, title, description,
                     category, tags, scenario, allow_show_workspace_name,
                     expected_row_version=None):
        tid = account.current_tenant_id
        if tid is None: raise MarketplaceError("No current tenant")
        if source_app.tenant_id != tid: raise SourceAppNotFound()
        if source_app.status != "normal": raise SourceAppUnavailable()
        self._lock_source_app(source_app.id, tid)
        asset = self._query_asset_by_source(source_app.id, for_update=True)
        if asset is None:
            return self._create_initial_submission(
                source_app=source_app, account=account, tenant_id=tid,
                title=title, description=description, category=category,
                tags=tags, scenario=scenario,
                allow_show_workspace_name=allow_show_workspace_name)
        if expected_row_version is None: raise SubmissionAlreadyPending()
        self._check_row_version(asset, expected_row_version)
        if asset.status == "pending": raise SubmissionAlreadyPending()
        pub = self._pub_val(asset)
        if "pending" not in _ALLOWED_TRANSITIONS.get((asset.status, pub), frozenset()):
            raise InvalidStatusTransition()
        old_rv = asset.row_version
        asset.title = title; asset.description = description.strip()
        asset.category = category.strip(); asset.tags = self._norm_tags(tags)
        asset.scenario = scenario.strip()
        asset.allow_show_workspace_name = allow_show_workspace_name
        asset.status = "pending"; asset.submitter_account_id = account.id
        asset.review_note = None; asset.reviewed_at = None; asset.reviewer_account_id = None
        asset.row_version += 1; self._session.flush()
        logger.info(_LOG_SUBMIT_RESUBMITTED, extra={
            "asset_id": asset.id, "source_app_id": source_app.id,
            "actor_account_id": account.id, "old_row_version": old_rv,
            "new_row_version": asset.row_version})
        return asset

    def _create_initial_submission(self, *, source_app, account, tenant_id, title,
                                   description, category, tags, scenario,
                                   allow_show_workspace_name):
        asset = EnterpriseMarketplaceAsset(
            source_tenant_id=tenant_id, source_app_id=source_app.id,
            submitter_account_id=account.id, title=title)
        asset.id = str(uuid.uuid4()); asset.status = "pending"
        asset.publication_status = EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED
        asset.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.NONE
        asset.description = description.strip(); asset.category = category.strip()
        asset.tags = self._norm_tags(tags); asset.scenario = scenario.strip()
        asset.allow_show_workspace_name = allow_show_workspace_name; asset.row_version = 0
        self._session.add(asset)
        try:
            self._session.flush()
        except IntegrityError as exc:
            if self._is_target_unique_violation(exc):
                raise ConcurrentOperation() from exc
            raise
        asset.row_version = 1; self._session.flush()
        logger.info(_LOG_SUBMIT_CREATED, extra={
            "asset_id": asset.id, "source_app_id": source_app.id,
            "source_tenant_id": tenant_id, "actor_account_id": account.id,
            "new_row_version": asset.row_version})
        return asset

    # ── Review ─────────────────────────────────────────────────────────

    def approve_asset(self, *, asset_id, reviewer, review_note=None, expected_row_version=0):
        asset = self._get_asset(asset_id, for_update=False)
        self._check_row_version(asset, expected_row_version)
        if asset.status != "pending": raise InvalidStatusTransition()
        said, stid = asset.source_app_id, asset.source_tenant_id
        source_app = self._lock_and_get_source_app(said, stid)
        if source_app.status != "normal": raise SourceAppUnavailable()
        asset = self._get_asset(asset_id, for_update=True)
        self._check_row_version(asset, expected_row_version)
        if asset.status != "pending": raise InvalidStatusTransition()
        if asset.source_app_id != said or asset.source_tenant_id != stid:
            raise InvalidStatusTransition()
        dsl_content = AppDslService.export_dsl(
            app_model=source_app, session=self._session, include_secret=False)
        data = yaml.safe_load(dsl_content)
        if not isinstance(data, dict): raise MarketplaceError("DSL must be a mapping")
        if data.get("kind") != "app": raise MarketplaceError("DSL kind must be 'app'")
        dsl_version = self._check_dsl_version(data.get("version", ""))
        self._validate_dsl_no_secrets(data)
        deps = self._extract_and_normalize_dependencies(data)
        sha = hashlib.sha256(dsl_content.encode("utf-8")).hexdigest()
        next_v = asset.next_snapshot_version; asset.next_snapshot_version += 1
        app_data = data.get("app", {})
        if not isinstance(app_data, dict): raise MarketplaceError("App must be mapping")
        aname, amode = app_data.get("name", ""), app_data.get("mode", "")
        if not aname or not amode: raise MarketplaceError("App name/mode required")
        tname = None
        tenant = self._session.get(Tenant, stid)
        if tenant: tname = tenant.name
        snap = EnterpriseMarketplaceAssetSnapshot(
            asset_id=asset.id, snapshot_version=next_v, dsl_content=dsl_content,
            dsl_version=dsl_version, content_sha256=sha, frozen_at=naive_utc_now(),
            source_app_id=source_app.id, source_tenant_id=stid,
            submitter_account_id=asset.submitter_account_id,
            reviewer_account_id=reviewer.id, title=asset.title,
            app_name=aname, app_mode=amode)
        snap.id = str(uuid.uuid4()); snap.source_tenant_name = tname
        snap.description = asset.description; snap.category = asset.category
        snap.tags = asset.tags; snap.scenario = asset.scenario
        snap.allow_show_workspace_name = asset.allow_show_workspace_name
        snap.app_description = app_data.get("description", "")
        it = app_data.get("icon_type")
        if it == "link": raise NonportableResourceReference()
        if isinstance(it, str): snap.app_icon_type = it
        snap.app_icon = app_data.get("icon")
        snap.app_icon_background = app_data.get("icon_background")
        snap.dependencies = deps; self._session.add(snap)
        old_rv = asset.row_version; asset.status = "approved"
        asset.publication_status = EnterpriseMarketplaceAssetPublicationStatus.PUBLISHED
        asset.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.READY
        asset.published_snapshot_id = snap.id
        asset.reviewer_account_id = reviewer.id
        asset.review_note = review_note.strip() if review_note else None
        asset.reviewed_at = naive_utc_now(); asset.row_version += 1
        self._session.flush()
        logger.info(_LOG_REVIEW_APPROVED, extra={
            "asset_id": asset.id, "snapshot_id": snap.id,
            "snapshot_version": next_v, "actor_account_id": reviewer.id,
            "new_row_version": asset.row_version})
        return asset, snap

    def reject_asset(self, *, asset_id, reviewer, review_note=None, expected_row_version=0):
        asset = self._get_asset(asset_id, for_update=True)
        self._check_row_version(asset, expected_row_version)
        if asset.status != "pending": raise InvalidStatusTransition()
        asset.status = "rejected"; asset.reviewer_account_id = reviewer.id
        asset.review_note = review_note.strip() if review_note else None
        asset.reviewed_at = naive_utc_now(); asset.row_version += 1; self._session.flush()
        logger.info(_LOG_REVIEW_REJECTED, extra={
            "asset_id": asset.id, "actor_account_id": reviewer.id,
            "new_row_version": asset.row_version})
        return asset

    # ── Unlist ─────────────────────────────────────────────────────────

    def unlist_asset(self, *, asset_id, reviewer, review_note=None, expected_row_version=0):
        asset = self._get_asset(asset_id, for_update=True)
        self._check_row_version(asset, expected_row_version)
        pub = self._pub_val(asset)
        if pub == "unlisted": raise AssetAlreadyUnlisted()
        if pub != "published": raise InvalidStatusTransition()
        asset.publication_status = EnterpriseMarketplaceAssetPublicationStatus.UNLISTED
        asset.reviewer_account_id = reviewer.id
        asset.review_note = review_note.strip() if review_note else None
        asset.reviewed_at = naive_utc_now(); asset.row_version += 1; self._session.flush()
        logger.info(_LOG_ASSET_UNLISTED, extra={
            "asset_id": asset.id, "actor_account_id": reviewer.id,
            "new_row_version": asset.row_version})
        return asset

    # ── Copy ───────────────────────────────────────────────────────────

    def copy_asset(self, *, asset_id, account):
        tid = account.current_tenant_id
        if tid is None: raise MarketplaceError("No current tenant")
        asset = self._get_asset(asset_id, for_update=False)
        if self._pub_val(asset) != "published": raise AssetNotFound()
        if self._snap_val(asset) != "ready": raise SnapshotNotReady()
        if not asset.published_snapshot_id: raise SnapshotNotReady()
        snap = self._session.get(EnterpriseMarketplaceAssetSnapshot, asset.published_snapshot_id)
        if snap is None or snap.asset_id != asset.id: raise SnapshotIntegrityError()
        if hashlib.sha256(snap.dsl_content.encode("utf-8")).hexdigest() != snap.content_sha256:
            raise SnapshotIntegrityError()
        if snap.source_app_id != asset.source_app_id: raise SnapshotIntegrityError()
        if snap.source_tenant_id != asset.source_tenant_id: raise SnapshotIntegrityError()
        if snap.dependencies:
            deps = self._parse_deps(snap.dependencies)
            for d in deps:
                if d.type == PluginDependencyType.Package: raise PrivatePluginDependency()
            try:
                leaked = DependenciesAnalysisService.get_leaked_dependencies(
                    tenant_id=tid, dependencies=deps)
            except Exception as exc:
                raise DependencyServiceUnavailable() from exc
            if leaked: raise DependencyUnavailable()
        import_app_id = str(uuid.uuid4())
        try:
            import_result = AppDslService(self._session).import_app(
                account=account, import_mode=ImportMode.YAML_CONTENT.value,
                yaml_content=snap.dsl_content, import_app_id=import_app_id)
        except Exception as exc:
            logger.warning(_LOG_COPY_FAILED, extra={
                "asset_id": asset_id, "snapshot_id": snap.id,
                "target_tenant_id": tid, "import_app_id": import_app_id,
                "stage": "import_app", "error_code": "import_app_exception"})
            raise CopyFailed() from exc
        if import_result.status == ImportStatus.COMPLETED:
            wl: list[str] = []
        elif import_result.status == ImportStatus.COMPLETED_WITH_WARNINGS:
            wl = [w.code for w in (import_result.warnings or []) if getattr(w, "code", None)]
        elif import_result.status == ImportStatus.PENDING:
            raise CopyPendingUnsupported()
        elif import_result.status == ImportStatus.FAILED:
            logger.warning(_LOG_COPY_FAILED, extra={
                "asset_id": asset_id, "snapshot_id": snap.id,
                "target_tenant_id": tid, "import_app_id": import_app_id,
                "stage": "import_failed", "error_code": "import_failed"})
            raise CopyFailed()
        else:
            raise CopyFailed()
        logger.info(_LOG_ASSET_COPIED, extra={
            "asset_id": asset_id, "snapshot_id": snap.id,
            "target_tenant_id": tid, "import_app_id": import_app_id,
            "status": import_result.status.value})
        return CopyResult(
            import_app_id=import_result.app_id or import_app_id,
            import_status=import_result.status.value, warnings=wl,
            snapshot_version=snap.snapshot_version, content_sha256=snap.content_sha256)

    # ── Backfill ──────────────────────────────────────────────────────

    def backfill_legacy_snapshot(self, *, asset_id, dry_run=True, expected_row_version=0):
        a = self._get_asset(asset_id, for_update=False)
        self._check_row_version(a, expected_row_version)
        old_state, leg = self._snap_val(a), a.status
        said, stid = a.source_app_id, a.source_tenant_id
        old_rv = a.row_version
        if old_state == "ready":
            return self._bf_ready_skip(asset_id, dry_run, old_state, leg, old_rv,
                                        said, stid, expected_row_version)
        if leg not in _BACKFILL_ELIGIBLE_STATUSES or old_state not in _BACKFILL_ELIGIBLE_STATES:
            return BackfillResult(asset_id=asset_id, dry_run=dry_run,
                old_snapshot_state=old_state, new_snapshot_state=old_state,
                old_row_version=old_rv, new_row_version=old_rv,
                legacy_status=leg, result_code="ineligible")
        try:
            source_app = self._lock_and_get_source_app(said, stid)
        except SourceAppNotFound:
            return self._bf_source_missing(asset_id, dry_run, old_state, leg, old_rv,
                                           said, stid, expected_row_version)
        if source_app.status != "normal":
            return self._bf_source_unavailable(asset_id, dry_run, old_state, leg, old_rv,
                                               said, stid, expected_row_version)
        a = self._get_asset(asset_id, for_update=True)
        self._check_row_version(a, expected_row_version)
        if a.source_app_id != said or a.source_tenant_id != stid:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "tenant_mismatch")
        if a.status != "approved" or self._snap_val(a) != "backfill_pending":
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "state_changed")
        if not a.reviewer_account_id:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "reviewer_missing")
        old_rv = a.row_version
        try:
            dsl = AppDslService.export_dsl(
                app_model=source_app, session=self._session, include_secret=False)
        except Exception:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "export_failed")
        try:
            data = yaml.safe_load(dsl)
            if not isinstance(data, dict) or data.get("kind") != "app":
                raise ValueError("bad DSL")
            dsl_ver = self._check_dsl_version(data.get("version", ""))
            self._validate_dsl_no_secrets(data)
            deps = self._extract_and_normalize_dependencies(data)
        except SnapshotContainsSecret:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "validation_failed")
        except NonportableResourceReference:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "validation_failed")
        except PrivatePluginDependency:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "private_dependency")
        except Exception:
            return self._bf_fail(asset_id, dry_run, old_state, leg, a, "parse_failed")
        sha = hashlib.sha256(dsl.encode("utf-8")).hexdigest()
        if dry_run:
            return BackfillResult(asset_id=asset_id, dry_run=True,
                old_snapshot_state=old_state, new_snapshot_state="ready",
                old_row_version=old_rv, new_row_version=a.row_version,
                legacy_status=leg, result_code="dry_run_ok", hash_fingerprint=sha[:12])
        next_v = a.next_snapshot_version; a.next_snapshot_version += 1
        app_data = data.get("app", {})
        aname, amode = app_data.get("name", ""), app_data.get("mode", "")
        tname = None
        tenant = self._session.get(Tenant, stid)
        if tenant: tname = tenant.name
        snap = EnterpriseMarketplaceAssetSnapshot(
            asset_id=a.id, snapshot_version=next_v, dsl_content=dsl,
            dsl_version=dsl_ver, content_sha256=sha, frozen_at=naive_utc_now(),
            source_app_id=source_app.id, source_tenant_id=stid,
            submitter_account_id=a.submitter_account_id,
            reviewer_account_id=a.reviewer_account_id,
            title=a.title, app_name=aname, app_mode=amode)
        snap.id = str(uuid.uuid4()); snap.source_tenant_name = tname
        snap.description = a.description; snap.category = a.category
        snap.tags = a.tags; snap.scenario = a.scenario
        snap.allow_show_workspace_name = a.allow_show_workspace_name
        snap.app_description = app_data.get("description", "")
        it = app_data.get("icon_type")
        if isinstance(it, str): snap.app_icon_type = it
        snap.app_icon = app_data.get("icon")
        snap.app_icon_background = app_data.get("icon_background")
        snap.dependencies = deps; self._session.add(snap)
        a.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.READY
        a.published_snapshot_id = snap.id
        a.publication_status = EnterpriseMarketplaceAssetPublicationStatus.PUBLISHED
        a.row_version += 1; a.snapshot_error_code = None; self._session.flush()
        logger.info(_LOG_BACKFILL_COMPLETED, extra={
            "asset_id": asset_id, "snapshot_id": snap.id, "result_code": "ok"})
        return BackfillResult(asset_id=asset_id, dry_run=False,
            old_snapshot_state=old_state, new_snapshot_state="ready",
            old_row_version=old_rv, new_row_version=a.row_version,
            legacy_status=leg, result_code="ok", hash_fingerprint=sha[:12])

    # ── Backfill sub-methods ──────────────────────────────────────────

    def _bf_ready_skip(self, aid, dr, os, leg, old_rv, exp_said, exp_stid, exp_rv):
        a = self._get_asset(aid, for_update=True)
        self._check_row_version(a, exp_rv)
        if a.source_app_id != exp_said or a.source_tenant_id != exp_stid:
            return self._bf_fail(aid, dr, os, leg, a, "source_id_changed")
        if not a.published_snapshot_id:
            return self._bf_fail(aid, dr, os, leg, a, "pointer_missing")
        snap = self._session.get(EnterpriseMarketplaceAssetSnapshot, a.published_snapshot_id)
        if snap is None:
            return self._bf_fail(aid, dr, os, leg, a, "snapshot_missing")
        if snap.asset_id != a.id:
            return self._bf_fail(aid, dr, os, leg, a, "pointer_mismatch")
        if snap.snapshot_version < 1:
            return self._bf_fail(aid, dr, os, leg, a, "version_invalid")
        if snap.source_app_id != a.source_app_id or snap.source_tenant_id != a.source_tenant_id:
            return self._bf_fail(aid, dr, os, leg, a, "snapshot_source_changed")
        if hashlib.sha256(snap.dsl_content.encode("utf-8")).hexdigest() != snap.content_sha256:
            return self._bf_fail(aid, dr, os, leg, a, "hash_mismatch")
        return BackfillResult(asset_id=aid, dry_run=dr,
            old_snapshot_state=os, new_snapshot_state=os,
            old_row_version=old_rv, new_row_version=a.row_version,
            legacy_status=leg, result_code="ready_skip",
            hash_fingerprint=snap.content_sha256[:12])

    def _bf_source_missing(self, aid, dr, os, leg, old_rv, said, stid, exp_rv):
        if not dr:
            a = self._get_asset(aid, for_update=True)
            self._check_row_version(a, exp_rv)
            if a.source_app_id != said or a.source_tenant_id != stid:
                return BackfillResult(asset_id=aid, dry_run=dr,
                    old_snapshot_state=os, new_snapshot_state="failed",
                    old_row_version=old_rv, new_row_version=a.row_version,
                    legacy_status=leg, result_code="tenant_mismatch")
            if a.status != "approved" or self._snap_val(a) != "backfill_pending":
                return BackfillResult(asset_id=aid, dry_run=dr,
                    old_snapshot_state=os, new_snapshot_state=os,
                    old_row_version=old_rv, new_row_version=a.row_version,
                    legacy_status=leg, result_code="state_changed")
            a.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.SOURCE_MISSING
            a.snapshot_error_code = "source_missing"; a.row_version += 1; self._session.flush()
            return BackfillResult(asset_id=aid, dry_run=dr,
                old_snapshot_state=os, new_snapshot_state="source_missing",
                old_row_version=old_rv, new_row_version=a.row_version,
                legacy_status=leg, result_code="source_missing")
        return BackfillResult(asset_id=aid, dry_run=dr,
            old_snapshot_state=os, new_snapshot_state="source_missing",
            old_row_version=old_rv, new_row_version=old_rv,
            legacy_status=leg, result_code="source_missing")

    def _bf_source_unavailable(self, aid, dr, os, leg, old_rv, said, stid, exp_rv):
        if not dr:
            a = self._get_asset(aid, for_update=True)
            self._check_row_version(a, exp_rv)
            if a.source_app_id != said or a.source_tenant_id != stid:
                return BackfillResult(asset_id=aid, dry_run=dr,
                    old_snapshot_state=os, new_snapshot_state="failed",
                    old_row_version=old_rv, new_row_version=a.row_version,
                    legacy_status=leg, result_code="tenant_mismatch")
            if a.status != "approved" or self._snap_val(a) != "backfill_pending":
                return BackfillResult(asset_id=aid, dry_run=dr,
                    old_snapshot_state=os, new_snapshot_state=os,
                    old_row_version=old_rv, new_row_version=a.row_version,
                    legacy_status=leg, result_code="state_changed")
            a.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.FAILED
            a.snapshot_error_code = "source_unavailable"; a.row_version += 1; self._session.flush()
            return BackfillResult(asset_id=aid, dry_run=dr,
                old_snapshot_state=os, new_snapshot_state="failed",
                old_row_version=old_rv, new_row_version=a.row_version,
                legacy_status=leg, result_code="source_unavailable")
        return BackfillResult(asset_id=aid, dry_run=dr,
            old_snapshot_state=os, new_snapshot_state="failed",
            old_row_version=old_rv, new_row_version=old_rv,
            legacy_status=leg, result_code="source_unavailable")

    def _bf_fail(self, aid, dr, os, leg, a, code):
        logger.error(_LOG_BACKFILL_FAILED, extra={
            "asset_id": aid, "error_code": code, "row_version": a.row_version})
        if not dr:
            a.snapshot_state = EnterpriseMarketplaceAssetSnapshotState.FAILED
            a.snapshot_error_code = code; a.row_version += 1; self._session.flush()
            return BackfillResult(asset_id=aid, dry_run=dr,
                old_snapshot_state=os, new_snapshot_state="failed",
                old_row_version=a.row_version - 1, new_row_version=a.row_version,
                legacy_status=leg, result_code=code)
        return BackfillResult(asset_id=aid, dry_run=dr,
            old_snapshot_state=os, new_snapshot_state="failed",
            old_row_version=a.row_version, new_row_version=a.row_version,
            legacy_status=leg, result_code=code)

    # ── Integrity ─────────────────────────────────────────────────────

    def check_integrity(self):
        o = self._session.scalar(text(
            "SELECT COUNT(1) FROM enterprise_marketplace_asset_snapshots s "
            "LEFT JOIN enterprise_marketplace_assets a ON s.asset_id = a.id WHERE a.id IS NULL")) or 0
        m = self._session.scalar(text(
            "SELECT COUNT(1) FROM enterprise_marketplace_assets a "
            "WHERE a.published_snapshot_id IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM enterprise_marketplace_asset_snapshots s WHERE s.id = a.published_snapshot_id)")) or 0
        mm = self._session.scalar(text(
            "SELECT COUNT(1) FROM enterprise_marketplace_assets a "
            "JOIN enterprise_marketplace_asset_snapshots s ON s.id = a.published_snapshot_id "
            "WHERE s.asset_id != a.id")) or 0
        return IntegrityReport(orphan_snapshot_count=o, missing_pointer_count=m, pointer_mismatch_count=mm)

    def count_by_state(self):
        res = self._session.execute(select(
            EnterpriseMarketplaceAsset.snapshot_state, func.count(EnterpriseMarketplaceAsset.id)
        ).group_by(EnterpriseMarketplaceAsset.snapshot_state)).all()
        return {(s.value if hasattr(s, "value") else s): c for s, c in res}

    def count_by_status(self):
        res = self._session.execute(select(
            EnterpriseMarketplaceAsset.status, func.count(EnterpriseMarketplaceAsset.id)
        ).group_by(EnterpriseMarketplaceAsset.status)).all()
        return {s: c for s, c in res}

    def list_all_asset_ids(self):
        return [r[0] for r in self._session.execute(
            select(EnterpriseMarketplaceAsset.id).order_by(EnterpriseMarketplaceAsset.id)).fetchall()]

    # ── Read services ─────────────────────────────────────────────────

    def list_my_submissions(self, *, tenant_id, submitter_account_id, page=1, limit=50,
                            keyword=None, category=None, sort="updated_at_desc"):
        stmt = select(EnterpriseMarketplaceAsset).where(
            EnterpriseMarketplaceAsset.source_tenant_id == tenant_id,
            EnterpriseMarketplaceAsset.submitter_account_id == submitter_account_id)
        return self._paginate_assets(stmt, page, limit, keyword, category, sort)

    def list_public_assets(self, *, page=1, limit=24, keyword=None, category=None,
                           sort="updated_at_desc"):
        stmt = (select(EnterpriseMarketplaceAsset, EnterpriseMarketplaceAssetSnapshot)
                .join(EnterpriseMarketplaceAssetSnapshot,
                      EnterpriseMarketplaceAsset.published_snapshot_id == EnterpriseMarketplaceAssetSnapshot.id)
                .where(
                    EnterpriseMarketplaceAsset.publication_status == EnterpriseMarketplaceAssetPublicationStatus.PUBLISHED,
                    EnterpriseMarketplaceAsset.snapshot_state == EnterpriseMarketplaceAssetSnapshotState.READY,
                    EnterpriseMarketplaceAsset.published_snapshot_id.isnot(None),
                    EnterpriseMarketplaceAssetSnapshot.asset_id == EnterpriseMarketplaceAsset.id))
        if keyword:
            stmt = stmt.where(EnterpriseMarketplaceAssetSnapshot.title.ilike(
                f"%{keyword.strip()[:255]}%"))
        if category:
            stmt = stmt.where(EnterpriseMarketplaceAssetSnapshot.category == category.strip())
        stmt = self._apply_snapshot_sort(stmt, sort)
        stmt = stmt.order_by(EnterpriseMarketplaceAsset.id)
        total = self._count(stmt)
        offset = (page - 1) * limit
        rows = self._session.execute(stmt.offset(offset).limit(limit)).all()
        items = [self._row_public(asset=row[0], snap=row[1]) for row in rows]
        return PageResult(items=items, page=page, limit=limit, total=total,
                          has_more=(offset + limit) < total)

    def get_public_asset(self, *, asset_id):
        asset = self._get_asset(asset_id, for_update=False)
        if self._pub_val(asset) != "published" or self._snap_val(asset) != "ready":
            raise AssetNotFound()
        if not asset.published_snapshot_id: raise AssetNotFound()
        snap = self._session.get(EnterpriseMarketplaceAssetSnapshot, asset.published_snapshot_id)
        if snap is None or snap.asset_id != asset.id: raise AssetNotFound()
        return self._row_public(asset=asset, snap=snap)

    def list_admin_assets(self, *, page=1, limit=50, keyword=None, category=None,
                          status=None, publication_status=None, snapshot_state=None,
                          sort="updated_at_desc"):
        stmt = select(EnterpriseMarketplaceAsset)
        if status: stmt = stmt.where(EnterpriseMarketplaceAsset.status.in_(status))
        if publication_status:
            pubs = [EnterpriseMarketplaceAssetPublicationStatus(p) for p in publication_status]
            stmt = stmt.where(EnterpriseMarketplaceAsset.publication_status.in_(pubs))
        if snapshot_state:
            snaps = [EnterpriseMarketplaceAssetSnapshotState(s) for s in snapshot_state]
            stmt = stmt.where(EnterpriseMarketplaceAsset.snapshot_state.in_(snaps))
        return self._paginate_assets(stmt, page, limit, keyword, category, sort)

    # ── Pagination ────────────────────────────────────────────────────

    def _paginate_assets(self, stmt, page, limit, keyword, category, sort):
        if keyword:
            stmt = stmt.where(EnterpriseMarketplaceAsset.title.ilike(
                f"%{keyword.strip()[:255]}%"))
        if category:
            stmt = stmt.where(EnterpriseMarketplaceAsset.category == category.strip())
        stmt = self._apply_asset_sort(stmt, sort)
        stmt = stmt.order_by(EnterpriseMarketplaceAsset.id)
        total = self._count(stmt)
        offset = (page - 1) * limit
        rows = self._session.execute(stmt.offset(offset).limit(limit)).scalars().all()
        items = [self._row_admin(a) for a in rows]
        return PageResult(items=items, page=page, limit=limit, total=total,
                          has_more=(offset + limit) < total)

    def _apply_asset_sort(self, stmt, sort):
        cols = {"updated_at_desc": EnterpriseMarketplaceAsset.updated_at.desc(),
                "created_at_desc": EnterpriseMarketplaceAsset.created_at.desc(),
                "title_asc": EnterpriseMarketplaceAsset.title.asc()}
        return stmt.order_by(cols.get(sort, EnterpriseMarketplaceAsset.updated_at.desc()))

    def _apply_snapshot_sort(self, stmt, sort):
        """Sort uses snapshot frozen_at (NOT updated_at which doesn't exist on snapshot)."""
        cols = {"updated_at_desc": EnterpriseMarketplaceAssetSnapshot.frozen_at.desc(),
                "created_at_desc": EnterpriseMarketplaceAssetSnapshot.frozen_at.desc(),
                "title_asc": EnterpriseMarketplaceAssetSnapshot.title.asc()}
        return stmt.order_by(cols.get(sort, EnterpriseMarketplaceAssetSnapshot.frozen_at.desc()))

    def _count(self, stmt):
        subq = stmt.order_by(None).subquery()
        return self._session.scalar(select(func.count()).select_from(subq)) or 0

    def _row_admin(self, a):
        return AssetSnapshotRow(
            asset_id=a.id, snapshot_id=None, snapshot_version=None,
            status=a.status, publication_status=self._pub_val(a),
            snapshot_state=self._snap_val(a),
            title=a.title, description=a.description or "", category=a.category,
            tags=list(a.tags) if a.tags else [], scenario=a.scenario or "",
            allow_show_workspace_name=a.allow_show_workspace_name,
            source_app_id=a.source_app_id, source_tenant_name=None,
            submitter_account_id=a.submitter_account_id,
            reviewer_account_id=a.reviewer_account_id,
            row_version=a.row_version, created_at=a.created_at, updated_at=a.updated_at,
            app_name=None, app_description=None, app_mode=None,
            app_icon_type=None, app_icon=None, app_icon_background=None,
            dsl_version=None, content_sha256=None, dependencies=None, frozen_at=None)

    def _row_public(self, *, asset, snap):
        """All public fields from snapshot only. No fallback to mutable asset fields."""
        st_name = None
        if snap.allow_show_workspace_name and snap.source_tenant_name:
            st_name = snap.source_tenant_name
        return AssetSnapshotRow(
            asset_id=asset.id, snapshot_id=snap.id,
            snapshot_version=snap.snapshot_version,
            status=asset.status, publication_status=self._pub_val(asset),
            snapshot_state=self._snap_val(asset),
            title=snap.title, description=snap.description or "",
            category=snap.category, tags=snap.tags,
            scenario=snap.scenario or "",
            allow_show_workspace_name=snap.allow_show_workspace_name,
            source_app_id=None, source_tenant_name=st_name,
            submitter_account_id=None, reviewer_account_id=None,
            row_version=asset.row_version,
            created_at=snap.frozen_at, updated_at=snap.frozen_at,
            app_name=snap.app_name, app_description=snap.app_description,
            app_mode=snap.app_mode, app_icon_type=snap.app_icon_type,
            app_icon=snap.app_icon, app_icon_background=snap.app_icon_background,
            dsl_version=snap.dsl_version, content_sha256=snap.content_sha256,
            dependencies=snap.dependencies, frozen_at=snap.frozen_at)

    # ── Internal helpers ──────────────────────────────────────────────

    def _lock_and_get_source_app(self, app_id, tenant_id):
        app = self._session.scalar(select(App).where(
            App.id == app_id, App.tenant_id == tenant_id).with_for_update())
        if app is None: raise SourceAppNotFound()
        return app

    def _lock_source_app(self, app_id, tenant_id):
        self._session.execute(select(App.id).where(
            App.id == app_id, App.tenant_id == tenant_id).with_for_update())

    def _get_asset(self, asset_id, *, for_update=False):
        stmt = select(EnterpriseMarketplaceAsset).where(EnterpriseMarketplaceAsset.id == asset_id)
        if for_update: stmt = stmt.with_for_update()
        a = self._session.scalar(stmt)
        if a is None: raise AssetNotFound()
        return a

    def _query_asset_by_source(self, source_app_id, *, for_update=False):
        stmt = select(EnterpriseMarketplaceAsset).where(
            EnterpriseMarketplaceAsset.source_app_id == source_app_id)
        if for_update: stmt = stmt.with_for_update()
        return self._session.scalar(stmt)

    @staticmethod
    def _check_row_version(asset, expected):
        if asset.row_version != expected: raise StaleAssetVersion()

    @staticmethod
    def _norm_tags(tags):
        s = set(); r = []
        for t in tags:
            n = t.strip().lower()
            if n and n not in s: s.add(n); r.append(n)
        return r

    @staticmethod
    def _pub_val(asset):
        p = asset.publication_status; return p.value if hasattr(p, "value") else p

    @staticmethod
    def _snap_val(asset):
        s = asset.snapshot_state; return s.value if hasattr(s, "value") else s

    @staticmethod
    def _is_target_unique_violation(exc):
        orig = getattr(exc, "orig", None)
        if orig is None: return False
        diag = getattr(orig, "diag", None)
        if diag is not None:
            cn = getattr(diag, "constraint_name", None)
            if cn and cn.lower() == _SOURCE_UNIQUE_CONSTRAINT.lower():
                return True
        return _SOURCE_UNIQUE_CONSTRAINT.lower() in str(orig).lower()

    # ── DSL ───────────────────────────────────────────────────────────

    @staticmethod
    def _check_dsl_version(version_str):
        if not version_str or not isinstance(version_str, str):
            raise MarketplaceError("Invalid DSL version")
        status = check_version_compatibility(version_str, CURRENT_APP_DSL_VERSION)
        if status == ImportStatus.FAILED: raise MarketplaceError("DSL version not compatible")
        if status == ImportStatus.PENDING: raise MarketplaceError("DSL version pending")
        return version_str

    # ── Sanitizer ─────────────────────────────────────────────────────

    def _validate_dsl_no_secrets(self, data):
        app_data = data.get("app")
        if isinstance(app_data, dict):
            it = app_data.get("icon_type")
            if isinstance(it, str) and it.lower() == "link":
                raise NonportableResourceReference()
        self._walk_dsl(data)

    def _walk_dsl(self, node):
        if isinstance(node, dict):
            vt = node.get("value_type", "")
            if isinstance(vt, str) and vt.lower() == "secret":
                v = node.get("value", "")
                if v: raise SnapshotContainsSecret()
            for key, value in node.items():
                kl = key.lower()
                self._check_credential_key(kl, value)
                self._check_owner_bound_key(kl, value)
                if kl in _REQUIRED_EMPTY_KEYS:
                    if value is not None and value != "":
                        raise NonportableResourceReference()
                self._walk_dsl(value)
        elif isinstance(node, list):
            for item in node: self._walk_dsl(item)

    def _check_credential_key(self, kl, value):
        for p in _FORBIDDEN_KEY_PATTERNS:
            if p in kl:
                if isinstance(value, (str, int, float, bool)) and bool(value) is not False:
                    raise SnapshotContainsSecret()
                if isinstance(value, (list, dict)) and value:
                    raise SnapshotContainsSecret()
                return

    def _check_owner_bound_key(self, kl, value):
        for p in _OWNER_BOUND_KEY_PATTERNS:
            if p in kl:
                if isinstance(value, (str, list, dict, int)) and \
                   (isinstance(value, (str, int)) and value) or \
                   (isinstance(value, (list, dict)) and value):
                    raise NonportableResourceReference()
                return

    # ── Dependencies ──────────────────────────────────────────────────

    @staticmethod
    def _extract_and_normalize_dependencies(data):
        rd = data.get("dependencies")
        if rd is None: return []
        if not isinstance(rd, list): raise MarketplaceError("Dependencies must be a list")
        valid = []
        for d in rd:
            if not isinstance(d, dict): raise MarketplaceError("Each dep must be a dict")
            pd = PluginDependency.model_validate(d)
            if pd.type == PluginDependencyType.Package: raise PrivatePluginDependency()
            valid.append(pd)
        seen = set(); result = []
        for pd in sorted(valid, key=lambda x: json.dumps(x.model_dump(mode="json"), sort_keys=True)):
            k = json.dumps(pd.model_dump(mode="json"), sort_keys=True)
            if k not in seen: seen.add(k); result.append(pd.model_dump(mode="json"))
        return result

    @staticmethod
    def _parse_deps(deps_data):
        result = []
        for d in deps_data:
            if not isinstance(d, dict): raise SnapshotIntegrityError()
            try:
                result.append(PluginDependency.model_validate(d))
            except PydanticValidationError as exc:
                raise SnapshotIntegrityError() from exc
        return result

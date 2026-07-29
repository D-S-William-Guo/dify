"""CLI tests for marketplace-snapshots command."""

from __future__ import annotations

import importlib
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from models.model import (
    EnterpriseMarketplaceAsset,
    EnterpriseMarketplaceAssetPublicationStatus,
    EnterpriseMarketplaceAssetSnapshotState,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cmd():
    mod = importlib.import_module("commands.data_migrate")
    return mod.marketplace_snapshots


def _asset(**kw):
    a = EnterpriseMarketplaceAsset(
        source_tenant_id=kw.pop("source_tenant_id", str(uuid.uuid4())),
        source_app_id=kw.pop("source_app_id", str(uuid.uuid4())),
        submitter_account_id=kw.pop("submitter_account_id", str(uuid.uuid4())),
        title=kw.pop("title", "Test"))
    a.id = kw.pop("id", str(uuid.uuid4()))
    a.status = kw.pop("status", "approved")
    a.publication_status = kw.pop(
        "publication_status", EnterpriseMarketplaceAssetPublicationStatus.UNPUBLISHED)
    a.snapshot_state = kw.pop(
        "snapshot_state", EnterpriseMarketplaceAssetSnapshotState.BACKFILL_PENDING)
    a.description = kw.pop("description", "")
    a.category = kw.pop("category", "General")
    a.tags = kw.pop("tags", [])
    a.scenario = kw.pop("scenario", "")
    a.allow_show_workspace_name = kw.pop("allow_show_workspace_name", False)
    a.row_version = kw.pop("row_version", 0)
    a.next_snapshot_version = kw.pop("next_snapshot_version", 1)
    a.published_snapshot_id = kw.pop("published_snapshot_id", None)
    a.reviewer_account_id = kw.pop("reviewer_account_id", None)
    a.snapshot_error_code = kw.pop("snapshot_error_code", None)
    return a


class TestCLI:
    def _mock_db(self):
        return MagicMock(engine=MagicMock())

    def _patch_all(self, **overrides):
        mock_instance = MagicMock()
        mock_instance.list_all_asset_ids.return_value = overrides.get("list_all_asset_ids", [])
        mock_instance.count_by_state.return_value = overrides.get("count_by_state", {})
        mock_instance.count_by_status.return_value = overrides.get("count_by_status", {})

        mock_bf = MagicMock()
        mock_bf.return_value = MagicMock(
            asset_id="a1", dry_run=overrides.get("dry_run", True),
            old_snapshot_state=overrides.get("old_state", "backfill_pending"),
            new_snapshot_state=overrides.get("new_state", "ready"),
            old_row_version=0, new_row_version=overrides.get("new_rv", 0),
            legacy_status="approved",
            result_code=overrides.get("result_code", "dry_run_ok"),
            hash_fingerprint="abc123def456")
        mock_instance.backfill_legacy_snapshot = mock_bf

        mock_svc = MagicMock()
        mock_svc.return_value = mock_instance
        return mock_svc, mock_bf

    def _make_asset_ctx(self, sess, asset_id="a1"):
        a = _asset(id=asset_id, source_app_id="SA1", source_tenant_id="ST1", row_version=0,
                   snapshot_state=EnterpriseMarketplaceAssetSnapshotState.BACKFILL_PENDING)
        sess.get.return_value = a
        return a, sess

    def test_full_inventory(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all(
            list_all_asset_ids=["a1", "a2"],
            count_by_state={"backfill_pending": 2},
            count_by_status={"approved": 2})

        inv_sess = MagicMock()
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "a1")

        sessions = iter([inv_sess, asset_sess, asset_sess])

        def sess_factory(*a, **kw):
            return MagicMock(__enter__=MagicMock(return_value=next(sessions)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_factory), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, [])
        assert result.exit_code == 0
        assert "a1" in result.stdout

    def test_dry_run_no_commit(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        inv_sess = MagicMock()
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "a1")

        def sess_factory(*a, **kw):
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if sess_factory.count == 0 else asset_sess)))
        sess_factory.count = 0

        def sess_wrapper(*a, **kw):
            val = sess_factory(*a, **kw)
            sess_factory.count += 1
            return val

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--asset-id", "a1"])
        assert result.exit_code == 0
        asset_sess.commit.assert_not_called()

    def test_apply_commits(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all(dry_run=False, result_code="ok",
                                             new_rv=1)
        inv_sess = MagicMock()
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "a1")
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--asset-id", "a1", "--apply"])
        assert result.exit_code == 0
        asset_sess.commit.assert_called_once()

    def test_id_file(self, runner, cmd, tmp_path):
        id_file = tmp_path / "ids.txt"
        id_file.write_text("id-1\nid-2\n")
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        inv_sess = MagicMock()
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "id-1")
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--id-file", str(id_file)])
        assert result.exit_code == 0

    def test_not_found_in_output(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        inv_sess = MagicMock()
        inv_sess.execute.return_value.fetchall.return_value = []
        asset_sess = MagicMock()
        asset_sess.get.return_value = None  # not found
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--asset-id", "nf-1"])
        assert "not_found" in result.stdout

    def test_output_0600(self, runner, cmd, tmp_path):
        out = tmp_path / "out.jsonl"
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        sess = MagicMock()

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session",
                   return_value=MagicMock(__enter__=MagicMock(return_value=sess))), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--output", str(out)])
        assert result.exit_code == 0
        assert (out.stat().st_mode & 0o777) == 0o600

    def test_manifest_sha256(self, runner, cmd, tmp_path):
        out = tmp_path / "out.jsonl"
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        sess = MagicMock()

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session",
                   return_value=MagicMock(__enter__=MagicMock(return_value=sess))), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--output", str(out)])
        assert "Manifest SHA-256" in result.stderr

    def test_jsonl_no_secrets(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        inv_sess = MagicMock()
        inv_sess.execute.return_value.fetchall.return_value = []
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "a1")
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--asset-id", "a1"])
        for line in result.stdout.strip().split("\n"):
            data = json.loads(line)
            assert "dsl_content" not in data

    def test_retry_manifest(self, runner, cmd, tmp_path):
        mf = tmp_path / "prev.jsonl"
        mf.write_text(
            json.dumps({"asset_id": "r1", "result_code": "error"}) + "\n" +
            json.dumps({"asset_id": "r2", "result_code": "ok"}) + "\n" +
            json.dumps({"total": 2}) + "\n")
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all()
        inv_sess = MagicMock()
        inv_sess.execute.return_value.fetchall.return_value = []
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "r1")
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        assert result.exit_code == 0
        assert "r1" in result.stdout

    def test_retry_malformed_fail_closed(self, runner, cmd, tmp_path):
        mf = tmp_path / "bad.jsonl"
        mf.write_text("not json")
        mock_db = self._mock_db()
        with patch("commands.data_migrate.db", mock_db):
            result = runner.invoke(cmd, ["--retry-manifest", str(mf)])
        assert result.exit_code != 0

    def test_summary_has_inventory(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc, mock_bf = self._patch_all(
            count_by_state={"backfill_pending": 3},
            count_by_status={"approved": 3})
        inv_sess = MagicMock()
        inv_sess.execute.return_value.fetchall.return_value = []
        asset_sess = MagicMock()
        self._make_asset_ctx(asset_sess, "a1")
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd, ["--asset-id", "a1"])
        lines = result.stdout.strip().split("\n")
        summary = json.loads(lines[-1])
        assert "inventory_status_counts" in summary
        assert "inventory_state_counts" in summary

    def test_error_threshold(self, runner, cmd):
        mock_db = self._mock_db()
        mock_svc = MagicMock()
        mock_inst = MagicMock()
        mock_inst.backfill_legacy_snapshot.side_effect = Exception("fail")
        mock_inst.list_all_asset_ids.return_value = []
        mock_inst.count_by_state.return_value = {}
        mock_inst.count_by_status.return_value = {}
        mock_svc.return_value = mock_inst

        inv_sess = MagicMock()
        inv_sess.execute.return_value.fetchall.return_value = []
        asset_sess = MagicMock()
        asset_sess.get.return_value = _asset(id="e1", row_version=0)
        call_count = [0]

        def sess_wrapper(*a, **kw):
            call_count[0] += 1
            return MagicMock(__enter__=MagicMock(return_value=(
                inv_sess if call_count[0] == 1 else asset_sess)))

        with patch("commands.data_migrate.db", mock_db), \
             patch("commands.data_migrate.Session", side_effect=sess_wrapper), \
             patch("commands.data_migrate.EnterpriseMarketplaceService", mock_svc):
            result = runner.invoke(cmd,
                                   ["--asset-id", "e1", "--asset-id", "e2",
                                    "--error-threshold", "1"])
        assert result.exit_code == 0
        assert "Error threshold" in result.stderr

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

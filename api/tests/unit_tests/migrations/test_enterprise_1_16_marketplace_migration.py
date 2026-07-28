"""Focused migration tests for B4-A enterprise marketplace migration.

Validates revision identity, Alembic graph, migration AST (DDL, server
defaults, no legacy status CHECK), unknown legacy status via in-memory
SQLite execution, downgrade data protection, and clean imports.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from types import ModuleType

from unittest import mock

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

B416E = "b416e5c4e702"
A71E = "a71e16c0de01"
C8F3 = "c8f3d9d4a1be"
F1A1 = "f1a14e1e9b41"
E2F0 = "e2f0a9b7c6d5"

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
MIGRATION_FILE = MIGRATIONS_DIR / "versions" / (
    f"2026_07_21_1400-{B416E}_finalize_enterprise_marketplace_schema.py"
)


def _make_script_directory() -> ScriptDirectory:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return ScriptDirectory.from_config(cfg)


def _parents(sd: ScriptDirectory, rev: str) -> tuple[str, ...]:
    r = sd.get_revision(rev)
    assert r is not None
    d = r.down_revision
    if d is None:
        return ()
    if isinstance(d, str):
        return (d,)
    return tuple(d)


def _load_migration_module(rev: str) -> ModuleType:
    if rev == B416E:
        path = MIGRATION_FILE
    else:
        sd = _make_script_directory()
        script = sd.get_revision(rev)
        assert script is not None
        path = Path(script.path)
    spec = importlib.util.spec_from_file_location(f"migration_{rev}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _migration_source() -> str:
    return MIGRATION_FILE.read_text()


def _upgrade_ast() -> ast.Module:
    return ast.parse(_upgrade_source())


def _upgrade_source() -> str:
    tree = ast.parse(_migration_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            return ast.unparse(node)
    return ""


def _downgrade_source() -> str:
    tree = ast.parse(_migration_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            return ast.unparse(node)
    return ""


class TestRevisionIdentity:
    def test_revision_value(self) -> None:
        module = _load_migration_module(B416E)
        assert module.revision == B416E

    def test_down_revision_value(self) -> None:
        module = _load_migration_module(B416E)
        assert module.down_revision == A71E

    def test_branch_labels_none(self) -> None:
        module = _load_migration_module(B416E)
        assert module.branch_labels is None

    def test_depends_on_none(self) -> None:
        module = _load_migration_module(B416E)
        assert module.depends_on is None


class TestAlembicGraph:
    def test_unique_head_is_b416e5c4e702(self) -> None:
        sd = _make_script_directory()
        assert sd.get_heads() == [B416E]

    def test_head_parent_is_a71e16c0de01(self) -> None:
        sd = _make_script_directory()
        assert _parents(sd, B416E) == (A71E,)


class TestB2MigrationsUnchanged:
    def test_c8f3_exists(self) -> None:
        assert _make_script_directory().get_revision(C8F3) is not None

    def test_f1a1_exists(self) -> None:
        assert _make_script_directory().get_revision(F1A1) is not None

    def test_e2f0_exists(self) -> None:
        assert _make_script_directory().get_revision(E2F0) is not None

    def test_a71e_exists(self) -> None:
        assert _make_script_directory().get_revision(A71E) is not None

    def test_b2_merge_upgrade_is_pass_only(self) -> None:
        src = ast.unparse(ast.parse(Path(
            _make_script_directory().get_revision(A71E).path  # type: ignore[union-attr]
        ).read_text()))
        for fn_name in ("upgrade", "downgrade"):
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                    stmts = [s for s in node.body if not isinstance(s, ast.Expr)]
                    assert len(stmts) == 1, f"{fn_name} has >1 non-docstring stmt"
                    assert isinstance(stmts[0], ast.Pass), f"{fn_name} body not just pass"


class TestMigrationServerDefaults:
    """Execute upgrade() with mocked alembic op to capture add_column Column objects
    and assert exact server_default values."""

    @pytest.fixture()
    def captured_columns(self) -> dict[str, sa.Column]:
        module = _load_migration_module(B416E)
        columns: dict[str, sa.Column] = {}

        def record_add_column(table_name: str, column: sa.Column, **kw) -> None:
            columns[column.name] = column

        with mock.patch.object(module, "op") as fake_op:
            fake_op.add_column.side_effect = record_add_column
            fake_op.create_table = mock.Mock()
            fake_op.create_index = mock.Mock()
            fake_op.execute = mock.Mock()
            fake_bind = mock.Mock()
            fake_bind.scalar.return_value = 0
            fake_op.get_bind.return_value = fake_bind
            fake_op.alter_column = mock.Mock()
            fake_op.create_check_constraint = mock.Mock()
            module.upgrade()

        return columns

    def test_publication_status_server_default(self, captured_columns) -> None:
        col = captured_columns["publication_status"]
        assert col.server_default is not None
        assert col.server_default.arg.text == "'unpublished'"

    def test_next_snapshot_version_server_default(self, captured_columns) -> None:
        col = captured_columns["next_snapshot_version"]
        assert col.server_default is not None
        assert col.server_default.arg.text == "1"

    def test_row_version_server_default(self, captured_columns) -> None:
        col = captured_columns["row_version"]
        assert col.server_default is not None
        assert col.server_default.arg.text == "0"

    def test_snapshot_state_server_default(self, captured_columns) -> None:
        col = captured_columns["snapshot_state"]
        assert col.server_default is not None
        assert col.server_default.arg.text == "'none'"

    def test_published_snapshot_id_no_server_default(self, captured_columns) -> None:
        col = captured_columns["published_snapshot_id"]
        assert col.server_default is None

    def test_snapshot_error_code_no_server_default(self, captured_columns) -> None:
        col = captured_columns["snapshot_error_code"]
        assert col.server_default is None


class TestMigrationUpgradeAST:
    def test_migration_file_exists(self) -> None:
        assert MIGRATION_FILE.exists()

    def test_creates_snapshot_table(self) -> None:
        assert "enterprise_marketplace_asset_snapshots" in _upgrade_source()

    def test_adds_all_six_b4_columns(self) -> None:
        src = _upgrade_source()
        for col in ("publication_status", "published_snapshot_id",
                     "next_snapshot_version", "row_version",
                     "snapshot_state", "snapshot_error_code"):
            assert col in src, f"missing {col} add_column"

    def test_initializes_with_case(self) -> None:
        src = _migration_source()
        assert "CASE" in src.upper()

    def test_no_import_service_or_network(self) -> None:
        tree = ast.parse(_migration_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for fb in ("services", "redis", "network", "httpx", "requests", "plugin"):
                    assert fb not in mod.lower(), f"forbidden import: {mod}"
            elif isinstance(node, ast.Import):
                names = ", ".join(a.name for a in node.names)
                for fb in ("redis", "requests", "httpx"):
                    assert fb not in names.lower()

    def test_no_python_row_iteration_in_upgrade(self) -> None:
        tree = _upgrade_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                pytest.fail("upgrade must not iterate rows in Python")

    def test_content_sha256_varchar_not_char(self) -> None:
        src = _upgrade_source()
        for m in re.finditer(r'content_sha256.*?\),', src, re.DOTALL):
            ctx = m.group()
            if re.search(r'\bCHAR\s*\(\s*64\s*\)', ctx) and "VARCHAR" not in ctx:
                pytest.fail(f"content_sha256 uses CHAR: {ctx.strip()}")

    def test_content_sha256_length_64(self) -> None:
        src = _upgrade_source()
        assert "VARCHAR(length=64)" in src or "VARCHAR(64)" in src or (
            "content_sha256" in src and "VARCHAR" in src
        )

    def test_no_legacy_status_check(self) -> None:
        tree = _upgrade_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, "attr") and node.func.attr == "create_check_constraint":
                    call_src = ast.unparse(node)
                    if (
                        "status" in call_src
                        and "publication_status" not in call_src
                        and "snapshot_state" not in call_src
                    ):
                        pytest.fail(f"legacy status CHECK: {call_src}")

    def test_next_snapshot_version_in_source(self) -> None:
        assert "next_snapshot_version" in _upgrade_source()

    def test_row_version_in_source(self) -> None:
        assert "row_version" in _upgrade_source()

    def test_case_module_constant_used(self) -> None:
        src = _migration_source()
        assert "_ASSET_INIT_SQL" in src, "CASE SQL must be module constant"
        assert "op.execute" in _upgrade_source()


class TestDowngradeAST:
    def test_data_protection_present(self) -> None:
        src = _downgrade_source()
        assert "enterprise_marketplace_asset_snapshots" in src
        assert "published_snapshot_id" in src

    def test_drops_indexes_and_columns(self) -> None:
        src = _downgrade_source()
        assert "drop" in src.lower()

    def test_guard_against_data_loss(self) -> None:
        src = _downgrade_source()
        assert "raise" in src or "RuntimeError" in src


class TestUpgradeNoStamp:
    def test_upgrade_no_stamp(self) -> None:
        assert "stamp" not in _upgrade_source().lower()

    def test_downgrade_no_stamp(self) -> None:
        assert "stamp" not in _downgrade_source().lower()

    def test_no_business_service_imports(self) -> None:
        tree = ast.parse(_migration_source())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                name = ""
                if isinstance(node, ast.ImportFrom):
                    name = node.module or ""
                else:
                    name = ", ".join(a.name for a in node.names)
                banned = ("service", "controller", "app_dsl", "export",
                          "import_app", "workflow_service", "dependencies_analysis")
                for b in banned:
                    assert b not in name.lower(), f"imports business module: {name}"


class TestKnownStatusMapping:
    def test_approved_unpublished_backfill_pending(self) -> None:
        assert "approved" in _migration_source()

    def test_unlisted_in_source(self) -> None:
        assert "unlisted" in _migration_source()

    def test_pending_in_source(self) -> None:
        assert "pending" in _migration_source()

    def test_rejected_in_source(self) -> None:
        assert "rejected" in _migration_source()


class TestUnknownLegacyStatusInMemory:
    """Execute the actual migration _ASSET_INIT_SQL against SQLite to prove
    unknown status handling without connecting to a real PostgreSQL database."""

    @pytest.fixture(scope="class")
    def asset_init_sql(self) -> str:
        module = _load_migration_module(B416E)
        return module._ASSET_INIT_SQL

    @pytest.fixture()
    def engine(self):
        e = sa.create_engine("sqlite:///:memory:")
        # Create minimal enterprise_marketplace_assets table with B4 columns
        with e.begin() as conn:
            conn.execute(sa.text("""
                CREATE TABLE enterprise_marketplace_assets (
                    id TEXT PRIMARY KEY,
                    source_tenant_id TEXT NOT NULL,
                    source_app_id TEXT NOT NULL,
                    submitter_account_id TEXT NOT NULL,
                    reviewer_account_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'General',
                    tags TEXT NOT NULL DEFAULT '[]',
                    scenario TEXT NOT NULL DEFAULT '',
                    allow_show_workspace_name INTEGER NOT NULL DEFAULT 0,
                    review_note TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    reviewed_at TEXT,
                    publication_status TEXT,
                    published_snapshot_id TEXT,
                    next_snapshot_version INTEGER,
                    row_version INTEGER,
                    snapshot_state TEXT,
                    snapshot_error_code TEXT
                )
            """))
        return e

    def _insert_fixture(self, conn, asset_id: str, status: str,
                        source_app_id: str = "app-1",
                        source_tenant_id: str = "tenant-1",
                        created_at: str = "2024-01-01T00:00:00",
                        updated_at: str = "2024-06-01T00:00:00",
                        reviewed_at: str | None = "2024-06-15T00:00:00") -> None:
        conn.execute(
            sa.text("""
                INSERT INTO enterprise_marketplace_assets
                    (id, source_tenant_id, source_app_id, submitter_account_id,
                     status, title, tags, created_at, updated_at, reviewed_at)
                VALUES
                    (:id, :source_tenant_id, :source_app_id, 'acct-1',
                     :status, 'Test Asset', '[]',
                     :created_at, :updated_at, :reviewed_at)
            """),
            {
                "id": asset_id, "source_tenant_id": source_tenant_id,
                "source_app_id": source_app_id, "status": status,
                "created_at": created_at, "updated_at": updated_at,
                "reviewed_at": reviewed_at,
            },
        )

    def test_unknown_status_preserved_and_mapped(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            self._insert_fixture(conn, "asset-unknown", "ancient_status",
                                 created_at="2024-01-01T00:00:00",
                                 updated_at="2024-06-01T00:00:00",
                                 reviewed_at="2024-06-15T00:00:00")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT * FROM enterprise_marketplace_assets WHERE id = 'asset-unknown'")
            ).mappings().one()

        assert row["status"] == "ancient_status"
        assert row["publication_status"] == "unpublished"
        assert row["snapshot_state"] == "failed"
        assert row["snapshot_error_code"] == "legacy_status_unknown"
        assert row["published_snapshot_id"] is None
        assert row["next_snapshot_version"] == 1
        assert row["row_version"] == 0
        assert row["source_app_id"] == "app-1"
        assert row["source_tenant_id"] == "tenant-1"
        assert row["created_at"] == "2024-01-01T00:00:00"
        assert row["updated_at"] == "2024-06-01T00:00:00"
        assert row["reviewed_at"] == "2024-06-15T00:00:00"

    def test_known_approved(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            self._insert_fixture(conn, "asset-approved", "approved")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT * FROM enterprise_marketplace_assets WHERE id = 'asset-approved'")
            ).mappings().one()

        assert row["status"] == "approved"
        assert row["publication_status"] == "unpublished"
        assert row["snapshot_state"] == "backfill_pending"
        assert row["snapshot_error_code"] is None

    def test_known_unlisted(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            self._insert_fixture(conn, "asset-unlisted", "unlisted")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT * FROM enterprise_marketplace_assets WHERE id = 'asset-unlisted'")
            ).mappings().one()

        assert row["status"] == "unlisted"
        assert row["publication_status"] == "unlisted"
        assert row["snapshot_state"] == "none"

    def test_known_pending(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            self._insert_fixture(conn, "asset-pending", "pending")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT * FROM enterprise_marketplace_assets WHERE id = 'asset-pending'")
            ).mappings().one()

        assert row["status"] == "pending"
        assert row["publication_status"] == "unpublished"
        assert row["snapshot_state"] == "none"

    def test_known_rejected(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            self._insert_fixture(conn, "asset-rejected", "rejected")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            row = conn.execute(
                sa.text("SELECT * FROM enterprise_marketplace_assets WHERE id = 'asset-rejected'")
            ).mappings().one()

        assert row["status"] == "rejected"
        assert row["publication_status"] == "unpublished"
        assert row["snapshot_state"] == "none"

    def test_row_count_unchanged(self, engine, asset_init_sql) -> None:
        with engine.begin() as conn:
            for i in range(3):
                self._insert_fixture(conn, f"asset-{i}", "pending")
            self._insert_fixture(conn, "asset-u", "ancient")

        with engine.begin() as conn:
            conn.execute(sa.text(asset_init_sql))

        with engine.begin() as conn:
            count = conn.execute(
                sa.text("SELECT COUNT(1) FROM enterprise_marketplace_assets")
            ).scalar()

        assert count == 4

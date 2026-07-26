"""Migration graph tests for the enterprise 1.16.0 replay (B2).

These tests verify the Alembic migration graph topology produced by B2:

- The three restored historical enterprise revisions (``c8f3d9d4a1be``,
  ``f1a14e1e9b41``, ``e2f0a9b7c6d5``) are parseable by Alembic's
  ``ScriptDirectory``.
- The parent relationships of the enterprise merge chain are correct.
- The new empty merge ``a71e16c0de01`` connects the old enterprise head
  ``e2f0a9b7c6d5`` with the official 1.16 head ``7a1c2d9e4b60``.
- The B2 graph has exactly one head: ``a71e16c0de01``.
- The empty merge's ``upgrade()``/``downgrade()`` perform no operations.
- The old enterprise head, the official 1.16 head and the historical
  enterprise start points all converge to the new head.

The tests use Alembic's real ``ScriptDirectory`` graph resolution so that
the assertions reflect how Alembic itself resolves the migration graph, not
fragile string matching against file contents.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

C8F3 = "c8f3d9d4a1be"
F1A1 = "f1a14e1e9b41"
E2F0 = "e2f0a9b7c6d5"
A71E = "a71e16c0de01"
OFFICIAL_116_HEAD = "7a1c2d9e4b60"
OFFICIAL_115_HEAD = "d9e8f7a6b5c4"
RECOMMENDED_APP_CATEGORIES = "a4f2d8c9b731"
WORKFLOW_COMMENTS = "227822d22895"

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def _make_script_directory() -> ScriptDirectory:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return ScriptDirectory.from_config(cfg)


def _parents(script_directory: ScriptDirectory, revision_id: str) -> tuple[str, ...]:
    revision = script_directory.get_revision(revision_id)
    assert revision is not None, f"revision {revision_id} not found in graph"
    down = revision.down_revision
    if down is None:
        return ()
    if isinstance(down, str):
        return (down,)
    return tuple(down)


def _ancestry(script_directory: ScriptDirectory, revision_id: str) -> set[str]:
    seen: set[str] = set()
    pending: list[str] = [revision_id]
    while pending:
        current = pending.pop()
        for parent in _parents(script_directory, current):
            if parent not in seen:
                seen.add(parent)
                pending.append(parent)
    return seen


def _load_migration_module(script_directory: ScriptDirectory, revision_id: str) -> ModuleType:
    script = script_directory.get_revision(revision_id)
    assert script is not None, f"revision {revision_id} not found in graph"
    path = Path(script.path)
    spec = importlib.util.spec_from_file_location(f"migration_{revision_id}", path)
    assert spec is not None and spec.loader is not None, f"cannot load module for {revision_id}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_directory() -> ScriptDirectory:
    return _make_script_directory()


class TestHistoricalRevisionsParseable:
    def test_c8f3d9d4a1be_is_parseable(self, script_directory: ScriptDirectory) -> None:
        assert script_directory.get_revision(C8F3) is not None

    def test_f1a14e1e9b41_is_parseable(self, script_directory: ScriptDirectory) -> None:
        assert script_directory.get_revision(F1A1) is not None

    def test_e2f0a9b7c6d5_is_parseable(self, script_directory: ScriptDirectory) -> None:
        assert script_directory.get_revision(E2F0) is not None


class TestEnterpriseMergeChainParents:
    def test_c8f3d9d4a1be_is_parent_of_f1a14e1e9b41(self, script_directory: ScriptDirectory) -> None:
        assert C8F3 in _parents(script_directory, F1A1)

    def test_f1a14e1e9b41_is_parent_of_e2f0a9b7c6d5(self, script_directory: ScriptDirectory) -> None:
        assert F1A1 in _parents(script_directory, E2F0)


class TestNewMergeParents:
    def test_a71e16c0de01_parents_are_exactly_e2f0_and_official_head(
        self, script_directory: ScriptDirectory
    ) -> None:
        assert set(_parents(script_directory, A71E)) == {E2F0, OFFICIAL_116_HEAD}


class TestSingleHead:
    def test_graph_has_exactly_one_head_and_it_is_a71e16c0de01(
        self, script_directory: ScriptDirectory
    ) -> None:
        heads = script_directory.get_heads()
        assert heads == [A71E]


class TestEmptyMergeIsNoop:
    @pytest.fixture()
    def merge_module(self, script_directory: ScriptDirectory) -> ModuleType:
        return _load_migration_module(script_directory, A71E)

    def test_upgrade_calls_no_alembic_operations(self, merge_module: ModuleType) -> None:
        with mock.patch.object(merge_module, "op", create=True) as fake_op:
            merge_module.upgrade()
        assert fake_op.mock_calls == []

    def test_downgrade_calls_no_alembic_operations(self, merge_module: ModuleType) -> None:
        with mock.patch.object(merge_module, "op", create=True) as fake_op:
            merge_module.downgrade()
        assert fake_op.mock_calls == []

    def test_merge_module_has_no_schema_modifying_imports(self, merge_module: ModuleType) -> None:
        assert not hasattr(merge_module, "sa")
        assert not hasattr(merge_module, "op")


class TestGraphConvergence:
    def test_old_enterprise_head_converges_to_new_head(
        self, script_directory: ScriptDirectory
    ) -> None:
        assert E2F0 in _ancestry(script_directory, A71E)

    def test_official_116_head_converges_to_new_head(
        self, script_directory: ScriptDirectory
    ) -> None:
        assert OFFICIAL_116_HEAD in _ancestry(script_directory, A71E)

    def test_enterprise_marketplace_start_converges_to_new_head(
        self, script_directory: ScriptDirectory
    ) -> None:
        assert C8F3 in _ancestry(script_directory, A71E)

    def test_enterprise_chain_ancestry_is_complete(
        self, script_directory: ScriptDirectory
    ) -> None:
        ancestry = _ancestry(script_directory, A71E)
        for revision in (
            E2F0,
            F1A1,
            OFFICIAL_115_HEAD,
            C8F3,
            RECOMMENDED_APP_CATEGORIES,
            WORKFLOW_COMMENTS,
        ):
            assert revision in ancestry, f"{revision} missing from a71e16c0de01 ancestry"

    def test_official_116_head_has_official_parent_chain(
        self, script_directory: ScriptDirectory
    ) -> None:
        ancestry = _ancestry(script_directory, OFFICIAL_116_HEAD)
        assert ancestry, "official 1.16 head should have ancestor revisions"

    def test_both_branches_reachable_from_new_head_via_distinct_parents(
        self, script_directory: ScriptDirectory
    ) -> None:
        parents = _parents(script_directory, A71E)
        assert E2F0 in parents
        assert OFFICIAL_116_HEAD in parents
        enterprise_ancestry = _ancestry(script_directory, E2F0)
        official_ancestry = _ancestry(script_directory, OFFICIAL_116_HEAD)
        assert E2F0 not in official_ancestry, "old enterprise head must not be an ancestor of official 1.16 head"
        assert OFFICIAL_116_HEAD not in enterprise_ancestry, "official 1.16 head must not be an ancestor of old enterprise head"

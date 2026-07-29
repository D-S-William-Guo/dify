import hashlib
import io
import json
import logging
import os
import sys
import uuid
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any, cast

import click
from sqlalchemy.orm import Session

from commands.rbac import migrate_dataset_permissions_to_rbac
from extensions.ext_database import db
from graphon.model_runtime.entities.model_entities import ModelType
from models.model import EnterpriseMarketplaceAsset
from services.enterprise_marketplace_service import EnterpriseMarketplaceService
from services.legacy_model_type_migration import (
    VALID_TABLE_NAMES,
    LegacyModelTypeMigrationService,
    load_tenant_ids_from_file,
)

_SUPPORTED_MODEL_TYPE_CHOICES = (
    ModelType.LLM.value,
    ModelType.TEXT_EMBEDDING.value,
    ModelType.RERANK.value,
)
_DEFAULT_CONCURRENCY = os.cpu_count() or 1


def _normalize_multi_value_option(
    values: tuple[str, ...],
    *,
    valid_values: tuple[str, ...],
    option_name: str,
) -> tuple[str, ...]:
    normalized_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        for item in value.split(","):
            normalized_item = item.strip()
            if not normalized_item:
                continue
            if normalized_item not in valid_values:
                raise click.BadParameter(
                    f"invalid value '{normalized_item}'. valid values: {', '.join(valid_values)}",
                    param_hint=option_name,
                )
            if normalized_item in seen_values:
                continue
            seen_values.add(normalized_item)
            normalized_values.append(normalized_item)

    return tuple(normalized_values)


@click.group(
    "data-migrate",
    help="Online data migration commands.",
)
def data_migrate() -> None:
    """Namespace for production data migration commands."""


@click.command(
    "legacy-model-types",
    help=(
        "Migrate legacy provider model_type values to canonical values. "
        "Default is dry-run and emits JSON lines only. "
        "If --tables includes provider_model_credentials, the command may also update "
        "provider_models and load_balancing_model_configs references so merged credentials stay reachable."
    ),
)
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Apply the migration. Default is dry-run.",
)
@click.option(
    "--tables",
    "tables",
    multiple=True,
    type=str,
    help=(
        "Limit migration to specific tables. Accepts comma-separated values or repeated flags.\n"
        "\n"
        "Options: load_balancing_model_configs, provider_model_credentials, "
        "provider_model_settings, provider_models, tenant_default_models.\n\n"
        "When provider_model_credentials is selected, provider_models and "
        "load_balancing_model_configs may also be updated for credential reference rewrites.\n"
        "\n"
        "If unspecified, all relevant tables are migrated."
    ),
)
@click.option(
    "--model-types",
    "model_types",
    multiple=True,
    type=str,
    help=(
        "Canonical model types to migrate. Accepts comma-separated values or repeated flags.\n"
        "\n"
        "Options: llm,text-embedding,rerank\n"
        "\n"
        "If unspecified, all relevant legacy model types are migrated."
    ),
)
@click.option(
    "--tenant-id-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help="Optional file containing tenant ids, one per line.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    help=(
        "Optional file path for JSON lines event logs. Defaults to stdout.\n"
        "It's highly recommended to save the event logs to a file and preserve it for a period of time."
    ),
)
@click.option(
    "--concurrency",
    type=click.IntRange(min=1),
    default=_DEFAULT_CONCURRENCY,
    show_default=True,
    help="Number of tenant-level worker threads to run in parallel.",
)
def legacy_model_types(
    apply: bool,
    tables: tuple[str, ...],
    model_types: tuple[str, ...],
    tenant_id_file: str | None,
    output: Path | None,
    concurrency: int = _DEFAULT_CONCURRENCY,
) -> None:
    """
    Migrate legacy provider-related model_type values and emit JSON lines events.
    """

    normalized_tables = _normalize_multi_value_option(
        tables,
        valid_values=VALID_TABLE_NAMES,
        option_name="--tables",
    )
    normalized_model_types = _normalize_multi_value_option(
        model_types,
        valid_values=_SUPPORTED_MODEL_TYPE_CHOICES,
        option_name="--model-types",
    )
    selected_model_types = (
        tuple(ModelType(model_type) for model_type in normalized_model_types)
        if normalized_model_types
        else (
            ModelType.LLM,
            ModelType.TEXT_EMBEDDING,
            ModelType.RERANK,
        )
    )
    tenant_ids = load_tenant_ids_from_file(tenant_id_file) if tenant_id_file else None

    output_context: AbstractContextManager[io.TextIOBase]
    if output is None:
        output_context = nullcontext(cast(io.TextIOBase, sys.stdout))
    else:
        try:
            output_context = output.open("w", encoding="utf-8")
        except OSError as exc:
            raise click.ClickException(f"failed to open output file '{output}': {exc.strerror or exc}") from exc

    with output_context as output_stream:
        LegacyModelTypeMigrationService(
            engine=db.engine,
            apply=apply,
            concurrency=concurrency,
            output=cast(io.TextIOBase, output_stream),
            tables=normalized_tables or None,
            model_types=selected_model_types,
            tenant_ids=tenant_ids,
        ).migrate()


@click.command(
    "marketplace-snapshots",
    help=(
        "Backfill legacy enterprise marketplace asset snapshots. "
        "Default is dry-run and emits JSON lines only. "
        "Use --apply to write to the database."
    ),
)
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Apply the backfill. Default is dry-run.",
)
@click.option(
    "--asset-id",
    multiple=True,
    type=str,
    help="Limit to specific asset IDs. Repeatable.",
)
@click.option(
    "--id-file",
    "id_file",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help="File containing asset IDs, one per line.",
)
@click.option(
    "--retry-manifest",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help="JSONL manifest from a prior run; retry incomplete assets.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    help=(
        "File path for JSONL event logs. Defaults to stdout. "
        "The file is created with mode 0600 and a SHA-256 record is logged."
    ),
)
@click.option(
    "--error-threshold",
    type=click.IntRange(min=1),
    default=10,
    show_default=True,
    help="Halt the run after this many consecutive errors.",
)
def marketplace_snapshots(
    apply: bool,
    asset_id: tuple[str, ...],
    id_file: str | None,
    retry_manifest: str | None,
    output: Path | None,
    error_threshold: int,
) -> None:
    """Backfill legacy marketplace snapshots with structured JSONL output.

    No DSL, email, token, credential, connection string, SQL, or internal
    exception text is emitted.  The manifest records asset ID, old status,
    source classification, before/after row version, result code, and the
    first 12 hex chars of the content SHA-256.
    """
    asset_ids = _collect_asset_ids(list(asset_id), id_file, retry_manifest)

    run_id = str(uuid.uuid4())
    output_file_obj = None
    output_stream: io.TextIOBase = cast(io.TextIOBase, sys.stdout)
    manifest_hash = hashlib.sha256()
    written_lines: list[bytes] = []

    def _write_entry(data: dict[str, Any]) -> None:
        line = json.dumps(data, sort_keys=True)
        line_bytes = (line + "\n").encode("utf-8")
        output_stream.write(line + "\n")
        output_stream.flush()
        written_lines.append(line_bytes)

    try:
        if output is not None:
            fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            output_file_obj = os.fdopen(fd, "w", encoding="utf-8")
            output_stream = output_file_obj
            os.fchmod(fd, 0o600)

        # Inventory via read-only session
        with Session(db.engine, expire_on_commit=False) as inv_session:
            inv_svc = EnterpriseMarketplaceService(inv_session)
            if not asset_ids:
                asset_ids = inv_svc.list_all_asset_ids()
            inv_state = inv_svc.count_by_state()
            inv_status = inv_svc.count_by_status()

        # Run-level started log (no DSL/credential)
        id_hash = hashlib.sha256(
            json.dumps(sorted(asset_ids)).encode("utf-8")).hexdigest()[:12]
        logger = logging.getLogger("marketplace.backfill")
        logger.info("marketplace.backfill_started", extra={
            "run_id": run_id, "mode": "apply" if apply else "dry_run",
            "selected_count": len(asset_ids), "id_manifest_hash": id_hash})

        # Write queued entries for ALL assets (interrupt recovery)
        for aid in asset_ids:
            _write_entry({"asset_id": aid, "result_code": "queued",
                           "dry_run": not apply, "run_id": run_id})

        status_acc: dict[str, int] = {}
        state_acc: dict[str, int] = {}
        source_acc: dict[str, int] = {}
        processed = 0
        consecutive_errors = 0
        total_assets = len(asset_ids)

        for aid in asset_ids:
            if consecutive_errors >= error_threshold:
                click.echo(f"Error threshold {error_threshold} reached, halting.", err=True)
                break

            try:
                with Session(db.engine, expire_on_commit=False) as asset_session:
                    svc = EnterpriseMarketplaceService(asset_session)
                    asset_obj = asset_session.get(EnterpriseMarketplaceAsset, aid)
                    if asset_obj is None:
                        _write_entry({"asset_id": aid, "result_code": "not_found",
                                      "dry_run": not apply, "run_id": run_id})
                        consecutive_errors += 1
                        continue

                    expected_rv = asset_obj.row_version
                    result = svc.backfill_legacy_snapshot(
                        asset_id=aid, dry_run=not apply,
                        expected_row_version=expected_rv)

                    if not result.dry_run:
                        asset_session.commit()

                    status_acc[result.legacy_status] = status_acc.get(
                        result.legacy_status, 0) + 1
                    state_acc[result.new_snapshot_state] = state_acc.get(
                        result.new_snapshot_state, 0) + 1
                    source_acc[result.result_code] = source_acc.get(
                        result.result_code, 0) + 1

                    entry: dict[str, Any] = {
                        "asset_id": aid,
                        "legacy_status": result.legacy_status,
                        "source_classification": result.result_code,
                        "old_snapshot_state": result.old_snapshot_state,
                        "new_snapshot_state": result.new_snapshot_state,
                        "old_row_version": result.old_row_version,
                        "new_row_version": result.new_row_version,
                        "result_code": result.result_code,
                        "dry_run": result.dry_run,
                        "run_id": run_id,
                    }
                    if result.hash_fingerprint:
                        entry["hash_fingerprint"] = result.hash_fingerprint
                    _write_entry(entry)
                    consecutive_errors = 0
                    processed += 1
            except Exception:
                consecutive_errors += 1
                _write_entry({
                    "asset_id": aid, "result_code": "error",
                    "dry_run": not apply, "run_id": run_id,
                })
                logger.error("marketplace.backfill_failed", extra={
                    "run_id": run_id, "asset_id": aid,
                    "error_code": "unexpected_error",
                })

        summary = {
            "run_id": run_id,
            "total": total_assets,
            "processed": processed,
            "failed": total_assets - processed,
            "inventory_status_counts": inv_status,
            "inventory_state_counts": inv_state,
            "status_counts": status_acc,
            "state_counts": state_acc,
            "source_classifications": source_acc,
            "applied": apply,
        }
        _write_entry(summary)

        for line_bytes in written_lines:
            manifest_hash.update(line_bytes)
        final_hash = manifest_hash.hexdigest()
        click.echo(f"Manifest SHA-256: {final_hash}", err=True)

        logger.info("marketplace.backfill_completed", extra={
            "run_id": run_id,
            "processed": processed,
            "failed": total_assets - processed,
            "manifest_sha256": final_hash[:12],
        })

    finally:
        if output_file_obj is not None:
            output_file_obj.close()


def _collect_asset_ids(cli_ids, id_file, retry_manifest_path):
    all_ids = list(cli_ids)
    if id_file:
        with open(id_file) as fh:
            for line in fh:
                s = line.strip()
                if s: all_ids.append(s)
    if retry_manifest_path:
        retry_ids = _parse_retry_manifest(retry_manifest_path)
        all_ids.extend(retry_ids)
    seen: set[str] = set()
    deduped: list[str] = []
    for aid in all_ids:
        if aid not in seen:
            seen.add(aid); deduped.append(aid)
    return deduped


def _parse_retry_manifest(path):
    retryable_codes = frozenset({
        "queued", "error", "source_missing", "failed",
        "export_failed", "parse_failed", "validation_failed",
        "private_dependency", "source_unavailable", "tenant_mismatch",
    })
    final_codes = frozenset({
        "ok", "dry_run_ok", "ready_skip", "ineligible", "not_found",
    })
    # Per-asset last status
    last_status: dict[str, str] = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    raise click.ClickException(f"Malformed JSON in retry manifest: {path}")
                if "summary" in obj and "total" in obj:
                    continue
                aid = obj.get("asset_id")
                if not aid: continue
                code = obj.get("result_code") or obj.get("status", "")
                if code: last_status[aid] = code
    except click.ClickException:
        raise
    except Exception:
        raise click.ClickException(f"Failed to read retry manifest: {path}")
    ids = []
    for aid, code in sorted(last_status.items()):
        if code in retryable_codes:
            ids.append(aid)
    return ids


data_migrate.add_command(marketplace_snapshots)
data_migrate.add_command(legacy_model_types)
data_migrate.add_command(migrate_dataset_permissions_to_rbac)

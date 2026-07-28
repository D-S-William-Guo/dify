"""finalize enterprise marketplace schema

Revision ID: b416e5c4e702
Revises: a71e16c0de01
Create Date: 2026-07-21 14:00:00.000000

Creates the append-only ``enterprise_marketplace_asset_snapshots`` table and
adds six B4 columns (publication_status, published_snapshot_id,
next_snapshot_version, row_version, snapshot_state, snapshot_error_code) to
``enterprise_marketplace_assets``.

Legacy ``status`` values are mapped to safe B4 defaults via a deterministic
SQL CASE expression; unknown values are mapped to ``unpublished / failed /
legacy_status_unknown`` without modifying the original ``status`` column.

No legacy status CHECK is added. No physical foreign keys are created.
Downgrade refuses to run when snapshot data or published pointers exist.
"""

import sqlalchemy as sa
from alembic import op

revision = "b416e5c4e702"
down_revision = "a71e16c0de01"
branch_labels = None
depends_on = None

_ASSET_INIT_SQL = """
    UPDATE enterprise_marketplace_assets
    SET
        publication_status = CASE status
            WHEN 'unlisted' THEN 'unlisted'
            WHEN 'approved' THEN 'unpublished'
            WHEN 'pending'  THEN 'unpublished'
            WHEN 'rejected' THEN 'unpublished'
            ELSE 'unpublished'
        END,
        published_snapshot_id = NULL,
        next_snapshot_version = 1,
        row_version = 0,
        snapshot_state = CASE status
            WHEN 'approved' THEN 'backfill_pending'
            WHEN 'unlisted' THEN 'none'
            WHEN 'pending'  THEN 'none'
            WHEN 'rejected' THEN 'none'
            ELSE 'failed'
        END,
        snapshot_error_code = CASE
            WHEN status NOT IN ('approved', 'unlisted', 'pending', 'rejected')
            THEN 'legacy_status_unknown'
            ELSE NULL
        END
"""


def upgrade():
    # 1. Create snapshot table (append-only, immutable)
    op.create_table(
        "enterprise_marketplace_asset_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("dsl_content", sa.Text(), nullable=False),
        sa.Column("dsl_version", sa.String(length=32), nullable=False),
        sa.Column("content_sha256", sa.VARCHAR(length=64), nullable=False),
        sa.Column("frozen_at", sa.DateTime(), nullable=False),
        sa.Column("source_app_id", sa.String(length=36), nullable=False),
        sa.Column("source_tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source_tenant_name", sa.String(length=255), nullable=True),
        sa.Column("submitter_account_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_account_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("category", sa.String(length=255), nullable=False, server_default=sa.text("'General'")),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "allow_show_workspace_name", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("app_name", sa.String(length=255), nullable=False),
        sa.Column("app_description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("app_mode", sa.String(length=32), nullable=False),
        sa.Column("app_icon_type", sa.String(length=32), nullable=True),
        sa.Column("app_icon", sa.Text(), nullable=True),
        sa.Column("app_icon_background", sa.String(length=32), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="enterprise_marketplace_snapshot_pkey"),
        sa.UniqueConstraint(
            "asset_id", "snapshot_version",
            name="enterprise_marketplace_snapshot_asset_version_uq",
        ),
        sa.CheckConstraint(
            "snapshot_version >= 1",
            name="ck_marketplace_snapshot_version",
        ),
        sa.CheckConstraint(
            "char_length(content_sha256) = 64",
            name="ck_marketplace_snapshot_content_sha256_length",
        ),
    )
    op.create_index(
        "enterprise_marketplace_snapshot_asset_frozen_idx",
        "enterprise_marketplace_asset_snapshots",
        ["asset_id", "frozen_at", "id"],
        unique=False,
    )
    op.create_index(
        "enterprise_marketplace_snapshot_sha256_idx",
        "enterprise_marketplace_asset_snapshots",
        ["content_sha256"],
        unique=False,
    )

    # 2. Add six B4 columns to the main asset table.
    #    nullable=True + server_default so existing rows are compatible.
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column(
            "publication_status", sa.String(length=32), nullable=True,
            server_default=sa.text("'unpublished'"),
        ),
    )
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column("published_snapshot_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column(
            "next_snapshot_version", sa.Integer(), nullable=True,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column(
            "row_version", sa.Integer(), nullable=True,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column(
            "snapshot_state", sa.String(length=32), nullable=True,
            server_default=sa.text("'none'"),
        ),
    )
    op.add_column(
        "enterprise_marketplace_assets",
        sa.Column("snapshot_error_code", sa.String(length=64), nullable=True),
    )

    # 3. Deterministic SQL CASE initialization of all existing rows.
    #    Known statuses:
    #      approved  → unpublished  /  backfill_pending
    #      unlisted  → unlisted     /  none
    #      pending   → unpublished  /  none
    #      rejected  → unpublished  /  none
    #
    #    Unknown statuses (ELSE): keep original status value,
    #    publication_status = 'unpublished', snapshot_state = 'failed',
    #    snapshot_error_code = 'legacy_status_unknown'.
    #
    #    next_snapshot_version = 1, row_version = 0 for all rows.
    #
    #    The old status column, source IDs, metadata, reviewer, row count,
    #    and three timestamps are NOT modified.
    op.execute(sa.text(_ASSET_INIT_SQL))

    # 4. After all rows are initialized, set NOT NULL on B4-owned columns.
    op.alter_column(
        "enterprise_marketplace_assets", "publication_status",
        existing_type=sa.String(length=32), nullable=False,
    )
    op.alter_column(
        "enterprise_marketplace_assets", "next_snapshot_version",
        existing_type=sa.Integer(), nullable=False,
    )
    op.alter_column(
        "enterprise_marketplace_assets", "row_version",
        existing_type=sa.Integer(), nullable=False,
    )
    op.alter_column(
        "enterprise_marketplace_assets", "snapshot_state",
        existing_type=sa.String(length=32), nullable=False,
    )

    # 5. Safe CHECK constraints only on B4-owned, exhaustively initialized columns.
    op.create_check_constraint(
        "ck_marketplace_asset_publication_status",
        "enterprise_marketplace_assets",
        "publication_status IN ('unpublished', 'published', 'unlisted')",
    )
    op.create_check_constraint(
        "ck_marketplace_asset_snapshot_state",
        "enterprise_marketplace_assets",
        "snapshot_state IN ('none', 'ready', 'backfill_pending', 'source_missing', 'failed')",
    )
    op.create_check_constraint(
        "ck_marketplace_asset_next_snapshot_version",
        "enterprise_marketplace_assets",
        "next_snapshot_version >= 1",
    )

    # 6. Additional B4 indexes.
    op.create_index(
        "enterprise_marketplace_asset_publication_idx",
        "enterprise_marketplace_assets",
        ["publication_status", "updated_at", "id"],
        unique=False,
    )
    op.create_index(
        "enterprise_marketplace_asset_submitter_idx",
        "enterprise_marketplace_assets",
        ["source_tenant_id", "submitter_account_id", "updated_at", "id"],
        unique=False,
    )


def downgrade():
    """Schema reversal – only for unreleased environments.

    Production rollback must use a complete backup restore; this downgrade
    refuses to run if any snapshot data or published pointers exist.
    """

    # Data-loss gate: refuse if snapshots exist or any asset has a published pointer.
    conn = op.get_bind()
    snapshot_count = conn.scalar(
        sa.text("SELECT COUNT(1) FROM enterprise_marketplace_asset_snapshots")
    )
    published_count = conn.scalar(
        sa.text(
            "SELECT COUNT(1) FROM enterprise_marketplace_assets"
            " WHERE published_snapshot_id IS NOT NULL"
        )
    )
    if snapshot_count or published_count:
        raise RuntimeError(
            "Downgrade refused: enterprise_marketplace_asset_snapshots is non-empty "
            f"({snapshot_count} rows) or enterprise_marketplace_assets has published "
            f"snapshot pointers ({published_count} rows). Restore from a backup instead."
        )

    # Drop B4 indexes.
    op.drop_index(
        "enterprise_marketplace_asset_submitter_idx",
        table_name="enterprise_marketplace_assets",
    )
    op.drop_index(
        "enterprise_marketplace_asset_publication_idx",
        table_name="enterprise_marketplace_assets",
    )

    # Drop B4 CHECK constraints.
    op.drop_constraint(
        "ck_marketplace_asset_next_snapshot_version",
        "enterprise_marketplace_assets",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketplace_asset_snapshot_state",
        "enterprise_marketplace_assets",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketplace_asset_publication_status",
        "enterprise_marketplace_assets",
        type_="check",
    )

    # Drop B4 new columns.
    op.drop_column("enterprise_marketplace_assets", "snapshot_error_code")
    op.drop_column("enterprise_marketplace_assets", "snapshot_state")
    op.drop_column("enterprise_marketplace_assets", "row_version")
    op.drop_column("enterprise_marketplace_assets", "next_snapshot_version")
    op.drop_column("enterprise_marketplace_assets", "published_snapshot_id")
    op.drop_column("enterprise_marketplace_assets", "publication_status")

    # Drop snapshot table (indexes + table).
    op.drop_index(
        "enterprise_marketplace_snapshot_sha256_idx",
        table_name="enterprise_marketplace_asset_snapshots",
    )
    op.drop_index(
        "enterprise_marketplace_snapshot_asset_frozen_idx",
        table_name="enterprise_marketplace_asset_snapshots",
    )
    op.drop_table("enterprise_marketplace_asset_snapshots")

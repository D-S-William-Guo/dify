"""align enterprise marketplace ID/FK columns to PostgreSQL uuid

Revision ID: e7c0a9d2b8f3
Revises: b416e5c4e702
Create Date: 2026-08-12 00:00:00.000000

Phase G fix (GPH-01): the B4 migration ``b416e5c4e702`` created the ID/FK
columns of ``enterprise_marketplace_assets`` and
``enterprise_marketplace_asset_snapshots`` as ``VARCHAR(36)``, while the ORM
(``api/models/model.py``) declares them with ``models.types.StringUUID``,
which maps to PostgreSQL ``uuid``. Queries that filter on these columns bind
UUID parameters and PostgreSQL rejects them with
``operator does not exist: character varying = uuid``, breaking submit /
review / copy / unlist.

This revision is a data-preserving ``ALTER TYPE ... USING col::uuid`` applied
only on PostgreSQL. On other dialects ``StringUUID`` already maps to
``CHAR(36)`` (the existing ``VARCHAR(36)`` is compatible), so nothing changes
there. PostgreSQL preserves indexes, unique constraints, and CHECK constraints
across the column-type rewrite.

Enterprise replay note: this is an enterprise fix that exists in no official
Dify release. A future official release may fix or upstream the same columns;
before upgrading to such a release, reconcile this revision against the new
official migration graph and drop it only once the official schema already
declares these columns as ``uuid``.
"""

import sqlalchemy as sa
from alembic import op

revision = "e7c0a9d2b8f3"
down_revision = "b416e5c4e702"
branch_labels = None
depends_on = None

_ASSETS_TABLE = "enterprise_marketplace_assets"
_SNAPSHOTS_TABLE = "enterprise_marketplace_asset_snapshots"

# Every ID/FK column the ORM declares as StringUUID (PostgreSQL uuid) but the
# B4 migration created as VARCHAR(36).
_ASSETS_UUID_COLUMNS = (
    "id",
    "source_app_id",
    "source_tenant_id",
    "submitter_account_id",
    "reviewer_account_id",
    "published_snapshot_id",
)
_SNAPSHOTS_UUID_COLUMNS = (
    "id",
    "asset_id",
    "source_app_id",
    "source_tenant_id",
    "submitter_account_id",
    "reviewer_account_id",
)

_ALTER_TABLE_SQL = (
    "ALTER TABLE {table} ALTER COLUMN {column} TYPE {type} USING {column}::{cast}"
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade():
    if not _is_postgresql():
        return
    for table, columns in (
        (_ASSETS_TABLE, _ASSETS_UUID_COLUMNS),
        (_SNAPSHOTS_TABLE, _SNAPSHOTS_UUID_COLUMNS),
    ):
        for column in columns:
            op.execute(sa.text(_ALTER_TABLE_SQL.format(table=table, column=column, type="UUID", cast="uuid")))


def downgrade():
    if not _is_postgresql():
        return
    for table, columns in (
        (_ASSETS_TABLE, _ASSETS_UUID_COLUMNS),
        (_SNAPSHOTS_TABLE, _SNAPSHOTS_UUID_COLUMNS),
    ):
        for column in columns:
            op.execute(
                sa.text(
                    _ALTER_TABLE_SQL.format(table=table, column=column, type="VARCHAR(36)", cast="text")
                )
            )

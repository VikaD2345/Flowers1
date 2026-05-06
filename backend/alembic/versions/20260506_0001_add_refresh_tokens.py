"""add refresh tokens table

Revision ID: 20260506_0001
Revises:
Create Date: 2026-05-06 00:01:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260506_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "app_refresh_tokens" in inspector.get_table_names():
        return

    op.create_table(
        "app_refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_app_refresh_tokens_user_id", "app_refresh_tokens", ["user_id"])
    op.create_index("ix_app_refresh_tokens_jti", "app_refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_app_refresh_tokens_token_hash", "app_refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "app_refresh_tokens" not in inspector.get_table_names():
        return

    op.drop_index("ix_app_refresh_tokens_token_hash", table_name="app_refresh_tokens")
    op.drop_index("ix_app_refresh_tokens_jti", table_name="app_refresh_tokens")
    op.drop_index("ix_app_refresh_tokens_user_id", table_name="app_refresh_tokens")
    op.drop_table("app_refresh_tokens")

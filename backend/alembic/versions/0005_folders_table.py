"""0005_folders_table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create folders table
    op.create_table(
        "folders",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Create indexes for folders table
    op.create_index("ix_folders_user_id", "folders", ["user_id"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    # 2. Add folder_id column to documents table
    op.add_column("documents", sa.Column("folder_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_documents_folder_id",
        "documents",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Create index for folder_id on documents table
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])


def downgrade() -> None:
    # Drop foreign key and column from documents
    op.drop_constraint("fk_documents_folder_id", "documents", type_="foreignkey")
    op.drop_index("ix_documents_folder_id", table_name="documents")
    op.drop_column("documents", "folder_id")

    # Drop indexes and folders table
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_index("ix_folders_user_id", table_name="folders")
    op.drop_table("folders")

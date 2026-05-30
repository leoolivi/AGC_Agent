"""0001_initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-05-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="owner"),
        sa.Column("notification_settings", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("document_type", sa.String(100)),
        sa.Column("document_type_confidence", sa.Float()),
        sa.Column("extracted_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("parse_status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # pgvector embedding column
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])

    op.create_table(
        "deadlines",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID()),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("deadline_type", sa.String(100), server_default="custom"),
        sa.Column("recurrence", sa.String(50), server_default="none"),
        sa.Column("recurrence_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("source", sa.String(50), server_default="manual"),
        sa.Column("source_confidence", sa.Float()),
        sa.Column("source_text", sa.Text()),
        sa.Column("notified_at", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(255)),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100)),
        sa.Column("tool_args", postgresql.JSONB(), server_default="{}"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("depends_on_task_id", sa.UUID()),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["agent_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pending_confirmations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_for_review", postgresql.JSONB(), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("user_comment", sa.Text()),
        sa.Column("group_id", sa.UUID()),
        sa.Column("group_type", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_confirmations_group_id",
        "pending_confirmations",
        ["group_id"],
        postgresql_where=sa.text("group_id IS NOT NULL"),
    )

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID()),
        sa.Column("to_addresses", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending_review"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("related_type", sa.String(100)),
        sa.Column("related_id", sa.UUID()),
        sa.Column("read", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID()),
        sa.Column("session_id", sa.String(255)),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100)),
        sa.Column("input_summary", sa.Text()),
        sa.Column("output_summary", sa.Text()),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("status", sa.String(50)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_inbox",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_source", postgresql.JSONB(), nullable=False),
        sa.Column("source_ref_id", sa.UUID()),
        sa.Column("agent_analysis", sa.Text(), nullable=False),
        sa.Column("urgency", sa.String(50), nullable=False),
        sa.Column("suggested_actions", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("chosen_action_id", sa.String(100)),
        sa.Column("chosen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_inbox_user_status_urgency",
        "agent_inbox",
        ["user_id", "status", "urgency", "created_at"],
    )

    op.create_table(
        "user_extraction_trust",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("total_extractions", sa.Integer(), server_default="0"),
        sa.Column("confirmed_without_edit", sa.Integer(), server_default="0"),
        sa.Column("edited_extractions", sa.Integer(), server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "document_type", "field_name"),
    )
    # Generated column for accuracy
    op.execute(
        "ALTER TABLE user_extraction_trust ADD COLUMN accuracy FLOAT "
        "GENERATED ALWAYS AS (confirmed_without_edit::float / NULLIF(total_extractions, 0)) STORED"
    )


def downgrade() -> None:
    op.drop_table("user_extraction_trust")
    op.drop_table("agent_inbox")
    op.drop_table("audit_log")
    op.drop_table("notifications")
    op.drop_table("email_drafts")
    op.drop_table("pending_confirmations")
    op.drop_table("agent_tasks")
    op.drop_table("deadlines")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")

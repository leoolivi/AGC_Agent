"""0004_agent_enhancement_schema

Revision ID: 0004
Revises: 0002, 0003
Create Date: 2026-06-01
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = ("0002", "0003")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add columns to existing tables ---

    # documents: source tracking for passive ingestion
    op.add_column(
        "documents",
        sa.Column("source", sa.String(20), server_default="upload"),
    )
    op.add_column(
        "documents",
        sa.Column("source_ref_id", sa.Text()),
    )

    # deadlines: calendar event and escalation rule linkage
    op.add_column(
        "deadlines",
        sa.Column("calendar_event_id", sa.Text()),
    )
    op.add_column(
        "deadlines",
        sa.Column(
            "escalation_rule_id",
            sa.UUID(),
        ),
    )

    # --- New tables ---

    # Source monitor configuration
    op.create_table(
        "monitored_sources",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_sync_token", sa.Text()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_count", sa.Integer(), server_default="0"),
        sa.Column("error_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source_type IN ('drive', 'gmail', 'calendar')",
            name="ck_monitored_sources_source_type",
        ),
    )
    op.create_index("ix_monitored_sources_user_id", "monitored_sources", ["user_id"])

    # Risky clause detection results
    op.create_table(
        "risky_clauses",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("paragraph_ref", sa.Text()),
        sa.Column("plain_language_explanation", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "severity IN ('alto', 'medio', 'basso')",
            name="ck_risky_clauses_severity",
        ),
    )
    op.create_index("ix_risky_clauses_document_id", "risky_clauses", ["document_id"])

    # Cross-document correlations
    op.create_table(
        "document_correlations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("target_document_id", sa.UUID(), nullable=False),
        sa.Column("correlation_type", sa.String(30), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("source_passage", sa.Text()),
        sa.Column("target_passage", sa.Text()),
        sa.Column("source_page", sa.Integer()),
        sa.Column("target_page", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["target_document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source_document_id != target_document_id",
            name="ck_document_correlations_different_docs",
        ),
    )
    op.create_index("ix_document_correlations_user_id", "document_correlations", ["user_id"])
    op.create_index(
        "ix_document_correlations_source_doc",
        "document_correlations",
        ["source_document_id"],
    )
    op.create_index(
        "ix_document_correlations_target_doc",
        "document_correlations",
        ["target_document_id"],
    )

    # Dossiers (logical document groups)
    op.create_table(
        "dossiers",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("dossier_type", sa.String(50)),
        sa.Column(
            "completeness_status",
            sa.String(20),
            nullable=False,
            server_default="incomplete",
        ),
        sa.Column("missing_items", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dossiers_user_id", "dossiers", ["user_id"])

    # Dossier-document junction table
    op.create_table(
        "dossier_documents",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text()),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("dossier_id", "document_id"),
    )

    # Escalation rules
    op.create_table(
        "escalation_rules",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("deadline_type", sa.String(30), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_escalation_rules_user_id", "escalation_rules", ["user_id"])

    # Now add the FK constraint on deadlines.escalation_rule_id
    # (must be after escalation_rules table is created)
    op.create_foreign_key(
        "fk_deadlines_escalation_rule_id",
        "deadlines",
        "escalation_rules",
        ["escalation_rule_id"],
        ["id"],
    )

    # Escalation execution state
    op.create_table(
        "escalation_executions",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("deadline_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.UUID(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("next_step_job_id", sa.Text()),
        sa.Column("history", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.Text()),
        sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["escalation_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_escalation_executions_deadline_id",
        "escalation_executions",
        ["deadline_id"],
    )
    op.create_index(
        "ix_escalation_executions_rule_id",
        "escalation_executions",
        ["rule_id"],
    )

    # Report generation history
    op.create_table(
        "reports",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("template_name", sa.Text(), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("storage_key", sa.Text()),
        sa.Column("export_destination", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "format IN ('pdf', 'excel')",
            name="ck_reports_format",
        ),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])


def downgrade() -> None:
    # Drop new tables in reverse dependency order
    op.drop_table("reports")
    op.drop_table("escalation_executions")

    # Drop FK on deadlines before dropping escalation_rules
    op.drop_constraint("fk_deadlines_escalation_rule_id", "deadlines", type_="foreignkey")

    op.drop_table("escalation_rules")
    op.drop_table("dossier_documents")
    op.drop_table("dossiers")
    op.drop_table("document_correlations")
    op.drop_table("risky_clauses")
    op.drop_table("monitored_sources")

    # Remove added columns from existing tables
    op.drop_column("deadlines", "escalation_rule_id")
    op.drop_column("deadlines", "calendar_event_id")
    op.drop_column("documents", "source_ref_id")
    op.drop_column("documents", "source")

"""Tests for WorkflowGraph and Phase 2 templates."""
from __future__ import annotations

import json

import pytest

from app.adapters.dummy.llm import DummyLLMAdapter
from app.agent.graphs.workflow_graph import WorkflowGraph
from app.agent.risk.engine import RiskEngine
from app.agent.workflows.templates import build_registry


@pytest.fixture
def workflow_graph() -> WorkflowGraph:
    registry = build_registry()
    risk = RiskEngine()
    llm = DummyLLMAdapter(content="ok")
    return WorkflowGraph(registry=registry, risk_engine=risk, llm=llm)


class TestWorkflowGraph:
    @pytest.mark.asyncio
    async def test_process_document(self, workflow_graph: WorkflowGraph) -> None:
        result = await workflow_graph.run("process_document", {"document_id": "doc-1"}, "user-1")
        assert result["workflow_id"] == "process_document"
        assert len(result["steps"]) == 3
        # read_document (risk 0) and classify_document (risk 1) should execute
        assert result["steps"][0]["status"] == "done"
        assert result["steps"][1]["status"] == "done"
        # create_deadline (risk 2) should also execute
        assert result["steps"][2]["status"] == "done"

    @pytest.mark.asyncio
    async def test_draft_payment_reminder_blocks_on_high_risk(self, workflow_graph: WorkflowGraph) -> None:
        result = await workflow_graph.run("draft_payment_reminder", {"document_id": "doc-1"}, "user-1")
        # draft_email has risk 3 in rules.yaml → waiting_confirmation
        # But search_documents (risk 0) should execute
        assert result["steps"][0]["status"] == "done"

    @pytest.mark.asyncio
    async def test_missing_args_raises(self, workflow_graph: WorkflowGraph) -> None:
        with pytest.raises(ValueError, match="Missing required args"):
            await workflow_graph.run("process_document", {}, "user-1")

    def test_registry_has_3_templates(self) -> None:
        registry = build_registry()
        assert len(registry.list_all()) == 6

    def test_all_templates_have_valid_tools(self) -> None:
        registry = build_registry()
        risk = RiskEngine()
        valid_tools = set(risk.tool_risk_base.keys())
        for template in registry.list_all():
            for step in template.steps:
                assert step.tool in valid_tools, f"{step.tool} not in rules.yaml"

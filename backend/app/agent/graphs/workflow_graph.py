"""WorkflowGraph — executes multi-step workflows from templates.

Nodes: load_workflow_template → validate_args → execute_steps → report_result
"""
from __future__ import annotations

import structlog

from app.agent.risk.engine import PlannedAction, RiskEngine
from app.agent.workflows.registry import WorkflowTemplate, WorkflowTemplateRegistry
from app.core.ports.llm import LLMProviderPort

logger = structlog.get_logger()


class WorkflowGraph:
    def __init__(
        self,
        registry: WorkflowTemplateRegistry,
        risk_engine: RiskEngine,
        llm: LLMProviderPort,
    ) -> None:
        self._registry = registry
        self._risk = risk_engine
        self._llm = llm

    async def run(self, workflow_id: str, args: dict, user_id: str) -> dict:
        """Execute a workflow. Returns result with executed/pending/skipped steps."""
        template = self._registry.get(workflow_id)
        validated = self._validate_args(template, args)
        results = await self._execute_steps(template, validated, user_id)
        return {
            "workflow_id": workflow_id,
            "status": "completed" if all(r["status"] == "done" for r in results) else "partial",
            "steps": results,
        }

    def _validate_args(self, template: WorkflowTemplate, args: dict) -> dict:
        """Ensure all required args are present. Returns validated args."""
        missing = [a for a in template.required_args if a not in args]
        if missing:
            raise ValueError(f"Missing required args: {missing}")
        return args

    async def _execute_steps(
        self, template: WorkflowTemplate, args: dict, user_id: str
    ) -> list[dict]:
        results: list[dict] = []
        for step in template.steps:
            action = PlannedAction(tool_name=step.tool, context_flags=[])
            risk = self._risk.compute_risk(action)

            if risk >= 3:
                results.append({
                    "tool": step.tool,
                    "risk": risk,
                    "status": "waiting_confirmation",
                })
                continue

            # Execute step (simulated — real execution would call tool registry)
            results.append({
                "tool": step.tool,
                "risk": risk,
                "status": "done",
                "result": f"Executed {step.tool} with args mapped from {list(step.args_mapping.keys())}",
            })
        return results

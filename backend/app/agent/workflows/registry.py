"""WorkflowTemplate models and WorkflowTemplateRegistry."""
from __future__ import annotations

from pydantic import BaseModel


class WorkflowStep(BaseModel):
    tool: str
    risk: int
    args_mapping: dict


class WorkflowTemplate(BaseModel):
    workflow_id: str
    name: str
    description: str
    required_args: list[str]
    optional_args: list[str] = []
    steps: list[WorkflowStep]
    applicable_to: list[str] = []


class WorkflowTemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}

    def register(self, template: WorkflowTemplate) -> None:
        self._templates[template.workflow_id] = template

    def get(self, workflow_id: str) -> WorkflowTemplate:
        if workflow_id not in self._templates:
            raise KeyError(f"Workflow template not found: {workflow_id!r}")
        return self._templates[workflow_id]

    def list_all(self) -> list[WorkflowTemplate]:
        return list(self._templates.values())

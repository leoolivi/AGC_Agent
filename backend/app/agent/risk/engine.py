"""RiskEngine — action risk scoring based on rules.yaml.

[TODO: TD-003] Replace with ML model without changing interface.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PlannedAction:
    tool_name: str
    args: dict = field(default_factory=dict)
    context_flags: list[str] = field(default_factory=list)


class RiskEngine:
    def __init__(self, rules_path: Path | None = None) -> None:
        if rules_path is None:
            rules_path = Path(__file__).parent / "rules.yaml"
        if not rules_path.exists():
            print(f"FATAL: rules.yaml not found at {rules_path}", file=sys.stderr)
            sys.exit(1)
        try:
            with open(rules_path) as f:
                self._rules: dict = yaml.safe_load(f)
            # Validate required keys
            for key in ("tool_risk_base", "context_modifiers", "confidence_thresholds"):
                if key not in self._rules:
                    raise ValueError(f"Missing required key: {key}")
        except (yaml.YAMLError, ValueError) as e:
            print(f"FATAL: rules.yaml malformed: {e}", file=sys.stderr)
            sys.exit(1)

    @property
    def tool_risk_base(self) -> dict[str, int]:
        return self._rules["tool_risk_base"]

    @property
    def context_modifiers(self) -> dict[str, int]:
        return self._rules["context_modifiers"]

    def compute_risk(self, action: PlannedAction, context: dict | None = None) -> int:
        """Compute risk: risk_base + sum(applicable context_modifiers). Clamped to [risk_base, 5]."""
        base = self._rules["tool_risk_base"].get(action.tool_name, 3)
        modifier_sum = sum(
            self._rules["context_modifiers"].get(flag, 0)
            for flag in action.context_flags
        )
        return min(base + modifier_sum, 5)

    def get_threshold(self, field_name: str) -> float:
        """Return confidence threshold for a field type from rules.yaml."""
        thresholds = self._rules["confidence_thresholds"]
        if field_name not in thresholds:
            return 0.85  # default threshold
        return thresholds[field_name]

    def effective_threshold(
        self, user_id: str, document_type: str, field_name: str, accuracy: float | None = None
    ) -> float:
        """Adjust threshold based on user trust. Higher accuracy → lower threshold."""
        base = self.get_threshold(field_name)
        if accuracy is None or accuracy < 0.7:
            return base
        # Reduce threshold by up to 15% based on accuracy (0.7→0%, 1.0→15%)
        reduction = (accuracy - 0.7) * 0.5  # max 0.15
        return max(base - reduction, 0.5)  # never below 0.5

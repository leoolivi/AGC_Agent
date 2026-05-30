"""Property test: Audit Log Append-Only.

Property 4: For any sequence of operations, the total count of audit_log records
must be monotonically non-decreasing. No operation can reduce the number of records.

Validates: Requirements 19.2
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.services.audit_service import AuditService

action_types = st.sampled_from([
    "document_upload", "document_classify", "llm_fallback",
    "tool_execute", "confirmation_approve", "confirmation_reject",
    "guardrail_block", "triage_complete",
])


@given(
    actions=st.lists(action_types, min_size=1, max_size=50),
)
@settings(max_examples=200)
def test_audit_log_append_only(actions: list[str]) -> None:
    """Count must be monotonically non-decreasing after each log() call."""
    service = AuditService()
    prev_count = 0

    for action in actions:
        service.log(action_type=action, user_id="user-1")
        current_count = service.count
        assert current_count > prev_count, (
            f"Count decreased from {prev_count} to {current_count} after logging {action}"
        )
        prev_count = current_count

    # Final count must equal number of actions
    assert service.count == len(actions)


@given(
    actions=st.lists(action_types, min_size=2, max_size=30),
)
@settings(max_examples=100)
def test_audit_log_entries_never_disappear(actions: list[str]) -> None:
    """Once logged, entries are always retrievable."""
    service = AuditService()
    for action in actions:
        service.log(action_type=action, user_id="user-1")

    all_entries = service.get_entries(limit=100)
    assert len(all_entries) == len(actions)

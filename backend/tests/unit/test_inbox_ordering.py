"""Property test: Inbox Urgency Ordering.

Property 6: For any set of AgentInboxItems with mixed urgency, the ordering must
satisfy urgency_rank(i) <= urgency_rank(j) for every adjacent pair.
At equal urgency, created_at DESC.

Validates: Requirements 10.1
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

URGENCY_RANK = {"immediate": 0, "today": 1, "this_week": 2, "low": 3}
URGENCIES = list(URGENCY_RANK.keys())


def sort_inbox_items(items: list[dict]) -> list[dict]:
    """Sort items by urgency rank ASC, then created_at DESC."""
    return sorted(
        items,
        key=lambda x: (URGENCY_RANK[x["urgency"]], -x["created_at"].timestamp()),
    )


@given(
    urgencies=st.lists(st.sampled_from(URGENCIES), min_size=2, max_size=50),
)
@settings(max_examples=300)
def test_inbox_urgency_ordering(urgencies: list[str]) -> None:
    """Sorted inbox must have non-decreasing urgency rank."""
    base_time = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    items = [
        {
            "id": f"item-{i}",
            "urgency": u,
            "created_at": base_time - timedelta(minutes=random.randint(0, 10000)),
        }
        for i, u in enumerate(urgencies)
    ]

    sorted_items = sort_inbox_items(items)

    # Verify urgency rank is non-decreasing
    for i in range(len(sorted_items) - 1):
        rank_i = URGENCY_RANK[sorted_items[i]["urgency"]]
        rank_j = URGENCY_RANK[sorted_items[i + 1]["urgency"]]
        assert rank_i <= rank_j, (
            f"Item {i} ({sorted_items[i]['urgency']}) has higher rank than item {i+1} ({sorted_items[i+1]['urgency']})"
        )

    # Verify within same urgency, created_at is DESC
    for i in range(len(sorted_items) - 1):
        if sorted_items[i]["urgency"] == sorted_items[i + 1]["urgency"]:
            assert sorted_items[i]["created_at"] >= sorted_items[i + 1]["created_at"], (
                f"Within same urgency, items not sorted by created_at DESC"
            )

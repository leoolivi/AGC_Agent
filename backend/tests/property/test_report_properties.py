"""Property-based tests for ReportGeneratorService."""
from __future__ import annotations

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.domain.report import ReportFilters, ReportRequest


@given(
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    st.sampled_from(["pdf", "excel"]),
)
@settings(max_examples=20)
def test_date_range_and_format_valid(d_from: date, d_to: date, fmt: str) -> None:
    if d_from <= d_to:
        req = ReportRequest(
            user_id=__import__("uuid").uuid4(),
            template_name="scadenze_mensili",
            date_from=d_from,
            date_to=d_to,
            filters=ReportFilters(),
            format=fmt,  # type: ignore[arg-type]
        )
        assert req.format == fmt
        assert req.date_from <= req.date_to

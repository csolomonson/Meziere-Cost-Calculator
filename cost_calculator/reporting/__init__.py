"""Linux-compatible PDF reporting boundary."""

from __future__ import annotations

import pandas as pd

from app_config import setting
from reporting.reportlab import (
    ReportAudience,
    render_customer_part_cost_document,
    render_internal_part_cost_document,
    render_part_cost_document,
)


class ReportRenderError(RuntimeError):
    """A saved costing run could not be rendered as PDF."""


def render_part_cost_pdf(
    part_cost_id: int,
    *,
    part_cost: pd.DataFrame | None = None,
    audience: str = ReportAudience.INTERNAL,
) -> bytes:
    """Load one saved run and render the selected reader-specific document."""
    from utils.queries import get_part_cost, get_saved_material_lines, get_saved_operation_lines

    try:
        saved_cost = part_cost if part_cost is not None else get_part_cost(part_cost_id)
        if saved_cost.empty:
            raise ReportRenderError("Costing run was not found")
        operation_lines = get_saved_operation_lines(part_cost_id)
        material_lines = get_saved_material_lines(part_cost_id)
        company_name = setting("COST_REPORT_COMPANY_NAME", "Meziere Enterprises") or "Meziere Enterprises"
        if audience == ReportAudience.INTERNAL:
            return render_internal_part_cost_document(
                saved_cost,
                operation_lines,
                material_lines,
                company_name=company_name,
            )
        if audience == ReportAudience.CUSTOMER:
            return render_customer_part_cost_document(
                saved_cost,
                operation_lines,
                material_lines,
                company_name=company_name,
            )
        raise ReportRenderError(f"Unknown report audience: {audience}")
    except ReportRenderError:
        raise
    except Exception as exc:
        raise ReportRenderError("The Part Cost report could not be rendered") from exc


__all__ = [
    "ReportAudience",
    "ReportRenderError",
    "render_customer_part_cost_document",
    "render_internal_part_cost_document",
    "render_part_cost_document",
    "render_part_cost_pdf",
]

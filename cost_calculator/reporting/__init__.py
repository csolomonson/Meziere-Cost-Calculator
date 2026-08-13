"""Linux-compatible PDF reporting boundary."""

from __future__ import annotations

import pandas as pd

from reporting.reportlab import render_part_cost_document


class ReportRenderError(RuntimeError):
    """A saved costing run could not be rendered as PDF."""


def render_part_cost_pdf(
    part_cost_id: int,
    *,
    part_cost: pd.DataFrame | None = None,
) -> bytes:
    """Load a saved run and render it without a platform-specific subprocess."""
    from utils.queries import get_part_cost, get_saved_material_lines, get_saved_operation_lines

    try:
        saved_cost = part_cost if part_cost is not None else get_part_cost(part_cost_id)
        if saved_cost.empty:
            raise ReportRenderError("Costing run was not found")
        operation_lines = get_saved_operation_lines(part_cost_id)
        material_lines = get_saved_material_lines(part_cost_id)
        return render_part_cost_document(saved_cost, operation_lines, material_lines)
    except ReportRenderError:
        raise
    except Exception as exc:
        raise ReportRenderError("The Part Cost report could not be rendered") from exc


__all__ = ["ReportRenderError", "render_part_cost_document", "render_part_cost_pdf"]

"""Authenticated PDF reports for saved costing runs."""

import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from reporting import ReportRenderError, render_part_cost_pdf
from utils.queries import get_part_cost


router = APIRouter()
logger = logging.getLogger(__name__)


def _pdf_filename(part_id: object, part_cost_id: int) -> str:
    safe_part_id = re.sub(r"[^A-Za-z0-9._-]+", "-", str(part_id or "part"))
    safe_part_id = safe_part_id.strip("-.") or "part"
    return f"{safe_part_id}-cost-{part_cost_id}.pdf"


@router.get("/api/reports/part-cost/{part_cost_id}")
def part_cost_report(part_cost_id: int):
    try:
        part_cost = get_part_cost(part_cost_id)
    except Exception as exc:
        logger.exception("Saved cost lookup failed for PartCostID %s", part_cost_id)
        raise HTTPException(
            status_code=500, detail="The saved costing run could not be loaded."
        ) from exc
    if part_cost.empty:
        raise HTTPException(status_code=404, detail="Costing run was not found.")

    try:
        pdf = render_part_cost_pdf(part_cost_id, part_cost=part_cost)
    except ReportRenderError as exc:
        logger.exception("PDF rendering failed for PartCostID %s", part_cost_id)
        raise HTTPException(
            status_code=500, detail="The Part Cost report could not be rendered."
        ) from exc

    filename = _pdf_filename(part_cost.iloc[0].get("ucpPartID"), part_cost_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

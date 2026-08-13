"""Cost calculation, history, retrieval, and persistence routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from costing.persistence import (
    costing_run_from_records,
    mark_part_cost_current,
    save_costing_run,
)
from utils.queries import (
    get_current_retail_price,
    get_part_cost,
    get_part_cost_history,
    get_recent_part_costs,
    get_saved_material_lines,
    get_saved_operation_lines,
)
from web.schemas import CostRequest, CostRunSaveRequest, CurrentCostRequest
from web.serialization import dataframe_records
from web.services import (
    build_costing_response,
    enrich_material_lines_from_child_costs,
    serialize_costing_run,
)


router = APIRouter()


@router.get("/api/costs/history")
def cost_history(part_id: str, revision_id: str = ""):
    try:
        rows = get_part_cost_history(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"history": dataframe_records(rows)}


@router.get("/api/costs/recent")
def recent_costs(
    limit: int = 10,
    before_date: datetime | None = None,
    before_id: int | None = None,
    after_date: datetime | None = None,
    after_id: int | None = None,
    part_id: str = "",
    direction: str = "newest",
):
    if (before_date is None) != (before_id is None):
        raise HTTPException(
            status_code=400,
            detail="before_date and before_id must be provided together",
        )
    if (after_date is None) != (after_id is None):
        raise HTTPException(
            status_code=400,
            detail="after_date and after_id must be provided together",
        )
    if direction not in {"newest", "older", "newer", "oldest"}:
        raise HTTPException(
            status_code=400,
            detail="direction must be newest, older, newer, or oldest",
        )
    if direction == "older" and before_date is None:
        raise HTTPException(
            status_code=400, detail="Older history requires a before cursor"
        )
    if direction == "newer" and after_date is None:
        raise HTTPException(
            status_code=400, detail="Newer history requires an after cursor"
        )
    if direction in {"newest", "oldest"} and (
        before_date is not None or after_date is not None
    ):
        raise HTTPException(
            status_code=400, detail="Edge history requests do not accept a cursor"
        )

    page_size = min(100, max(1, int(limit or 10)))
    try:
        rows = get_recent_part_costs(
            page_size + 1,
            before_date=before_date if direction == "older" else None,
            before_id=before_id if direction == "older" else None,
            after_date=after_date if direction == "newer" else None,
            after_id=after_id if direction == "newer" else None,
            part_id_prefix=part_id,
            oldest_first=direction == "oldest",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    has_more_in_direction = len(rows.index) > page_size
    records = dataframe_records(rows.iloc[:page_size])
    if direction in {"newer", "oldest"}:
        records.reverse()

    has_older = (
        has_more_in_direction if direction in {"newest", "older"} else direction == "newer"
    )
    has_newer = (
        has_more_in_direction if direction in {"newer", "oldest"} else direction == "older"
    )
    older_cursor = None
    newer_cursor = None
    if records:
        if has_older:
            last = records[-1]
            older_cursor = {
                "date": last["ucpDateCosted"],
                "id": last["ucpPartCostID"],
            }
        if has_newer:
            first = records[0]
            newer_cursor = {
                "date": first["ucpDateCosted"],
                "id": first["ucpPartCostID"],
            }

    return {
        "costs": records,
        "has_older": has_older,
        "has_newer": has_newer,
        "older_cursor": older_cursor,
        "newer_cursor": newer_cursor,
    }


@router.get("/api/costs/{part_cost_id}")
def saved_cost(part_cost_id: int):
    try:
        costing_run = {
            "part_cost": get_part_cost(part_cost_id),
            "operation_lines": get_saved_operation_lines(part_cost_id),
            "material_lines": get_saved_material_lines(part_cost_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if costing_run["part_cost"].empty:
        raise HTTPException(status_code=404, detail="Costing run was not found.")

    costing_run["material_lines"] = enrich_material_lines_from_child_costs(
        costing_run["material_lines"]
    )

    part_cost = costing_run["part_cost"].iloc[0]
    retail_rows = get_current_retail_price(
        part_cost.get("ucpPartID"), part_cost.get("ucpPartRevision") or ""
    )
    if not retail_rows.empty:
        costing_run["part_cost"].at[
            costing_run["part_cost"].index[0], "ucpRetailUnitPrice"
        ] = retail_rows.iloc[0].get("retail_unit_price")

    return serialize_costing_run(costing_run)


@router.post("/api/costs/current")
def set_current_cost(request: CurrentCostRequest):
    try:
        mark_part_cost_current(request.part_cost_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True}


@router.post("/api/costs/calculate")
def calculate_cost(request: CostRequest, http_request: Request):
    costing_run = build_costing_response(
        request, http_request.state.principal.username
    )
    return serialize_costing_run(costing_run)


@router.post("/api/costs/save")
def save_cost(request: CostRequest, http_request: Request):
    costing_run = build_costing_response(
        request, http_request.state.principal.username
    )

    try:
        part_cost_id = save_costing_run(
            costing_run, make_current=request.make_current
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = serialize_costing_run(costing_run)
    response["part_cost_id"] = part_cost_id
    return response


@router.post("/api/costs/save-run")
def save_cost_run(request: CostRunSaveRequest, http_request: Request):
    part_cost = dict(request.part_cost)
    part_cost["ucpCostedBy"] = http_request.state.principal.username
    costing_run = costing_run_from_records(
        part_cost=part_cost,
        operation_lines=request.operation_lines,
        material_lines=request.material_lines,
    )

    try:
        part_cost_id = save_costing_run(
            costing_run, make_current=request.make_current
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = serialize_costing_run(costing_run)
    response["part_cost_id"] = part_cost_id
    return response


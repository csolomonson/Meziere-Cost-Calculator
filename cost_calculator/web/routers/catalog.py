"""ERP catalog, purchasing, and job-explorer routes."""

from fastapi import APIRouter, HTTPException

from utils.queries import (
    get_bom,
    get_current_or_last_part_cost,
    get_current_retail_price,
    get_external_operation_pos,
    get_last_material_po,
    get_material_pos,
    get_operation_jobs,
    get_operations,
    get_part,
    get_recent_jobs,
    search_operations,
    search_parts,
    search_processes,
    search_work_centers,
)
from web.serialization import dataframe_records
from web.services import part_cost_unit_breakdown


router = APIRouter()


@router.get("/api/parts/search")
def part_search(q: str = ""):
    if len(q.strip()) < 2:
        return {"parts": []}

    try:
        rows = search_parts(q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"parts": dataframe_records(rows)}


@router.get("/api/materials/default")
def material_default(part_id: str, revision_id: str = ""):
    try:
        part_rows = get_part(part_id.strip(), revision_id)
        bom_rows = get_bom(part_id.strip(), revision_id)
        operation_rows = get_operations(part_id.strip(), revision_id)
        has_manufacturing_detail = not bom_rows.empty or not operation_rows.empty
        history_rows = get_current_or_last_part_cost(part_id.strip(), revision_id)
        po_rows = get_last_material_po(part_id.strip(), revision_id)
        retail_rows = get_current_retail_price(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    part = dataframe_records(part_rows)
    retail = dataframe_records(retail_rows)
    retail_unit_price = retail[0].get("retail_unit_price") if retail else None
    route_status = {
        "has_manufacturing_detail": has_manufacturing_detail,
        "manufacturing_material_count": len(bom_rows),
        "manufacturing_operation_count": len(operation_rows),
    }
    if has_manufacturing_detail and not history_rows.empty:
        history = dataframe_records(history_rows)[0]
        history_row = history_rows.iloc[0]
        return {
            **route_status,
            "part": part[0] if part else None,
            "source": "manufactured_history",
            "unit_cost": history.get("ucpUnitRawCost"),
            **part_cost_unit_breakdown(history_row),
            "retail_unit_price": retail_unit_price,
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": history.get("ucpDateCosted"),
            "material_markup": None,
            "manufactured_part_cost_id": history.get("ucpPartCostID"),
            "manufactured_part_cost_is_current": bool(history.get("ucpIsCurrent")),
        }

    if has_manufacturing_detail:
        return {
            **route_status,
            "part": part[0] if part else None,
            "source": "manufactured_route",
            "unit_cost": None,
            "retail_unit_price": retail_unit_price,
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "material_markup": None,
        }

    if not po_rows.empty:
        po = dataframe_records(po_rows)[0]
        return {
            **route_status,
            "part": part[0] if part else None,
            "source": "purchase_order",
            "unit_cost": po.get("pmlInventoryUnitCostBase")
            or po.get("pmlPurchaseUnitCostBase"),
            "retail_unit_price": retail_unit_price,
            "minimum_purchase_qty": 1,
            "last_po": f"{po.get('pmlPurchaseOrderID')}-{po.get('pmlPurchaseOrderLineID')}",
            "last_po_cost": po.get("pmlInventoryUnitCostBase")
            or po.get("pmlPurchaseUnitCostBase"),
            "last_po_purchase_unit_cost": po.get("pmlPurchaseUnitCostBase"),
            "last_po_conversion_factor": po.get("pmlConversionFactor"),
            "last_po_purchase_unit": po.get("pmlPurchaseUnitOfMeasure")
            or po.get("pmlPurchaseUnitOfMeasureID")
            or po.get("pmlPurchaseUOM")
            or po.get("pmlPurchaseUM"),
            "last_po_inventory_unit": po.get("pmlInventoryUnitOfMeasure")
            or po.get("pmlInventoryUnitOfMeasureID")
            or po.get("pmlInventoryUOM")
            or po.get("pmlInventoryUM"),
            "last_po_date": po.get("pmlDueDate") or po.get("pmlCreatedDate"),
            "material_markup": None,
        }

    if not history_rows.empty:
        history = dataframe_records(history_rows)[0]
        history_row = history_rows.iloc[0]
        return {
            **route_status,
            "part": part[0] if part else None,
            "source": "manufactured_history",
            "unit_cost": history.get("ucpUnitRawCost"),
            **part_cost_unit_breakdown(history_row),
            "retail_unit_price": retail_unit_price,
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": history.get("ucpDateCosted"),
            "material_markup": None,
            "manufactured_part_cost_id": history.get("ucpPartCostID"),
            "manufactured_part_cost_is_current": bool(history.get("ucpIsCurrent")),
        }

    return {
        **route_status,
        "part": part[0] if part else None,
        "source": "erp_estimate",
        "unit_cost": None,
        "retail_unit_price": retail_unit_price,
        "minimum_purchase_qty": 0,
        "last_po": None,
        "last_po_cost": None,
        "last_po_date": None,
        "material_markup": None,
    }


@router.get("/api/operations/search")
def operation_search(q: str = ""):
    if len(q.strip()) < 2:
        return {"operations": []}

    try:
        rows = search_operations(q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"operations": dataframe_records(rows)}


@router.get("/api/work-centers/search")
def work_center_search(q: str = ""):
    if len(q.strip()) < 1:
        return {"work_centers": []}

    try:
        rows = search_work_centers(q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"work_centers": dataframe_records(rows)}


@router.get("/api/processes/search")
def process_search(q: str = "", work_center_id: str = ""):
    if len(q.strip()) < 1 and not work_center_id.strip():
        return {"processes": []}

    try:
        rows = search_processes(q.strip(), work_center_id.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"processes": dataframe_records(rows)}


@router.get("/api/purchase-orders/material")
def material_purchase_orders(part_id: str, revision_id: str = ""):
    try:
        rows = get_material_pos(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"purchase_orders": dataframe_records(rows)}


@router.get("/api/jobs/recent")
def recent_jobs(part_id: str, revision_id: str = ""):
    try:
        rows = get_recent_jobs(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"jobs": dataframe_records(rows)}


@router.get("/api/jobs/operation")
def operation_jobs(part_id: str, revision_id: str = "", operation_sequence: int = 0):
    if not operation_sequence:
        return {"jobs": []}

    try:
        rows = get_operation_jobs(part_id.strip(), revision_id, operation_sequence)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"jobs": dataframe_records(rows)}


@router.get("/api/purchase-orders/external-operation")
def external_operation_purchase_orders(
    part_id: str,
    revision_id: str = "",
    method_operation_id: int = 0,
):
    try:
        rows = get_external_operation_pos(
            part_id.strip(), revision_id, method_operation_id
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"purchase_orders": dataframe_records(rows)}


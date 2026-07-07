from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from costing.calculator import build_part_cost
from costing.persistence import costing_run_from_records, mark_part_cost_current, save_costing_run, save_costing_settings
from utils.queries import get_bom, get_current_or_last_part_cost, get_external_operation_pos, get_global_cost_defaults, get_last_material_po, get_machine_cost_defaults, get_markup_breaks, get_material_pos, get_operations, get_part, get_part_cost, get_part_cost_history, get_saved_material_lines, get_saved_operation_lines, search_operations, search_parts


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Product Cost Calculator", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MarkupBreak(BaseModel):
    breakQty: float = Field(..., gt=0)
    material: float = Field(1, gt=0)
    labor: float = Field(1, gt=0)
    machine: float = Field(1, gt=0)
    external: float = Field(1, gt=0)
    additional: float = Field(1, gt=0)


class CostRequest(BaseModel):
    part_id: str = Field(..., min_length=1)
    revision_id: str = ""
    quantity: float = Field(1, gt=0)
    markup_breaks: list[MarkupBreak] | None = None
    costed_by: str | None = None
    notes: str | None = None
    make_current: bool = False


class SettingsRequest(BaseModel):
    part_id: str | None = None
    revision_id: str = ""
    markup_breaks: list[MarkupBreak] = []
    global_defaults: dict | None = None
    machine_defaults: dict = {}
    shift_settings: dict | None = None


class CostRunSaveRequest(BaseModel):
    part_cost: dict
    operation_lines: list[dict] = []
    material_lines: list[dict] = []
    make_current: bool = False


class CurrentCostRequest(BaseModel):
    part_cost_id: int


def dataframe_records(df: pd.DataFrame):
    if df.empty:
        return []

    clean_df = df.where(pd.notna(df), None)
    return [serialize_value(row) for row in clean_df.to_dict(orient="records")]


def serialize_value(value):
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, memoryview):
        return value.tobytes().hex()

    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()

    if pd.isna(value):
        return None

    return value


def serialize_costing_run(costing_run):
    part_cost_records = dataframe_records(costing_run["part_cost"])
    return {
        "part_cost": part_cost_records[0] if part_cost_records else None,
        "operation_lines": dataframe_records(costing_run["operation_lines"]),
        "material_lines": dataframe_records(costing_run["material_lines"]),
    }


def build_costing_response(request: CostRequest):
    try:
        costing_run = build_part_cost(
            part_id=request.part_id.strip(),
            revision_id=request.revision_id,
            cost_quantity=request.quantity,
            costed_by=request.costed_by,
            notes=request.notes,
            markup_breaks=[item.dict() for item in request.markup_breaks] if request.markup_breaks else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return costing_run


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/parts/search")
def part_search(q: str = ""):
    if len(q.strip()) < 2:
        return {"parts": []}

    try:
        rows = search_parts(q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"parts": dataframe_records(rows)}


@app.get("/api/materials/default")
def material_default(part_id: str, revision_id: str = ""):
    try:
        part_rows = get_part(part_id.strip(), revision_id)
        has_manufacturing_detail = (
            not get_bom(part_id.strip(), revision_id).empty
            or not get_operations(part_id.strip(), revision_id).empty
        )
        history_rows = get_current_or_last_part_cost(part_id.strip(), revision_id)
        po_rows = get_last_material_po(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    part = dataframe_records(part_rows)
    if has_manufacturing_detail and not history_rows.empty:
        history = dataframe_records(history_rows)[0]
        return {
            "part": part[0] if part else None,
            "source": "manufactured_history",
            "unit_cost": history.get("ucpUnitMarkedUpCost"),
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": history.get("ucpDateCosted"),
            "material_markup": 1,
            "manufactured_part_cost_id": history.get("ucpPartCostID"),
        }

    if has_manufacturing_detail:
        return {
            "part": part[0] if part else None,
            "source": "manufactured_route",
            "unit_cost": None,
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "material_markup": 1,
        }

    if not po_rows.empty:
        po = dataframe_records(po_rows)[0]
        return {
            "part": part[0] if part else None,
            "source": "purchase_order",
            "unit_cost": po.get("pmlPurchaseUnitCostBase"),
            "minimum_purchase_qty": 1,
            "last_po": f"{po.get('pmlPurchaseOrderID')}-{po.get('pmlPurchaseOrderLineID')}",
            "last_po_cost": po.get("pmlPurchaseUnitCostBase"),
            "last_po_date": po.get("pmlDueDate") or po.get("pmlCreatedDate"),
            "material_markup": None,
        }

    if not history_rows.empty:
        history = dataframe_records(history_rows)[0]
        return {
            "part": part[0] if part else None,
            "source": "manufactured_history",
            "unit_cost": history.get("ucpUnitMarkedUpCost"),
            "minimum_purchase_qty": 0,
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": history.get("ucpDateCosted"),
            "material_markup": 1,
            "manufactured_part_cost_id": history.get("ucpPartCostID"),
        }

    return {
        "part": part[0] if part else None,
        "source": "erp_estimate",
        "unit_cost": None,
        "minimum_purchase_qty": 0,
        "last_po": None,
        "last_po_cost": None,
        "last_po_date": None,
        "material_markup": None,
    }


@app.get("/api/settings/defaults")
def settings_defaults(part_id: str = "", revision_id: str = ""):
    try:
        markup_rows = get_markup_breaks(part_id.strip() or None, revision_id)
        global_rows = get_global_cost_defaults()
        machine_rows = get_machine_cost_defaults()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    global_defaults = dataframe_records(global_rows)
    return {
        "markup_breaks": dataframe_records(markup_rows),
        "global_defaults": global_defaults[0] if global_defaults else None,
        "machine_defaults": dataframe_records(machine_rows),
    }


@app.post("/api/settings/defaults")
def save_settings_defaults(request: SettingsRequest):
    try:
        save_costing_settings(
            part_id=request.part_id,
            revision_id=request.revision_id,
            markup_breaks=[item.dict() for item in request.markup_breaks],
            global_defaults=request.global_defaults,
            machine_defaults=request.machine_defaults,
            shift_settings=request.shift_settings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True}


@app.get("/api/costs/history")
def cost_history(part_id: str, revision_id: str = ""):
    try:
        rows = get_part_cost_history(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"history": dataframe_records(rows)}


@app.get("/api/costs/{part_cost_id}")
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

    return serialize_costing_run(costing_run)


@app.post("/api/costs/current")
def set_current_cost(request: CurrentCostRequest):
    try:
        mark_part_cost_current(request.part_cost_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True}


@app.get("/api/operations/search")
def operation_search(q: str = ""):
    if len(q.strip()) < 2:
        return {"operations": []}

    try:
        rows = search_operations(q.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"operations": dataframe_records(rows)}


@app.post("/api/costs/calculate")
def calculate_cost(request: CostRequest):
    costing_run = build_costing_response(request)
    return serialize_costing_run(costing_run)


@app.get("/api/purchase-orders/material")
def material_purchase_orders(part_id: str, revision_id: str = ""):
    try:
        rows = get_material_pos(part_id.strip(), revision_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"purchase_orders": dataframe_records(rows)}


@app.get("/api/purchase-orders/external-operation")
def external_operation_purchase_orders(
    part_id: str,
    revision_id: str = "",
    method_operation_id: int = 0,
):
    try:
        rows = get_external_operation_pos(part_id.strip(), revision_id, method_operation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"purchase_orders": dataframe_records(rows)}


@app.post("/api/costs/save")
def save_cost(request: CostRequest):
    costing_run = build_costing_response(request)

    try:
        part_cost_id = save_costing_run(costing_run, make_current=request.make_current)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = serialize_costing_run(costing_run)
    response["part_cost_id"] = part_cost_id
    return response


@app.post("/api/costs/save-run")
def save_cost_run(request: CostRunSaveRequest):
    costing_run = costing_run_from_records(
        part_cost=request.part_cost,
        operation_lines=request.operation_lines,
        material_lines=request.material_lines,
    )

    try:
        part_cost_id = save_costing_run(costing_run, make_current=request.make_current)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = serialize_costing_run(costing_run)
    response["part_cost_id"] = part_cost_id
    return response


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")

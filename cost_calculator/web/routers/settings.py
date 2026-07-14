"""Costing-default read and write routes."""

import pandas as pd
from fastapi import APIRouter, HTTPException

from costing.persistence import save_costing_settings
from utils.queries import (
    get_global_cost_defaults,
    get_machine_cost_defaults,
    get_markup_break_rows,
)
from web.schemas import SettingsRequest
from web.serialization import dataframe_records


router = APIRouter()


@router.get("/api/settings/defaults")
def settings_defaults(part_id: str = "", revision_id: str = ""):
    try:
        scoped_part_id = part_id.strip() or None
        global_markup_rows = get_markup_break_rows()
        part_markup_rows = (
            get_markup_break_rows(scoped_part_id, revision_id)
            if scoped_part_id
            else pd.DataFrame()
        )
        markup_rows = (
            part_markup_rows if not part_markup_rows.empty else global_markup_rows
        )
        global_rows = get_global_cost_defaults()
        machine_rows = get_machine_cost_defaults()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    global_defaults = dataframe_records(global_rows)
    return {
        "markup_breaks": dataframe_records(markup_rows),
        "global_markup_breaks": dataframe_records(global_markup_rows),
        "part_markup_breaks": dataframe_records(part_markup_rows),
        "markup_break_scope": "part" if not part_markup_rows.empty else "global",
        "global_defaults": global_defaults[0] if global_defaults else None,
        "machine_defaults": dataframe_records(machine_rows),
    }


@router.post("/api/settings/defaults")
def save_settings_defaults(request: SettingsRequest):
    try:
        save_costing_settings(
            part_id=request.part_id,
            revision_id=request.revision_id,
            markup_breaks=[item.dict() for item in request.markup_breaks],
            global_markup_breaks=(
                [item.dict() for item in request.global_markup_breaks]
                if request.global_markup_breaks is not None
                else None
            ),
            part_markup_breaks=(
                [item.dict() for item in request.part_markup_breaks]
                if request.part_markup_breaks is not None
                else None
            ),
            markup_break_scope=request.markup_break_scope,
            global_defaults=request.global_defaults,
            machine_defaults=request.machine_defaults,
            shift_settings=request.shift_settings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True}


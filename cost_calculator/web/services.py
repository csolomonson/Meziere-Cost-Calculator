"""Application services used by the HTTP route layer."""

import json

import pandas as pd
from fastapi import HTTPException

from costing.calculator import build_part_cost
from utils.queries import get_current_retail_prices, get_part_cost
from web.schemas import CostRequest
from web.serialization import dataframe_records, parse_json_list, serialize_value


def serialize_costing_run(costing_run):
    part_cost_records = dataframe_records(costing_run["part_cost"])
    if part_cost_records:
        attach_retail_price_levels(part_cost_records[0])
    return {
        "part_cost": part_cost_records[0] if part_cost_records else None,
        "operation_lines": dataframe_records(costing_run["operation_lines"]),
        "material_lines": dataframe_records(costing_run["material_lines"]),
    }


def attach_retail_price_levels(part_cost):
    snapshot = parse_json_list(part_cost.get("ucpRetailPriceLevelsJson"))
    if snapshot:
        part_cost["ucpRetailPrices"] = snapshot
        list_price = next(
            (
                row.get("retail_unit_price")
                for row in snapshot
                if row.get("imiCustomerGroupID") == "CG01"
            ),
            None,
        )
        if list_price is not None:
            part_cost["ucpRetailUnitPrice"] = list_price
        return

    try:
        rows = get_current_retail_prices(
            part_cost.get("ucpPartID") or "",
            part_cost.get("ucpPartRevision") or "",
        )
    except Exception:
        rows = pd.DataFrame()
    levels = dataframe_records(rows)
    if levels:
        part_cost["ucpRetailPrices"] = levels
        list_price = next(
            (
                row.get("retail_unit_price")
                for row in levels
                if row.get("imiCustomerGroupID") == "CG01"
            ),
            None,
        )
        if list_price is not None:
            part_cost["ucpRetailUnitPrice"] = list_price
    elif part_cost.get("ucpRetailUnitPrice") is not None:
        part_cost["ucpRetailPrices"] = [
            {
                "imiCustomerGroupID": "CG01",
                "price_label": "LIST",
                "retail_unit_price": part_cost.get("ucpRetailUnitPrice"),
            }
        ]


def build_costing_response(request: CostRequest, costed_by: str):
    try:
        costing_run = build_part_cost(
            part_id=request.part_id.strip(),
            revision_id=request.revision_id,
            cost_quantity=request.quantity,
            costed_by=costed_by,
            notes=request.notes,
            markup_breaks=(
                [item.dict() for item in request.markup_breaks]
                if request.markup_breaks
                else None
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    enrich_part_cost_retail_snapshot(costing_run)
    return costing_run


def enrich_part_cost_retail_snapshot(costing_run):
    part_cost = costing_run.get("part_cost")
    if part_cost is None or part_cost.empty:
        return
    index = part_cost.index[0]
    part_id = part_cost.at[index, "ucpPartID"] if "ucpPartID" in part_cost.columns else ""
    revision_id = (
        part_cost.at[index, "ucpPartRevision"]
        if "ucpPartRevision" in part_cost.columns
        else ""
    )
    levels = dataframe_records(get_current_retail_prices(part_id or "", revision_id or ""))
    if levels:
        part_cost.at[index, "ucpRetailPriceLevelsJson"] = json.dumps(levels, default=str)


def part_cost_unit_breakdown(part_cost):
    quantity = serialize_value(part_cost.get("ucpCostQuantity")) or 1
    if not quantity:
        quantity = 1
    fields = [
        ("materials_raw_unit_cost", "ucpMaterialsRawCost"),
        ("machine_raw_unit_cost", "ucpMachineTimeRawCost"),
        ("labor_raw_unit_cost", "ucpLaborRawCost"),
        ("external_raw_unit_cost", "ucpExternalOperationsRawCost"),
        ("additional_raw_unit_cost", "ucpAdditionalRawCost"),
    ]
    breakdown = {
        key: (serialize_value(part_cost.get(field)) or 0) / quantity
        for key, field in fields
    }
    if not any(breakdown.values()):
        breakdown["materials_raw_unit_cost"] = serialize_value(
            part_cost.get("ucpUnitRawCost")
        ) or 0
    return breakdown


MATERIAL_BREAKDOWN_FIELDS = [
    ("materials_raw_unit_cost", "ucmMaterialsRawCost"),
    ("machine_raw_unit_cost", "ucmMachineTimeRawCost"),
    ("labor_raw_unit_cost", "ucmLaborRawCost"),
    ("external_raw_unit_cost", "ucmExternalOperationsRawCost"),
    ("additional_raw_unit_cost", "ucmAdditionalRawCost"),
]


def enrich_material_lines_from_child_costs(material_lines):
    if material_lines.empty or "ucmManufacturedPartCostID" not in material_lines.columns:
        return material_lines

    material_lines = material_lines.copy()
    for _, column in MATERIAL_BREAKDOWN_FIELDS:
        if column not in material_lines.columns:
            material_lines[column] = 0.0

    for index, line in material_lines.iterrows():
        child_part_cost_id = line.get("ucmManufacturedPartCostID")
        if child_part_cost_id is None or pd.isna(child_part_cost_id):
            continue

        try:
            child_rows = get_part_cost(int(child_part_cost_id))
        except Exception:
            continue
        if child_rows.empty:
            continue

        child = child_rows.iloc[0]
        breakdown = part_cost_unit_breakdown(child)
        required_quantity = serialize_value(line.get("ucmTotalQuantityRequired"))
        if not required_quantity:
            required_quantity = (
                serialize_value(line.get("ucmQtyPerAssembly")) or 0
            ) * (serialize_value(line.get("ucmCostQuantity")) or 1)

        raw_total = 0.0
        for unit_key, line_column in MATERIAL_BREAKDOWN_FIELDS:
            bucket_total = (breakdown.get(unit_key) or 0) * (required_quantity or 0)
            material_lines.at[index, line_column] = bucket_total
            raw_total += bucket_total

        material_lines.at[index, "ucmUnitCost"] = serialize_value(
            child.get("ucpUnitRawCost")
        ) or 0
        material_lines.at[index, "ucmRawCost"] = raw_total
        material_lines.at[index, "ucmCostSource"] = "manufactured_history"
        material_lines.at[index, "ucmIsPurchased"] = False
        material_lines.at[index, "ucmManufacturedPartCostIsCurrent"] = bool(
            serialize_value(child.get("ucpIsCurrent"))
        )

    return material_lines


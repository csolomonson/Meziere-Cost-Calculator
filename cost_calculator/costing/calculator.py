from datetime import UTC, datetime

import pandas as pd

from costing.common import first_value, number
from costing.materials import build_material_cost_lines, update_material_costs
from costing.operations import build_operation_cost_lines, update_internal_costs
from utils.queries import get_markup_breaks, get_part


DEFAULT_MARKUP_BREAKS = [
    {
        "breakQty": 1,
        "material": 1.25,
        "labor": 1.15,
        "machine": 1.15,
        "external": 1.25,
        "additional": 1.15,
    },
    {
        "breakQty": 10,
        "material": 1.25,
        "labor": 1.15,
        "machine": 1.15,
        "external": 1.25,
        "additional": 1.15,
    },
    {
        "breakQty": 100,
        "material": 1.25,
        "labor": 1.15,
        "machine": 1.15,
        "external": 1.25,
        "additional": 1.15,
    },
    {
        "breakQty": 1000,
        "material": 1.25,
        "labor": 1.15,
        "machine": 1.15,
        "external": 1.25,
        "additional": 1.15,
    },
    {
        "breakQty": 10000,
        "material": 1.25,
        "labor": 1.15,
        "machine": 1.15,
        "external": 1.25,
        "additional": 1.15,
    },
]


def active_markup_break(markup_breaks, cost_quantity):
    breaks = markup_breaks or []
    sorted_breaks = sorted(breaks, key=lambda row: number(row.get("breakQty"), 0.0))
    if not sorted_breaks:
        return {}

    active = sorted_breaks[0]
    for row in sorted_breaks:
        if number(cost_quantity, 0.0) >= number(row.get("breakQty"), 0.0):
            active = row
    return active


def apply_markup_breaks(operation_lines, material_lines, markup_breaks, cost_quantity):
    if not markup_breaks:
        return operation_lines, material_lines

    active = active_markup_break(markup_breaks, cost_quantity)

    material_lines = material_lines.copy()
    if not material_lines.empty:
        default_material_markup = number(active.get("material"), 1.0)
        for index, line in material_lines.iterrows():
            cost_source = str(line.get("ucmCostSource") or "")
            if cost_source.startswith("manufactured_"):
                continue
            material_lines.at[index, "ucmMaterialMarkup"] = default_material_markup

    operation_lines = operation_lines.copy()
    if not operation_lines.empty:
        operation_lines["ucoLaborMarkup"] = number(active.get("labor"), 1.0)
        operation_lines["ucoMachineCostMarkup"] = number(active.get("machine"), 1.0)
        operation_lines["ucoExternalOperationMarkup"] = number(active.get("external"), 1.0)
        operation_lines["ucoAdditionalCostMarkup"] = number(active.get("additional"), 1.0)

    return operation_lines, material_lines


def build_part_cost(
    part_id,
    revision_id="",
    cost_quantity=1,
    costed_by=None,
    notes=None,
    part_cost_id=None,
    markup_breaks=None,
):
    if markup_breaks is None:
        markup_breaks = dataframe_records(get_markup_breaks(part_id, revision_id))

    part_df = get_part(part_id, revision_id)

    operation_lines = build_operation_cost_lines(
        part_id=part_id,
        revision_id=revision_id,
        part_cost_id=part_cost_id,
        cost_quantity=cost_quantity,
    )

    material_lines = build_material_cost_lines(
        part_id=part_id,
        revision_id=revision_id,
        part_cost_id=part_cost_id,
        cost_quantity=cost_quantity,
    )

    operation_lines, material_lines = apply_markup_breaks(
        operation_lines=operation_lines,
        material_lines=material_lines,
        markup_breaks=markup_breaks,
        cost_quantity=cost_quantity,
    )
    operation_lines = update_internal_costs(operation_lines)
    material_lines = update_material_costs(material_lines)

    part_cost = summarize_part_cost(
        part_df=part_df,
        part_id=part_id,
        revision_id=revision_id,
        cost_quantity=cost_quantity,
        operation_lines=operation_lines,
        material_lines=material_lines,
        costed_by=costed_by,
        notes=notes,
        part_cost_id=part_cost_id,
    )

    return {
        "part_cost": part_cost,
        "operation_lines": operation_lines,
        "material_lines": material_lines,
    }


def summarize_part_cost(
    part_df,
    part_id,
    revision_id,
    cost_quantity,
    operation_lines,
    material_lines,
    costed_by=None,
    notes=None,
    part_cost_id=None,
):
    materials_raw = sum_column(material_lines, "ucmRawCost")
    materials_marked_up = sum_column(material_lines, "ucmMarkedUpCost")

    machine_raw = sum_column(operation_lines, "ucoMachineRawCost")
    machine_marked_up = sum_column(operation_lines, "ucoMachineMarkedUpCost")

    labor_raw = sum_column(operation_lines, "ucoLaborRawCost")
    labor_marked_up = sum_column(operation_lines, "ucoLaborMarkedUpCost")

    external_raw = sum_column(operation_lines, "ucoExternalOperationRawCost")
    external_marked_up = sum_column(operation_lines, "ucoExternalOperationMarkedUpCost")

    additional_raw = sum_column(operation_lines, "ucoAdditionalCostRawCost")
    additional_marked_up = sum_column(operation_lines, "ucoAdditionalCostMarkedUpCost")

    total_raw = materials_raw + machine_raw + labor_raw + external_raw + additional_raw
    total_marked_up = (
        materials_marked_up
        + machine_marked_up
        + labor_marked_up
        + external_marked_up
        + additional_marked_up
    )

    safe_quantity = number(cost_quantity, 0.0)
    unit_raw = total_raw / safe_quantity if safe_quantity else 0.0
    unit_marked_up = total_marked_up / safe_quantity if safe_quantity else 0.0

    return pd.DataFrame([{
        "ucpPartCostID": part_cost_id,
        "ucpPartID": part_id,
        "ucpPartRevision": revision_id,
        "ucpPartDescription": first_value(part_df, "impPartShortDescription"),
        "ucpCostQuantity": cost_quantity,
        "ucpDateCosted": datetime.now(UTC),
        "ucpCostedBy": costed_by,
        "ucpMaterialsRawCost": materials_raw,
        "ucpMaterialsMarkedUpCost": materials_marked_up,
        "ucpMachineTimeRawCost": machine_raw,
        "ucpMachineTimeMarkedUpCost": machine_marked_up,
        "ucpLaborRawCost": labor_raw,
        "ucpLaborMarkedUpCost": labor_marked_up,
        "ucpExternalOperationsRawCost": external_raw,
        "ucpExternalOperationsMarkedUpCost": external_marked_up,
        "ucpAdditionalRawCost": additional_raw,
        "ucpAdditionalMarkedUpCost": additional_marked_up,
        "ucpTotalRawCost": total_raw,
        "ucpTotalMarkedUpCost": total_marked_up,
        "ucpUnitRawCost": unit_raw,
        "ucpUnitMarkedUpCost": unit_marked_up,
        "ucpNotes": notes,
    }])


def sum_column(df, column):
    if df.empty or column not in df.columns:
        return 0.0

    return float(df[column].fillna(0).sum())


def dataframe_records(df):
    if df.empty:
        return []

    return df.where(pd.notna(df), None).to_dict(orient="records")

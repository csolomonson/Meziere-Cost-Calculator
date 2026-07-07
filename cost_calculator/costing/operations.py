import math

import pandas as pd

from costing.common import markup_multiplier, number
from utils.queries import get_default_costs, get_last_external_operation_po, get_operations


DEFAULT_COST_COLUMNS = [
    "ucdDefaultLaborHourlyCost",
    "ucdDefaultMachineRunningHourlyCost",
    "ucdDefaultMachineOccupiedHourlyCost",
    "ucdDefaultBatchResetTimeHours",
    "ucdDefaultBatchIdleTimeHours",
    "ucdDefaultMaterialMarkup",
    "ucdDefaultLaborMarkup",
    "ucdDefaultMachineCostMarkup",
    "ucdDefaultExternalOperationMarkup",
    "ucdDefaultAdditionalCostMarkup",
]

OPERATION_COST_COLUMNS = [
    "ucoPartOperationLineID",
    "ucoPartCostID",
    "ucoCostQuantity",
    "ucoQuantityPerAssembly",
    "ucoWorkCenterID",
    "ucoOperationID",
    "ucoOperationDescription",
    "ucoSetupTimeHours",
    "ucoCycleTimeHours",
    "ucoBatchSize",
    "ucoBatchTimeHours",
    "ucoAutomated",
    "ucoMachineRunningHourlyCost",
    "ucoMachineOccupiedHourlyCost",
    "ucoMachineCostMarkup",
    "ucoSetupLaborRate",
    "ucoBatchResetTimeHours",
    "ucoBatchIdleTimeHours",
    "ucoUseAfterHoursIdle",
    "ucoStartTime",
    "ucoAfterHoursIdleRateMultiplier",
    "ucoAfterHoursIdleTimeHours",
    "ucoBatchResetLaborRate",
    "ucoLaborMarkup",
    "ucoExternalJob",
    "ucoLastPO",
    "ucoLastPOCost",
    "ucoLastPODate",
    "ucoExternalCost",
    "ucoExternalOperationMarkup",
    "ucoAdditionalCostPerPart",
    "ucoAdditionalCostTotal",
    "ucoAdditionalCostMarkup",
    "ucoAdditionalCostRawCost",
    "ucoAdditionalCostMarkedUpCost",
    "ucoMachineRawCost",
    "ucoMachineMarkedUpCost",
    "ucoLaborRawCost",
    "ucoLaborMarkedUpCost",
    "ucoExternalOperationRawCost",
    "ucoExternalOperationMarkedUpCost",
    "ucoLineRawCost",
    "ucoLineMarkedUpCost",
]

DEFAULT_FALLBACKS = {
    "ucdDefaultLaborHourlyCost": 0.0,
    "ucdDefaultMachineRunningHourlyCost": 0.0,
    "ucdDefaultMachineOccupiedHourlyCost": 0.0,
    "ucdDefaultBatchResetTimeHours": 0.0,
    "ucdDefaultBatchIdleTimeHours": 0.0,
    "ucdDefaultMaterialMarkup": 1.0,
    "ucdDefaultLaborMarkup": 1.0,
    "ucdDefaultMachineCostMarkup": 1.0,
    "ucdDefaultExternalOperationMarkup": 1.0,
    "ucdDefaultAdditionalCostMarkup": 1.0,
}


def normalize_default_costs(defaults_df):
    defaults_df = defaults_df.copy()

    if "ucdWorkCenterID" not in defaults_df.columns:
        defaults_df["ucdWorkCenterID"] = "__GLOBAL__"

    if "ucdMinimumQuantity" not in defaults_df.columns:
        defaults_df["ucdMinimumQuantity"] = 1

    for column, fallback in DEFAULT_FALLBACKS.items():
        if column not in defaults_df.columns:
            defaults_df[column] = fallback

    if defaults_df.empty:
        defaults_df = pd.DataFrame([{
            "ucdWorkCenterID": "__GLOBAL__",
            "ucdMinimumQuantity": 1,
            **DEFAULT_FALLBACKS,
        }])

    return defaults_df


def get_best_default_row(defaults_df, work_center_id, cost_quantity):
    defaults_df = normalize_default_costs(defaults_df)
    matches = defaults_df[
        (defaults_df["ucdWorkCenterID"] == work_center_id)
        & (defaults_df["ucdMinimumQuantity"] <= cost_quantity)
    ]

    if matches.empty:
        return None

    matches = matches.sort_values("ucdMinimumQuantity", ascending=False)
    return matches.iloc[0]


def resolve_defaults_for_work_center(defaults_df, work_center_id, cost_quantity):
    defaults_df = normalize_default_costs(defaults_df)
    global_row = get_best_default_row(
        defaults_df=defaults_df,
        work_center_id="__GLOBAL__",
        cost_quantity=cost_quantity,
    )

    if global_row is None:
        raise ValueError(
            "No __GLOBAL__ default row found for this quantity. "
            "Add one DefaultCosts row with ucdWorkCenterID='__GLOBAL__'."
        )

    work_center_row = get_best_default_row(
        defaults_df=defaults_df,
        work_center_id=work_center_id,
        cost_quantity=cost_quantity,
    )

    resolved = {}
    for col in DEFAULT_COST_COLUMNS:
        if work_center_row is not None and pd.notna(work_center_row[col]):
            resolved[col] = work_center_row[col]
        elif pd.notna(global_row[col]):
            resolved[col] = global_row[col]
        else:
            resolved[col] = DEFAULT_FALLBACKS[col]

    return resolved


def production_standard_to_cycle_time_hours(production_standard):
    production_standard = number(production_standard, 0.0)

    if production_standard == 0:
        return 0.0

    return production_standard / 60


def resolve_external_operation_cost(part_id, revision_id, op, quantity):
    po_df = get_last_external_operation_po(
        part_id=part_id,
        revision_id=revision_id,
        method_operation_id=op.get("imoMethodOperationID"),
    )

    if po_df.empty:
        return {
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "external_cost": 0.0,
        }

    po = po_df.iloc[0]
    unit_cost = number(po.get("pmlPurchaseUnitCostBase"), 0.0)
    setup_charge = number(po.get("pmlSetupChargeBase"), 0.0)
    external_cost = quantity * unit_cost + setup_charge
    po_date = po.get("pmlDueDate")
    if pd.isna(po_date):
        po_date = po.get("pmlCreatedDate")

    return {
        "last_po": f"{po.get('pmlPurchaseOrderID')}-{po.get('pmlPurchaseOrderLineID')}",
        "last_po_cost": unit_cost,
        "last_po_date": po_date,
        "external_cost": external_cost,
    }


def truthy(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def parse_time_to_hours(value, fallback):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return fallback

    text = str(value).strip()
    if not text:
        return fallback

    try:
        if ":" in text:
            hours_text, minutes_text = text.split(":", 1)
            return float(hours_text) + float(minutes_text[:2]) / 60
        return float(text)
    except Exception:
        return fallback


def after_hours_idle_time(start_time, occupied_hours, shift_start="06:00", shift_end="14:30"):
    occupied_hours = number(occupied_hours, 0.0)
    if occupied_hours <= 0:
        return 0.0

    shift_start_hour = parse_time_to_hours(shift_start, 6.0)
    shift_end_hour = parse_time_to_hours(shift_end, 14.5)
    shift_length = shift_end_hour - shift_start_hour
    if shift_length <= 0:
        shift_length += 24

    start_hour = parse_time_to_hours(start_time, shift_start_hour)
    while start_hour < shift_start_hour:
        start_hour += 24
    while start_hour >= shift_start_hour + 24:
        start_hour -= 24

    end_hour = start_hour + occupied_hours
    shift_day = math.floor((end_hour - shift_start_hour) / 24)
    current_shift_start = shift_start_hour + shift_day * 24
    current_shift_end = current_shift_start + shift_length

    if current_shift_start <= end_hour <= current_shift_end:
        return 0.0

    if end_hour < current_shift_start:
        return current_shift_start - end_hour

    return current_shift_start + 24 - end_hour


def build_operation_cost_lines(
    part_id,
    revision_id="",
    part_cost_id=None,
    cost_quantity=1,
    batch_size=1,
):
    erp_ops = get_operations(part_id, revision_id)
    defaults_df = get_default_costs()

    if erp_ops.empty:
        return pd.DataFrame(columns=OPERATION_COST_COLUMNS)

    rows = []

    for _, op in erp_ops.iterrows():
        setup_hours = number(op.get("imoSetupHours"), 0.0)
        qty_per_assembly = number(op.get("imoQuantityPerAssembly"), 1.0)
        cycle_time_hours = production_standard_to_cycle_time_hours(
            op.get("imoProductionStandard")
        )
        run_time_hours = cycle_time_hours * qty_per_assembly * cost_quantity

        defaults = resolve_defaults_for_work_center(
            defaults_df=defaults_df,
            work_center_id=op.get("imoWorkCenterID"),
            cost_quantity=cost_quantity,
        )

        labor_hourly_cost = number(defaults["ucdDefaultLaborHourlyCost"], 0.0)
        external_job = number(op.get("imoOperationType"), 0) == 2
        operation_quantity = cost_quantity * qty_per_assembly
        external_cost = {
            "last_po": None,
            "last_po_cost": None,
            "last_po_date": None,
            "external_cost": 0.0,
        }
        if external_job:
            external_cost = resolve_external_operation_cost(
                part_id=part_id,
                revision_id=revision_id,
                op=op,
                quantity=operation_quantity,
            )

        rows.append({
            "ucoPartOperationLineID": op.get("imoMethodOperationID"),
            "ucoPartCostID": part_cost_id,
            "ucoCostQuantity": cost_quantity,
            "ucoQuantityPerAssembly": qty_per_assembly,
            "ucoWorkCenterID": op.get("imoWorkCenterID"),
            "ucoOperationID": op.get("imoProcessID"),
            "ucoOperationDescription": op.get("imoProcessShortDescription"),
            "ucoSetupTimeHours": setup_hours,
            "ucoCycleTimeHours": cycle_time_hours,
            "ucoBatchSize": batch_size,
            "ucoBatchTimeHours": run_time_hours,
            "ucoAutomated": False,
            "ucoMachineRunningHourlyCost": number(defaults["ucdDefaultMachineRunningHourlyCost"], 0.0),
            "ucoMachineOccupiedHourlyCost": number(defaults["ucdDefaultMachineOccupiedHourlyCost"], 0.0),
            "ucoMachineCostMarkup": markup_multiplier(defaults["ucdDefaultMachineCostMarkup"]),
            "ucoSetupLaborRate": labor_hourly_cost,
            "ucoBatchResetTimeHours": number(defaults["ucdDefaultBatchResetTimeHours"], 0.0),
            "ucoBatchIdleTimeHours": number(defaults["ucdDefaultBatchIdleTimeHours"], 0.0),
            "ucoUseAfterHoursIdle": False,
            "ucoStartTime": "",
            "ucoAfterHoursIdleRateMultiplier": 1.0,
            "ucoAfterHoursIdleTimeHours": 0.0,
            "ucoBatchResetLaborRate": labor_hourly_cost,
            "ucoLaborMarkup": markup_multiplier(defaults["ucdDefaultLaborMarkup"]),
            "ucoExternalJob": external_job,
            "ucoLastPO": external_cost["last_po"],
            "ucoLastPOCost": external_cost["last_po_cost"],
            "ucoLastPODate": external_cost["last_po_date"],
            "ucoExternalCost": external_cost["external_cost"],
            "ucoExternalOperationMarkup": markup_multiplier(defaults["ucdDefaultExternalOperationMarkup"]),
            "ucoAdditionalCostPerPart": 0.0,
            "ucoAdditionalCostTotal": 0.0,
            "ucoAdditionalCostMarkup": markup_multiplier(defaults["ucdDefaultAdditionalCostMarkup"]),
            "ucoAdditionalCostRawCost": 0.0,
            "ucoAdditionalCostMarkedUpCost": 0.0,
            "ucoMachineRawCost": 0.0,
            "ucoMachineMarkedUpCost": 0.0,
            "ucoLaborRawCost": 0.0,
            "ucoLaborMarkedUpCost": 0.0,
            "ucoExternalOperationRawCost": 0.0,
            "ucoExternalOperationMarkedUpCost": 0.0,
            "ucoLineRawCost": 0.0,
            "ucoLineMarkedUpCost": 0.0,
        })

    return pd.DataFrame(rows, columns=OPERATION_COST_COLUMNS)


def update_internal_costs(op_lines_df, batch_size=1):
    op_lines_df = op_lines_df.copy()

    if op_lines_df.empty:
        return op_lines_df

    for n, line in op_lines_df.iterrows():
        cost_quantity = number(line.get("ucoCostQuantity"), 0.0)
        qty_per_assembly = number(line.get("ucoQuantityPerAssembly"), 0.0)
        quantity = cost_quantity * qty_per_assembly

        line_batch_size = number(line.get("ucoBatchSize"), batch_size)
        if line_batch_size and line_batch_size > 0 and quantity > 0:
            number_of_batches = math.ceil(quantity / line_batch_size)
        else:
            number_of_batches = 0

        number_of_resets = max(number_of_batches - 1, 0)

        raw_additional_cost = (
            quantity * number(line.get("ucoAdditionalCostPerPart"), 0.0)
            + number(line.get("ucoAdditionalCostTotal"), 0.0)
        )
        markedup_additional_cost = raw_additional_cost * markup_multiplier(
            line.get("ucoAdditionalCostMarkup")
        )

        setup_raw_cost = (
            number(line.get("ucoSetupLaborRate"), 0.0)
            * number(line.get("ucoSetupTimeHours"), 0.0)
        )
        tending_raw_cost = (
            number(line.get("ucoBatchResetLaborRate"), 0.0)
            * number_of_resets
            * number(line.get("ucoBatchResetTimeHours"), 0.0)
        )
        labor_raw_cost = setup_raw_cost + tending_raw_cost
        markedup_labor_cost = labor_raw_cost * markup_multiplier(line.get("ucoLaborMarkup"))

        cycle_time_hours = number(line.get("ucoCycleTimeHours"), 0.0)
        setup_time_hours = number(line.get("ucoSetupTimeHours"), 0.0)
        reset_time_hours = number(line.get("ucoBatchResetTimeHours"), 0.0)
        idle_time_hours = number(line.get("ucoBatchIdleTimeHours"), 0.0)

        base_machine_occupied_time = (
            setup_time_hours
            + quantity * cycle_time_hours
            + number_of_resets * (reset_time_hours + idle_time_hours)
        )
        if truthy(line.get("ucoUseAfterHoursIdle")):
            after_hours_idle_hours = after_hours_idle_time(
                line.get("ucoStartTime"),
                base_machine_occupied_time,
                line.get("ucoFirstShiftStartTime", "06:00"),
                line.get("ucoFirstShiftEndTime", "14:30"),
            )
        else:
            after_hours_idle_hours = 0.0
        machine_running_time = cycle_time_hours * quantity
        occupied_rate = number(line.get("ucoMachineOccupiedHourlyCost"), 0.0)
        after_hours_multiplier = number(line.get("ucoAfterHoursIdleRateMultiplier"), 1.0)
        machine_time_raw_cost = (
            base_machine_occupied_time * occupied_rate
            + after_hours_idle_hours * occupied_rate * after_hours_multiplier
            + machine_running_time * number(line.get("ucoMachineRunningHourlyCost"), 0.0)
        )
        markedup_machine_cost = machine_time_raw_cost * markup_multiplier(
            line.get("ucoMachineCostMarkup")
        )

        external_raw_cost = number(line.get("ucoExternalCost"), 0.0)
        markedup_external_cost = external_raw_cost * markup_multiplier(
            line.get("ucoExternalOperationMarkup")
        )

        line_is_external = bool(line.get("ucoExternalJob"))
        if line_is_external:
            labor_raw_cost = 0.0
            markedup_labor_cost = 0.0
            machine_time_raw_cost = 0.0
            markedup_machine_cost = 0.0

        line_raw_cost = (
            raw_additional_cost
            + labor_raw_cost
            + machine_time_raw_cost
            + external_raw_cost
        )
        line_markedup_cost = (
            markedup_additional_cost
            + markedup_labor_cost
            + markedup_machine_cost
            + markedup_external_cost
        )

        op_lines_df.at[n, "ucoAfterHoursIdleTimeHours"] = 0.0 if line_is_external else after_hours_idle_hours
        op_lines_df.at[n, "ucoAdditionalCostRawCost"] = raw_additional_cost
        op_lines_df.at[n, "ucoAdditionalCostMarkedUpCost"] = markedup_additional_cost
        op_lines_df.at[n, "ucoMachineRawCost"] = machine_time_raw_cost
        op_lines_df.at[n, "ucoMachineMarkedUpCost"] = markedup_machine_cost
        op_lines_df.at[n, "ucoLaborRawCost"] = labor_raw_cost
        op_lines_df.at[n, "ucoLaborMarkedUpCost"] = markedup_labor_cost
        op_lines_df.at[n, "ucoExternalOperationRawCost"] = external_raw_cost
        op_lines_df.at[n, "ucoExternalOperationMarkedUpCost"] = markedup_external_cost
        op_lines_df.at[n, "ucoLineRawCost"] = line_raw_cost
        op_lines_df.at[n, "ucoLineMarkedUpCost"] = line_markedup_cost

    return op_lines_df

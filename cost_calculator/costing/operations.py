from utils.queries import get_operations, get_default_costs
from utils.dataframes import COSTING_TABLE_COLUMNS
import pandas as pd
import math

DEFAULT_COST_COLUMNS = [
    "ucdDefaultLaborHourlyCost",
    "ucdDefaultMachineRunningHourlyCost",
    "ucdDefaultMachineOccupiedHourlyCost",
    "ucdDefaultMaterialMarkup",
    "ucdDefaultLaborMarkup",
    "ucdDefaultMachineCostMarkup",
    "ucdDefaultExternalOperationMarkup",
    "ucdDefaultAdditionalCostMarkup",
]


def get_best_default_row(defaults_df, work_center_id, cost_quantity):
    """
    Return the row for this work center with the largest minimum quantity
    less than or equal to the requested cost quantity.

    Returns None if no matching row exists.
    """
    matches = defaults_df[
        (defaults_df["ucdWorkCenterID"] == work_center_id)
        & (defaults_df["ucdMinimumQuantity"] <= cost_quantity)
    ]

    if matches.empty:
        return None

    matches = matches.sort_values("ucdMinimumQuantity", ascending=False)
    return matches.iloc[0]


def resolve_defaults_for_work_center(defaults_df, work_center_id, cost_quantity):
    """
    Resolve defaults using this rule:

    1. Find best matching work-center row.
    2. Find best matching __GLOBAL__ row.
    3. For each default column, use work-center value if present.
       Otherwise fall back to __GLOBAL__.
    """
    global_row = get_best_default_row(
        defaults_df=defaults_df,
        work_center_id="__GLOBAL__",
        cost_quantity=cost_quantity,
    )

    if global_row is None:
        raise ValueError(
            f"No __GLOBAL__ default row found for quantity {cost_quantity}. "
            "You need at least one DefaultCosts row with "
            "ucdWorkCenterID='__GLOBAL__' and ucdMinimumQuantity <= cost_quantity."
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
        else:
            resolved[col] = global_row[col]

    return resolved


def production_standard_to_cycle_time_hours(production_standard):
    """
    Assumption:
    imoProductionStandard is minutes per piece.
    """
    production_standard = production_standard or 0

    if production_standard == 0:
        return 0

    return production_standard / 60


def build_operation_cost_lines(
    part_id,
    revision_id="",
    part_cost_id=None,
    cost_quantity=1,
    batch_size=1,
):
    erp_ops = get_operations(part_id, revision_id)
    defaults_df = get_default_costs()

    rows = []

    for _, op in erp_ops.iterrows():
        setup_hours = op["imoSetupHours"] or 0
        qty_per_assembly = op["imoQuantityPerAssembly"] or 1

        cycle_time_hours = production_standard_to_cycle_time_hours(
            op["imoProductionStandard"]
        )

        # This is runtime for the requested quote quantity.
        run_time_hours = cycle_time_hours * qty_per_assembly * cost_quantity

        defaults = resolve_defaults_for_work_center(
            defaults_df=defaults_df,
            work_center_id=op["imoWorkCenterID"],
            cost_quantity=cost_quantity,
        )

        machine_running_hourly_cost = (
            defaults["ucdDefaultMachineRunningHourlyCost"] or 0
        )
        machine_occupied_hourly_cost = (
            defaults["ucdDefaultMachineOccupiedHourlyCost"] or 0
        )
        labor_hourly_cost = defaults["ucdDefaultLaborHourlyCost"] or 0

        machine_markup = defaults["ucdDefaultMachineCostMarkup"] or 0
        labor_markup = defaults["ucdDefaultLaborMarkup"] or 0
        external_operation_markup = (
            defaults["ucdDefaultExternalOperationMarkup"] or 0
        )
        additional_cost_markup = defaults["ucdDefaultAdditionalCostMarkup"] or 0

        external_job = op["imoOperationType"] == 2

        row = {
            "ucoPartOperationLineID": op["imoMethodOperationID"],
            "ucoPartCostID": part_cost_id,

            "ucoCostQuantity": cost_quantity,
            "ucoQuantityPerAssembly": qty_per_assembly,

            "ucoWorkCenterID": op["imoWorkCenterID"],
            "ucoOperationID": op["imoProcessID"],
            "ucoOperationDescription": op["imoProcessShortDescription"],

            "ucoSetupTimeHours": setup_hours,
            "ucoCycleTimeHours": cycle_time_hours,

            # Automation/operator-tending batch size.
            "ucoBatchSize": batch_size,
            "ucoBatchTimeHours": run_time_hours,

            "ucoAutomated": False,

            "ucoMachineRunningHourlyCost": machine_running_hourly_cost,
            "ucoMachineOccupiedHourlyCost": machine_occupied_hourly_cost,
            "ucoMachineCostMarkup": machine_markup,

            "ucoSetupLaborRate": labor_hourly_cost,
            "ucoBatchResetTimeHours": 0,
            "ucoBatchResetLaborRate": labor_hourly_cost,
            "ucoLaborMarkup": labor_markup,

            "ucoExternalJob": external_job,
            "ucoLastPO": None,
            "ucoLastPOCost": None,
            "ucoLastPODate": None,
            "ucoExternalCost": 0,
            "ucoExternalOperationMarkup": external_operation_markup,

            "ucoAdditionalCostPerPart": 0,
            "ucoAdditionalCostTotal": 0,
            "ucoAdditionalCostMarkup": additional_cost_markup,

            "ucoAdditionalCostRawCost": 0,
            "ucoAdditionalCostMarkedUpCost": 0,

            "ucoMachineRawCost": 0,
            "ucoMachineMarkedUpCost": 0,

            "ucoLaborRawCost": 0,
            "ucoLaborMarkedUpCost": 0,

            "ucoExternalOperationRawCost": 0,
            "ucoExternalOperationMarkedUpCost": 0,

            "ucoLineRawCost": 0,
            "ucoLineMarkedUpCost": 0,
        }

        rows.append(row)

    return pd.DataFrame(
        rows,
        columns=COSTING_TABLE_COLUMNS["OperationCostLines"],
    )

def update_internal_costs(op_lines_df, batch_size=1):
    for n, line in op_lines_df.iterrows():
        quantity = line['ucoCostQuantity'] * line['ucoQuantityPerAssembly']
        raw_additional_cost = quantity * line['ucoAdditionalCostPerPart'] + line['ucoAdditionalCostTotal']

        if batch_size and batch_size > 0:
            number_of_batches = math.ceil(quantity / batch_size)
        else:
            number_of_batches = 0

        setup_labor_hours = line['ucoSetupTimeHours'] 
        total_tending_labor_hours = (number_of_batches - 1) * line['ucoBatchResetTimeHours']
        setup_raw_cost = line['ucoSetupLaborRate'] * setup_labor_hours
        tending_raw_cost = line['ucoBatchResetLaborRate'] * total_tending_labor_hours
        labor_raw_cost = setup_raw_cost + tending_raw_cost

        machine_occupied_time = line['ucoSetupTimeHours'] + quantity * line['ucoCycleTimeHours'] + (number_of_batches - 1) * line['ucoBatchResetTimeHours']
        machine_running_time = line['ucoCycleTimeHours'] * quantity
        machine_time_raw_cost = machine_occupied_time * line['ucoMachineOccupiedHourlyCost'] + machine_running_time * line['ucoMachineRunningHourlyCost']

        markedup_additional_cost = raw_additional_cost * line['ucoAdditionalCostMarkup']
        markedup_labor_cost = labor_raw_cost * line['ucoLaborMarkup']
        markedup_machine_cost = machine_time_raw_cost *  line['ucoMachineCostMarkup']

        


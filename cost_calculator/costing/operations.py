from utils.queries import get_operations
import pandas as pd

def build_operation_cost_lines(
    part_id,
    revision_id='',
    part_cost_id=None,
    batch_size=1,
):
    erp_ops = get_operations(part_id, revision_id)

    rows = []

    for _, op in erp_ops.iterrows():
        setup_hours = op["imoSetupHours"] or 0
        production_standard = op["imoProductionStandard"] or 0

        # imoProductionStandard is assumed minutes per piece
        if production_standard and production_standard != 0:
            cycle_time_hours = production_standard / 60
        else:
            cycle_time_hours = 0

        qty_per_assembly = op["imoQuantityPerAssembly"] or 1

        batch_time_hours = cycle_time_hours * qty_per_assembly * batch_size

        row = {
            "ucoPartOperationLineID": op["imoMethodOperationID"],
            "ucoPartCostID": part_cost_id,

            "ucoWorkCenterID": op["imoWorkCenterID"],
            "ucoOperationID": op["imoProcessID"],
            "ucoOperationDescription": op["imoProcessShortDescription"],

            "ucoSetupTimeHours": setup_hours,
            "ucoCycleTimeHours": cycle_time_hours,
            "ucoBatchSize": batch_size,
            "ucoBatchTimeHours": batch_time_hours,

            "ucoAutomated": False,

            "ucoMachineRunningHourlyCost": 0,
            "ucoMachineOccupiedHourlyCost": 0,
            "ucoMachineCostMarkup": 0,

            "ucoSetupLaborRate": 0,
            "ucoBatchResetTimeHours": 0,
            "ucoBatchResetLaborRate": 0,
            "ucoLaborMarkup": 0,

            "ucoExternalJob": False,
            "ucoLastPO": None,
            "ucoLastPOCost": None,
            "ucoExternalOperationMarkup": 0,

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

    return pd.DataFrame(rows, columns=row.keys())

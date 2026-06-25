import pandas as pd

COSTING_TABLE_COLUMNS = {
    "PartCosts": [
        "ucpPartCostID",
        "ucpPartID",
        "ucpPartRevision",
        "ucpPartDescription",

        "ucpCostQuantity",

        "ucpDateCosted",
        "ucpCostedBy",

        "ucpMaterialsRawCost",
        "ucpMaterialsMarkedUpCost",

        "ucpMachineTimeRawCost",
        "ucpMachineTimeMarkedUpCost",

        "ucpLaborRawCost",
        "ucpLaborMarkedUpCost",

        "ucpExternalOperationsRawCost",
        "ucpExternalOperationsMarkedUpCost",

        "ucpAdditionalRawCost",
        "ucpAdditionalMarkedUpCost",

        "ucpTotalRawCost",
        "ucpTotalMarkedUpCost",

        "ucpUnitRawCost",
        "ucpUnitMarkedUpCost",

        "ucpNotes",
    ],

    "OperationCostLines": [
        "ucoPartOperationLineID",
        "ucoPartCostID",

        "ucoCostQuantity",

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
        "ucoBatchResetLaborRate",
        "ucoLaborMarkup",

        "ucoExternalJob",
        "ucoLastPO",
        "ucoLastPOCost",
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
    ],

    "MaterialCostLines": [
        "ucmPartMaterialLineID",
        "ucmPartCostID",

        "ucmCostQuantity",

        "ucmMaterialID",
        "ucmMaterialDescription",

        "ucmQtyPerAssembly",
        "ucmTotalQuantityRequired",

        "ucmIsPurchased",

        "ucmLastPO",
        "ucmLastPOCost",

        "ucmUnitCost",
        "ucmMinimumPurchaseQty",

        "ucmMaterialMarkup",

        "ucmRawCost",
        "ucmMarkedUpCost",
    ],

    "DefaultCosts": [
        "ucdDefaultCostID",

        "ucdWorkCenterID",
        "ucdMinimumQuantity",

        "ucdDefaultLaborHourlyCost",
        "ucdDefaultMachineRunningHourlyCost",
        "ucdDefaultMachineOccupiedHourlyCost",

        "ucdDefaultMaterialMarkup",
        "ucdDefaultLaborMarkup",
        "ucdDefaultMachineCostMarkup",
        "ucdDefaultExternalOperationMarkup",
        "ucdDefaultAdditionalCostMarkup",
    ],
}


def empty_costing_dataframe(table_name: str) -> pd.DataFrame:
    """
    Return an empty DataFrame for one costing table.

    Example:
        part_costs_df = empty_costing_dataframe("PartCosts")
    """
    if table_name not in COSTING_TABLE_COLUMNS:
        valid_tables = ", ".join(COSTING_TABLE_COLUMNS.keys())
        raise ValueError(
            f"Unknown table_name '{table_name}'. "
            f"Expected one of: {valid_tables}"
        )

    return pd.DataFrame(columns=COSTING_TABLE_COLUMNS[table_name])


def empty_costing_dataframes() -> dict[str, pd.DataFrame]:
    """
    Return empty DataFrames for all costing tables.

    Example:
        dfs = empty_costing_dataframes()
        operation_lines_df = dfs["OperationCostLines"]
    """
    return {
        table_name: pd.DataFrame(columns=columns)
        for table_name, columns in COSTING_TABLE_COLUMNS.items()
    }
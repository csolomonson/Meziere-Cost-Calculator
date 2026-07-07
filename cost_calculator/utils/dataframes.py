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
        "ucmCostSource",
        "ucmManufacturedPartCostID",
        "ucmLastPO",
        "ucmLastPOCost",
        "ucmLastPODate",
        "ucmUnitCost",
        "ucmMinimumPurchaseQty",
        "ucmMaterialMarkup",
        "ucmWasteQuantity",
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
    "CostingSettings": [
        "ucsSettingKey",
        "ucsSettingValue",
        "ucsUpdatedDate",
    ],
}


def empty_costing_dataframe(table_name: str) -> pd.DataFrame:
    if table_name not in COSTING_TABLE_COLUMNS:
        valid_tables = ", ".join(COSTING_TABLE_COLUMNS.keys())
        raise ValueError(
            f"Unknown table_name '{table_name}'. "
            f"Expected one of: {valid_tables}"
        )

    return pd.DataFrame(columns=COSTING_TABLE_COLUMNS[table_name])


def empty_costing_dataframes() -> dict[str, pd.DataFrame]:
    return {
        table_name: pd.DataFrame(columns=columns)
        for table_name, columns in COSTING_TABLE_COLUMNS.items()
    }

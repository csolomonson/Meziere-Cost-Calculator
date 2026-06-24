import pandas as pd

COSTING_TABLE_COLUMNS = {
    "PartCosts": [
        "ucpPartCostID",
        "ucpPartID",
        "ucpPartRevision",
        "ucpPartDescription",
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

        "ucpTotalRawCost",
        "ucpTotalMarkedUpCost",

        "ucpNotes",
    ],

    "OperationCostLines": [
        "ucoPartOperationLineID",
        "ucoPartCostID",

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

        "ucmMaterialID",
        "ucmMaterialDescription",

        "ucmQtyPerAssembly",
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
        "ucdWorkCenterID",

        "ucdDefaultLaborHourlyCost",
        "ucdDefaultMachineRunningHourlyCost",
        "ucdDefaultMachineOccupiedHourlyCost",

        "ucdDefaultMaterialMarkup",
        "ucdDefaultLaborMarkup",
        "ucdDefaultMachineCostMarkup",
        "ucdDefaultExternalOperationMarkup",
    ],
}


def empty_costing_dataframes():
    return {
        table_name: pd.DataFrame(columns=columns)
        for table_name, columns in COSTING_TABLE_COLUMNS.items()
    }
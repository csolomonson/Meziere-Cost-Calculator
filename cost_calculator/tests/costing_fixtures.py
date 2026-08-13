"""Shared DataFrame builders for costing tests."""

import pandas as pd


PART_ID = "WPBBC01U"
REVISION_ID = ""
COST_QUANTITY = 10000


def wpbbc01u_defaults_df():
    return pd.DataFrame([
        {
            "ucdWorkCenterID": "__GLOBAL__",
            "ucdMinimumQuantity": 1,
            "ucdDefaultLaborHourlyCost": 25.0,
            "ucdDefaultMachineRunningHourlyCost": 20.0,
            "ucdDefaultMachineOccupiedHourlyCost": 5.0,
            "ucdDefaultMaterialMarkup": 1.25,
            "ucdDefaultLaborMarkup": 1.15,
            "ucdDefaultMachineCostMarkup": 1.15,
            "ucdDefaultExternalOperationMarkup": 1.25,
            "ucdDefaultAdditionalCostMarkup": 1.15,
        }
    ])


def wpbbc01u_operations_df(include_external=False):
    rows = [
        (10, "SAW1", "CUT01", "Saw Cutting", 0.25, 1.5, 1),
        (20, "M22", "MILL", "MILL OPERATION", 8.75, 34.6667, 1),
        (30, "WETHE", "DEBUR", "Parts Deburring", 1.0, 20.0, 1),
        (40, "POLIS", "POLIS", "Polishing", 0.1, 10.0, 1),
        (50, "DRYHE", "POLIS", "Polishing", 0.1, 15.0, 1),
        (60, "WASH", "WASH", "Parts Washing", 0.25, 0.25, 1),
    ]

    if include_external:
        rows[3] = (40, "POLIS", "POLIS", "Polishing", 0.1, 10.0, 2)

    return pd.DataFrame([
        {
            "imoMethodID": PART_ID,
            "imoMethodRevisionID": REVISION_ID,
            "imoMethodOperationID": method_operation_id,
            "imoWorkCenterID": work_center_id,
            "imoProcessID": process_id,
            "imoProcessShortDescription": description,
            "imoQuantityPerAssembly": 1.0,
            "imoSetupHours": setup_hours,
            "imoProductionStandard": production_standard_minutes,
            "imoOperationType": operation_type,
        }
        for (
            method_operation_id,
            work_center_id,
            process_id,
            description,
            setup_hours,
            production_standard_minutes,
            operation_type,
        ) in rows
    ])


def wpbbc01u_bom_df():
    return pd.DataFrame([
        {
            "immMethodID": PART_ID,
            "immMethodRevisionID": REVISION_ID,
            "immPartID": "WPBBC01U-MAT",
            "immPartRevisionID": "",
            "immPartShortDescription": "WPBBC01U raw material",
            "immQuantityPerAssembly": 1.0,
            "immEstimatedUnitCost": 2.75,
            "immBackflush": True,
        }
    ])


def empty_bom_for_children(part_id, revision_id=""):
    return wpbbc01u_bom_df() if part_id == PART_ID else pd.DataFrame()


def wpbbc01u_part_df():
    return pd.DataFrame([
        {
            "impPartID": PART_ID,
            "impPartRevisionID": REVISION_ID,
            "impPartShortDescription": "WPBBC01U finished part",
        }
    ])


def wpbbc01u_material_po_df():
    return pd.DataFrame([
        {
            "pmlPurchaseOrderID": "PO7001",
            "pmlPurchaseOrderLineID": 1,
            "pmlPurchaseUnitCostBase": 3.10,
            "pmlPurchaseQuantity": 12000,
            "pmlPurchaseQuantityReceived": 12000,
            "pmlDueDate": pd.NaT,
            "pmlCreatedDate": pd.Timestamp("2026-06-10"),
        }
    ])


def converted_material_po_df():
    return pd.DataFrame([
        {
            "pmlPurchaseOrderID": "PO8001",
            "pmlPurchaseOrderLineID": 2,
            "pmlPurchaseUnitCostBase": 12.00,
            "pmlInventoryUnitCostBase": 1.50,
            "pmlConversionFactor": 0.125,
            "pmlPurchaseQuantity": 100,
            "pmlPurchaseQuantityReceived": 100,
            "pmlDueDate": pd.NaT,
            "pmlCreatedDate": pd.Timestamp("2026-06-20"),
        }
    ])


def wpbbc01u_external_po_df():
    return pd.DataFrame([
        {
            "pmlPurchaseOrderID": "PO9001",
            "pmlPurchaseOrderLineID": 3,
            "pmlPurchaseUnitCostBase": 0.80,
            "pmlSetupChargeBase": 125.00,
            "pmlTotalExtendedCostBase": 8125.00,
            "pmlPurchaseQuantity": 10000,
            "pmlPurchaseQuantityReceived": 10000,
            "pmlDueDate": pd.NaT,
            "pmlCreatedDate": pd.Timestamp("2026-06-15"),
        }
    ])


def manufactured_part_cost_df():
    return pd.DataFrame([
        {
            "ucpPartCostID": 42,
            "ucpUnitRawCost": 4.00,
            "ucpUnitMarkedUpCost": 5.00,
            "ucpDateCosted": pd.Timestamp("2026-07-01"),
        }
    ])

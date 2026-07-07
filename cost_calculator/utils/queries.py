import pandas as pd
from sqlalchemy import text

from utils.erp_cursor import app_cnxn, erp_cnxn


def query_params(params=()):
    param_dict = {}
    for i, value in enumerate(params):
        param_dict[f"param{i + 1}"] = value
    return param_dict


def run_erp_query(query, params=()):
    return pd.read_sql(text(query), erp_cnxn, params=query_params(params))


def run_app_query(query, params=()):
    return pd.read_sql(text(query), app_cnxn, params=query_params(params))


def run_query(query, params=()):
    return run_erp_query(query, params)


def get_part(part_id, revision_id=""):
    if revision_id:
        query = """
        SELECT TOP 1
            p.impPartID,
            r.imrPartRevisionID AS impPartRevisionID,
            r.imrShortDescription AS impPartShortDescription,
            r.imrShortDescription AS impRevisionShortDescription
        FROM Parts p
        LEFT JOIN PartRevisions r
            ON r.imrPartID = p.impPartID
            AND r.imrPartRevisionID = :param2
        WHERE p.impPartID = :param1
        ORDER BY COALESCE(r.imrInactive, 0), r.imrPartRevisionID
        """
        return run_query(query, (part_id, revision_id))

    query = """
    SELECT TOP 1
        p.impPartID,
        r.imrPartRevisionID AS impPartRevisionID,
        r.imrShortDescription AS impPartShortDescription,
        r.imrShortDescription AS impRevisionShortDescription
    FROM Parts p
    LEFT JOIN PartRevisions r
        ON r.imrPartID = p.impPartID
        AND COALESCE(r.imrInactive, 0) = 0
    WHERE p.impPartID = :param1
    ORDER BY COALESCE(r.imrInactive, 0), r.imrPartRevisionID
    """
    return run_query(query, (part_id,))


def get_bom(part_id, revision_id=""):
    query = """
    SELECT
        immMethodID,
        immMethodRevisionID,
        immPartID,
        immPartRevisionID,
        immPartShortDescription,
        immQuantityPerAssembly,
        immEstimatedUnitCost
    FROM PartMaterials
    WHERE immMethodID = :param1
        AND immMethodRevisionID = :param2
        AND immBackflush = 1
    ORDER BY immPartID
    """
    return run_query(query, (part_id, revision_id))


def get_operations(part_id, revision_id=""):
    query = """
    SELECT
        imoMethodID,
        imoMethodRevisionID,
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoMethodOperationID,
        imoOperationType
    FROM PartOperations
    WHERE imoMethodID = :param1
        AND imoMethodRevisionID = :param2
    ORDER BY imoMethodOperationID
    """
    return run_query(query, (part_id, revision_id))


def get_default_costs():
    if app_table_exists("CostingGlobalDefaults") and app_table_exists("MachineCostDefaults"):
        global_defaults = run_app_query("""
        SELECT TOP 1
            N'__GLOBAL__' AS ucdWorkCenterID,
            CAST(1 AS DECIMAL(19,6)) AS ucdMinimumQuantity,
            ucgDefaultLaborHourlyCost AS ucdDefaultLaborHourlyCost,
            ucgDefaultMachineRunningHourlyCost AS ucdDefaultMachineRunningHourlyCost,
            ucgDefaultMachineOccupiedHourlyCost AS ucdDefaultMachineOccupiedHourlyCost,
            ucgDefaultBatchResetTimeHours AS ucdDefaultBatchResetTimeHours,
            ucgDefaultBatchIdleTimeHours AS ucdDefaultBatchIdleTimeHours,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultMaterialMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultLaborMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultMachineCostMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultExternalOperationMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultAdditionalCostMarkup
        FROM CostingGlobalDefaults
        ORDER BY ucgGlobalDefaultID
        """)
        machine_defaults = run_app_query("""
        SELECT
            ucmWorkCenterID AS ucdWorkCenterID,
            CAST(1 AS DECIMAL(19,6)) AS ucdMinimumQuantity,
            ucmDefaultLaborHourlyCost AS ucdDefaultLaborHourlyCost,
            ucmDefaultMachineRunningHourlyCost AS ucdDefaultMachineRunningHourlyCost,
            ucmDefaultMachineOccupiedHourlyCost AS ucdDefaultMachineOccupiedHourlyCost,
            ucmDefaultBatchResetTimeHours AS ucdDefaultBatchResetTimeHours,
            ucmDefaultBatchIdleTimeHours AS ucdDefaultBatchIdleTimeHours,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultMaterialMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultLaborMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultMachineCostMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultExternalOperationMarkup,
            CAST(NULL AS DECIMAL(9,4)) AS ucdDefaultAdditionalCostMarkup
        FROM MachineCostDefaults
        """)
        return pd.concat([global_defaults, machine_defaults], ignore_index=True)

    return run_app_query("SELECT * FROM DefaultCosts")


def app_table_exists(table_name):
    query = f"""
    SELECT CASE WHEN OBJECT_ID(N'dbo.{table_name}', N'U') IS NULL THEN 0 ELSE 1 END AS table_exists
    """
    try:
        rows = run_app_query(query)
    except Exception:
        return False
    return not rows.empty and bool(rows.iloc[0]["table_exists"])


def app_column_exists(table_name, column_name):
    query = """
    SELECT CASE
        WHEN COL_LENGTH(:param1, :param2) IS NULL THEN 0
        ELSE 1
    END AS column_exists
    """
    try:
        rows = run_app_query(query, (f"dbo.{table_name}", column_name))
    except Exception:
        return False
    return not rows.empty and bool(rows.iloc[0]["column_exists"])


def part_costs_has_current_column():
    return app_column_exists("PartCosts", "ucpIsCurrent")


def get_markup_breaks(part_id=None, revision_id=""):
    if not app_table_exists("MarkupBreaks"):
        return pd.DataFrame()

    if part_id:
        part_rows = run_app_query("""
        SELECT
            umbMinimumQuantity AS breakQty,
            umbMaterialMarkup AS material,
            umbLaborMarkup AS labor,
            umbMachineCostMarkup AS machine,
            umbExternalOperationMarkup AS [external],
            umbAdditionalCostMarkup AS additional
        FROM MarkupBreaks
        WHERE umbPartID = :param1
            AND umbPartRevision = :param2
        ORDER BY umbMinimumQuantity
        """, (part_id, revision_id or ""))
        if not part_rows.empty:
            return part_rows

    return run_app_query("""
    SELECT
        umbMinimumQuantity AS breakQty,
        umbMaterialMarkup AS material,
        umbLaborMarkup AS labor,
        umbMachineCostMarkup AS machine,
        umbExternalOperationMarkup AS [external],
        umbAdditionalCostMarkup AS additional
    FROM MarkupBreaks
    WHERE umbPartID IS NULL
    ORDER BY umbMinimumQuantity
    """)


def get_global_cost_defaults():
    if app_table_exists("CostingGlobalDefaults"):
        return run_app_query("SELECT TOP 1 * FROM CostingGlobalDefaults ORDER BY ucgGlobalDefaultID")
    return pd.DataFrame()


def get_machine_cost_defaults():
    if app_table_exists("MachineCostDefaults"):
        return run_app_query("SELECT * FROM MachineCostDefaults ORDER BY ucmWorkCenterID")
    return pd.DataFrame()


def get_last_external_operation_po(part_id, revision_id, method_operation_id):
    query = """
    SELECT TOP 1
        pmlPurchaseOrderID,
        pmlPurchaseOrderLineID,
        pmlPurchaseUnitCostBase,
        pmlSetupChargeBase,
        pmlTotalExtendedCostBase,
        pmlPurchaseQuantity,
        pmlPurchaseQuantityReceived,
        pmlDueDate,
        pmlCreatedDate
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlJobOperationID = :param3
        AND pmlPurchaseQuantityReceived > 0
        AND pmlPurchaseUnitCostBase > 0
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (part_id, revision_id, method_operation_id))


def get_last_material_po(material_id, material_revision_id=""):
    query = """
    SELECT TOP 1
        pmlPurchaseOrderID,
        pmlPurchaseOrderLineID,
        pmlPurchaseUnitCostBase,
        pmlPurchaseQuantity,
        pmlPurchaseQuantityReceived,
        pmlDueDate,
        pmlCreatedDate
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlPurchaseQuantityReceived > 0
        AND pmlPurchaseUnitCostBase > 0
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (material_id, material_revision_id))


def get_last_part_cost(part_id, revision_id=""):
    query = """
    SELECT TOP 1
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        CAST(0 AS BIT) AS ucpIsCurrent
    FROM PartCosts
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
    ORDER BY
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """
    return run_app_query(query, (part_id, revision_id))


def get_current_part_cost(part_id, revision_id=""):
    if not part_costs_has_current_column():
        return pd.DataFrame()

    query = """
    SELECT TOP 1
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        ucpIsCurrent
    FROM PartCosts
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
        AND ucpIsCurrent = 1
    ORDER BY
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """
    return run_app_query(query, (part_id, revision_id))


def get_current_or_last_part_cost(part_id, revision_id=""):
    current = get_current_part_cost(part_id, revision_id)
    return current if not current.empty else get_last_part_cost(part_id, revision_id)


def get_part_cost_history(part_id, revision_id="", limit=20):
    current_select = "ucpIsCurrent" if part_costs_has_current_column() else "CAST(0 AS BIT) AS ucpIsCurrent"
    current_order = "ucpIsCurrent DESC," if part_costs_has_current_column() else ""
    query = """
    SELECT TOP 20
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpCostedBy,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        {current_select},
        ucpNotes
    FROM PartCosts
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
    ORDER BY
        {current_order}
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """.format(current_select=current_select, current_order=current_order)
    return run_app_query(query, (part_id, revision_id))


def get_part_cost(part_cost_id):
    return run_app_query("SELECT * FROM PartCosts WHERE ucpPartCostID = :param1", (part_cost_id,))


def get_saved_operation_lines(part_cost_id):
    return run_app_query(
        "SELECT * FROM OperationCostLines WHERE ucoPartCostID = :param1 ORDER BY ucoPartOperationLineID",
        (part_cost_id,),
    )


def get_saved_material_lines(part_cost_id):
    return run_app_query(
        "SELECT * FROM MaterialCostLines WHERE ucmPartCostID = :param1 ORDER BY ucmPartMaterialLineID",
        (part_cost_id,),
    )


def search_operations(search_text, limit=12):
    query = """
    SELECT TOP 12
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoOperationType
    FROM PartOperations
    WHERE imoProcessID LIKE :param1
        OR imoProcessShortDescription LIKE :param1
        OR imoWorkCenterID LIKE :param1
    GROUP BY
        imoWorkCenterID,
        imoProcessID,
        imoProcessShortDescription,
        imoQuantityPerAssembly,
        imoSetupHours,
        imoProductionStandard,
        imoOperationType
    ORDER BY imoProcessShortDescription
    """
    return run_query(query, (f"%{search_text}%",))


def get_external_operation_pos(part_id, revision_id, method_operation_id):
    query = """
    SELECT TOP 100 *
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
        AND pmlPartRevisionID = :param2
        AND pmlJobOperationID = :param3
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (part_id, revision_id, method_operation_id))


def get_material_pos(material_id, material_revision_id=""):
    if material_revision_id:
        query = """
        SELECT TOP 100 *
        FROM PurchaseOrderLines
        WHERE pmlPartID = :param1
            AND pmlPartRevisionID = :param2
        ORDER BY
            COALESCE(pmlDueDate, pmlCreatedDate) DESC,
            pmlPurchaseOrderID DESC,
            pmlPurchaseOrderLineID DESC
        """
        return run_query(query, (material_id, material_revision_id))

    query = """
    SELECT TOP 100 *
    FROM PurchaseOrderLines
    WHERE pmlPartID = :param1
    ORDER BY
        COALESCE(pmlDueDate, pmlCreatedDate) DESC,
        pmlPurchaseOrderID DESC,
        pmlPurchaseOrderLineID DESC
    """
    return run_query(query, (material_id,))


def search_parts(search_text, limit=12):
    query = """
    SELECT TOP 12
        imrPartID AS impPartID,
        imrPartRevisionID AS impPartRevisionID,
        imrShortDescription AS impShortDescription
    FROM PartRevisions
    WHERE imrPartID LIKE :param1
        AND COALESCE(imrInactive, 0) = 0
    ORDER BY imrPartID
    """
    return run_query(query, (f"%{search_text}%",))

"""Read-only repository for app-owned costing data."""

import pandas as pd

from utils.app_storage import app_object_name, app_table


PART_COSTS = app_table("PartCosts")
OPERATION_COST_LINES = app_table("OperationCostLines")
MATERIAL_COST_LINES = app_table("MaterialCostLines")
COSTING_GLOBAL_DEFAULTS = app_table("CostingGlobalDefaults")
MACHINE_COST_DEFAULTS = app_table("MachineCostDefaults")
MARKUP_BREAKS = app_table("MarkupBreaks")
DEFAULT_COSTS = app_table("DefaultCosts")


def get_default_costs(*, run_app_query, table_exists):
    if table_exists("CostingGlobalDefaults") and table_exists(
        "MachineCostDefaults"
    ):
        global_defaults = run_app_query(f"""
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
        FROM {COSTING_GLOBAL_DEFAULTS}
        ORDER BY ucgGlobalDefaultID
        """)
        machine_defaults = run_app_query(f"""
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
        FROM {MACHINE_COST_DEFAULTS}
        """)
        return pd.concat([global_defaults, machine_defaults], ignore_index=True)

    return run_app_query(f"SELECT * FROM {DEFAULT_COSTS}")


def app_table_exists(table_name, *, run_app_query):
    query = """
    SELECT CASE WHEN OBJECT_ID(:param1, N'U') IS NULL THEN 0 ELSE 1 END AS table_exists
    """
    try:
        rows = run_app_query(query, (app_object_name(table_name),))
    except Exception:
        return False
    return not rows.empty and bool(rows.iloc[0]["table_exists"])


def app_column_exists(table_name, column_name, *, run_app_query):
    query = """
    SELECT CASE
        WHEN COL_LENGTH(:param1, :param2) IS NULL THEN 0
        ELSE 1
    END AS column_exists
    """
    try:
        rows = run_app_query(query, (app_object_name(table_name), column_name))
    except Exception:
        return False
    return not rows.empty and bool(rows.iloc[0]["column_exists"])


def part_costs_has_current_column(*, column_exists):
    return column_exists("PartCosts", "ucpIsCurrent")


def get_markup_break_rows(
    part_id=None, revision_id="", *, run_app_query, table_exists
):
    if not table_exists("MarkupBreaks"):
        return pd.DataFrame()

    if part_id:
        return run_app_query(
            f"""
        SELECT
            umbMinimumQuantity AS breakQty,
            umbMaterialMarkup AS material,
            umbLaborMarkup AS labor,
            umbMachineCostMarkup AS machine,
            umbExternalOperationMarkup AS [external],
            umbAdditionalCostMarkup AS additional
        FROM {MARKUP_BREAKS}
        WHERE umbPartID = :param1
            AND umbPartRevision = :param2
        ORDER BY umbMinimumQuantity
        """,
            (part_id, revision_id or ""),
        )

    return run_app_query(f"""
    SELECT
        umbMinimumQuantity AS breakQty,
        umbMaterialMarkup AS material,
        umbLaborMarkup AS labor,
        umbMachineCostMarkup AS machine,
        umbExternalOperationMarkup AS [external],
        umbAdditionalCostMarkup AS additional
    FROM {MARKUP_BREAKS}
    WHERE umbPartID IS NULL
    ORDER BY umbMinimumQuantity
    """)


def get_markup_breaks(
    part_id=None, revision_id="", *, table_exists, markup_row_loader
):
    if not table_exists("MarkupBreaks"):
        return pd.DataFrame()

    if part_id:
        part_rows = markup_row_loader(part_id, revision_id or "")
        if not part_rows.empty:
            return part_rows

    return markup_row_loader()


def get_global_cost_defaults(*, run_app_query, table_exists):
    if table_exists("CostingGlobalDefaults"):
        return run_app_query(
            f"SELECT TOP 1 * FROM {COSTING_GLOBAL_DEFAULTS} ORDER BY ucgGlobalDefaultID"
        )
    return pd.DataFrame()


def get_machine_cost_defaults(*, run_app_query, table_exists):
    if table_exists("MachineCostDefaults"):
        return run_app_query(
            f"SELECT * FROM {MACHINE_COST_DEFAULTS} ORDER BY ucmWorkCenterID"
        )
    return pd.DataFrame()


def get_last_part_cost(part_id, revision_id="", *, run_app_query):
    query = f"""
    SELECT TOP 1
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpMaterialsRawCost,
        ucpMaterialsMarkedUpCost,
        ucpMachineTimeRawCost,
        ucpMachineTimeMarkedUpCost,
        ucpLaborRawCost,
        ucpLaborMarkedUpCost,
        ucpExternalOperationsRawCost,
        ucpExternalOperationsMarkedUpCost,
        ucpAdditionalRawCost,
        ucpAdditionalMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        CAST(0 AS BIT) AS ucpIsCurrent
    FROM {PART_COSTS}
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
    ORDER BY
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """
    return run_app_query(query, (part_id, revision_id))


def get_current_part_cost(
    part_id, revision_id="", *, run_app_query, has_current_column
):
    if not has_current_column():
        return pd.DataFrame()

    query = f"""
    SELECT TOP 1
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpMaterialsRawCost,
        ucpMaterialsMarkedUpCost,
        ucpMachineTimeRawCost,
        ucpMachineTimeMarkedUpCost,
        ucpLaborRawCost,
        ucpLaborMarkedUpCost,
        ucpExternalOperationsRawCost,
        ucpExternalOperationsMarkedUpCost,
        ucpAdditionalRawCost,
        ucpAdditionalMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        ucpIsCurrent
    FROM {PART_COSTS}
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
        AND ucpIsCurrent = 1
    ORDER BY
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """
    return run_app_query(query, (part_id, revision_id))


def get_part_cost_history(
    part_id, revision_id="", limit=20, *, run_app_query, has_current_column
):
    current_select = (
        "ucpIsCurrent"
        if has_current_column()
        else "CAST(0 AS BIT) AS ucpIsCurrent"
    )
    current_order = "ucpIsCurrent DESC," if has_current_column() else ""
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
        ucpMaterialsRawCost,
        ucpMaterialsMarkedUpCost,
        ucpMachineTimeRawCost,
        ucpMachineTimeMarkedUpCost,
        ucpLaborRawCost,
        ucpLaborMarkedUpCost,
        ucpExternalOperationsRawCost,
        ucpExternalOperationsMarkedUpCost,
        ucpAdditionalRawCost,
        ucpAdditionalMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        {current_select},
        ucpNotes
    FROM {part_costs}
    WHERE ucpPartID = :param1
        AND ucpPartRevision = :param2
    ORDER BY
        {current_order}
        ucpDateCosted DESC,
        ucpPartCostID DESC
    """.format(
        current_select=current_select,
        current_order=current_order,
        part_costs=PART_COSTS,
    )
    return run_app_query(query, (part_id, revision_id))


def get_recent_part_costs(
    limit=25,
    before_date=None,
    before_id=None,
    after_date=None,
    after_id=None,
    part_id_prefix="",
    oldest_first=False,
    *,
    run_app_query,
    has_current_column,
):
    limit = min(101, max(1, int(limit or 25)))
    clauses = []
    params = []

    part_id_prefix = str(part_id_prefix or "").strip()
    if part_id_prefix:
        params.append(f"{part_id_prefix}%")
        clauses.append(f"ucpPartID LIKE :param{len(params)}")

    if before_date is not None and before_id is not None:
        params.extend([before_date, int(before_id)])
        date_param = f":param{len(params) - 1}"
        id_param = f":param{len(params)}"
        clauses.append(
            f"(ucpDateCosted < {date_param} "
            f"OR (ucpDateCosted = {date_param} AND ucpPartCostID < {id_param}))"
        )

    if after_date is not None and after_id is not None:
        params.extend([after_date, int(after_id)])
        date_param = f":param{len(params) - 1}"
        id_param = f":param{len(params)}"
        clauses.append(
            f"(ucpDateCosted > {date_param} "
            f"OR (ucpDateCosted = {date_param} AND ucpPartCostID > {id_param}))"
        )

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    current_select = (
        "ucpIsCurrent"
        if has_current_column()
        else "CAST(0 AS BIT) AS ucpIsCurrent"
    )
    order_direction = "ASC" if oldest_first or after_date is not None else "DESC"
    query = f"""
    SELECT TOP {limit}
        ucpPartCostID,
        ucpPartID,
        ucpPartRevision,
        ucpPartDescription,
        ucpCostQuantity,
        ucpDateCosted,
        ucpCostedBy,
        ucpUnitRawCost,
        ucpUnitMarkedUpCost,
        ucpMaterialsRawCost,
        ucpMaterialsMarkedUpCost,
        ucpMachineTimeRawCost,
        ucpMachineTimeMarkedUpCost,
        ucpLaborRawCost,
        ucpLaborMarkedUpCost,
        ucpExternalOperationsRawCost,
        ucpExternalOperationsMarkedUpCost,
        ucpAdditionalRawCost,
        ucpAdditionalMarkedUpCost,
        ucpTotalRawCost,
        ucpTotalMarkedUpCost,
        {current_select}
    FROM {PART_COSTS}
    {where_clause}
    ORDER BY
        ucpDateCosted {order_direction},
        ucpPartCostID {order_direction}
    """
    return run_app_query(query, tuple(params))


def get_part_cost(part_cost_id, *, run_app_query):
    return run_app_query(
        f"SELECT * FROM {PART_COSTS} WHERE ucpPartCostID = :param1",
        (part_cost_id,),
    )


def get_saved_operation_lines(part_cost_id, *, run_app_query):
    return run_app_query(
        f"SELECT * FROM {OPERATION_COST_LINES} WHERE ucoPartCostID = :param1 ORDER BY ucoPartOperationLineID",
        (part_cost_id,),
    )


def get_saved_material_lines(part_cost_id, *, run_app_query):
    return run_app_query(
        f"SELECT * FROM {MATERIAL_COST_LINES} WHERE ucmPartCostID = :param1 ORDER BY ucmPartMaterialLineID",
        (part_cost_id,),
    )

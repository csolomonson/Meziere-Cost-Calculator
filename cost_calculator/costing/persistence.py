import json

import pandas as pd
from sqlalchemy import inspect, text

from utils.app_storage import APP_SCHEMA, app_object_name, app_table
from utils.erp_cursor import APP_DATABASE, app_cnxn


IDENTITY_COLUMNS = {
    "PartCosts": {"ucpPartCostID"},
    "MaterialCostLines": {"ucmPartMaterialLineID"},
}

PART_COSTS = app_table("PartCosts")
MARKUP_BREAKS = app_table("MarkupBreaks")
COSTING_GLOBAL_DEFAULTS = app_table("CostingGlobalDefaults")
MACHINE_COST_DEFAULTS = app_table("MachineCostDefaults")


def save_costing_run(costing_run, make_current=False):
    part_cost_df = costing_run["part_cost"].copy()
    if "ucpIsCurrent" in part_cost_df.columns:
        part_cost_df["ucpIsCurrent"] = False
    operation_lines_df = costing_run["operation_lines"].copy()
    material_lines_df = costing_run["material_lines"].copy()

    with app_cnxn.begin() as connection:
        assert_app_database(connection)
        part_cost_id = insert_part_cost(connection, part_cost_df)

        if not operation_lines_df.empty:
            operation_lines_df["ucoPartCostID"] = part_cost_id
            insert_lines(connection, "OperationCostLines", operation_lines_df)

        if not material_lines_df.empty:
            material_lines_df["ucmPartCostID"] = part_cost_id
            insert_lines(connection, "MaterialCostLines", material_lines_df)

        if make_current:
            set_current_part_cost(connection, part_cost_id)

    costing_run["part_cost"].at[0, "ucpPartCostID"] = part_cost_id
    costing_run["part_cost"].at[0, "ucpIsCurrent"] = bool(make_current)
    return part_cost_id


def costing_run_from_records(part_cost, operation_lines, material_lines):
    return {
        "part_cost": pd.DataFrame([part_cost or {}]),
        "operation_lines": pd.DataFrame(operation_lines or []),
        "material_lines": pd.DataFrame(material_lines or []),
    }


def set_current_part_cost(connection, part_cost_id):
    if not table_has_column(connection, "PartCosts", "ucpIsCurrent"):
        raise RuntimeError(
            "The database needs the PartCosts.ucpIsCurrent migration before a current cost can be selected. "
            "For a new or intentionally reset database, use database/reset_schema.sql."
        )

    part_cost = connection.execute(
        text(f"""
        SELECT ucpPartID, ucpPartRevision
        FROM {PART_COSTS}
        WHERE ucpPartCostID = :part_cost_id
        """),
        {"part_cost_id": part_cost_id},
    ).mappings().first()
    if not part_cost:
        raise ValueError(f"Part cost {part_cost_id} was not found.")

    connection.execute(
        text(f"""
        UPDATE {PART_COSTS}
        SET ucpIsCurrent = 0
        WHERE ucpPartID = :part_id
            AND ucpPartRevision = :revision_id
        """),
        {
            "part_id": part_cost["ucpPartID"],
            "revision_id": part_cost["ucpPartRevision"],
        },
    )
    connection.execute(
        text(f"""
        UPDATE {PART_COSTS}
        SET ucpIsCurrent = 1
        WHERE ucpPartCostID = :part_cost_id
        """),
        {"part_cost_id": part_cost_id},
    )


def mark_part_cost_current(part_cost_id):
    with app_cnxn.begin() as connection:
        assert_app_database(connection)
        set_current_part_cost(connection, part_cost_id)


def save_costing_settings(
    part_id,
    revision_id,
    markup_breaks,
    global_defaults,
    machine_defaults,
    shift_settings=None,
    global_markup_breaks=None,
    part_markup_breaks=None,
    markup_break_scope="part",
):
    with app_cnxn.begin() as connection:
        assert_app_database(connection)
        scoped_part_id = (part_id or "").strip() or None
        if global_markup_breaks is not None:
            save_markup_breaks(connection, None, "", global_markup_breaks)
        elif not scoped_part_id:
            save_markup_breaks(connection, None, "", markup_breaks or [])

        if scoped_part_id:
            rows = part_markup_breaks if markup_break_scope == "part" else []
            if rows is None:
                rows = markup_breaks or []
            save_markup_breaks(connection, scoped_part_id, revision_id, rows)
        if global_defaults:
            save_global_defaults(connection, global_defaults, shift_settings or {})
        if machine_defaults is not None:
            save_machine_defaults(connection, machine_defaults)


def save_markup_breaks(connection, part_id, revision_id, markup_breaks):
    scoped_part_id = (part_id or "").strip() or None
    scoped_revision_id = revision_id or ""
    if scoped_part_id:
        connection.execute(
            text(f"DELETE FROM {MARKUP_BREAKS} WHERE umbPartID = :part_id AND umbPartRevision = :revision_id"),
            {"part_id": scoped_part_id, "revision_id": scoped_revision_id},
        )
    else:
        connection.execute(text(f"DELETE FROM {MARKUP_BREAKS} WHERE umbPartID IS NULL"))

    for row in markup_breaks:
        connection.execute(
            text(f"""
            INSERT INTO {MARKUP_BREAKS} (
                umbPartID,
                umbPartRevision,
                umbMinimumQuantity,
                umbMaterialMarkup,
                umbLaborMarkup,
                umbMachineCostMarkup,
                umbExternalOperationMarkup,
                umbAdditionalCostMarkup
            )
            VALUES (
                :part_id,
                :revision_id,
                :break_qty,
                :material,
                :labor,
                :machine,
                :external,
                :additional
            )
            """),
            {
                "part_id": scoped_part_id,
                "revision_id": scoped_revision_id if scoped_part_id else None,
                "break_qty": row.get("breakQty"),
                "material": row.get("material"),
                "labor": row.get("labor"),
                "machine": row.get("machine"),
                "external": row.get("external"),
                "additional": row.get("additional"),
            },
        )


def save_global_defaults(connection, defaults, shift_settings):
    if not connection.execute(text(f"SELECT TOP 1 1 FROM {COSTING_GLOBAL_DEFAULTS}")).first():
        connection.execute(text(f"INSERT INTO {COSTING_GLOBAL_DEFAULTS} DEFAULT VALUES"))

    connection.execute(
        text(f"""
        UPDATE {COSTING_GLOBAL_DEFAULTS}
        SET
            ucgDefaultLaborHourlyCost = :labor,
            ucgDefaultMachineRunningHourlyCost = :running,
            ucgDefaultMachineOccupiedHourlyCost = :occupied,
            ucgDefaultBatchResetTimeHours = :reset_hours,
            ucgDefaultBatchIdleTimeHours = :idle_hours,
            ucgDefaultFirstShiftStart = :shift_start,
            ucgDefaultFirstShiftEnd = :shift_end,
            ucgDefaultAfterHoursIdleRateMultiplier = :after_hours_multiplier,
            ucgUpdatedDate = SYSUTCDATETIME()
        WHERE ucgGlobalDefaultID = (
            SELECT TOP 1 ucgGlobalDefaultID FROM {COSTING_GLOBAL_DEFAULTS} ORDER BY ucgGlobalDefaultID
        )
        """),
        {
            "labor": defaults.get("ucoSetupLaborRate"),
            "running": defaults.get("ucoMachineRunningHourlyCost"),
            "occupied": defaults.get("ucoMachineOccupiedHourlyCost"),
            "reset_hours": defaults.get("ucoBatchResetTimeHours"),
            "idle_hours": defaults.get("ucoBatchIdleTimeHours"),
            "shift_start": shift_settings.get("firstShiftStart", "06:00"),
            "shift_end": shift_settings.get("firstShiftEnd", "14:30"),
            "after_hours_multiplier": shift_settings.get("afterHoursIdleMultiplier", 1),
        },
    )


def save_machine_defaults(connection, machine_defaults):
    for machine, defaults in machine_defaults.items():
        connection.execute(
            text(f"""
            MERGE {MACHINE_COST_DEFAULTS} AS target
            USING (SELECT :machine AS ucmWorkCenterID) AS source
                ON target.ucmWorkCenterID = source.ucmWorkCenterID
            WHEN MATCHED THEN UPDATE SET
                ucmDefaultLaborHourlyCost = :labor,
                ucmDefaultMachineRunningHourlyCost = :running,
                ucmDefaultMachineOccupiedHourlyCost = :occupied,
                ucmDefaultBatchResetTimeHours = :reset_hours,
                ucmDefaultBatchIdleTimeHours = :idle_hours,
                ucmUpdatedDate = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN INSERT (
                ucmWorkCenterID,
                ucmDefaultLaborHourlyCost,
                ucmDefaultMachineRunningHourlyCost,
                ucmDefaultMachineOccupiedHourlyCost,
                ucmDefaultBatchResetTimeHours,
                ucmDefaultBatchIdleTimeHours
            )
            VALUES (
                :machine,
                :labor,
                :running,
                :occupied,
                :reset_hours,
                :idle_hours
            );
            """),
            {
                "machine": machine,
                "labor": defaults.get("ucoSetupLaborRate"),
                "running": defaults.get("ucoMachineRunningHourlyCost"),
                "occupied": defaults.get("ucoMachineOccupiedHourlyCost"),
                "reset_hours": defaults.get("ucoBatchResetTimeHours"),
                "idle_hours": defaults.get("ucoBatchIdleTimeHours"),
            },
        )


def assert_app_database(connection):
    current_database = connection.execute(text("SELECT DB_NAME()")).scalar_one()
    if current_database != APP_DATABASE:
        raise RuntimeError(
            f"Refusing to write costing data to {current_database}. "
            f"Expected {APP_DATABASE}."
        )


def insert_part_cost(connection, part_cost_df):
    row = clean_row(frame_for_table(connection, "PartCosts", prepare_part_cost_frame(part_cost_df)).iloc[0].to_dict())

    columns = list(row.keys())
    column_sql = ", ".join(columns)
    value_sql = ", ".join(f":{column}" for column in columns)
    query = text(
        f"INSERT INTO {PART_COSTS} ({column_sql}) "
        f"OUTPUT INSERTED.ucpPartCostID "
        f"VALUES ({value_sql})"
    )

    return connection.execute(query, row).scalar_one()


def prepare_part_cost_frame(part_cost_df):
    frame = part_cost_df.copy()
    if "ucpRetailPriceLevelsJson" not in frame.columns and "ucpRetailPrices" in frame.columns:
        frame["ucpRetailPriceLevelsJson"] = frame["ucpRetailPrices"].map(serialize_json_value)
    return frame


def serialize_json_value(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def insert_lines(connection, table_name, lines_df):
    assert_supported_line_table_shape(connection, table_name)
    frame = frame_for_table(connection, table_name, lines_df)
    if frame.empty:
        return

    frame = apply_line_defaults(table_name, frame)
    frame = clean_frame(frame)
    frame.to_sql(
        table_name,
        connection,
        schema=APP_SCHEMA,
        if_exists="append",
        index=False,
    )


def assert_supported_line_table_shape(connection, table_name):
    if table_name != "OperationCostLines":
        return

    if table_column_is_identity(connection, table_name, "ucoPartOperationLineID"):
        raise RuntimeError(
            "OperationCostLines.ucoPartOperationLineID is still an identity column. "
            f"Run database/migrations/001_migrate_operation_sequence_identity.sql against {APP_DATABASE}.{APP_SCHEMA} once so operation "
            "sequence IDs can be saved as 10, 20, 30 per part cost."
        )


def frame_for_table(connection, table_name, df):
    table_columns = get_table_columns(connection, table_name)
    identity_columns = IDENTITY_COLUMNS.get(table_name, set())
    writable_columns = [
        column
        for column in df.columns
        if column in table_columns and column not in identity_columns
    ]

    return df[writable_columns].copy()


def apply_line_defaults(table_name, frame):
    if table_name == "OperationCostLines" and "ucoAutomated" in frame.columns:
        frame = frame.copy()
        frame["ucoAutomated"] = frame["ucoAutomated"].fillna(False)
    return frame


def clean_row(row):
    return {
        key: clean_value(value)
        for key, value in row.items()
    }


def clean_frame(frame):
    return frame.astype(object).map(clean_value)


def clean_value(value):
    if isinstance(value, str) and value.strip().lower() in {"nat", "nan", "none", "null"}:
        return None
    return None if pd.isna(value) else value


def get_table_columns(connection, table_name):
    inspector = inspect(connection)
    return {
        column["name"]
        for column in inspector.get_columns(table_name, schema=APP_SCHEMA)
    }


def table_has_column(connection, table_name, column_name):
    return column_name in get_table_columns(connection, table_name)


def table_column_is_identity(connection, table_name, column_name):
    return bool(connection.execute(
        text("""
        SELECT COLUMNPROPERTY(OBJECT_ID(:table_name), :column_name, 'IsIdentity')
        """),
        {"table_name": app_object_name(table_name), "column_name": column_name},
    ).scalar() or 0)

"""Compatibility facade for ERP and app-database repositories.

Callers can keep importing the established functions from ``utils.queries``.
The implementations are separated by database ownership in
``repositories.erp`` and ``repositories.costing``.
"""

import pandas as pd
from sqlalchemy import text

from repositories import costing as costing_repository
from repositories import erp as erp_repository
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
    """Backwards-compatible name for ERP reads."""

    return run_erp_query(query, params)


def get_part(part_id, revision_id=""):
    return erp_repository.get_part(
        part_id, revision_id, run_query=run_query
    )


def get_bom(part_id, revision_id=""):
    return erp_repository.get_bom(
        part_id, revision_id, run_query=run_query
    )


def get_operations(part_id, revision_id=""):
    return erp_repository.get_operations(
        part_id, revision_id, run_query=run_query
    )


def get_default_costs():
    return costing_repository.get_default_costs(
        run_app_query=run_app_query,
        table_exists=app_table_exists,
    )


def app_table_exists(table_name):
    return costing_repository.app_table_exists(
        table_name, run_app_query=run_app_query
    )


def app_column_exists(table_name, column_name):
    return costing_repository.app_column_exists(
        table_name,
        column_name,
        run_app_query=run_app_query,
    )


def part_costs_has_current_column():
    return costing_repository.part_costs_has_current_column(
        column_exists=app_column_exists
    )


def get_markup_break_rows(part_id=None, revision_id=""):
    return costing_repository.get_markup_break_rows(
        part_id,
        revision_id,
        run_app_query=run_app_query,
        table_exists=app_table_exists,
    )


def get_markup_breaks(part_id=None, revision_id=""):
    return costing_repository.get_markup_breaks(
        part_id,
        revision_id,
        table_exists=app_table_exists,
        markup_row_loader=get_markup_break_rows,
    )


def get_global_cost_defaults():
    return costing_repository.get_global_cost_defaults(
        run_app_query=run_app_query,
        table_exists=app_table_exists,
    )


def get_machine_cost_defaults():
    return costing_repository.get_machine_cost_defaults(
        run_app_query=run_app_query,
        table_exists=app_table_exists,
    )


def get_last_external_operation_po(part_id, revision_id, method_operation_id):
    return erp_repository.get_last_external_operation_po(
        part_id,
        revision_id,
        method_operation_id,
        run_query=run_query,
    )


def get_last_material_po(material_id, material_revision_id=""):
    return erp_repository.get_last_material_po(
        material_id,
        material_revision_id,
        run_query=run_query,
    )


def get_last_part_cost(part_id, revision_id=""):
    return costing_repository.get_last_part_cost(
        part_id,
        revision_id,
        run_app_query=run_app_query,
    )


def get_current_part_cost(part_id, revision_id=""):
    return costing_repository.get_current_part_cost(
        part_id,
        revision_id,
        run_app_query=run_app_query,
        has_current_column=part_costs_has_current_column,
    )


def get_current_or_last_part_cost(part_id, revision_id=""):
    current = get_current_part_cost(part_id, revision_id)
    return current if not current.empty else get_last_part_cost(part_id, revision_id)


def get_part_cost_history(part_id, revision_id="", limit=20):
    return costing_repository.get_part_cost_history(
        part_id,
        revision_id,
        limit,
        run_app_query=run_app_query,
        has_current_column=part_costs_has_current_column,
    )


def get_recent_part_costs(
    limit=25,
    before_date=None,
    before_id=None,
    after_date=None,
    after_id=None,
    part_id_prefix="",
    oldest_first=False,
):
    return costing_repository.get_recent_part_costs(
        limit,
        before_date,
        before_id,
        after_date,
        after_id,
        part_id_prefix,
        oldest_first,
        run_app_query=run_app_query,
        has_current_column=part_costs_has_current_column,
    )


def get_part_cost(part_cost_id):
    return costing_repository.get_part_cost(
        part_cost_id, run_app_query=run_app_query
    )


def get_saved_operation_lines(part_cost_id):
    return costing_repository.get_saved_operation_lines(
        part_cost_id, run_app_query=run_app_query
    )


def get_saved_material_lines(part_cost_id):
    return costing_repository.get_saved_material_lines(
        part_cost_id, run_app_query=run_app_query
    )


def search_operations(search_text, limit=12):
    return erp_repository.search_operations(
        search_text, limit, run_query=run_query
    )


def search_work_centers(search_text, limit=12):
    return erp_repository.search_work_centers(
        search_text, limit, run_query=run_query
    )


def search_processes(search_text, work_center_id="", limit=50):
    return erp_repository.search_processes(
        search_text,
        work_center_id,
        limit,
        run_query=run_query,
    )


def get_external_operation_pos(part_id, revision_id, method_operation_id):
    return erp_repository.get_external_operation_pos(
        part_id,
        revision_id,
        method_operation_id,
        run_query=run_query,
    )


def get_material_pos(material_id, material_revision_id=""):
    return erp_repository.get_material_pos(
        material_id,
        material_revision_id,
        run_query=run_query,
    )


def get_current_retail_price(part_id, revision_id=""):
    return erp_repository.get_current_retail_price(
        part_id,
        revision_id,
        run_query=run_query,
        legacy_lookup=get_current_retail_price_legacy,
    )


def get_current_retail_prices(part_id, revision_id=""):
    return erp_repository.get_current_retail_prices(
        part_id,
        revision_id,
        run_query=run_query,
    )


def get_current_retail_price_legacy(part_id, revision_id=""):
    return erp_repository.get_current_retail_price_legacy(
        part_id,
        revision_id,
        run_query=run_query,
    )


def add_retail_unit_price(rows):
    return erp_repository.add_retail_unit_price(rows)


def get_recent_jobs(part_id, revision_id="", limit=20):
    return erp_repository.get_recent_jobs(
        part_id,
        revision_id,
        limit,
        run_query=run_query,
    )


def get_operation_jobs(
    part_id, revision_id="", operation_sequence=0, limit=20
):
    return erp_repository.get_operation_jobs(
        part_id,
        revision_id,
        operation_sequence,
        limit,
        run_query=run_query,
    )


def search_parts(search_text, limit=12):
    return erp_repository.search_parts(
        search_text, limit, run_query=run_query
    )

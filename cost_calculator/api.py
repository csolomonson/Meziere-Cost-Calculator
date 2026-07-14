"""Compatibility entry point for the FastAPI application.

The HTTP implementation lives under :mod:`web`.  This module intentionally
re-exports the established models, helpers, and route callables so existing
``api:app`` deployments and direct imports continue to work.
"""

from authentication import AuthenticationError, authenticate_request
from app_config import setting
from costing.calculator import build_part_cost
from costing.conversion_calculator import calculate_conversion, calculator_config
from costing.persistence import (
    costing_run_from_records,
    mark_part_cost_current,
    save_costing_run,
    save_costing_settings,
)
from update_contract import request_update, update_status
from user_management import (
    UserConflictError,
    UserStoreError,
    add_user,
    delete_user,
    list_users,
    update_user,
)
from utils.queries import (
    get_bom,
    get_current_or_last_part_cost,
    get_current_retail_price,
    get_current_retail_prices,
    get_external_operation_pos,
    get_global_cost_defaults,
    get_last_material_po,
    get_machine_cost_defaults,
    get_markup_breaks,
    get_markup_break_rows,
    get_material_pos,
    get_operation_jobs,
    get_operations,
    get_part,
    get_part_cost,
    get_part_cost_history,
    get_recent_jobs,
    get_recent_part_costs,
    get_saved_material_lines,
    get_saved_operation_lines,
    search_operations,
    search_parts,
    search_processes,
    search_work_centers,
)
from web.app import app, require_authentication
from web.dependencies import require_administrator, user_management_error
from web.paths import BASE_DIR, STATIC_DIR
from web.routers.admin import change_user, create_user, get_users, remove_user
from web.routers.catalog import (
    external_operation_purchase_orders,
    material_default,
    material_purchase_orders,
    operation_jobs,
    operation_search,
    part_search,
    process_search,
    recent_jobs,
    work_center_search,
)
from web.routers.costs import (
    calculate_cost,
    cost_history,
    recent_costs,
    save_cost,
    save_cost_run,
    saved_cost,
    set_current_cost,
)
from web.routers.settings import save_settings_defaults, settings_defaults
from web.routers.system import (
    conversion_calculator_calculate,
    conversion_calculator_settings,
    get_update,
    health,
    index,
    install_update,
    session,
    version,
)
from web.schemas import (
    ConversionCalculationRequest,
    CostRequest,
    CostRunSaveRequest,
    CurrentCostRequest,
    MarkupBreak,
    SettingsRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from web.serialization import dataframe_records, parse_json_list, serialize_value
from web.services import (
    MATERIAL_BREAKDOWN_FIELDS,
    attach_retail_price_levels,
    build_costing_response,
    enrich_material_lines_from_child_costs,
    enrich_part_cost_retail_snapshot,
    part_cost_unit_breakdown,
    serialize_costing_run,
)

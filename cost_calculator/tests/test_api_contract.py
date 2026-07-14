import unittest

import api
from api import app


EXPECTED_APPLICATION_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/admin/users"),
    ("POST", "/api/admin/users"),
    ("DELETE", "/api/admin/users/{username}"),
    ("PUT", "/api/admin/users/{username}"),
    ("GET", "/api/conversion-calculator"),
    ("POST", "/api/conversion-calculator/calculate"),
    ("POST", "/api/costs/calculate"),
    ("POST", "/api/costs/current"),
    ("GET", "/api/costs/history"),
    ("GET", "/api/costs/recent"),
    ("POST", "/api/costs/save"),
    ("POST", "/api/costs/save-run"),
    ("GET", "/api/costs/{part_cost_id}"),
    ("GET", "/api/health"),
    ("GET", "/api/jobs/operation"),
    ("GET", "/api/jobs/recent"),
    ("GET", "/api/materials/default"),
    ("GET", "/api/operations/search"),
    ("GET", "/api/parts/search"),
    ("GET", "/api/processes/search"),
    ("GET", "/api/purchase-orders/external-operation"),
    ("GET", "/api/purchase-orders/material"),
    ("GET", "/api/session"),
    ("GET", "/api/settings/defaults"),
    ("POST", "/api/settings/defaults"),
    ("GET", "/api/update"),
    ("POST", "/api/update/install"),
    ("GET", "/api/version"),
    ("GET", "/api/work-centers/search"),
}

EXPECTED_COMPATIBILITY_EXPORTS = {
    "AuthenticationError",
    "BASE_DIR",
    "ConversionCalculationRequest",
    "CostRequest",
    "CostRunSaveRequest",
    "CurrentCostRequest",
    "MATERIAL_BREAKDOWN_FIELDS",
    "MarkupBreak",
    "STATIC_DIR",
    "SettingsRequest",
    "UserConflictError",
    "UserCreateRequest",
    "UserStoreError",
    "UserUpdateRequest",
    "add_user",
    "app",
    "attach_retail_price_levels",
    "authenticate_request",
    "build_costing_response",
    "build_part_cost",
    "calculate_conversion",
    "calculate_cost",
    "calculator_config",
    "change_user",
    "conversion_calculator_calculate",
    "conversion_calculator_settings",
    "cost_history",
    "costing_run_from_records",
    "create_user",
    "dataframe_records",
    "delete_user",
    "enrich_material_lines_from_child_costs",
    "enrich_part_cost_retail_snapshot",
    "external_operation_purchase_orders",
    "get_bom",
    "get_current_or_last_part_cost",
    "get_current_retail_price",
    "get_current_retail_prices",
    "get_external_operation_pos",
    "get_global_cost_defaults",
    "get_last_material_po",
    "get_machine_cost_defaults",
    "get_markup_break_rows",
    "get_markup_breaks",
    "get_material_pos",
    "get_operation_jobs",
    "get_operations",
    "get_part",
    "get_part_cost",
    "get_part_cost_history",
    "get_recent_jobs",
    "get_recent_part_costs",
    "get_saved_material_lines",
    "get_saved_operation_lines",
    "get_update",
    "get_users",
    "health",
    "index",
    "install_update",
    "list_users",
    "mark_part_cost_current",
    "material_default",
    "material_purchase_orders",
    "operation_jobs",
    "operation_search",
    "parse_json_list",
    "part_cost_unit_breakdown",
    "part_search",
    "process_search",
    "recent_costs",
    "recent_jobs",
    "remove_user",
    "request_update",
    "require_administrator",
    "require_authentication",
    "save_cost",
    "save_cost_run",
    "save_costing_run",
    "save_costing_settings",
    "save_settings_defaults",
    "saved_cost",
    "search_operations",
    "search_parts",
    "search_processes",
    "search_work_centers",
    "serialize_costing_run",
    "serialize_value",
    "session",
    "set_current_cost",
    "setting",
    "settings_defaults",
    "update_status",
    "update_user",
    "user_management_error",
    "version",
    "work_center_search",
}


class ApiContractTests(unittest.TestCase):
    def test_compatibility_entry_point_retains_established_exports(self):
        missing = {
            name for name in EXPECTED_COMPATIBILITY_EXPORTS if not hasattr(api, name)
        }

        self.assertEqual(missing, set())

    def test_application_route_paths_and_methods_are_stable(self):
        actual = {
            (method, path)
            for route in app.routes
            if ((path := getattr(route, "path", "")) == "/" or path.startswith("/api/"))
            for method in (getattr(route, "methods", None) or set())
        }

        self.assertEqual(actual, EXPECTED_APPLICATION_ROUTES)

    def test_openapi_schema_preserves_the_application_paths(self):
        schema = app.openapi()
        actual_paths = {
            path
            for path in schema["paths"]
            if path == "/" or path.startswith("/api/")
        }

        self.assertEqual(
            actual_paths,
            {path for _method, path in EXPECTED_APPLICATION_ROUTES},
        )


if __name__ == "__main__":
    unittest.main()

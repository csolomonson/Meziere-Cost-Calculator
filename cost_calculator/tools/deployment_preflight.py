"""Fail-fast production checks used before changing the running containers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from reportlab import Version as reportlab_version
from sqlalchemy import text

from utils.erp_cursor import APP_DATABASE, ERP_DATABASE, app_cnxn, erp_cnxn


REQUIRED_TABLES = (
    "PartCosts",
    "OperationCostLines",
    "MaterialCostLines",
    "CostingGlobalDefaults",
    "MachineCostDefaults",
    "MarkupBreaks",
    "CostingSettings",
)


def check_user_seed() -> None:
    seed_path = Path("/run/secrets/app_users_seed")
    deployed_path = Path(
        os.getenv("COST_APP_USERS_JSON_FILE", "/var/lib/cost-app-users/app_users.json")
    )
    users_path = deployed_path if deployed_path.is_file() else seed_path
    users = json.loads(users_path.read_text(encoding="utf-8"))
    if not isinstance(users, dict) or not users:
        raise RuntimeError("The application user seed must contain at least one user")
    if not any("administrators" in record.get("groups", []) for record in users.values() if isinstance(record, dict)):
        raise RuntimeError("The application user seed must contain an administrator")


def check_erp_database() -> None:
    with erp_cnxn.connect() as connection:
        connection.execute(text("SELECT TOP 1 1 FROM Parts"))


def check_costing_database() -> None:
    query = text(
        "SELECT CASE WHEN OBJECT_ID(:table_name, 'U') IS NULL THEN 0 ELSE 1 END"
    )
    with app_cnxn.connect() as connection:
        missing = [
            table_name
            for table_name in REQUIRED_TABLES
            if not connection.execute(
                query, {"table_name": f"dbo.{table_name}"}
            ).scalar_one()
        ]
    if missing:
        raise RuntimeError(
            "The costing database is missing required tables: " + ", ".join(missing)
        )


def main() -> None:
    checks = (
        ("application user seed", check_user_seed),
        (f"ERP database {ERP_DATABASE}", check_erp_database),
        (f"costing database {APP_DATABASE}", check_costing_database),
    )
    for label, check in checks:
        print(f"Checking {label} ...", flush=True)
        check()
        print(f"OK: {label}", flush=True)
    print(f"OK: ReportLab {reportlab_version}", flush=True)


if __name__ == "__main__":
    main()

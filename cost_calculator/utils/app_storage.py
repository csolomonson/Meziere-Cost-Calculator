"""Validated names for app-owned objects in SQL Server."""

import re

from app_config import setting


_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_@$-]{0,127}$")
APP_SCHEMA = setting("COST_APP_SCHEMA", "dbo") or "dbo"


def quote_identifier(identifier: str) -> str:
    """Return a safely bracketed SQL Server identifier.

    Identifiers cannot be query parameters. Restricting configuration and all
    constant table names to a conservative SQL Server identifier alphabet keeps
    the qualified names safe to interpolate into application SQL.
    """

    if not _SQL_IDENTIFIER.fullmatch(identifier):
        raise RuntimeError(
            f"Unsupported SQL identifier {identifier!r}; use letters, numbers, "
            "underscore, hyphen, @, or $, starting with a letter or underscore."
        )
    return f"[{identifier}]"


def app_table(table_name: str) -> str:
    return f"{quote_identifier(APP_SCHEMA)}.{quote_identifier(table_name)}"


def app_object_name(table_name: str) -> str:
    quote_identifier(table_name)
    return f"{APP_SCHEMA}.{table_name}"

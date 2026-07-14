# Database scripts

These SQL Server scripts manage the costing tables in the `M2_ME` database.

## New or disposable database

Run [`reset_schema.sql`](reset_schema.sql) to create the current costing schema and its initial default rows.

> **Warning:** `reset_schema.sql` is destructive. It drops the existing costing tables, their data, and the legacy `DefaultCosts` table before recreating the current schema. Back up any data that must be retained before running it.

The reset script already creates the current schema, so the migrations are not required afterward.

## Existing database

To retain existing costing data, do not run the reset script. Back up the database, then run the files in [`migrations/`](migrations/) in ascending numeric order:

1. `001_migrate_operation_sequence_identity.sql` replaces an identity-based operation-line key while retaining the original table as `OperationCostLines_IdentityBackup`.
2. `002_add_snapshot_columns.sql` adds the snapshot fields and manufactured-part reference index used by the application.
3. `003_add_part_cost_history_indexes.sql` adds the indexes used by recent-cost and part-history queries.

The numeric prefix is the execution order and should remain stable. Add future migrations with the next available number instead of editing a migration that may already have been applied.

All scripts contain SQL Server `GO` batch separators. The reset script and migrations `001` and `002` select `M2_ME` explicitly; select `M2_ME` before running migration `003`. Run the scripts with a SQL Server tool that recognizes `GO`, such as SQL Server Management Studio or `sqlcmd`.

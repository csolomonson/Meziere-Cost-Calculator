# Database scripts

These SQL Server scripts manage app-owned costing tables. The application supports
two storage layouts:

| Layout | Database | Schema |
| --- | --- | --- |
| Dedicated database | A separate database such as `M2_ME` | `dbo` by default |
| ERP namespace | The ERP database such as `M1_ME` | A dedicated schema such as `CostCalculator` |

Do not place app-owned tables in the ERP database's `dbo` schema. Keeping them in a
dedicated schema prevents collisions and permits schema-scoped write permissions.

## Installer-selected storage

On a new Ubuntu installation, `deployment/ubuntu/install.sh` asks which layout to
use and writes `COST_APP_STORAGE_MODE`, `COST_APP_DATABASE`, and
`COST_APP_SCHEMA` to `.env`. It then generates:

```text
deployment/runtime/reset-selected-storage.sql
```

The generated script is destructive. A database administrator must review it and
run it with SSMS in SQLCMD mode or with `sqlcmd -b`; the application runtime login
must not receive database- or schema-creation privileges. The script creates the
dedicated database when that layout is selected, creates the selected schema and
current tables, maps the configured SQL login if needed, and grants it DML rights
only on the app schema. Grant the runtime login read access to the required ERP
objects separately.

After the administrator runs the generated script, rerun the installer. Its
preflight verifies the selected database and schema before changing containers.
To replace the selection on an existing rehearsal deployment, use:

```bash
sudo bash deployment/ubuntu/install.sh --configure-storage
```

This rewrites only the three storage settings and does not migrate existing data.
Run the newly generated DBA script only when the selected target is new or its
costing data is intentionally disposable.

## New or disposable database

For a deployment-selected target, use the generated script described above. The
checked-in [`reset_schema.sql`](reset_schema.sql) remains the canonical
`M2_ME.dbo` source from which the installer renders the selected database and
schema, and creates the current tables and initial default rows.

> **Warning:** `reset_schema.sql` is destructive. It drops the existing costing tables, their data, and the legacy `DefaultCosts` table before recreating the current schema. Back up any data that must be retained before running it.

The reset script already creates the current schema, so the migrations are not required afterward.

## Existing database

To retain existing costing data, do not run the reset script. Back up the database, then run the files in [`migrations/`](migrations/) in ascending numeric order:

1. `001_migrate_operation_sequence_identity.sql` replaces an identity-based operation-line key while retaining the original table as `OperationCostLines_IdentityBackup`.
2. `002_add_snapshot_columns.sql` adds the snapshot fields and manufactured-part reference index used by the application.
3. `003_add_part_cost_history_indexes.sql` adds the indexes used by recent-cost and part-history queries.

The numeric prefix is the execution order and should remain stable. Add future migrations with the next available number instead of editing a migration that may already have been applied.

The existing numbered migrations target the legacy `M2_ME.dbo` layout. A newly
created ERP-schema layout already contains their changes and must not run those
legacy migrations. Future migrations must use the configured app schema.

All scripts contain SQL Server `GO` batch separators. Run them with a SQL Server
tool that recognizes `GO`, such as SQL Server Management Studio or `sqlcmd`.

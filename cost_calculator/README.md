# Product Cost Calculator

The Product Cost Calculator combines ERP manufacturing data, purchase history,
saved costing runs, and configurable markups in an authenticated FastAPI and React
application. It can also calculate and optionally save a cost from the command line.

For code ownership and request/data flow, see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). For production rollout, HTTPS,
secrets, and update-supervisor design, see
[`deployment/DEPLOYMENT.md`](deployment/DEPLOYMENT.md).

## Project map

| Path | Responsibility |
| --- | --- |
| `api.py` | Stable `api:app` deployment and import compatibility entry point |
| `web/` | FastAPI application, schemas, services, serialization, and grouped routers |
| `repositories/` | ERP and costing-database read queries |
| `utils/queries.py` | Compatibility facade for established query imports |
| `costing/` | Cost rules, line calculations, summaries, conversions, and persistence |
| `frontend/src/` | Authored React source, organized by API, domain, components, and features |
| `static/` | HTML shell and generated production bundles |
| `tests/`, `frontend/tests/` | Backend contracts and pure frontend-domain tests |
| `database/` | Destructive schema reset and ordered, data-preserving migrations |
| `reporting/` | Cross-platform ReportLab PDF documents for saved costing runs |
| `deployment/`, `secrets/` | Native VM runtime and secret-file documentation |

## Local setup

The application expects Python 3.13, Node.js, pnpm, and a SQL Server ODBC driver.
The checked-in Visual Studio project is configured for the local `cost_env` virtual
environment.

Create the virtual environment once, install the backend and frontend dependencies,
then build the browser bundle:

```powershell
py -3.13 -m venv cost_env
.\cost_env\Scripts\python.exe -m pip install -r requirements.txt
pnpm install
pnpm run build
```

For local-only development without a password prompt, opt out of authentication
explicitly and start Uvicorn:

```powershell
$env:COST_APP_AUTH_REQUIRED = "false"
.\cost_env\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/>. Do not disable authentication on a
network-accessible deployment.

For an authenticated direct launch, the application reads
`secrets/app_users.json` and `secrets/db_password.txt` by default. Explicit
environment variables and `*_FILE` settings take precedence. Restart the server
after changing a secret file. Direct Windows launches default to the locally
installed `ODBC Driver 17 for SQL Server`; the native Ubuntu service uses Driver
18.

The command-line entry point uses the same costing domain:

```powershell
.\cost_env\Scripts\python.exe cost_calculator.py PART_ID --quantity 100 --revision ""
```

Add `--save` only when the configured costing database is ready to accept the run.

## Verification

Run the complete backend suite, the frontend domain suite, and the production bundle
build before merging a behavior-affecting change:

```powershell
.\cost_env\Scripts\python.exe -m unittest discover -s tests -v
pnpm test
pnpm run build
```

`tests/test_api_contract.py` protects the complete route path/method surface. The
frontend tests protect formatting, quantity-break selection, edit tolerances,
after-hours timing, and cost recalculation relationships.

## API organization

All routes except `GET /api/health` and `GET /api/ready` require HTTP Basic
authentication and membership in `users` or `administrators`. An account with
only the `sales-orders` group can use the co-hosted Sales Order Queue without
accessing this application. The root page receives the authenticated session,
and saved costs are attributed to that user even if a client submits a different
`costed_by` value.

The API is grouped as follows:

- costing: calculation, save, save-run, current selection, history, recent history,
  and saved-run retrieval under `/api/costs`;
- ERP lookup: parts, materials, operations, work centers, processes, jobs, and
  purchase orders;
- settings: global/part markup breaks and machine/shift defaults;
- administration: file-backed user management for the `administrators` group;
- reporting: authenticated internal cost-audit and customer-safe PDFs for saved
  `PartCostID` values under `/api/reports`;
- system: health, session, version, update contract, and conversion calculator.

When running locally, the authenticated OpenAPI UI is available at `/docs`.

## Database scripts

Read [`database/README.md`](database/README.md) before changing a schema.
`database/reset_schema.sql` deliberately drops costing data and is only for a new or
disposable database. Existing installations should back up first and apply the
numbered files in `database/migrations/` in order.

## Production

Production runs directly on an Ubuntu Server 22.04 or 24.04 LTS VM. The installer creates a
versioned Python environment under `/opt/cost-calculator`, runs Uvicorn as a
restricted systemd service on loopback, and installs Caddy as the HTTPS service on
port 443. Docker and Compose are not used.

From a reviewed checkout or extracted tagged release:

```bash
sudo bash deployment/ubuntu/install.sh
```

Configuration is stored under `/etc/cost-calculator`; SQL credentials, application
users, generated DBA SQL, and update state persist under
`/var/lib/cost-calculator`. Caddy keeps its separate CA state under
`/var/lib/caddy/data`. A candidate release must pass the database, schema, user,
and PDF preflight before the active-release symlink changes.

See [`deployment/DEPLOYMENT.md`](deployment/DEPLOYMENT.md) for publishing and
architecture, [`deployment/UBUNTU.md`](deployment/UBUNTU.md) for the exact
Ubuntu install/update/rollback procedure, and
[`docs/REPORTING.md`](docs/REPORTING.md) for the ReportLab PDF design.

The application is available through Caddy on HTTPS port 443 by hostname or VM
IPv4 address. The verifier exports Caddy's public local root certificate to
`/var/lib/cost-calculator/caddy-root.crt` for managed client distribution.

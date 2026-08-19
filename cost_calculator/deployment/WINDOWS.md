# Retired Windows Server deployment (historical reference)

This path is no longer supported for production. The approved target is the Ubuntu
VM described in [`UBUNTU.md`](UBUNTU.md). These instructions are retained only to
preserve earlier deployment work during migration and must not be used for the
August 17, 2026 rollout.

This is the primary production deployment for Windows Server 2019. The FastAPI
application runs as a native Windows service on localhost. IIS owns the public
HTTPS endpoint and reverse-proxies requests to the service. Crystal Reports can
later run as a second native service without changing the API hosting model.

## Runtime layout

| Location | Contents |
| --- | --- |
| Application release directory | Python source, virtual environment, built React assets, and service wrapper configuration |
| `C:\ProgramData\CostCalculator\native-settings.json` | Non-secret service configuration |
| `C:\ProgramData\CostCalculator\secrets` | Database password and application user directory |
| `C:\ProgramData\CostCalculator\logs` | Rotating API service logs |
| `C:\ProgramData\CostCalculator\update` | Privilege-separated update status and request contract |

The installer restricts the secrets directory to Local System and the local
Administrators group. If the service is later assigned a dedicated Windows
account, grant that account read access to `db_password.txt` and read/write access
to `app_users.json` before changing the service identity.

## Server prerequisites

Install the following on Windows Server 2019:

- all current Windows security updates and .NET Framework 4.8;
- 64-bit Python 3.13 installed for all users in a machine-wide directory;
- Microsoft ODBC Driver 18 for SQL Server;
- IIS, Application Request Routing (ARR), and URL Rewrite;
- Node.js and pnpm only when the frontend will be built on the server;
- WinSW 2.12 (.NET Framework executable), transferred through the approved
  software-distribution process.
- SAP Crystal Reports 64-bit runtime at the same service-pack level used to build
  the report renderer.

WinSW is not committed to this repository. Keep the downloaded executable with
the release artifacts and verify its checksum before installation.

## Prepare a release

Prefer building and testing on a build machine, then copying an immutable release
directory to the server. The directory must include `static\dist\app.js` and
`static\dist\app.css`; those generated files are not tracked in Git. To enable
PDF reports, it must also include the Release output from
`reporting\Build-Renderer.ps1` and `reports\PartCost.rpt`. See
[`../docs/REPORTING.md`](../docs/REPORTING.md).

Before the first installation, create these ignored files in the release:

```text
secrets\db_password.txt
secrets\app_users.json
```

The installer copies them into the protected ProgramData directory only when the
destination files do not already exist. It never overwrites deployed secrets.

## Install the API service

Open an elevated PowerShell session in the release directory and run:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\deployment\windows\Install-Native.ps1 `
  -WinSWPath C:\Installers\WinSW.NET461.exe `
  -DbServer "SQLSERVER,1433" `
  -DbUsername "cost_app_access" `
  -ErpDatabase "M1_ME" `
  -AppDatabase "M2_ME" `
  -AppVersion "1.0.0"
```

Use `-TrustServerCertificate` only for a database certificate that cannot yet be
validated normally. The installer creates `cost_env`, installs Python packages,
builds the frontend when pnpm is present, installs `CostCalculatorApi`, starts it,
and checks `http://127.0.0.1:8000/api/health`.

On an offline server, prepare the virtual environment and frontend in the release
artifact, then use `-SkipDependencyInstall -SkipFrontendBuild`.

Subsequent installations retain `native-settings.json`. Pass `-Reconfigure` with
the complete desired database and runtime parameters to replace it.

## Configure IIS

1. Create an IIS site with an organization-issued HTTPS certificate.
2. Enable Anonymous Authentication for the site and disable IIS Basic and Windows
   Authentication. FastAPI owns application authentication and must receive the
   `Authorization` header unchanged.
3. Enable ARR proxying and URL Rewrite.
4. Copy `deployment\windows\iis-web.config` to the IIS site's physical directory
   as `web.config`.
5. Keep port 8000 closed in Windows Firewall. The API deliberately listens only on
   `127.0.0.1`; IIS is the only public listener.
6. Request `/api/health` through the HTTPS site, verify an unauthenticated request
   to `/` returns 401, and verify a valid application login succeeds.

If a different internal port is selected during installation, update the rewrite
URL in `web.config` to match.

## Operations and upgrades

Use ordinary Windows service controls:

```powershell
Get-Service CostCalculatorApi
Restart-Service CostCalculatorApi
```

Logs are under `C:\ProgramData\CostCalculator\logs`. WinSW restarts the API after
an unexpected exit and gives Uvicorn up to 30 seconds for a graceful stop.

For an upgrade:

1. Back up the application database and ProgramData secrets.
2. Build and test a versioned release directory.
3. Stop `CostCalculatorApi`.
4. Install the new release from its directory using the existing WinSW binary and
   `-SkipFrontendBuild` when the bundle is already present.
5. Run the health, authentication, database-read, and save checks.
6. Open a saved worksheet's PDF and verify the report connects to the production
   costing database.
7. Retain the previous release directory until verification is complete.

Rollback by stopping the service and reinstalling it from the previous release
directory. Database migrations require their own documented rollback or restore;
switching application files does not reverse a schema change.

To remove only the Windows service while preserving configuration, users, logs,
and secrets:

```powershell
.\deployment\windows\Uninstall-Native.ps1
```

The supported production replacement is the native Ubuntu VM deployment in
[`UBUNTU.md`](UBUNTU.md). The application no longer ships a container deployment.

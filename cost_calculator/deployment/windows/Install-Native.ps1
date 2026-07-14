[CmdletBinding()]
param(
    [string]$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")),
    [string]$PythonCommand = "py",
    [string]$WinSWPath = "",
    [string]$DbServer = "localhost\MEZIEREDB22",
    [string]$DbUsername = "cost_app_access",
    [string]$ErpDatabase = "M1_ME",
    [string]$AppDatabase = "M2_ME",
    [string]$AppVersion = "development",
    [string]$AppRepository = "",
    [int]$Port = 8000,
    [ValidateRange(1, 32)][int]$Workers = 2,
    [switch]$TrustServerCertificate,
    [switch]$Reconfigure,
    [switch]$SkipDependencyInstall,
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$serviceName = "CostCalculatorApi"
$DataRoot = Join-Path $env:ProgramData "CostCalculator"
$serviceDirectory = Join-Path $AppRoot "deployment\windows"
$serviceExecutable = Join-Path $serviceDirectory "CostCalculator.Api.exe"
$serviceConfig = Join-Path $serviceDirectory "CostCalculator.Api.xml"
$venvPython = Join-Path $AppRoot "cost_env\Scripts\python.exe"
$settingsPath = Join-Path $DataRoot "native-settings.json"
$secretsRoot = Join-Path $DataRoot "secrets"
$logsRoot = Join-Path $DataRoot "logs"
$updateRoot = Join-Path $DataRoot "update"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this installer from an elevated PowerShell session."
    }
}

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $Command $($Arguments -join ' ')"
    }
}

function Copy-InitialSecret {
    param([string]$Name)
    $destination = Join-Path $secretsRoot $Name
    if (Test-Path $destination) {
        return
    }
    $source = Join-Path $AppRoot "secrets\$Name"
    if (-not (Test-Path $source)) {
        throw "Create $source before installing, or create $destination in the protected data directory."
    }
    Copy-Item -LiteralPath $source -Destination $destination
}

function Protect-SecretPath {
    param([string]$Path, [switch]$Directory)
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        $acl.RemoveAccessRuleSpecific($rule)
    }
    $inheritance = if ($Directory) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else {
        [Security.AccessControl.InheritanceFlags]::None
    }
    foreach ($sidValue in @("S-1-5-18", "S-1-5-32-544")) {
        $sid = [Security.Principal.SecurityIdentifier]::new($sidValue)
        $account = $sid.Translate([Security.Principal.NTAccount])
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $account,
            [Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance,
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule) | Out-Null
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

Assert-Administrator
$AppRoot = (Resolve-Path $AppRoot).Path

if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be between 1 and 65535."
}
if (-not (Test-Path $serviceConfig)) {
    throw "The WinSW configuration was not found at $serviceConfig."
}

New-Item -ItemType Directory -Force -Path $DataRoot, $secretsRoot, $logsRoot, $updateRoot | Out-Null
Copy-InitialSecret "app_users.json"
Copy-InitialSecret "db_password.txt"
Protect-SecretPath -Path $secretsRoot -Directory
Protect-SecretPath -Path (Join-Path $secretsRoot "app_users.json")
Protect-SecretPath -Path (Join-Path $secretsRoot "db_password.txt")

if (-not $SkipDependencyInstall) {
    if (-not (Test-Path $venvPython)) {
        Invoke-Checked $PythonCommand @("-3.13", "-m", "venv", (Join-Path $AppRoot "cost_env"))
    }
    Invoke-Checked $venvPython @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked $venvPython @("-m", "pip", "install", "-r", (Join-Path $AppRoot "requirements.txt"))
} elseif (-not (Test-Path $venvPython)) {
    throw "The application virtual environment does not exist at $venvPython."
}

$frontendBundle = Join-Path $AppRoot "static\dist\app.js"
if (-not $SkipFrontendBuild) {
    $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($null -eq $pnpm) {
        if (-not (Test-Path $frontendBundle)) {
            throw "pnpm is required to build the frontend, or deploy a release containing static\dist and use -SkipFrontendBuild."
        }
        Write-Warning "pnpm was not found; retaining the existing frontend bundle."
    } else {
        Invoke-Checked $pnpm.Source @("install", "--frozen-lockfile", "--dir", $AppRoot)
        Invoke-Checked $pnpm.Source @("--dir", $AppRoot, "run", "build")
    }
} elseif (-not (Test-Path $frontendBundle)) {
    throw "The production frontend bundle is missing at $frontendBundle."
}

if ($Reconfigure -or -not (Test-Path $settingsPath)) {
    $settings = [ordered]@{
        COST_APP_AUTH_REQUIRED = $true
        COST_APP_USERS_JSON_FILE = (Join-Path $secretsRoot "app_users.json")
        COST_DB_PASSWORD_FILE = (Join-Path $secretsRoot "db_password.txt")
        COST_DB_SERVER = $DbServer
        COST_DB_USERNAME = $DbUsername
        COST_DB_DRIVER = "ODBC Driver 18 for SQL Server"
        COST_ERP_DATABASE = $ErpDatabase
        COST_APP_DATABASE = $AppDatabase
        COST_DB_TRUST_SERVER_CERTIFICATE = [bool]$TrustServerCertificate
        COST_APP_HOST = "127.0.0.1"
        COST_APP_PORT = $Port
        COST_APP_WORKERS = $Workers
        COST_APP_FORWARDED_ALLOW_IPS = "127.0.0.1"
        APP_VERSION = $AppVersion
        APP_REPOSITORY = $AppRepository
        UPDATE_STATUS_FILE = (Join-Path $updateRoot "update-status.json")
        UPDATE_REQUEST_FILE = (Join-Path $updateRoot "update-request.json")
    }
    $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding UTF8
} else {
    Write-Host "Retaining existing service settings at $settingsPath. Use -Reconfigure to replace them."
}

if ($WinSWPath) {
    $resolvedWinSW = (Resolve-Path $WinSWPath).Path
    if ($resolvedWinSW -ne $serviceExecutable) {
        Copy-Item -LiteralPath $resolvedWinSW -Destination $serviceExecutable -Force
    }
}
if (-not (Test-Path $serviceExecutable)) {
    throw "Provide -WinSWPath pointing to a WinSW 2.x executable. It will be copied to $serviceExecutable."
}

$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($null -ne $existingService) {
    if ($existingService.Status -ne "Stopped") {
        Invoke-Checked $serviceExecutable @("stop")
    }
    Invoke-Checked $serviceExecutable @("uninstall")
}
Invoke-Checked $serviceExecutable @("install")
Invoke-Checked $serviceExecutable @("start")

$healthUrl = "http://127.0.0.1`:$Port/api/health"
$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        # The worker may still be starting.
    }
}
if (-not $healthy) {
    throw "The service was installed but its health check failed. Review $logsRoot."
}

Write-Host "Product Cost Calculator API is running as $serviceName at $healthUrl"
Write-Host "Configure IIS to proxy HTTPS traffic to http://127.0.0.1`:$Port."

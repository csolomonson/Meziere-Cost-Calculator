[CmdletBinding()]
param(
    [string]$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this command from an elevated PowerShell session."
}

$serviceExecutable = Join-Path $AppRoot "deployment\windows\CostCalculator.Api.exe"
$service = Get-Service -Name "CostCalculatorApi" -ErrorAction SilentlyContinue
if ($null -eq $service) {
    Write-Host "Product Cost Calculator API service is not installed."
    exit 0
}
if (-not (Test-Path $serviceExecutable)) {
    throw "The service wrapper was not found at $serviceExecutable."
}
if ($service.Status -ne "Stopped") {
    & $serviceExecutable stop
    if ($LASTEXITCODE -ne 0) { throw "Could not stop the service." }
}
& $serviceExecutable uninstall
if ($LASTEXITCODE -ne 0) { throw "Could not uninstall the service." }

Write-Host "Product Cost Calculator API service was removed."
Write-Host "Application data and secrets under ProgramData were preserved."

[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")][string]$Configuration = "Release",
    [string]$MSBuildPath = ""
)

$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "CrystalReportRenderer\CrystalReportRenderer.csproj"

if (-not $MSBuildPath) {
    $command = Get-Command MSBuild.exe -ErrorAction SilentlyContinue
    if ($command) {
        $MSBuildPath = $command.Source
    }
}
if (-not $MSBuildPath) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $installation = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath
        if ($installation) {
            $candidate = Join-Path $installation "MSBuild\Current\Bin\MSBuild.exe"
            $roslynTargets = Join-Path $installation "MSBuild\Current\Bin\Roslyn\Microsoft.CSharp.Core.targets"
            if ((Test-Path $candidate) -and (Test-Path $roslynTargets)) {
                $MSBuildPath = $candidate
            }
        }
    }
}
if (-not $MSBuildPath) {
    $frameworkMSBuild = Join-Path $env:windir "Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe"
    if (Test-Path $frameworkMSBuild) {
        $MSBuildPath = $frameworkMSBuild
    }
}
if (-not $MSBuildPath -or -not (Test-Path $MSBuildPath)) {
    throw "MSBuild was not found. Install Visual Studio with .NET Framework 4.8 build tools."
}

& $MSBuildPath $project /t:Rebuild /p:Configuration=$Configuration /p:Platform=x64 /nologo
if ($LASTEXITCODE -ne 0) {
    throw "CrystalReportRenderer build failed with exit code $LASTEXITCODE."
}

$output = Join-Path $PSScriptRoot "CrystalReportRenderer\bin\$Configuration\CrystalReportRenderer.exe"
if (-not (Test-Path $output)) {
    throw "The renderer build completed without producing $output."
}
Write-Host "Built $output"

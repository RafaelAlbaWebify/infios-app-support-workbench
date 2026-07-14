param(
    [int]$Port = 8000,
    [string]$Database = "",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating local Python environment..."
    python -m venv .venv
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python virtual environment was not created correctly."
}

& $python -m pip install -U pip
& $python -m pip install -e .

$arguments = @("-m", "app.cli", "serve", "--port", $Port)
if ($Database) { $arguments += @("--database", $Database) }
if ($NoBrowser) { $arguments += "--no-browser" }

Write-Host "Starting INFIOS at http://127.0.0.1:$Port"
& $python @arguments

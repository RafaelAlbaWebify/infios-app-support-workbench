param(
    [int]$Port = 8000,
    [string]$Database = "",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtime = Join-Path $packageRoot ".runtime"
$python = Join-Path $runtime "Scripts\python.exe"
$wheel = Get-ChildItem (Join-Path $packageRoot "wheels\*.whl") | Select-Object -First 1

if (-not $wheel) {
    throw "The INFIOS wheel is missing from the package."
}

if (-not (Test-Path $python)) {
    Write-Host "Creating the local INFIOS runtime..."
    python -m venv $runtime
}

if (-not (Test-Path $python)) {
    throw "Python could not create the package runtime. Install Python 3.10 or newer and try again."
}

& $python -m pip install -U pip
& $python -m pip install --upgrade $wheel.FullName

if (-not $Database) {
    $dataDirectory = Join-Path $packageRoot "data"
    New-Item -ItemType Directory -Force -Path $dataDirectory | Out-Null
    $Database = Join-Path $dataDirectory "infios-cases.sqlite3"
}

$arguments = @("-m", "app.cli", "serve", "--port", $Port, "--database", $Database)
if ($NoBrowser) { $arguments += "--no-browser" }

Write-Host "Starting INFIOS at http://127.0.0.1:$Port"
& $python @arguments

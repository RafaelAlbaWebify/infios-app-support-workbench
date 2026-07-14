param(
    [int]$Port = 8000,
    [string]$Database = "",
    [switch]$KeepServerRunning
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evidenceRoot = Join-Path $env:USERPROFILE "Downloads\INFIOS_RELEASE_VALIDATION_$timestamp"
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

if (-not $Database) {
    $Database = Join-Path $evidenceRoot "validation-cases.sqlite3"
}

$baseUrl = "http://127.0.0.1:$Port"
$serverLog = Join-Path $evidenceRoot "server-output.log"
$serverErrorLog = Join-Path $evidenceRoot "server-error.log"
$reportPath = Join-Path $evidenceRoot "release-validation.md"
$summaryPath = Join-Path $evidenceRoot "case-summary.md"
$handoverPath = Join-Path $evidenceRoot "l2-handover.md"

function Wait-ForInfios {
    param([int]$TimeoutSeconds = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 2
            if ($health.status -eq "ok") { return $health }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)
    throw "INFIOS did not become ready at $baseUrl within $TimeoutSeconds seconds."
}

function Stop-InfiosOnPort {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

$launcher = Join-Path $repoRoot "tools\start-infios.ps1"
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $launcher,
    "-Port", $Port,
    "-Database", $Database
)

Write-Host "Starting INFIOS release validation..."
Write-Host "Evidence folder: $evidenceRoot"
$process = Start-Process powershell.exe -ArgumentList $arguments -RedirectStandardOutput $serverLog -RedirectStandardError $serverErrorLog -PassThru

try {
    $health = Wait-ForInfios
    Start-Process $baseUrl

    $case = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/cases" -ContentType "application/json" -Body (@{
        title = "Windows release validation"
        application = "INFIOS sample application"
        impact = "Sample validation only"
        affected_scope = "Single sample user"
    } | ConvertTo-Json)

    $evidence = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/cases/$($case.case_id)/evidence" -ContentType "application/json" -Body (@{
        evidence_type = "user_report"
        source = "Windows release validation"
        content = "Sample evidence created by the public-safe release validation script."
        certainty = "reported"
    } | ConvertTo-Json)

    $package = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/cases/$($case.case_id)/escalations" -ContentType "application/json" -Body (@{
        target_team = "L2 Application Support"
        requested_action = "Review this public-safe sample validation case."
    } | ConvertTo-Json)

    Invoke-WebRequest -Uri "$baseUrl/api/cases/$($case.case_id)/summary/download" -OutFile $summaryPath
    Invoke-WebRequest -Uri "$baseUrl/api/cases/$($case.case_id)/escalations/$($package.package_id)/download" -OutFile $handoverPath

    $browserOpened = Read-Host "Did your default browser open and display the INFIOS dashboard? (yes/no)"
    $dashboardUsable = Read-Host "Was the local dashboard visibly usable? (yes/no)"

    Start-Process $summaryPath
    $summaryOpened = Read-Host "Did the downloaded case-summary Markdown open correctly? (yes/no)"
    Start-Process $handoverPath
    $handoverOpened = Read-Host "Did the downloaded L2 handover Markdown open correctly? (yes/no)"
    $publicSafe = Read-Host "Was only sample/public-safe data used? (yes/no)"

    $failedAnswers = @($browserOpened, $dashboardUsable, $summaryOpened, $handoverOpened, $publicSafe) |
        ForEach-Object { $_.Trim().ToLowerInvariant() -in @("yes", "y") } |
        Where-Object { -not $_ } |
        Measure-Object |
        Select-Object -ExpandProperty Count
    $result = if ($failedAnswers -eq 0) { "PASS" } else { "FAIL" }

    @"
# INFIOS v0.1.0 Windows interactive validation

- Result: **$result**
- Timestamp: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")
- Windows: $([System.Environment]::OSVersion.VersionString)
- PowerShell: $($PSVersionTable.PSVersion)
- Python launcher: `$launcher`
- INFIOS URL: `$baseUrl`
- Health version: `$($health.version)`
- Database: `$Database`
- Case ID: `$($case.case_id)`
- Evidence ID: `$($evidence.evidence_id)`
- Escalation package ID: `$($package.package_id)`

## Interactive confirmations

- Default browser opened and displayed INFIOS: $browserOpened
- Dashboard visibly usable: $dashboardUsable
- Case-summary Markdown opened: $summaryOpened
- L2 handover Markdown opened: $handoverOpened
- Only sample/public-safe data used: $publicSafe

## Generated evidence

- Server output log: `$serverLog`
- Server error log: `$serverErrorLog`
- Case summary: `$summaryPath`
- L2 handover: `$handoverPath`

Attach this report to GitHub issue #18. Do not merge or publish v0.1.0 if the result is FAIL.
"@ | Set-Content -Path $reportPath -Encoding UTF8

    Write-Host "Validation result: $result"
    Write-Host "Evidence report: $reportPath"
    Start-Process explorer.exe -ArgumentList $evidenceRoot

    if ($result -ne "PASS") {
        exit 1
    }
} finally {
    if (-not $KeepServerRunning) {
        Stop-InfiosOnPort
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

param(
    [Parameter(Mandatory=$true)][string]$Distribution,
    [Parameter(Mandatory=$true)][string]$ReportDirectory
)
$ErrorActionPreference = 'Stop'
$test = Join-Path $PSScriptRoot 'test-sampling-shutdown.ps1'
& $test -Distribution $Distribution -ReportDirectory (Join-Path $ReportDirectory 'normal')
$seen = @{}
$temporarilyUnavailable = {
    param($Process)
    if (!$seen.ContainsKey($Process.Id)) { $seen[$Process.Id]=$true; return $null }
    return $Process.MainModule.FileName
}.GetNewClosure()
& $test -Distribution $Distribution -ReportDirectory (Join-Path $ReportDirectory 'unavailable') -ReadProcessPath $temporarilyUnavailable
$missing = @(Get-Content -LiteralPath (Join-Path $ReportDirectory 'unavailable/observations.json') -Raw | ConvertFrom-Json | Where-Object { !$_.processPath })
if ($missing.Count -ne 3) { throw 'Unavailable-path regression did not exercise every timing.' }

$mismatchDirectory = Join-Path $ReportDirectory 'mismatch'
$rejected = $false
try {
    & $test -Distribution $Distribution -ReportDirectory $mismatchDirectory -ReadProcessPath { param($Process) 'C:\unexpected\quantum-worker.exe' }
} catch {
    if (!$_.Exception.Message.StartsWith('Unexpected child executable.')) { throw }
    $rejected = $true
}
if (!$rejected) { throw 'Unexpected executable path was accepted.' }
foreach ($record in @(Get-Content -LiteralPath (Join-Path $mismatchDirectory 'observations.json') -Raw | ConvertFrom-Json)) {
    $remaining = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.childId)"
    if ($remaining -and $remaining.ParentProcessId -eq $record.parentId) { throw 'Failed observation left its worker running.' }
}
Write-Output 'PASS: unavailable-path retry, genuine path mismatch rejection, and failed-observation cleanup.'

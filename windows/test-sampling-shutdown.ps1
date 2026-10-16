param(
    [Parameter(Mandatory=$true)][string]$Distribution,
    [Parameter(Mandatory=$true)][string]$ReportDirectory
)
$ErrorActionPreference = 'Stop'
$Distribution = (Resolve-Path -LiteralPath $Distribution).Path
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null
$ReportDirectory = (Resolve-Path -LiteralPath $ReportDirectory).Path
$appPath = Join-Path $Distribution 'QuantumStudio.exe'
$workerPath = Join-Path $Distribution 'quantum-worker.exe'
$circuitPath = Join-Path $ReportDirectory 'shutdown.qcircuit'
$steps = @(for ($index=0; $index -lt 128; $index++) { @{Gate='H'; Angle=''; Wires=@($index % 25)} })
@{Version=1; Qubits=25; Steps=$steps} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $circuitPath -Encoding UTF8
$results = @()
foreach ($delay in @(0,200,500)) {
    $report = Join-Path $ReportDirectory ("shutdown-$delay.txt")
    $parent = Start-Process -FilePath $appPath -ArgumentList @('--sampling-circuit-test', ('"'+$circuitPath+'"'), ('"'+$report+'"')) -WindowStyle Hidden -PassThru
    $child = $null
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        while (!$child -and !$parent.HasExited -and [DateTime]::UtcNow -lt $deadline) {
            $record = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($parent.Id)" | Where-Object { $_.Name -eq 'quantum-worker.exe' } | Select-Object -First 1
            if ($record) {
                if (![String]::Equals($record.ExecutablePath,$workerPath,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected child executable.' }
                $child = Get-Process -Id $record.ProcessId -ErrorAction Stop
            } else { Start-Sleep -Milliseconds 100 }
        }
        if (!$child) { throw 'Sampling worker did not start.' }
        if ($delay) { Start-Sleep -Milliseconds $delay }
        if ($child.HasExited) { throw 'Worker finished before shutdown could be tested.' }
        if (!$parent.CloseMainWindow()) { throw 'Could not request GUI shutdown.' }
        $parentExited = $parent.WaitForExit(5000)
        $childExited = $child.WaitForExit(3000)
        $results += @{delayMilliseconds=$delay; parentExited=$parentExited; workerExited=$childExited}
        if (!$parentExited -or !$childExited) { throw 'Closing the sampling GUI left a live process.' }
    } finally {
        # Clean up only this test's parent and verified child, even on a regression.
        if ($child) { if (!$child.HasExited) { $child.Kill(); $child.WaitForExit() }; $child.Dispose() }
        if (!$parent.HasExited) { $parent.Kill(); $parent.WaitForExit() }
        $parent.Dispose()
        $results | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $ReportDirectory 'results.json') -Encoding UTF8
    }
}
Write-Output 'PASS: closing the GUI stops its sampling worker at three shutdown timings.'

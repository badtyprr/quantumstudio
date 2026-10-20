param(
    [Parameter(Mandatory=$true)][string]$Distribution,
    [Parameter(Mandatory=$true)][string]$ReportDirectory,
    # Injection is only for deterministic tests of unavailable process metadata.
    [scriptblock]$ReadProcessPath = { param($Process) $Process.MainModule.FileName }
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
$observations = @()
foreach ($delay in @(0,200,500)) {
    $report = Join-Path $ReportDirectory ("shutdown-$delay.txt")
    $parent = Start-Process -FilePath $appPath -ArgumentList @('--sampling-circuit-test', ('"'+$circuitPath+'"'), ('"'+$report+'"')) -WindowStyle Hidden -PassThru
    $child = $null
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        while (!$child -and !$parent.HasExited -and [DateTime]::UtcNow -lt $deadline) {
            $record = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($parent.Id)" | Where-Object { $_.Name -eq 'quantum-worker.exe' } | Select-Object -First 1
            if ($record) {
                $candidate = Get-Process -Id $record.ProcessId -ErrorAction SilentlyContinue
                $observedPath = $null
                $queryError = $null
                try {
                    if ($candidate -and !$candidate.HasExited) {
                        try { $observedPath = & $ReadProcessPath $candidate }
                        catch [System.ComponentModel.Win32Exception] { $queryError = $_.Exception.Message }
                        catch [System.InvalidOperationException] { $queryError = $_.Exception.Message }
                    }
                    $observations += @{parentId=$parent.Id; childId=$record.ProcessId; cimPath=$record.ExecutablePath; processPath=$observedPath; queryError=$queryError}
                    # CIM may identify the new process before it exposes its
                    # executable path. Bind and verify the live process instead.
                    if (![String]::IsNullOrWhiteSpace($observedPath)) {
                        if (![String]::Equals($observedPath,$workerPath,[StringComparison]::OrdinalIgnoreCase)) {
                            throw "Unexpected child executable. Expected '$workerPath'; observed '$observedPath'."
                        }
                        if ($candidate.StartTime.ToUniversalTime() -lt $parent.StartTime.ToUniversalTime()) { throw 'Child process predates the test parent.' }
                        $child = $candidate
                        $candidate = $null
                    }
                } finally { if ($candidate) { $candidate.Dispose() } }
                if (!$child) { Start-Sleep -Milliseconds 100 }
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
        if (!$parent.HasExited) {
            # A failed observation may precede child verification. Give our GUI
            # its normal cancellation path before resorting to forced cleanup.
            $closed = $parent.CloseMainWindow()
            if (!$closed -or !$parent.WaitForExit(5000)) { $parent.Kill(); $parent.WaitForExit() }
        }
        $parent.Dispose()
        $results | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $ReportDirectory 'results.json') -Encoding UTF8
        $observations | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $ReportDirectory 'observations.json') -Encoding UTF8
    }
}
Write-Output 'PASS: closing the GUI stops its sampling worker at three shutdown timings.'

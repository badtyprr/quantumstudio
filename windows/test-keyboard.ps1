param([string]$Distribution = (Join-Path (Split-Path $PSScriptRoot -Parent) 'dist\QuantumStudio'))
$ErrorActionPreference = 'Stop'
$app = Join-Path $Distribution 'QuantumStudio.exe'
if (!(Test-Path -LiteralPath (Join-Path $Distribution 'quantum-worker.exe'))) { throw 'Build and package the calculation worker before keyboard integration testing.' }
$resultPath = Join-Path ([IO.Path]::GetTempPath()) ('quantum-enter-' + [Guid]::NewGuid().ToString('N') + '.txt')
$process = Start-Process -FilePath $app -ArgumentList @('--enter-key-test', ('"' + $resultPath + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $process.WaitForExit(20000)) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Enter integration test timed out.'
    }
    if ($process.ExitCode -ne 0) { throw 'Enter integration test failed.' }
    $result = Get-Content -LiteralPath $resultPath -Raw
    if (-not $result.StartsWith('PASS:')) { throw "Enter integration validation failed: $result" }
    Write-Output $result
} finally {
    $process.Dispose()
    if (Test-Path -LiteralPath $resultPath) { Remove-Item -LiteralPath $resultPath }
}

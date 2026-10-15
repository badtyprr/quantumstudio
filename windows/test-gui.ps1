$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
& (Join-Path $PSScriptRoot 'build-gui.ps1')
$validation = Join-Path $repo 'dist\gui-validation'
New-Item -ItemType Directory -Force $validation | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$sessionTest = Join-Path $validation 'session-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$sessionTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'SessionStore.cs') (Join-Path $PSScriptRoot 'SessionStoreTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Session tests did not compile.' }
& $sessionTest
if ($LASTEXITCODE -ne 0) { throw 'Session tests failed.' }
$app = Join-Path $repo 'dist\QuantumStudio\QuantumStudio.exe'
$layout = Join-Path $validation ('layout-' + [Guid]::NewGuid().ToString('N') + '.txt')
$process = Start-Process -FilePath $app -ArgumentList @('--circuit-layout-test', ('"' + $layout + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $process.WaitForExit(30000)) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Circuit layout test timed out.'
    }
    if ($process.ExitCode -ne 0) { throw 'Circuit layout test failed.' }
    $result = Get-Content -LiteralPath $layout -Raw
    if (-not $result.StartsWith('PASS:')) { throw "Circuit layout validation failed: $result" }
    Write-Output $result
} finally { $process.Dispose() }

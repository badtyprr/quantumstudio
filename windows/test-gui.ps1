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
$qasmTest = Join-Path $validation 'qasm-input-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$qasmTest" (Join-Path $PSScriptRoot 'QasmImport.cs') (Join-Path $PSScriptRoot 'QasmImportTests.cs') (Join-Path $PSScriptRoot 'BoundedUtf8File.cs')
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM input tests did not compile.' }
& $qasmTest
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM input tests failed.' }
$circuitTest = Join-Path $validation 'circuit-file-tests.exe'
$circuitArgs = @('/nologo', '/target:exe', "/out:$circuitTest", "/reference:$fx\WPF\PresentationFramework.dll", "/reference:$fx\WPF\PresentationCore.dll", "/reference:$fx\WPF\WindowsBase.dll", "/reference:$fx\System.Xaml.dll", "/reference:$fx\System.Web.Extensions.dll")
foreach ($source in @('CircuitFileTests.cs','CircuitComposer.cs','QasmAngle.cs','QasmImport.cs','BoundedUtf8File.cs')) { $circuitArgs += Join-Path $PSScriptRoot $source }
& "$fx\csc.exe" @circuitArgs
if ($LASTEXITCODE -ne 0) { throw 'Circuit file tests did not compile.' }
& $circuitTest
if ($LASTEXITCODE -ne 0) { throw 'Circuit file tests failed.' }
$app = Join-Path $repo 'dist\QuantumStudio\QuantumStudio.exe'
$layout = Join-Path $validation ('layout-' + [Guid]::NewGuid().ToString('N') + '.txt')
$process = Start-Process -FilePath $app -ArgumentList @('--circuit-layout-test', ('"' + $layout + '"')) -WindowStyle Hidden -PassThru
try {
    # Exercise all layout combinations with the full 512-step circuit.
    $layoutDeadline = [DateTime]::UtcNow.AddSeconds(120)
    while (-not $process.WaitForExit(1000) -and [DateTime]::UtcNow -lt $layoutDeadline) {}
    if (-not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Circuit layout test timed out.'
    }
    if ($process.ExitCode -ne 0) { throw 'Circuit layout test failed.' }
    $result = Get-Content -LiteralPath $layout -Raw
    if (-not $result.StartsWith('PASS:')) { throw "Circuit layout validation failed: $result" }
    Write-Output $result
} finally { $process.Dispose() }

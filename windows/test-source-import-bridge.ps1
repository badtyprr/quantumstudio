param([string]$Distribution = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$Distribution) { $Distribution = Join-Path $repo 'dist\QuantumStudio' }
$Distribution = [IO.Path]::GetFullPath($Distribution)
if (!(Test-Path -LiteralPath (Join-Path $Distribution 'qasm-import\qasm-import.exe'))) { throw 'Build the frozen compiler before testing its C# bridge.' }
$validation = Join-Path $repo 'dist\source-bridge-validation'
New-Item -ItemType Directory -Force $validation | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
# The bridge resolves its compiler beside the executable, exactly as the GUI does.
# Keep this temporary test executable out of the distributable payload.
$test = Join-Path $Distribution ('source-bridge-test-'+[Guid]::NewGuid().ToString('N')+'.exe')
try {
    $compilerArgs = @('/nologo','/target:exe',"/out:$test","/reference:$fx\System.Web.Extensions.dll")
    foreach ($source in @('NumericalSampling.cs','ClassicalExpression.cs','ClassicalCircuit.cs','SourceCircuitDocument.cs','ClassicalProgramHistory.cs','QasmImport.cs','BoundedUtf8File.cs','SourceImportBridgeTests.cs')) { $compilerArgs += Join-Path $PSScriptRoot $source }
    & "$fx\csc.exe" @compilerArgs
    if ($LASTEXITCODE -ne 0) { throw 'Source import bridge tests did not compile.' }
    & $test $validation
    if ($LASTEXITCODE -ne 0) { throw 'Source import bridge tests failed.' }
} finally {
    if (Test-Path -LiteralPath $test) { Remove-Item -LiteralPath $test }
}

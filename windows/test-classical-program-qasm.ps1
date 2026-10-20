param([string]$CasesPath)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$CasesPath) {
    $CasesPath = Join-Path $repo ("dist/program-qasm/" + [Guid]::NewGuid().ToString('N') + "/cases.json")
}
$CasesPath = [IO.Path]::GetFullPath($CasesPath)
if (Test-Path -LiteralPath $CasesPath) { throw 'Select a fresh program-case path.' }
New-Item -ItemType Directory -Force -Path (Split-Path $CasesPath -Parent) | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$test = Join-Path $repo 'dist/ClassicalProgramQasmTests.exe'
$sources = @('ClassicalProgramQasm.cs', 'ClassicalQasmScopes.cs', 'ClassicalProgramQasmTests.cs', 'ClassicalCircuit.cs',
    'NumericalSampling.cs', 'ClassicalExpression.cs', 'ClassicalExpressionQasm.cs',
    'ClassicalQasmStorage.cs', 'QasmGateSerializer.cs', 'QasmAngle.cs') |
    ForEach-Object { Join-Path $PSScriptRoot $_ }
& "$fx/csc.exe" /nologo /target:exe "/out:$test" "/reference:$fx/System.Web.Extensions.dll" $sources
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM program tests did not compile.' }
& $test $CasesPath
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM program tests failed.' }
Write-Output "Generated semantic cases: $CasesPath"

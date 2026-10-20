param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$OutputDirectory) { $OutputDirectory = Join-Path $repo ("dist/export-validation/" + [Guid]::NewGuid().ToString('N')) }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Select a fresh export-test directory.' }
New-Item -ItemType Directory -Force -Path (Join-Path $repo 'dist') | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$test = Join-Path $repo 'dist/ClassicalQasmExportTests.exe'
$sources = @('ClassicalQasmExport.cs','ClassicalQasmExportTests.cs','ClassicalProgramQasm.cs',
    'ClassicalQasmScopes.cs','ClassicalCircuit.cs','NumericalSampling.cs','ClassicalExpression.cs',
    'ClassicalExpressionQasm.cs','ClassicalQasmStorage.cs','QasmGateSerializer.cs','QasmAngle.cs',
    'QasmImport.cs','BoundedUtf8File.cs') | ForEach-Object { Join-Path $PSScriptRoot $_ }
& "$fx/csc.exe" /nologo /target:exe "/out:$test" "/reference:$fx/System.Web.Extensions.dll" $sources
if ($LASTEXITCODE -ne 0) { throw 'Atomic export tests did not compile.' }
& $test $OutputDirectory
if ($LASTEXITCODE -ne 0) { throw 'Atomic export tests failed.' }

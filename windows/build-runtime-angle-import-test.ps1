param([string]$OutputPath)
$ErrorActionPreference='Stop'
if (!$OutputPath) { $OutputPath=Join-Path (Split-Path $PSScriptRoot -Parent) 'dist\gui-validation\runtime-angle-import-tests.exe' }
New-Item -ItemType Directory -Force (Split-Path $OutputPath -Parent) | Out-Null
$fx=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$sources=@('ClassicalCircuit.cs','ClassicalExpression.cs','NumericalSampling.cs','RuntimeAngleImportTests.cs',
    'ClassicalProgramQasm.cs','ClassicalQasmScopes.cs','ClassicalExpressionQasm.cs','ClassicalQasmStorage.cs','QasmGateSerializer.cs','QasmAngle.cs') |
    ForEach-Object { Join-Path $PSScriptRoot $_ }
& "$fx\csc.exe" /nologo /target:exe "/out:$OutputPath" "/reference:$fx\System.Web.Extensions.dll" $sources
if ($LASTEXITCODE -ne 0) { throw 'Runtime angle import adapter test did not compile.' }

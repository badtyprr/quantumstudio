param()
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$out=Join-Path $repo 'dist\real-expression-text-tests.exe'
New-Item -ItemType Directory -Force (Split-Path $out -Parent) | Out-Null
$fx=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$sources=@('ClassicalRealExpressionText.cs','ClassicalRealExpressionTextTests.cs','ClassicalExpressionText.cs','ClassicalCircuit.cs','ClassicalExpression.cs','NumericalSampling.cs') |
    ForEach-Object { Join-Path $PSScriptRoot $_ }
& "$fx\csc.exe" /nologo /target:exe "/out:$out" "/reference:$fx\System.Web.Extensions.dll" $sources
if ($LASTEXITCODE -ne 0) { throw 'Real expression text tests did not compile.' }
& $out
if ($LASTEXITCODE -ne 0) { throw 'Real expression text tests failed.' }

param([string]$OutputPath)
$ErrorActionPreference='Stop'
if (!$OutputPath) { $OutputPath=Join-Path (Split-Path $PSScriptRoot -Parent) 'dist\gui-validation\runtime-angle-import-tests.exe' }
New-Item -ItemType Directory -Force (Split-Path $OutputPath -Parent) | Out-Null
$fx=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
& "$fx\csc.exe" /nologo /target:exe "/out:$OutputPath" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'ClassicalCircuit.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'RuntimeAngleImportTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Runtime angle import adapter test did not compile.' }

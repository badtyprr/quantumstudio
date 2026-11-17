param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputPath){throw 'Select a new adapter output path.'}
New-Item -ItemType Directory -Force (Split-Path $OutputPath -Parent) | Out-Null
$fx=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$sources=@('ClassicalCircuit.cs','ClassicalExpression.cs','NumericalSampling.cs','QirImportBridgeTests.cs') |
    ForEach-Object { Join-Path $PSScriptRoot $_ }
& "$fx\csc.exe" /nologo /target:exe "/out:$OutputPath" "/reference:$fx\System.Web.Extensions.dll" $sources
if($LASTEXITCODE -ne 0){throw 'QIR native import test adapter did not compile.'}

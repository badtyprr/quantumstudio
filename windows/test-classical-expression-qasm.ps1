param([string]$CasesPath)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (!$CasesPath) {
    $CasesPath = Join-Path $repo ("dist/expression-qasm/" + [Guid]::NewGuid().ToString('N') + "/cases.json")
}
$CasesPath = [IO.Path]::GetFullPath($CasesPath)
if (Test-Path -LiteralPath $CasesPath) { throw 'Preserve earlier expression test cases; select a fresh path.' }
New-Item -ItemType Directory -Force -Path (Split-Path $CasesPath -Parent) | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$test = Join-Path $repo 'dist/ClassicalExpressionQasmTests.exe'
& "$fx/csc.exe" /nologo /target:exe "/out:$test" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalExpressionQasm.cs') (Join-Path $PSScriptRoot 'ClassicalExpressionQasmTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Typed OpenQASM expression test compilation failed.' }
& $test $CasesPath
if ($LASTEXITCODE -ne 0) { throw 'Typed OpenQASM expression tests failed.' }
Write-Output "Generated semantic cases: $CasesPath"

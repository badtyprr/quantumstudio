param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$validation=Join-Path $repo 'dist\gui-validation'
New-Item -ItemType Directory -Force $validation | Out-Null
$report=Join-Path $validation ('runtime-editor-'+[Guid]::NewGuid().ToString('N')+'.txt')
$app=Join-Path $Distribution 'QuantumStudio.exe'
$process=Start-Process -FilePath $app -ArgumentList @('--classical-editor-test',('"'+$report+'"')) -WindowStyle Hidden -PassThru
try {
    if (!$process.WaitForExit(30000)) { $process.Kill();$process.WaitForExit();throw 'Runtime angle editor checks timed out.' }
    if ($process.ExitCode -ne 0 -or !(Get-Content -LiteralPath $report -Raw).StartsWith('PASS:')) { throw 'Runtime angle editor interactions failed.' }
} finally { $process.Dispose() }
& (Join-Path $PSScriptRoot 'build-runtime-angle-import-test.ps1')
& $PythonPath (Join-Path $PSScriptRoot 'test-runtime-angle-editor.py') --prefix ($report+'.png.rotations') --adapter (Join-Path $validation 'runtime-angle-import-tests.exe') --worker (Join-Path $Distribution 'quantum-worker.exe')
if ($LASTEXITCODE -ne 0) { throw 'Runtime angle editor execution checks failed.' }

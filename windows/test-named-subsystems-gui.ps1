param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$Evidence,[Parameter(Mandatory=$true)][string]$WorkerRevision)
$ErrorActionPreference='Stop'
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
if(Test-Path -LiteralPath $Evidence){throw 'Use a fresh GUI evidence directory.'}
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$driver=Join-Path $Evidence 'dev17-gui-tests.exe'
& "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'Dev17GuiTests.cs')
if($LASTEXITCODE -ne 0){throw 'DEV-17 GUI driver compilation failed.'}
$app=Join-Path $Distribution 'QuantumStudio.exe'
$worker=Join-Path $Distribution 'quantum-worker.exe'
$provenance=@{application_path=$app;application_sha256=(Get-FileHash -LiteralPath $app).Hash.ToLower();worker_path=$worker;worker_revision=$WorkerRevision;worker_sha256=(Get-FileHash -LiteralPath $worker).Hash.ToLower();driver_sha256=(Get-FileHash -LiteralPath $driver).Hash.ToLower();verified_after_run=$false}
$provenance | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
$process=Start-Process -FilePath $driver -ArgumentList @(('"'+$app+'"'),('"'+$Evidence+'"')) -WindowStyle Hidden -PassThru
try {
 if(!$process.WaitForExit(300000)){$process.Kill();$process.WaitForExit();throw 'DEV-17 GUI tests timed out.'}
 $result=Get-Content -LiteralPath (Join-Path $Evidence 'result.txt') -Raw
 if($process.ExitCode -ne 0 -or !$result.StartsWith('PASS:')){throw $result}
 if((Get-FileHash -LiteralPath $app).Hash.ToLower() -ne $provenance.application_sha256 -or (Get-FileHash -LiteralPath $worker).Hash.ToLower() -ne $provenance.worker_sha256){throw 'GUI binaries changed during validation.'}
 $provenance.verified_after_run=$true
 $provenance | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
 Write-Output $result
}finally{$process.Dispose()}

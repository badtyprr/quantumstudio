param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$Evidence,[switch]$CompileOnly,[Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference='Stop'
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
if(Test-Path -LiteralPath $Evidence){throw 'Use a fresh GUI evidence directory.'}
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$driver=Join-Path $Evidence 'dev12-gui-tests.exe'
& "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'Dev12GuiTests.cs')
if($LASTEXITCODE -ne 0){throw 'DEV-12 GUI driver compilation failed.'}
if($CompileOnly){return}
$expressions=@('expect(2*X-Z,H*|0>)','apply(X,apply(CX,apply(Rx(pi/3),|000>,[2]),[2,1]),[0])','diff(expect(-471/2000*I+471/2000*Z,Rx(x)*|0>),x)','diff(expect(Z,Rx(2*x)*|0>),x,1,pi/4)','heigenvalues([4,-1,0;-1,4,-1;0,-1,4])','heigenvectors([4,-1,0;-1,4,-1;0,-1,4])','heigenvectors([0,-i;i,0])')
$expressions | Set-Content -LiteralPath (Join-Path $Evidence 'expressions.txt') -Encoding utf8
$app=Join-Path $Distribution 'QuantumStudio.exe'
if(!(Test-Path -LiteralPath (Join-Path $Distribution 'quantum-worker.exe'))){throw 'Actual worker is required.'}
$guiProvenance=@{application_path=$app;application_sha256=(Get-FileHash -LiteralPath $app).Hash.ToLower();worker_sha256=(Get-FileHash -LiteralPath (Join-Path $Distribution 'quantum-worker.exe')).Hash.ToLower();verified_after_run=$false}
$guiProvenance | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
$process=Start-Process -FilePath $driver -ArgumentList @(('"'+$app+'"'),('"'+$Evidence+'"')) -WindowStyle Hidden -PassThru
try {
 if(!$process.WaitForExit(300000)){$process.Kill();$process.WaitForExit();throw 'DEV-12 GUI tests timed out.'}
 $result=Get-Content -LiteralPath (Join-Path $Evidence 'result.txt') -Raw
 if($process.ExitCode -ne 0 -or !$result.StartsWith('PASS:')){throw $result}
 & $PythonPath (Join-Path $PSScriptRoot '../docs/learning-evidence/dev12/gui-verify.py') $Distribution $Evidence
 if($LASTEXITCODE -ne 0){throw 'Independent DEV-12 clipboard verification failed.'}
 if((Get-FileHash -LiteralPath $app).Hash.ToLower() -ne $guiProvenance.application_sha256 -or (Get-FileHash -LiteralPath (Join-Path $Distribution 'quantum-worker.exe')).Hash.ToLower() -ne $guiProvenance.worker_sha256){throw 'GUI binaries changed during validation.'}
 $guiProvenance.verified_after_run=$true
 $guiProvenance | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
 Write-Output $result
}finally{$process.Dispose()}

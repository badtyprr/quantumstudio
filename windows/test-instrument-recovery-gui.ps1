param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$Evidence,[Parameter(Mandatory=$true)][string]$Fixtures,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
if(Test-Path -LiteralPath $Evidence){throw 'Use a fresh evidence directory to preserve earlier results.'}
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$driver=Join-Path $Evidence 'instrument-recovery-gui-tests.exe'
& "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'InstrumentRecoveryGuiTests.cs')
if($LASTEXITCODE -ne 0){throw 'Instrument recovery GUI driver compilation failed.'}
if($CompileOnly){return}
$app=Join-Path $Distribution 'QuantumStudio.exe'
if(!(Test-Path -LiteralPath (Join-Path $Distribution 'quantum-worker.exe'))){throw 'Actual worker is required.'}
$hashes=@{}
foreach($name in @('QuantumStudio.exe','quantum-worker.exe')){$hashes[$name]=(Get-FileHash -LiteralPath (Join-Path $Distribution $name) -Algorithm SHA256).Hash}
$hashes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'binary-hashes-before.json')
$process=Start-Process -FilePath $driver -ArgumentList @(('"'+$app+'"'),('"'+$Evidence+'"'),('"'+(Resolve-Path -LiteralPath $Fixtures).Path+'"')) -WindowStyle Hidden -PassThru
try {
 if(!$process.WaitForExit(180000)){$process.Kill();$process.WaitForExit();throw 'Instrument recovery GUI tests timed out.'}
 $result=Get-Content -LiteralPath (Join-Path $Evidence 'result.txt') -Raw
 if($process.ExitCode -ne 0 -or !$result.StartsWith('PASS:')){throw $result}
 foreach($name in $hashes.Keys){if((Get-FileHash -LiteralPath (Join-Path $Distribution $name) -Algorithm SHA256).Hash -ne $hashes[$name]){throw 'Tested binary changed during GUI validation.'}}
 $hashes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'binary-hashes-after.json')
 Write-Output $result
}finally{$process.Dispose()}

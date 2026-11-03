param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$Fixtures,[Parameter(Mandatory=$true)][string]$Evidence,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
$Fixtures=(Resolve-Path -LiteralPath $Fixtures).Path
if(Test-Path -LiteralPath $Evidence){throw 'Use a fresh GUI evidence directory.'}
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$driver=Join-Path $Evidence 'steane-gui-tests.exe'
& "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'SteaneTransversalGuiTests.cs')
if($LASTEXITCODE -ne 0){throw 'Steane GUI driver compilation failed.'}
if($CompileOnly){return}
$paths=@('QuantumStudio.exe','quantum-worker.exe','qasm-import/qasm-import.exe')
$hashes=@{}
foreach($path in $paths){$hashes[$path]=(Get-FileHash -LiteralPath (Join-Path $Distribution $path)).Hash.ToLower()}
$provenance=@{package=$Distribution;binary_sha256=$hashes;verified_after_run=$false;mode='fresh GUI test hooks; no file-dialog claim'}
$provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
$app=Join-Path $Distribution 'QuantumStudio.exe'
$process=Start-Process -FilePath $driver -ArgumentList @(('"'+$app+'"'),('"'+$Fixtures+'"'),('"'+$Evidence+'"')) -WindowStyle Hidden -PassThru
try {
 if(!$process.WaitForExit(300000)){$process.Kill();$process.WaitForExit();throw 'Steane GUI tests timed out.'}
 $result=Get-Content -LiteralPath (Join-Path $Evidence 'result.txt') -Raw
 if($process.ExitCode -ne 0 -or !$result.StartsWith('PASS:')){throw $result}
 foreach($path in $paths){if((Get-FileHash -LiteralPath (Join-Path $Distribution $path)).Hash.ToLower() -ne $hashes[$path]){throw 'GUI binaries changed during validation.'}}
 $provenance.verified_after_run=$true
 $provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Evidence 'provenance.json')
 Write-Output $result
}finally{$process.Dispose()}

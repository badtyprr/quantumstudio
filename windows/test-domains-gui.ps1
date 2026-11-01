param([Parameter(Mandatory=$true)][string]$Distribution,[Parameter(Mandatory=$true)][string]$Evidence,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
$driver=Join-Path $Evidence 'domain-gui-tests.exe'
& "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'DomainGuiTests.cs')
if($LASTEXITCODE -ne 0){throw 'Domain GUI driver compilation failed.'}
if($CompileOnly){return}
$app=Join-Path $Distribution 'QuantumStudio.exe'
if(!(Test-Path -LiteralPath (Join-Path $Distribution 'quantum-worker.exe'))){throw 'Actual worker is required.'}
$process=Start-Process -FilePath $driver -ArgumentList @(('"'+$app+'"'),('"'+$Evidence+'"')) -WindowStyle Hidden -PassThru
try {
 if(!$process.WaitForExit(180000)){$process.Kill();$process.WaitForExit();throw 'Domain GUI tests timed out.'}
 $result=Get-Content -LiteralPath (Join-Path $Evidence 'result.txt') -Raw
 if($process.ExitCode -ne 0 -or !$result.StartsWith('PASS:')){throw $result}
 Write-Output $result
}finally{$process.Dispose()}


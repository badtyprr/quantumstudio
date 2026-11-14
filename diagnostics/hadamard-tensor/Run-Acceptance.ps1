# Requires a disposable, dedicated hosted Windows guest; never run on a personal desktop.
param(
 [Parameter(Mandatory=$true)][string]$Distribution,
 [Parameter(Mandatory=$true)][string]$Evidence,
 [Parameter(Mandatory=$true)][string]$Revision
)
$ErrorActionPreference='Stop'
if($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted'){throw 'Dedicated GitHub-hosted guest required.'}
if($PSVersionTable.PSVersion.Major -lt 7){throw 'PowerShell 7 required.'}
# Start-Process inherits PS7 module paths; a Windows PowerShell child can lose cmdlets.
$powerShell=(Get-Process -Id $PID).Path
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
if(Test-Path -LiteralPath $Evidence){throw 'Fresh evidence directory required.'}
New-Item -ItemType Directory -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$manifest=Get-Content -LiteralPath (Join-Path $Distribution 'build-manifest.json') -Raw | ConvertFrom-Json
if($manifest.revision -ne $Revision){throw 'Candidate manifest revision mismatch.'}
function Verify-Payload {
 foreach($entry in $manifest.files){
  $path=[IO.Path]::GetFullPath((Join-Path $Distribution $entry.path))
  if(!$path.StartsWith($Distribution+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Manifest path escapes payload.'}
  if((Get-FileHash -LiteralPath $path).Hash -ne $entry.sha256){throw "Payload mismatch: $($entry.path)"}
 }
}
function Run-Driver([string]$Executable,[string[]]$Arguments,[string]$Name){
 $owned=@{}
 $p=Start-Process -FilePath $Executable -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Evidence "$Name.stdout.log") -RedirectStandardError (Join-Path $Evidence "$Name.stderr.log")
 $owned[$p.Id]=$p.StartTime.ToUniversalTime().ToString('o')
 $deadline=[DateTime]::UtcNow.AddSeconds(330)
 $cleanup=@();$cleanupErrors=@();$driverFailure=$null
 try {
  do {
   $all=@(Get-CimInstance Win32_Process)
   # Repeated closure handles multiple descendant generations in one snapshot.
   do {
    $added=$false
    foreach($child in $all){
     if($owned.ContainsKey([int]$child.ParentProcessId) -and !$owned.ContainsKey([int]$child.ProcessId)){
      $parent=Get-Process -Id $child.ParentProcessId -ErrorAction SilentlyContinue
      $current=Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
      if($parent -and $current -and $parent.StartTime.ToUniversalTime().ToString('o') -eq $owned[[int]$child.ParentProcessId] -and
         $current.StartTime -ge $parent.StartTime -and
         [Math]::Abs(($current.StartTime.ToUniversalTime()-$child.CreationDate.ToUniversalTime()).TotalMilliseconds) -lt 1){
       $owned[[int]$child.ProcessId]=$current.StartTime.ToUniversalTime().ToString('o'); $added=$true
      }
     }
    }
   } while($added)
   $logBytes=0L
   foreach($suffix in @('stdout','stderr')){
    $log=Get-Item -LiteralPath (Join-Path $Evidence "$Name.$suffix.log") -ErrorAction SilentlyContinue
    if($log){$logBytes+=$log.Length}
   }
   if($logBytes -gt 16777216){throw "$Name exceeded the 16 MiB observed output limit"}
   if($p.HasExited){break}
   Start-Sleep -Milliseconds 500
  } while([DateTime]::UtcNow -lt $deadline)
  if(!$p.HasExited){throw "$Name timed out"}
  $p.WaitForExit()
  if($p.ExitCode -ne 0){throw "$Name exited $($p.ExitCode)"}
 } catch {$driverFailure=$_;throw} finally {
  foreach($id in $owned.Keys){
   try {
    $live=Get-Process -Id $id -ErrorAction SilentlyContinue
    if($live -and $live.StartTime.ToUniversalTime().ToString('o') -eq $owned[$id]){
     $live.Kill($true); $live.WaitForExit(10000) | Out-Null
     $cleanup+=@{pid=$id;start=$owned[$id];terminated=$live.HasExited}
     if(!$live.HasExited){$cleanupErrors+="Owned process $id did not terminate."}
    }
   } catch {$cleanupErrors+="Owned process ${id}: $($_.Exception.Message)"}
  }
  $identities=@(foreach($id in $owned.Keys){@{pid=$id;start=$owned[$id]}})
  try {
   @{observed_processes=$identities;cleanup=$cleanup;cleanup_errors=$cleanupErrors;primary_failure=if($driverFailure){$driverFailure.Exception.Message}else{$null};limitation='Polling can miss short-lived parents; dedicated single-job guest required. Guest disposal is final containment. Output limit is checked every polling interval, so transient overshoot is possible.'} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence "$Name.processes.json")
  } catch {$cleanupErrors+="Process evidence: $($_.Exception.Message)"}
  try {$p.Dispose()} catch {$cleanupErrors+="Process disposal: $($_.Exception.Message)"}
  if(!$driverFailure -and $cleanupErrors.Count){throw ($cleanupErrors -join '; ')}
 }

}
$passed=$false;$primaryFailure=$null
try {
 Verify-Payload
 Copy-Item -LiteralPath (Join-Path $Distribution 'build-manifest.json') -Destination $Evidence
 & (Join-Path $repo 'diagnostics/dev17-unattended/Inspect-Environment.ps1') -Evidence (Join-Path $Evidence 'environment') | Out-Null
 $environment=Get-Content (Join-Path $Evidence 'environment/environment.json') -Raw | ConvertFrom-Json
 if(!$environment.clipboard_open -or !$environment.clipboard_handle_closed){throw 'Native Clipboard preflight denied; no escalation attempted.'}
 @{revision=$Revision;runner=$env:RUNNER_NAME;image=$env:ImageOS;image_version=$env:ImageVersion;run=$env:GITHUB_RUN_ID;attempt=$env:GITHUB_RUN_ATTEMPT;sha=$env:GITHUB_SHA;job=$env:GITHUB_JOB} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'run.json')
 $source=Get-Content (Join-Path $PSScriptRoot 'source.json') -Raw | ConvertFrom-Json
 $fragment=Join-Path $PSScriptRoot 'fragment.txt'
 if((Get-FileHash -LiteralPath $fragment).Hash -ne $source.fragment_sha256){throw 'Source fragment mismatch.'}
 Copy-Item -LiteralPath $fragment,(Join-Path $PSScriptRoot 'source.json'),(Join-Path $PSScriptRoot 'expected.json') -Destination $Evidence
 $fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
 $driver=Join-Path $Evidence 'hadamard-tensor-gui-tests.exe'
 & "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $repo 'windows/HadamardTensorGuiTests.cs')
 if($LASTEXITCODE -ne 0){throw 'Hadamard-tensor driver compilation failed.'}
 Run-Driver $driver @(('"'+(Join-Path $Distribution 'QuantumStudio.exe')+'"'),('"'+$Evidence+'"')) 'hadamard-tensor'
 $result=Get-Content (Join-Path $Evidence 'result.json') -Raw | ConvertFrom-Json
 if(!$result.passed -or !$result.clipboardRestored -or $result.calls -ne 9 -or $result.checks -lt 45){throw 'Incomplete hadamard-tensor GUI result.'}
 $records=@(Get-Content (Join-Path $Evidence 'records.json') -Raw | ConvertFrom-Json)
 $expected=Get-Content (Join-Path $PSScriptRoot 'expected.json') -Raw | ConvertFrom-Json
 $first=$expected.symbolic_first;$stable=$expected.symbolic_stable;$two=$expected.two_qubit_copy;$one=$expected.one_qubit_copy
 $copies=@($first,$stable,$stable,'1',$stable,$two,$two,$one,$one)
 $expressions=@([IO.File]::ReadAllText($fragment),$first,$stable,'1',$stable,('replace(replace(replace('+$stable+',n,2),x_0,1),x_1,0)'),$two,('replace(replace('+$stable+',n,1),x_0,1)'),$one)
 $modes=@(0,1,1,1,1,0,1,0,1)
 if($records.Count -ne 9){throw 'Wrong calculation count.'}
 for($i=0;$i -lt 9;$i++){
  $record=$records[$i]
  if($record.expression -cne $expressions[$i] -or $record.mode -ne $modes[$i] -or $record.copy -cne $copies[$i] -or $record.state -ne 'passed' -or $record.label -ne 'EXACT RESULT' -or $record.status -ne 'Result copied.'){throw "GUI record $i mismatch."}
  if($i -eq 3 -and $record.display -cne '1'){throw 'Intervening scalar display changed.'}
  if($i -in @(5,6) -and $record.display -cne $expected.two_qubit_display){throw 'Two-qubit displayed vector changed.'}
  if($i -in @(7,8) -and $record.display -cne $expected.one_qubit_display){throw 'One-qubit displayed vector changed.'}
 }
 if([IO.File]::ReadAllText((Join-Path $Evidence 'saved-session.json')) -cne [IO.File]::ReadAllText((Join-Path $Evidence 'restored-session.json'))){throw 'Session restore mismatch.'}
 foreach($name in @('hadamard-tensor.qsession','final-session.json')){if(!(Test-Path -LiteralPath (Join-Path $Evidence $name))){throw "Missing $name"}}
 foreach($name in @('original','ordinary-copy','reopened','bound-two','numeric-copy','one-qubit')){
  $bytes=[IO.File]::ReadAllBytes((Join-Path $Evidence "$name.png"))
  if($bytes.Length -lt 8 -or [Convert]::ToHexString($bytes[0..7]) -ne '89504E470D0A1A0A'){throw 'Missing/invalid PNG capture.'}
 }
 $passed=$true
 } catch {$primaryFailure=$_;throw} finally {
 $payloadUnchanged=$false;$payloadError=$null;$finalErrors=@()
 try {Verify-Payload;$payloadUnchanged=$true} catch {$payloadError=$_.Exception.ToString()}
 try {
  @{unchanged=$payloadUnchanged;error=$payloadError} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'payload-after.json')
 } catch {$finalErrors+="Payload evidence: $($_.Exception.Message)"}
 try {
  $paths=@((Join-Path $Distribution 'QuantumStudio.exe'),(Join-Path $Distribution 'quantum-worker.exe'),(Join-Path $repo 'windows/HadamardTensorGuiTests.cs'))+@(Get-ChildItem -LiteralPath $PSScriptRoot -File | Select-Object -ExpandProperty FullName)+@(Get-ChildItem -LiteralPath $Evidence -File -Recurse | Select-Object -ExpandProperty FullName)
  $hashes=@(foreach($path in $paths){
   try {Get-FileHash -LiteralPath $path | Select-Object Path,Hash} catch {$finalErrors+="Hash ${path}: $($_.Exception.Message)"}
  })
  $hashes | ConvertTo-Json | Set-Content (Join-Path $Evidence 'hashes.json')
 } catch {$finalErrors+="Hash evidence: $($_.Exception.Message)"}
 try {
  @{automated_pass=($passed -and $payloadUnchanged -and !$finalErrors.Count);primary_failure=if($primaryFailure){$primaryFailure.Exception.ToString()}else{$null};evidence_errors=$finalErrors;visual_review='pending';revision=$Revision;scope='Nine GUI Calculate/Copy routes and production session Save/Open methods; no native file dialogs, whole notebook acceptance, merge or publication.';clipboard='Restored by harness on normal completion. Forced termination cannot guarantee restoration; disposable dedicated hosted guest only.';utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Evidence 'verdict.json')
 } catch {$finalErrors+="Verdict evidence: $($_.Exception.Message)"}
 if(!$primaryFailure -and (!$payloadUnchanged -or $finalErrors.Count)){throw ('Final verification failed: '+$payloadError+'; '+($finalErrors -join '; '))}
}

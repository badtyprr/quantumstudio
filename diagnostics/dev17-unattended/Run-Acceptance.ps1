# Requires PowerShell 7. Runs original fixture unchanged, then supplemental keywords.
param(
 [Parameter(Mandatory=$true)][string]$Distribution,
 [Parameter(Mandatory=$true)][string]$Evidence,
 [Parameter(Mandatory=$true)][string]$Revision
)
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'PowerShell 7 required.'}
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
 $cleanup=@()
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
   if($p.HasExited){break}
   Start-Sleep -Milliseconds 500
  } while([DateTime]::UtcNow -lt $deadline)
  if(!$p.HasExited){throw "$Name timed out"}
  $p.WaitForExit()
  if($p.ExitCode -ne 0){throw "$Name exited $($p.ExitCode)"}
 } finally {
  foreach($id in $owned.Keys){
   $live=Get-Process -Id $id -ErrorAction SilentlyContinue
   if($live -and $live.StartTime.ToUniversalTime().ToString('o') -eq $owned[$id]){
    $live.Kill($true); $live.WaitForExit(10000) | Out-Null
    $cleanup+=@{pid=$id;start=$owned[$id];terminated=$live.HasExited}
   }
  }
  $identities=@(foreach($id in $owned.Keys){@{pid=$id;start=$owned[$id]}})
  @{observed_processes=$identities;cleanup=$cleanup;limitation='Polling can miss short-lived parents; dedicated single-job guest required. Guest disposal is final containment.'} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence "$Name.processes.json")
  $p.Dispose()
  if(@($cleanup | Where-Object { !$_.terminated }).Count){throw "$Name left owned processes running."}
 }
}
$passed=$false
try {
 Verify-Payload
 Copy-Item -LiteralPath (Join-Path $Distribution 'build-manifest.json') -Destination $Evidence
 & (Join-Path $PSScriptRoot 'Inspect-Environment.ps1') -Evidence (Join-Path $Evidence 'environment') | Out-Null
 @{revision=$Revision;runner=$env:RUNNER_NAME;image=$env:ImageOS;image_version=$env:ImageVersion;run=$env:GITHUB_RUN_ID;attempt=$env:GITHUB_RUN_ATTEMPT;sha=$env:GITHUB_SHA;job=$env:GITHUB_JOB} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'run.json')
 $environment=Get-Content (Join-Path $Evidence 'environment/environment.json') -Raw | ConvertFrom-Json
 if(!$environment.clipboard_open){throw 'Native Clipboard preflight denied; no escalation attempted.'}
 $original=Join-Path $repo 'windows/test-named-subsystems-gui.ps1'
 Run-Driver 'powershell.exe' @('-NoProfile','-File',('"'+$original+'"'),'-Distribution',('"'+$Distribution+'"'),'-Evidence',('"'+(Join-Path $Evidence 'original')+'"'),'-WorkerRevision',$Revision) 'original'
 $originalResult=Get-Content (Join-Path $Evidence 'original/result.txt') -Raw
 $originalProvenance=Get-Content (Join-Path $Evidence 'original/provenance.json') -Raw | ConvertFrom-Json
 if(!$originalResult.StartsWith('PASS:') -or !$originalProvenance.verified_after_run){throw 'Original fixture did not verify.'}
 $keyword=Join-Path $Evidence 'keywords'
 New-Item -ItemType Directory -Path $keyword | Out-Null
 $fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
 $driver=Join-Path $keyword 'keyword-gui-tests.exe'
 & "$fx/csc.exe" /nologo /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'KeywordGuiTests.cs')
 if($LASTEXITCODE -ne 0){throw 'Keyword driver compilation failed.'}
 Run-Driver $driver @(('"'+(Join-Path $Distribution 'QuantumStudio.exe')+'"'),('"'+$keyword+'"')) 'keywords'
 if(!(Get-Content (Join-Path $keyword 'result.txt') -Raw).StartsWith('PASS:')){throw 'Keyword fixture did not pass.'}
 foreach($name in @('evaluated-mapping','tex-trace-reopened','unequal-dimensions','unknown-label')){if(!(Test-Path (Join-Path $Evidence "original/$name.png"))){throw 'Missing original capture.'}}
 foreach($name in @('not','and','or','xor')){foreach($extension in @('-trace.png','.qsession')){if(!(Test-Path (Join-Path $keyword ($name+$extension)))){throw 'Missing keyword evidence.'}}}
 Verify-Payload
 $passed=$true
} finally {
 $paths=@((Join-Path $Distribution 'QuantumStudio.exe'),(Join-Path $Distribution 'quantum-worker.exe'),(Join-Path $repo 'windows/Dev17GuiTests.cs'),(Join-Path $repo 'windows/test-named-subsystems-gui.ps1'))+@(Get-ChildItem -LiteralPath $PSScriptRoot -File | Select-Object -ExpandProperty FullName)+@(Get-ChildItem -LiteralPath $Evidence -Filter '*.exe' -Recurse | Select-Object -ExpandProperty FullName)
 $paths | Get-FileHash | Select-Object Path,Hash | ConvertTo-Json | Set-Content (Join-Path $Evidence 'hashes.json')
 @{automated_pass=$passed;visual_review='pending';unattended_route='unproven until executed on independent guest';revision=$Revision;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'verdict.json')
}

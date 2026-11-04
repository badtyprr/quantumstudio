# Dedicated hosted guest only. Never changes the product payload or desktop policy.
param(
 [Parameter(Mandatory=$true)][string]$Distribution,
 [Parameter(Mandatory=$true)][string]$Evidence,
 [Parameter(Mandatory=$true)][string]$Revision,
 [Parameter(Mandatory=$true)][string]$ProductSource,
 [Parameter(Mandatory=$true)][string]$HarnessRevision,
 [Parameter(Mandatory=$true)][string]$CandidateArchive,
 [Parameter(Mandatory=$true)][string]$SourceArchive
)
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'PowerShell 7 required.'}
if($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted'){throw 'Dedicated GitHub-hosted guest required.'}
if($Revision -cne '3fdf7ebd6141feec7c48005c4e3557229ed794c0'){throw 'This finite acceptance pins the reviewed complement product.'}
if($HarnessRevision -cnotmatch '^[0-9a-f]{40}$'){throw 'Full harness revision required.'}
$ProductSource=(Resolve-Path -LiteralPath $ProductSource).Path
$harness=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$productHead=git -C $ProductSource rev-parse HEAD
if($LASTEXITCODE -ne 0 -or $productHead -cne $Revision){throw 'Product checkout mismatch.'}
$harnessHead=git -C $harness rev-parse HEAD
if($LASTEXITCODE -ne 0 -or $harnessHead -cne $HarnessRevision){throw 'Harness checkout mismatch.'}
$harnessStatus=git -C $harness status --porcelain --untracked-files=all
if($LASTEXITCODE -ne 0 -or $harnessStatus){throw 'Harness checkout must be clean.'}
$Distribution=(Resolve-Path -LiteralPath $Distribution).Path
$CandidateArchive=(Resolve-Path -LiteralPath $CandidateArchive).Path
$SourceArchive=(Resolve-Path -LiteralPath $SourceArchive).Path
if(Test-Path -LiteralPath $Evidence){throw 'Fresh acceptance evidence required.'}
New-Item -ItemType Directory -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$manifestPath=Join-Path $Distribution 'build-manifest.json'
$manifestHash=(Get-FileHash -LiteralPath $manifestPath).Hash
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($manifest.revision -cne $Revision -or $manifest.candidate -isnot [bool] -or !$manifest.candidate){throw 'Expected exact-source Candidate payload.'}
$archives=@(Get-FileHash -LiteralPath $CandidateArchive,$SourceArchive | Select-Object Path,Hash)
$archives | ConvertTo-Json | Set-Content (Join-Path $Evidence 'archive-hashes-before.json')
Copy-Item -LiteralPath $manifestPath -Destination $Evidence
@{product_revision=$Revision;harness_revision=$HarnessRevision;candidate=$true;publication=$false;
  run=$env:GITHUB_RUN_ID;attempt=$env:GITHUB_RUN_ATTEMPT;event_revision=$env:GITHUB_SHA;
  product_source=$ProductSource;distribution=$Distribution;manifest_sha256=$manifestHash;
  session_route='Application serializer save/open and GUI recalculation; no native file dialogs.'} |
 ConvertTo-Json | Set-Content (Join-Path $Evidence 'binding.json')

function Verify-Payload {
 if((Get-FileHash -LiteralPath $manifestPath).Hash -ne $manifestHash){throw 'Manifest changed.'}
 $expected=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 [void]$expected.Add('build-manifest.json')
 foreach($entry in $manifest.files){
  if([IO.Path]::IsPathRooted($entry.path) -or !$expected.Add($entry.path)){throw 'Duplicate/rooted manifest path.'}
  $path=[IO.Path]::GetFullPath((Join-Path $Distribution $entry.path))
  if(!$path.StartsWith($Distribution+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Manifest path escapes payload.'}
  if((Get-FileHash -LiteralPath $path).Hash -ne $entry.sha256){throw "Payload mismatch: $($entry.path)"}
 }
 $actual=@(Get-ChildItem -LiteralPath $Distribution -Recurse -File | ForEach-Object { [IO.Path]::GetRelativePath($Distribution,$_.FullName).Replace('\','/') })
 if(!$expected.SetEquals($actual)){throw 'Payload file inventory changed.'}
 foreach($entry in $archives){if((Get-FileHash -LiteralPath $entry.Path).Hash -ne $entry.Hash){throw 'Candidate/source archive changed.'}}
}

function Run-Driver([string]$Executable,[string[]]$Arguments){
 $owned=@{};$cleanup=@()
 $p=Start-Process -FilePath $Executable -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Evidence 'driver.stdout.log') -RedirectStandardError (Join-Path $Evidence 'driver.stderr.log')
 $owned[$p.Id]=$p.StartTime.ToUniversalTime().ToString('o')
 $deadline=[DateTime]::UtcNow.AddSeconds(600)
 try {
  do {
   $all=@(Get-CimInstance Win32_Process)
   do {
    $added=$false
    foreach($child in $all){
     if($owned.ContainsKey([int]$child.ParentProcessId) -and !$owned.ContainsKey([int]$child.ProcessId)){
      $parent=Get-Process -Id $child.ParentProcessId -ErrorAction SilentlyContinue
      $current=Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
      if($parent -and $current -and $parent.StartTime.ToUniversalTime().ToString('o') -eq $owned[[int]$child.ParentProcessId] -and
         $current.StartTime -ge $parent.StartTime -and
         [Math]::Abs(($current.StartTime.ToUniversalTime()-$child.CreationDate.ToUniversalTime()).TotalMilliseconds) -lt 1){
       $owned[[int]$child.ProcessId]=$current.StartTime.ToUniversalTime().ToString('o');$added=$true
      }
     }
    }
   } while($added)
   if($p.HasExited){break}
   Start-Sleep -Milliseconds 500
  } while([DateTime]::UtcNow -lt $deadline)
  if(!$p.HasExited){throw 'Complement driver timed out.'}
  $p.WaitForExit()
  if($p.ExitCode -ne 0){throw "Complement driver exited $($p.ExitCode)."}
 } finally {
  foreach($id in $owned.Keys){
   $live=Get-Process -Id $id -ErrorAction SilentlyContinue
   if($live -and $live.StartTime.ToUniversalTime().ToString('o') -eq $owned[$id]){
    $live.Kill($true);$live.WaitForExit(10000) | Out-Null
    $cleanup+=@{pid=$id;start=$owned[$id];terminated=$live.HasExited}
   }
  }
  @{observed_processes=@(foreach($id in $owned.Keys){@{pid=$id;start=$owned[$id]}});cleanup=$cleanup;
    limitation='Polling can miss short-lived parents. Dedicated hosted guest disposal is final containment.'} |
   ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Evidence 'processes.json')
  $p.Dispose()
  if(@($cleanup | Where-Object {!$_.terminated}).Count){throw 'Owned driver processes remained.'}
 }
}

$passed=$false;$integrity=$false
try {
 Verify-Payload
 & (Join-Path $ProductSource 'diagnostics/dev17-unattended/Inspect-Environment.ps1') -Evidence (Join-Path $Evidence 'environment') | Out-Null
 $environment=Get-Content (Join-Path $Evidence 'environment/environment.json') -Raw | ConvertFrom-Json
 if(!$environment.clipboard_open){throw 'Native Clipboard preflight denied; no escalation attempted.'}
 $fx=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319'
 $driver=Join-Path $Evidence 'complement-gui-tests.exe'
 & "$fx/csc.exe" /nologo /codepage:65001 /target:exe /platform:x64 "/out:$driver" "/reference:$fx/WPF/PresentationFramework.dll" "/reference:$fx/WPF/PresentationCore.dll" "/reference:$fx/WPF/WindowsBase.dll" "/reference:$fx/System.Xaml.dll" "/reference:$fx/System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'ComplementGuiTests.cs')
 if($LASTEXITCODE -ne 0){throw 'Complement GUI driver compilation failed.'}
 $gui=Join-Path $Evidence 'gui'
 Run-Driver $driver @(('"'+(Join-Path $Distribution 'QuantumStudio.exe')+'"'),('"'+$gui+'"'))
 $result=Get-Content (Join-Path $gui 'result.json') -Raw | ConvertFrom-Json
 $cases=@('tex-zero','bra-one','plain-bra-control','x-control','xor-control','deferred-copy','deferred-b0','deferred-b1','session-reopen','reopened-b0','reopened-b1','invalid-two','invalid-negative','invalid-fraction','opaque-notable','opaque-not0','reject-multiletter')
 if(!$result.passed -or $result.cases.Count -ne 17 -or (Compare-Object $cases $result.cases)){throw 'Finite complement cases did not all pass.'}
 if($result.actual_clipboard_reads -ne 26 -or $result.actual_session_checks -ne 1 -or $result.native_file_dialogs){throw 'Clipboard/session route did not match the finite contract.'}
 if((Get-FileHash -LiteralPath (Join-Path $gui 'complement.qsession')).Hash -ne $result.session_sha256){throw 'Session hash mismatch.'}
 foreach($name in @('concrete','bra','deferred','reopened','invalid-domain','opaque','invalid-syntax')){
  if(!(Test-Path -LiteralPath (Join-Path $gui ($name+'.png')))){throw "Missing capture: $name"}
 }
 $passed=$true
} finally {
 try {Verify-Payload;$integrity=$true} finally {
  $paths=@($manifestPath,(Join-Path $Distribution 'QuantumStudio.exe'),(Join-Path $Distribution 'quantum-worker.exe'))+
   @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Select-Object -ExpandProperty FullName)+
   @(Get-ChildItem -LiteralPath $Evidence -Recurse -File | Select-Object -ExpandProperty FullName)
  $paths | Get-FileHash | Select-Object Path,Hash | ConvertTo-Json | Set-Content (Join-Path $Evidence 'hashes.json')
  @{automated_pass=($passed -and $integrity);payload_integrity=$integrity;product_revision=$Revision;harness_revision=$HarnessRevision;
    candidate=$true;publication=$false;visual_review='pending';native_file_dialogs=$false;
    route='Dedicated hosted guest; not locked-local-desktop acceptance.';utc=[DateTime]::UtcNow.ToString('o')} |
   ConvertTo-Json | Set-Content (Join-Path $Evidence 'verdict.json')
 }
}

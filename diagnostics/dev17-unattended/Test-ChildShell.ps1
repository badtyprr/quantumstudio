# Regression for the actual Run-Driver shell selection; no GUI or payload required.
param([Parameter(Mandatory=$true)][string]$Evidence)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Evidence){throw 'Fresh evidence directory required.'}
New-Item -ItemType Directory -Path $Evidence | Out-Null
$Evidence=(Resolve-Path -LiteralPath $Evidence).Path
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-Acceptance.ps1'),[ref]$null,[ref]$errors)
if($errors){throw ($errors | Out-String)}
$function=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Run-Driver'},$true)
Invoke-Expression $function.Extent.Text
# Evaluate the production selector and use the actual original-wrapper launch target.
$selector=$ast.Find({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$powerShell'},$true)
if($selector){Invoke-Expression $selector.Extent.Text}
$call=$ast.Find({param($n) $n -is [System.Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Run-Driver' -and $n.CommandElements[-1].Extent.Text -eq "'original'"},$true)
$target=Invoke-Expression $call.CommandElements[1].Extent.Text
$probe=Join-Path $Evidence 'probe.ps1'
@'
param([switch]$Fail)
$ErrorActionPreference='Stop'
$hash=Get-FileHash -LiteralPath $PSCommandPath
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Child must use PowerShell 7.'}
@{path=(Get-Process -Id $PID).Path;version=$PSVersionTable.PSVersion.ToString();hash=$hash.Hash} | ConvertTo-Json
if($Fail){
 $child=Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList @('-NoProfile','-Command','Start-Sleep -Seconds 30') -WindowStyle Hidden -PassThru
 @{pid=$child.Id;start=$child.StartTime.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'child.json')
 Start-Sleep -Seconds 3
 exit 23
}
'@ | Set-Content -LiteralPath $probe
Run-Driver $target @('-NoProfile','-File',('"'+$probe+'"')) 'availability'
$observed=Get-Content (Join-Path $Evidence 'availability.stdout.log') -Raw | ConvertFrom-Json
if($observed.path -ne (Get-Process -Id $PID).Path){throw 'Child executable differs from current host.'}
if($observed.hash -ne (Get-FileHash -LiteralPath $probe).Hash){throw 'Child file hashing failed.'}
$failed=$false
try { Run-Driver $target @('-NoProfile','-File',('"'+$probe+'"'),'-Fail') 'nonzero' }
catch { if($_.Exception.Message -ne 'nonzero exited 23'){throw}; $failed=$true }
if(!$failed){throw 'Runner suppressed child failure.'}
$child=Get-Content (Join-Path $Evidence 'child.json') -Raw | ConvertFrom-Json
$live=Get-Process -Id $child.pid -ErrorAction SilentlyContinue
if($live -and $live.StartTime.ToUniversalTime().ToString('o') -eq $child.start){throw 'Owned child survived cleanup.'}
$cleanup=Get-Content (Join-Path $Evidence 'nonzero.processes.json') -Raw | ConvertFrom-Json
if(!@($cleanup.cleanup | Where-Object { $_.pid -eq $child.pid -and $_.terminated }).Count){throw 'Missing successful child cleanup evidence.'}
@{passed=$true;target=$target;nonzero_exit=23;child_terminated=$true} | ConvertTo-Json | Set-Content (Join-Path $Evidence 'result.json')
Get-Content (Join-Path $Evidence 'result.json')

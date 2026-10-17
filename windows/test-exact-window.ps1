param([Parameter(Mandatory=$true)][string]$Distribution)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$output=Join-Path $repo 'dist\exact-window-validation'
New-Item -ItemType Directory -Force $output | Out-Null
$cases=@(
 @{Name='symbolic';Output=@(0);Gate='Ry(x)';Reset=$false},
 @{Name='saved-before-reset';Output=@(0);Gate='X';Reset=$true},
 @{Name='empty-output';Output=@();Gate='H';Reset=$false}
)
foreach($case in $cases) {
 $steps=@(@{Kind='Gate';Expression=$case.Gate;Wires=@(0)},@{Kind='Measure';Wires=@(0);ClassicalBit=0})
 if($case.Reset){$steps+=@{Kind='Reset';Wires=@(0)}}
 $document=@{Version=2;Qubits=1;Registers=@(@{Name='c';Size=1});OutputBits=$case.Output;Steps=$steps}
 $inputFile=Join-Path $output ($case.Name+'.qcircuit');$report=Join-Path $output ($case.Name+'.txt')
 [IO.File]::WriteAllText($inputFile,($document|ConvertTo-Json -Depth 10),(New-Object Text.UTF8Encoding($false)))
 $process=Start-Process -FilePath (Join-Path $Distribution 'QuantumStudio.exe') -ArgumentList @('--exact-circuit-test',('"'+$inputFile+'"'),('"'+$report+'"')) -WindowStyle Hidden -PassThru
 try {
  if(!$process.WaitForExit(30000)){$process.Kill();$process.WaitForExit();throw 'Exact window test timed out.'}
  if($process.ExitCode -ne 0 -or !(Test-Path $report)){throw 'Exact window test failed.'}
  $message=Get-Content -LiteralPath $report -Raw
  if(!$message.StartsWith('PASS:')){throw $message}
  # PowerShell's object conversion cannot represent the valid empty-record key.
  # Rename only that JSON key for inspection; the saved artifact remains unchanged.
  $json=Get-Content -LiteralPath ($report+'.json') -Raw
  $saved=$json.Replace('"":','"__empty_record__":')|ConvertFrom-Json
  $entries=@($saved.Result.probabilities.PSObject.Properties)
  if($saved.Circuit.Qubits -ne 1 -or $saved.Result.classical_bits -ne 1){throw 'Captured circuit changed.'}
  if($case.Name -eq 'symbolic') {
   if($entries.Count -ne 2 -or $saved.Result.probabilities.'0' -notmatch 'cos' -or $saved.Result.probabilities.'1' -notmatch 'sin'){throw 'Symbolic probabilities were lost.'}
  }elseif($case.Name -eq 'saved-before-reset') {
   if($entries.Count -ne 1 -or $saved.Result.probabilities.'1' -ne '1'){throw 'Saved record was lost on reset.'}
  }else {
   if($entries.Count -ne 1 -or $entries[0].Name -ne '__empty_record__' -or $entries[0].Value -ne '1'){throw 'Empty output did not preserve total mass.'}
  }
  foreach($entry in $entries) {
   $label=if($entry.Name -eq '__empty_record__'){''}else{$entry.Name}
   if(!(Get-Content -LiteralPath ($report+'.tsv') -Raw).Contains($label+"`t"+$entry.Value)){throw 'Copy data lost an exact value.'}
  }
  foreach($suffix in @('.png','.minimum.png')){if((Get-Item -LiteralPath ($report+$suffix)).Length -lt 1000){throw 'Missing exact window screenshot.'}}
  Write-Output ('PASS: '+$case.Name+' exact results, export data, normal and minimum layouts.')
 }finally{$process.Dispose()}
}

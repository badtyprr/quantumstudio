param([string]$MsysRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) '.tools\msys64'))
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$output = [IO.Path]::GetFullPath((Join-Path $repo 'dist\QuantumStudio'))
& "$PSScriptRoot\build-gui.ps1"
& "$PSScriptRoot\build-qasm-import.ps1"
$nativeBin = Join-Path $MsysRoot 'ucrt64\bin'
Copy-Item (Join-Path $repo 'src\qalc.exe') $output
$queue = [Collections.Generic.Queue[string]]::new()
$queue.Enqueue((Join-Path $output 'quantum-worker.exe'))
$queue.Enqueue((Join-Path $output 'qalc.exe'))
$dependencies = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
while ($queue.Count) {
    $binary = $queue.Dequeue()
    $imports = & "$nativeBin\objdump.exe" -p $binary
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect imports: $binary" }
    foreach ($line in $imports) {
        if ($line -match 'DLL Name:\s*(\S+)') {
            $name = $Matches[1]
            $source = Join-Path $nativeBin $name
            if ((Test-Path -LiteralPath $source) -and $dependencies.Add($name)) {
                Copy-Item -LiteralPath $source -Destination $output
                $queue.Enqueue((Join-Path $output $name))
            }
        }
    }
}
# Remove only redundant DLLs from this generated distribution, never recursively.
foreach ($dll in Get-ChildItem -LiteralPath $output -Filter '*.dll') {
    if ($dll.DirectoryName -ne $output) { throw 'Unexpected packaging path.' }
    if (!$dependencies.Contains($dll.Name)) { Remove-Item -LiteralPath $dll.FullName }
}
# Produce stripped copies separately: in-place GNU strip can fail during
# Windows executable scanning even when the destination can be copied safely.
foreach ($name in @('quantum-worker.exe', 'qalc.exe')) {
    $stripped = Join-Path $repo ('.tools/' + $name + '.stripped')
    & "$nativeBin\strip.exe" -o $stripped (Join-Path $output $name)
    if ($LASTEXITCODE -ne 0) { throw "Native executable stripping failed: $name" }
    for ($attempt = 0; ; $attempt++) {
        try {
            Copy-Item -LiteralPath $stripped -Destination (Join-Path $output $name) -Force
            break
        } catch [System.IO.IOException] {
            if ($attempt -ge 4) {
                Write-Warning "Keeping the built $name without stripping because Windows has locked it."
                break
            }
            Start-Sleep -Milliseconds 1000
        }
    }
}
New-Item -ItemType Directory -Force "$output\data" | Out-Null
Copy-Item "$repo\data\*.xml" "$output\data"
New-Item -ItemType Directory -Force "$output\definitions" | Out-Null
Copy-Item "$repo\data\*.xml" "$output\definitions"
Copy-Item "$repo\COPYING" "$output\LICENSE.txt"
Copy-Item "$PSScriptRoot\Notation-guide.html" $output
Copy-Item "$PSScriptRoot\README.txt" $output
Copy-Item "$repo\docs\quantum-notation.md" "$output\Research-and-coverage.md"
Copy-Item "$repo\docs\learning-source-inventory.json" "$output\Learning-source-inventory.json"
Copy-Item "$repo\docs\ibm-learning-sections.json" "$output\IBM-learning-sections.json"
Copy-Item "$repo\docs\qbraid-notebook-audit.json" "$output\qbraid-notebook-audit.json"
Copy-Item "$MsysRoot\ucrt64\share\licenses" "$output\licenses" -Recurse -Force
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-qasm-import.py"
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM import verification failed.' }
& "$PSScriptRoot\test-quantum.ps1" -Distribution $output
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-power-gates.py"
if ($LASTEXITCODE -ne 0) { throw 'Power-gate phase verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-hellinger.py"
if ($LASTEXITCODE -ne 0) { throw 'Hellinger distribution verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-binary-fractions.py"
if ($LASTEXITCODE -ne 0) { throw 'Binary numeral verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-indexed-spin.py"
if ($LASTEXITCODE -ne 0) { throw 'Indexed spin verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-rectangular-channels.py"
if ($LASTEXITCODE -ne 0) { throw 'Rectangular channel verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-ibm-measurement-lessons.py"
if ($LASTEXITCODE -ne 0) { throw 'IBM measurement lesson verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-matrix-order.py"
if ($LASTEXITCODE -ne 0) { throw 'Hermitian matrix order verification failed.' }
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-guide.py"
if ($LASTEXITCODE -ne 0) { throw 'Offline guide structure verification failed.' }
$cssTest = Join-Path $repo '.tools/css-circuit-package-test'
$cssProcess = Start-Process -FilePath (Join-Path $output 'QuantumStudio.exe') -ArgumentList @('--css-circuit-test', ('"' + $cssTest + '"')) -WindowStyle Hidden -PassThru -Wait
if ($cssProcess.ExitCode -ne 0) { throw "CSS circuit GUI verification failed; see $cssTest.txt" }
Get-Content -LiteralPath "$cssTest.txt"
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-css-circuits.py" $cssTest
if ($LASTEXITCODE -ne 0) { throw 'CSS circuit amplitude/export verification failed.' }
$cssEncoderTest = Join-Path $repo '.tools/css-encoder-circuit-package-test'
$cssEncoderProcess = Start-Process -FilePath (Join-Path $output 'QuantumStudio.exe') -ArgumentList @('--css-encoder-circuit-test', ('"' + $cssEncoderTest + '"')) -WindowStyle Hidden -PassThru -Wait
if ($cssEncoderProcess.ExitCode -ne 0) { throw "CSS encoder GUI verification failed; see $cssEncoderTest.txt" }
Get-Content -LiteralPath "$cssEncoderTest.txt"
& "$repo\.tools\qasm-venv\Scripts\python.exe" "$PSScriptRoot\test-css-encoder-circuits.py" $cssEncoderTest
if ($LASTEXITCODE -ne 0) { throw 'CSS encoder basis/amplitude verification failed.' }
Compress-Archive -Path $output -DestinationPath "$repo\dist\QuantumStudio-Windows-x64.zip" -Force
Get-FileHash "$repo\dist\QuantumStudio-Windows-x64.zip" -Algorithm SHA256

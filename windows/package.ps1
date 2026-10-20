param(
    [Parameter(Mandatory=$true)][string]$MsysRoot,
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [switch]$Candidate
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$MsysRoot = (Resolve-Path -LiteralPath $MsysRoot).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$output = Join-Path $repo 'dist\QuantumStudio'
function Invoke-SourceGit([string[]]$Arguments) {
    $result = & git -C $repo @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $Arguments" }
    return $result
}
function Assert-UnchangedSources {
    if ($revision -ne (Invoke-SourceGit -Arguments @('rev-parse','HEAD'))) { throw 'Source revision changed during the build.' }
    # Autoreconf and make dist regenerate these documentation/translation files.
    # Every other tracked input must still match the recorded revision.
    $changes = @(Invoke-SourceGit -Arguments @('diff','--name-only','HEAD'))
    $unexpected = @($changes | Where-Object { $_ -notmatch '^(ABOUT-NLS|INSTALL|(po|po-defs)/[^/]+\.pot?)$' })
    if ($unexpected.Count) { throw ('Source inputs changed during the build: ' + ($unexpected -join ', ')) }
}
$revision = Invoke-SourceGit -Arguments @('rev-parse','HEAD')
if (Invoke-SourceGit -Arguments @('status','--porcelain','--untracked-files=all')) { throw 'Package from a clean source checkout.' }
if (!$Candidate) {
    Invoke-SourceGit -Arguments @('fetch','origin','master') | Out-Null
    if ($revision -ne (Invoke-SourceGit -Arguments @('rev-parse','origin/master'))) { throw 'Releases must use the current merged master tip.' }
}
if (Test-Path -LiteralPath $output) { throw 'Use a fresh checkout: the package output directory already exists.' }
if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'build-native.sh'))) { throw 'The reviewed native build script is required.' }
$oldSource = $env:QUANTUM_SOURCE_DIR
$oldPython = $env:QUANTUM_PYTHON
try {
    $env:QUANTUM_SOURCE_DIR = $repo.Replace('\','/')
    $env:QUANTUM_PYTHON = $PythonPath.Replace('\','/')
    & (Join-Path $MsysRoot 'usr\bin\bash.exe') -lc 'export PATH="/ucrt64/bin:$PATH"; cd "$QUANTUM_SOURCE_DIR" && bash windows/build-native.sh && make dist-gzip'
    if ($LASTEXITCODE -ne 0) { throw 'Native build or tests failed.' }
} finally {
    $env:QUANTUM_SOURCE_DIR = $oldSource
    $env:QUANTUM_PYTHON = $oldPython
}
$archives = @(Get-ChildItem -LiteralPath $repo -Filter 'libqalculate-*.tar.gz' -File)
if ($archives.Count -ne 1) { throw 'Expected exactly one generated source archive.' }
& $PythonPath (Join-Path $PSScriptRoot 'test-source-dist.py') $archives[0].FullName
if ($LASTEXITCODE -ne 0) { throw 'Source archive verification failed.' }
Copy-Item -LiteralPath $archives[0].FullName -Destination (Join-Path $repo 'dist\QuantumStudio-source.tar.gz')
& (Join-Path $PSScriptRoot 'test-gui.ps1')
& (Join-Path $PSScriptRoot 'build-qasm-import.ps1') -PythonPath $PythonPath
& (Join-Path $PSScriptRoot 'test-source-import-bridge.ps1') -Distribution $output
& $PythonPath (Join-Path $PSScriptRoot 'test-composer-source-import.py') --package $output
if ($LASTEXITCODE -ne 0) { throw 'Composer source import validation failed.' }
& $PythonPath (Join-Path $PSScriptRoot 'test-classical-module-import.py') --package $output
if ($LASTEXITCODE -ne 0) { throw 'Classical module import validation failed.' }
& $PythonPath (Join-Path $PSScriptRoot 'test-source-files-ui.py') --package $output
if ($LASTEXITCODE -ne 0) { throw 'Source check/reimport GUI tests failed.' }
& $PythonPath (Join-Path $PSScriptRoot 'test-qasm-file-import.py') --frozen (Join-Path $output 'qasm-import/qasm-import.exe')
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM file import tests failed.' }
& $PythonPath (Join-Path $PSScriptRoot 'test-qasm-protocol.py')
if ($LASTEXITCODE -ne 0) { throw 'Packaged OpenQASM process contract tests failed.' }
$nativeBin = Join-Path $MsysRoot 'ucrt64\bin'
$queue = [Collections.Generic.Queue[string]]::new()
$queue.Enqueue((Join-Path $output 'quantum-worker.exe'))
$queue.Enqueue((Join-Path $output 'qalc.exe'))
$dependencies = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
while ($queue.Count) {
    $binary = $queue.Dequeue()
    $imports = & (Join-Path $nativeBin 'objdump.exe') -p $binary
    if ($LASTEXITCODE -ne 0) { throw "Cannot inspect imports: $binary" }
    foreach ($line in $imports) {
        if ($line -match 'DLL Name:\s*(\S+)') {
            $name = $Matches[1]
            if ([IO.Path]::GetFileName($name) -ne $name) { throw 'Invalid imported DLL name.' }
            $source = Join-Path $nativeBin $name
            if ((Test-Path -LiteralPath $source) -and $dependencies.Add($name)) {
                Copy-Item -LiteralPath $source -Destination $output
                $queue.Enqueue((Join-Path $output $name))
            }
        }
    }
}
New-Item -ItemType Directory -Path (Join-Path $output 'data') | Out-Null
Copy-Item (Join-Path $repo 'data\*.xml') (Join-Path $output 'data')
Copy-Item (Join-Path $repo 'COPYING') (Join-Path $output 'LICENSE.txt')
Copy-Item (Join-Path $PSScriptRoot 'Notation-guide.html') $output
Copy-Item (Join-Path $PSScriptRoot 'README.txt') $output
Copy-Item (Join-Path $repo 'docs\quantum-notation.md') (Join-Path $output 'Research-notes.md')
Copy-Item (Join-Path $MsysRoot 'ucrt64\share\licenses') (Join-Path $output 'licenses') -Recurse
$oldDefinitions = $env:QALCULATE_DEFINITIONS_DIR
try {
    $env:QALCULATE_DEFINITIONS_DIR = Join-Path $output 'data'
    & $PythonPath (Join-Path $repo 'src\quantum-worker-test.py') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged worker tests failed.' }
    & $PythonPath (Join-Path $repo 'src\quantum-sampling-request-test.py') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged numerical sampling tests failed.' }
    & $PythonPath (Join-Path $repo 'src\quantum-exact-request-test.py') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged exact circuit tests failed.' }
    & $PythonPath (Join-Path $repo 'src\quantum-classical-request-test.py') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged classical expression tests failed.' }
    & $PythonPath (Join-Path $repo 'src\quantum-loop-request-test.py') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged runtime loop checks failed.' }
    & (Join-Path $repo 'dist\gui-validation\classical-expression-tests.exe') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged classical expression adapter tests failed.' }
    & (Join-Path $repo 'dist\gui-validation\exact-circuit-tests.exe') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged exact circuit adapter tests failed.' }
    & (Join-Path $PSScriptRoot 'test-exact-window.ps1') -Distribution $output
    & (Join-Path $repo 'dist\gui-validation\sampling-tests.exe') (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged sampling adapter tests failed.' }
    & $PythonPath (Join-Path $PSScriptRoot 'test-qasm-import.py') --worker (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged OpenQASM numeric tests failed.' }
    & $PythonPath (Join-Path $PSScriptRoot 'test-qasm-classical-expressions.py') --worker (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged OpenQASM classical expression tests failed.' }
    $expressionCases = Join-Path $repo ('dist/expression-qasm/' + [Guid]::NewGuid().ToString('N') + '/cases.json')
    & (Join-Path $PSScriptRoot 'test-classical-expression-qasm.ps1') -CasesPath $expressionCases
    & $PythonPath (Join-Path $PSScriptRoot 'test-classical-expression-qasm.py') --cases $expressionCases --worker (Join-Path $output 'quantum-worker.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Packaged typed OpenQASM expression tests failed.' }
    & (Join-Path $PSScriptRoot 'test-keyboard.ps1') -Distribution $output
} finally { $env:QALCULATE_DEFINITIONS_DIR = $oldDefinitions }
$smoke = Join-Path $repo 'dist\package-smoke.png'
$process = Start-Process -FilePath (Join-Path $output 'QuantumStudio.exe') -ArgumentList @('--smoke-test', ('"'+$smoke+'"')) -WindowStyle Hidden -PassThru
try {
    if (!$process.WaitForExit(300000)) { $process.Kill(); $process.WaitForExit(); throw 'Packaged GUI smoke test timed out.' }
    if ($process.ExitCode -ne 0 -or !(Get-Content -LiteralPath ($smoke+'.txt') -Raw).StartsWith('PASS:')) { throw 'Packaged GUI smoke test failed.' }
} finally { $process.Dispose() }
$samplingReport = Join-Path $repo 'dist\sampling-smoke.txt'
$samplingProcess = Start-Process -FilePath (Join-Path $output 'QuantumStudio.exe') -ArgumentList @('--sampling-test', ('"'+$samplingReport+'"')) -WindowStyle Hidden -PassThru
try {
    if (!$samplingProcess.WaitForExit(45000)) { $samplingProcess.Kill(); $samplingProcess.WaitForExit(); throw 'Packaged sampling GUI timed out.' }
    if ($samplingProcess.ExitCode -ne 0 -or !(Get-Content -LiteralPath $samplingReport -Raw).StartsWith('PASS:')) { throw 'Packaged sampling GUI failed.' }
    Get-Content -LiteralPath $samplingReport
} finally { $samplingProcess.Dispose() }
& (Join-Path $PSScriptRoot 'test-sampling-shutdown.ps1') -Distribution $output -ReportDirectory (Join-Path $repo 'dist\sampling-shutdown')
Assert-UnchangedSources
if (!$Candidate) {
    Invoke-SourceGit -Arguments @('fetch','origin','master') | Out-Null
    if ($revision -ne (Invoke-SourceGit -Arguments @('rev-parse','origin/master'))) { throw 'Master changed during the build; rebuild the current merged tip.' }
}
$manifest = [ordered]@{revision=$revision; candidate=[bool]$Candidate; files=@()}
foreach ($file in Get-ChildItem -LiteralPath $output -File -Recurse) {
    $manifest.files += [ordered]@{path=$file.FullName.Substring($output.Length+1).Replace('\','/'); sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'build-manifest.json') -Encoding UTF8
$name = if ($Candidate) { 'QuantumStudio-candidate-Windows-x64.zip' } else { 'QuantumStudio-Windows-x64.zip' }
$zip = Join-Path $repo ('dist\'+$name)
Compress-Archive -LiteralPath $output -DestinationPath $zip
$verifyArguments = @((Join-Path $PSScriptRoot 'test-package.py'), $zip, '--revision', $revision)
if ($Candidate) { $verifyArguments += '--candidate' }
& $PythonPath @verifyArguments
if ($LASTEXITCODE -ne 0) { throw 'Portable ZIP verification failed.' }
Get-FileHash -LiteralPath $zip -Algorithm SHA256

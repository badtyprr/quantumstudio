$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
& (Join-Path $PSScriptRoot 'build-gui.ps1')
$validation = Join-Path $repo 'dist\gui-validation'
New-Item -ItemType Directory -Force $validation | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$sourceDocumentTest = Join-Path $validation 'source-circuit-document-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$sourceDocumentTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'SourceCircuitDocument.cs') (Join-Path $PSScriptRoot 'SourceCircuitDocumentTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Source circuit document tests did not compile.' }
& $sourceDocumentTest (Join-Path $PSScriptRoot 'fixtures/qb004/provenance-envelope.json')
if ($LASTEXITCODE -ne 0) { throw 'Source circuit document tests failed.' }
$textTest = Join-Path $validation 'classical-expression-text-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$textTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalCircuit.cs') (Join-Path $PSScriptRoot 'ClassicalExpressionText.cs') (Join-Path $PSScriptRoot 'ClassicalExpressionTextTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Classical expression text tests did not compile.' }
& $textTest
if ($LASTEXITCODE -ne 0) { throw 'Classical expression text tests failed.' }
$expressionTest = Join-Path $validation 'classical-expression-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$expressionTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalExpressionTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Classical expression adapter tests did not compile.' }
& $expressionTest
if ($LASTEXITCODE -ne 0) { throw 'Classical expression adapter tests failed.' }
& (Join-Path $PSScriptRoot 'test-classical-expression-qasm.ps1')
& (Join-Path $PSScriptRoot 'test-classical-storage-qasm.ps1')
& (Join-Path $PSScriptRoot 'test-classical-program-qasm.ps1')
& (Join-Path $PSScriptRoot 'test-classical-export.ps1')
$exactTest = Join-Path $validation 'exact-circuit-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$exactTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalCircuit.cs') (Join-Path $PSScriptRoot 'ExactCircuit.cs') (Join-Path $PSScriptRoot 'ExactCircuitTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Exact circuit adapter tests did not compile.' }
& $exactTest
if ($LASTEXITCODE -ne 0) { throw 'Exact circuit adapter tests failed.' }
$sessionTest = Join-Path $validation 'session-tests.exe'
$classicalTest = Join-Path $validation 'classical-circuit-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$classicalTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalCircuit.cs') (Join-Path $PSScriptRoot 'ClassicalCircuitTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Classical circuit tests did not compile.' }
& $classicalTest
if ($LASTEXITCODE -ne 0) { throw 'Classical circuit tests failed.' }
& $classicalTest --legacy-cold
if ($LASTEXITCODE -ne 0) { throw 'Cold legacy circuit tests failed.' }
$historyTest = Join-Path $validation 'classical-history-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$historyTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'NumericalSampling.cs') (Join-Path $PSScriptRoot 'ClassicalExpression.cs') (Join-Path $PSScriptRoot 'ClassicalCircuit.cs') (Join-Path $PSScriptRoot 'ClassicalProgramHistory.cs') (Join-Path $PSScriptRoot 'SourceCircuitDocument.cs') (Join-Path $PSScriptRoot 'ClassicalProgramHistoryTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Classical history tests did not compile.' }
& $historyTest
if ($LASTEXITCODE -ne 0) { throw 'Classical history tests failed.' }
& "$fx\csc.exe" /nologo /target:exe "/out:$sessionTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'SessionStore.cs') (Join-Path $PSScriptRoot 'MatrixDeclarations.cs') (Join-Path $PSScriptRoot 'SessionStoreTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Session tests did not compile.' }
& $sessionTest
if ($LASTEXITCODE -ne 0) { throw 'Session tests failed.' }
$matrixTest = Join-Path $validation 'matrix-declarations-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$matrixTest" "/reference:$fx\System.Web.Extensions.dll" (Join-Path $PSScriptRoot 'SessionStore.cs') (Join-Path $PSScriptRoot 'MatrixDeclarations.cs') (Join-Path $PSScriptRoot 'MatrixDeclarationsTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Matrix declaration tests did not compile.' }
& $matrixTest
if ($LASTEXITCODE -ne 0) { throw 'Matrix declaration tests failed.' }
$qasmTest = Join-Path $validation 'qasm-input-tests.exe'
& "$fx\csc.exe" /nologo /target:exe "/out:$qasmTest" (Join-Path $PSScriptRoot 'QasmImport.cs') (Join-Path $PSScriptRoot 'QasmImportTests.cs') (Join-Path $PSScriptRoot 'BoundedUtf8File.cs')
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM input tests did not compile.' }
& $qasmTest
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM input tests failed.' }
# Both editor-hosting test executables need the complete export component.
$exportSources = @('ClassicalQasmExport.cs','ClassicalProgramQasm.cs','ClassicalQasmScopes.cs','ClassicalExpressionQasm.cs','ClassicalQasmStorage.cs') | ForEach-Object { Join-Path $PSScriptRoot $_ }
$circuitTest = Join-Path $validation 'circuit-file-tests.exe'
$circuitArgs = @('/nologo', '/target:exe', "/out:$circuitTest", "/reference:$fx\WPF\PresentationFramework.dll", "/reference:$fx\WPF\PresentationCore.dll", "/reference:$fx\WPF\WindowsBase.dll", "/reference:$fx\System.Xaml.dll", "/reference:$fx\System.Web.Extensions.dll")
foreach ($source in @('CircuitFileTests.cs','ComposerSourceTests.cs','NumericalSampling.cs','ClassicalExpression.cs','ClassicalCircuit.cs','ClassicalProgramHistory.cs','SourceCircuitDocument.cs','ClassicalProgramWindow.cs','ClassicalExpressionText.cs','ExactCircuit.cs','ExactCircuitWindow.cs','SamplingWindow.cs','SamplingReadout.cs','CircuitComposer.cs','QasmGateSerializer.cs','WorkspaceTheme.cs','QasmAngle.cs','QasmImport.cs','BoundedUtf8File.cs')) { $circuitArgs += Join-Path $PSScriptRoot $source }
$circuitArgs += @((Join-Path $PSScriptRoot 'SourceFilesWindow.cs'), "/reference:$fx\System.Windows.Forms.dll")
$circuitArgs += $exportSources
& "$fx\csc.exe" @circuitArgs
if ($LASTEXITCODE -ne 0) { throw 'Circuit file tests did not compile.' }
& $circuitTest
if ($LASTEXITCODE -ne 0) { throw 'Circuit file tests failed.' }
$samplingTest = Join-Path $validation 'sampling-tests.exe'
$samplingArgs = @('/nologo', '/target:exe', "/out:$samplingTest", "/reference:$fx\WPF\PresentationFramework.dll", "/reference:$fx\WPF\PresentationCore.dll", "/reference:$fx\WPF\WindowsBase.dll", "/reference:$fx\System.Xaml.dll", "/reference:$fx\System.Web.Extensions.dll")
foreach ($source in @('SamplingTests.cs','NumericalSampling.cs','ClassicalExpression.cs','ClassicalCircuit.cs','ClassicalProgramHistory.cs','SourceCircuitDocument.cs','ClassicalProgramWindow.cs','ClassicalExpressionText.cs','ExactCircuit.cs','ExactCircuitWindow.cs','SamplingWindow.cs','SamplingReadout.cs','CircuitComposer.cs','QasmGateSerializer.cs','WorkspaceTheme.cs','QasmAngle.cs','QasmImport.cs','BoundedUtf8File.cs')) { $samplingArgs += Join-Path $PSScriptRoot $source }
$samplingArgs += @((Join-Path $PSScriptRoot 'SourceFilesWindow.cs'), "/reference:$fx\System.Windows.Forms.dll")
$samplingArgs += $exportSources
& "$fx\csc.exe" @samplingArgs
if ($LASTEXITCODE -ne 0) { throw 'Sampling tests did not compile.' }
& $samplingTest
if ($LASTEXITCODE -ne 0) { throw 'Sampling tests failed.' }
$app = Join-Path $repo 'dist\QuantumStudio\QuantumStudio.exe'
$matrixGuiTest = Join-Path $validation 'matrix-declarations-gui-tests.exe'
$matrixGuiArgs = @('/nologo', '/target:exe', '/platform:x64', "/out:$matrixGuiTest", "/reference:$fx\WPF\PresentationFramework.dll", "/reference:$fx\WPF\PresentationCore.dll", "/reference:$fx\WPF\WindowsBase.dll", "/reference:$fx\System.Xaml.dll", "/reference:$fx\System.Web.Extensions.dll", (Join-Path $PSScriptRoot 'MatrixDeclarationsGuiTests.cs'))
& "$fx\csc.exe" @matrixGuiArgs
if ($LASTEXITCODE -ne 0) { throw 'Matrix declaration GUI tests did not compile.' }
$matrixGuiImage = Join-Path $validation 'matrix-declarations.png'
$matrixGuiProcess = Start-Process -FilePath $matrixGuiTest -ArgumentList @(('"' + $app + '"'), ('"' + $matrixGuiImage + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $matrixGuiProcess.WaitForExit(30000)) { $matrixGuiProcess.Kill(); $matrixGuiProcess.WaitForExit(); throw 'Matrix declaration GUI tests timed out.' }
    if ($matrixGuiProcess.ExitCode -ne 0) { throw 'Matrix declaration GUI tests failed.' }
} finally { $matrixGuiProcess.Dispose() }

$classicalReport = Join-Path $validation ('classical-editor-' + [Guid]::NewGuid().ToString('N') + '.txt')
$classicalProcess = Start-Process -FilePath $app -ArgumentList @('--classical-editor-test', ('"' + $classicalReport + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $classicalProcess.WaitForExit(30000)) { $classicalProcess.Kill(); $classicalProcess.WaitForExit(); throw 'Classical editor test timed out.' }
    if ($classicalProcess.ExitCode -ne 0 -or !(Get-Content -LiteralPath $classicalReport -Raw).StartsWith('PASS:')) { throw "Classical editor failed: $(Get-Content -LiteralPath $classicalReport -Raw)" }
    Get-Content -LiteralPath $classicalReport
} finally { $classicalProcess.Dispose() }
$sessionResult = Join-Path $validation ('session-preservation-' + [Guid]::NewGuid().ToString('N') + '.txt')
$sessionProcess = Start-Process -FilePath $app -ArgumentList @('--session-preservation-test', ('"' + $sessionResult + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $sessionProcess.WaitForExit(30000)) { $sessionProcess.Kill(); $sessionProcess.WaitForExit(); throw 'Session preservation test timed out.' }
    $sessionReport = Get-Content -LiteralPath $sessionResult -Raw
    if ($sessionProcess.ExitCode -ne 0 -or -not $sessionReport.StartsWith('PASS:')) { throw $sessionReport }
    Write-Output $sessionReport
} finally { $sessionProcess.Dispose() }
$editorResult = Join-Path $validation ('state-editor-' + [Guid]::NewGuid().ToString('N') + '.txt')
$editorProcess = Start-Process -FilePath $app -ArgumentList @('--state-editor-test', ('"' + $editorResult + '"')) -WindowStyle Hidden -PassThru
try {
    if (-not $editorProcess.WaitForExit(30000)) { $editorProcess.Kill(); $editorProcess.WaitForExit(); throw 'State editor test timed out.' }
    if ($editorProcess.ExitCode -ne 0) { throw "State editor test failed: $(Get-Content -LiteralPath $editorResult -Raw)" }
    $editorReport = Get-Content -LiteralPath $editorResult -Raw
    if (-not $editorReport.StartsWith('PASS:')) { throw $editorReport }
    Write-Output $editorReport
} finally { $editorProcess.Dispose() }
$layout = Join-Path $validation ('layout-' + [Guid]::NewGuid().ToString('N') + '.txt')
$process = Start-Process -FilePath $app -ArgumentList @('--circuit-layout-test', ('"' + $layout + '"')) -WindowStyle Hidden -PassThru
try {
    # Exercise all layout combinations with the full 512-step circuit.
    $layoutDeadline = [DateTime]::UtcNow.AddSeconds(120)
    while (-not $process.WaitForExit(1000) -and [DateTime]::UtcNow -lt $layoutDeadline) {}
    if (-not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Circuit layout test timed out.'
    }
    if ($process.ExitCode -ne 0) { throw 'Circuit layout test failed.' }
    $result = Get-Content -LiteralPath $layout -Raw
    if (-not $result.StartsWith('PASS:')) { throw "Circuit layout validation failed: $result" }
    Write-Output $result
} finally { $process.Dispose() }

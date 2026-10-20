$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$output = Join-Path $repo 'dist\QuantumStudio'
New-Item -ItemType Directory -Force $output | Out-Null
$fx = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$compilerArgs = @('/nologo', '/target:winexe', '/platform:x64', "/out:$output\QuantumStudio.exe",
    "/resource:$PSScriptRoot\MainWindow.xaml,MainWindow.xaml",
    "/resource:$PSScriptRoot\examples.json,examples.json",
    "/reference:$fx\WPF\PresentationFramework.dll", "/reference:$fx\WPF\PresentationCore.dll",
    "/reference:$fx\WPF\WindowsBase.dll", "/reference:$fx\System.Xaml.dll", "/reference:$fx\System.Web.Extensions.dll", "$PSScriptRoot\QuantumStudio.cs", "$PSScriptRoot\CircuitComposer.cs", "$PSScriptRoot\QasmAngle.cs")
$compilerArgs += "$PSScriptRoot\QasmGateSerializer.cs"
$compilerArgs += "$PSScriptRoot\SessionStore.cs"
$compilerArgs += "$PSScriptRoot\MatrixDeclarations.cs"
$compilerArgs += "$PSScriptRoot\MatrixDeclarationEditor.cs"
$compilerArgs += "$PSScriptRoot\NumericalSampling.cs"
$compilerArgs += "$PSScriptRoot\ClassicalExpression.cs"
$compilerArgs += "$PSScriptRoot\ClassicalExpressionQasm.cs"
$compilerArgs += "$PSScriptRoot\ClassicalExpressionText.cs"
$compilerArgs += "$PSScriptRoot\ExactCircuit.cs"
$compilerArgs += "$PSScriptRoot\ExactCircuitWindow.cs"
$compilerArgs += "$PSScriptRoot\ClassicalCircuit.cs"
$compilerArgs += "$PSScriptRoot\ClassicalProgramHistory.cs"
$compilerArgs += "$PSScriptRoot\SourceCircuitDocument.cs"
$compilerArgs += "$PSScriptRoot\SourceFilesWindow.cs"
$compilerArgs += "/reference:$fx\System.Windows.Forms.dll"
$compilerArgs += "$PSScriptRoot\ClassicalProgramWindow.cs"
$compilerArgs += "$PSScriptRoot\SamplingWindow.cs"
$compilerArgs += "$PSScriptRoot\SamplingReadout.cs"
$compilerArgs += "$PSScriptRoot\NamedStateEditor.cs"
$compilerArgs += "$PSScriptRoot\WorkspaceTheme.cs"
$compilerArgs += "/resource:$PSScriptRoot\WorkspaceTheme.xaml,WorkspaceTheme.xaml"
$compilerArgs += "$PSScriptRoot\QasmImport.cs"
$compilerArgs += "$PSScriptRoot\BoundedUtf8File.cs"
$compilerArgs += "$PSScriptRoot\CssCircuitTests.cs"
$compilerArgs += "$PSScriptRoot\CssEncoderCircuitTests.cs"
& "$fx\csc.exe" @compilerArgs
if ($LASTEXITCODE -ne 0) { throw 'GUI compilation failed.' }

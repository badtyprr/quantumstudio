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
$compilerArgs += "$PSScriptRoot\SessionStore.cs"
$compilerArgs += "$PSScriptRoot\NamedStateEditor.cs"
$compilerArgs += "$PSScriptRoot\QasmImport.cs"
$compilerArgs += "$PSScriptRoot\BoundedUtf8File.cs"
$compilerArgs += "$PSScriptRoot\CssCircuitTests.cs"
$compilerArgs += "$PSScriptRoot\CssEncoderCircuitTests.cs"
& "$fx\csc.exe" @compilerArgs
if ($LASTEXITCODE -ne 0) { throw 'GUI compilation failed.' }

param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$python = if ($PythonPath) { (Resolve-Path -LiteralPath $PythonPath).Path } else { Join-Path $repo '.tools/qasm-venv/Scripts/python.exe' }
if (!(Test-Path $python)) { throw 'Create .tools/qasm-venv and install windows/qasm-import-requirements.txt first.' }
& $python -c "import pyqasm, PyInstaller; assert pyqasm.__version__ == '1.0.4'"
if ($LASTEXITCODE -ne 0) { throw 'Install windows/qasm-import-requirements.txt in .tools/qasm-venv.' }
& $python -m PyInstaller --noconfirm --clean --onedir --name qasm-import --distpath "$repo/dist/QuantumStudio" --workpath "$repo/.tools/qasm-import-build" --specpath "$repo/.tools" --collect-all pyqasm --collect-all openqasm3 --copy-metadata pyqasm --copy-metadata antlr4-python3-runtime "$PSScriptRoot/qasm-import.py"
if ($LASTEXITCODE -ne 0) { throw 'OpenQASM compiler packaging failed.' }
$licenses = Join-Path $repo 'dist/QuantumStudio/qasm-import/licenses'
New-Item -ItemType Directory -Force $licenses | Out-Null
$site = & $python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
if ($LASTEXITCODE -ne 0) { throw 'Could not locate compiler package licenses.' }
foreach ($metadata in Get-ChildItem -LiteralPath $site -Directory -Filter '*.dist-info') {
    $destination = Join-Path $licenses $metadata.Name
    New-Item -ItemType Directory -Force $destination | Out-Null
    foreach ($file in Get-ChildItem -LiteralPath $metadata.FullName) {
        if ($file.Name -match '^(licenses|license.*|copying.*|notice.*|METADATA)$') {
            Copy-Item -LiteralPath $file.FullName -Destination $destination -Recurse -Force
        }
    }
}
$pythonLicense = & $python -c "import sys; from pathlib import Path; print(Path(sys.base_prefix)/'LICENSE.txt')"
Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licenses 'Python-LICENSE.txt') -Force
& $python (Join-Path $PSScriptRoot 'test-qasm-arrays.py') --frozen (Join-Path $repo 'dist/QuantumStudio/qasm-import/qasm-import.exe')
if ($LASTEXITCODE -ne 0) { throw 'Compile-time array source/frozen checks failed.' }

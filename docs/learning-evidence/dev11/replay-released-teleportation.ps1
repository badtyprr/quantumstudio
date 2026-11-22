# Exercise the same compiler, session serialization and request builders as the release.
param(
    [Parameter(Mandatory)][string]$Directory,
    [Parameter(Mandatory)][string]$AppDirectory
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $AppDirectory).Path
$assembly = [Reflection.Assembly]::LoadFile("$root/QuantumStudio.exe")
$staticMethods = [Reflection.BindingFlags]'Static, Public, NonPublic'
$load = $assembly.GetType('ClassicalCircuit').GetMethod('Load', $staticMethods)
$sampling = $assembly.GetType('NumericalSampling')
$exact = $sampling.GetMethod('RequestExact', $staticMethods)
$sampled = $sampling.GetMethod('RequestClassical', $staticMethods)

foreach ($file in (Get-ChildItem -LiteralPath $Directory -Filter '*.qasm')) {
    $document = Get-Content -LiteralPath $file.FullName -Raw | & "$root/qasm-import/qasm-import.exe" --classical
    if ($LASTEXITCODE) { throw "Compiler rejected $($file.Name)" }
    $circuit = $load.Invoke($null, @(($document -join [Environment]::NewLine)))
    $saved = $circuit.Serialize()
    $circuit = $load.Invoke($null, @($saved))
    if ($circuit.Serialize() -cne $saved) { throw "Session round trip failed for $($file.Name)" }

    $fields = [object[]]@($circuit.OutputBits, $circuit.SamplingGates(), $circuit.VariableTypes,
        $circuit.LoopConditionBudget, $circuit.NumericTypes, $circuit.ArrayAllocations)
    $counts = [object[]]@($circuit.Qubits, $circuit.ClassicalBits)
    $request = $exact.Invoke($null, ($counts + $fields))
    [IO.File]::WriteAllBytes([IO.Path]::ChangeExtension($file.FullName, 'exact'), $request)
    $request = $sampled.Invoke($null, ($counts + @(10000, [uint64]731) + $fields))
    [IO.File]::WriteAllBytes([IO.Path]::ChangeExtension($file.FullName, 'sampled'), $request)
}

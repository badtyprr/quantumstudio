# DEV-16e verification on the published Windows package

The two editors passed the nested-module acceptance cases on the published checkpoint c5a456cd. The test began with the released ZIP and verified its SHA-256 against the release manifest. After the tests, every file from that ZIP was compared byte for byte with its installed copy.

The numerical composer imported each original QB-004 module through a wrapper and a nested Unicode directory for all eight three-bit preparations. For each case the saved circuit, the recompiled standalone export, and a separately inlined source program produced the expected 16-state probability vector. The oracle flips the ancilla exactly for odd input parity; Bernstein–Vazirani returns the input XOR 6 with equal probabilities for the two ancilla outcomes. The Windows import action also verified undo, redo, save and reopen.

The classical editor tested six preparations, exporting each original and edited program. The twelve standalone exports passed twelve exact and twelve 10,000-shot checks against independently specified observable results, including early termination. Both editors retained all three source files and their original bytes.

Each editor also exercised the real Source files dialog on both module graphs. A missing dependency and an invalid replacement each failed to reimport and preserved the circuit. A valid change to the secret reimported a different circuit. Undo restored the entire original serialized document. All four original module files were verified after restoration. The test driver invokes the dialog methods directly; the released application, compiler and worker binaries are the original published files.

## Reproduction

Unpack the verified Windows ZIP into a disposable directory. Run windows/test-classical-module-export.py with that package, its worker and a fresh output directory. Run replay-nested-composer.py with the package, windows/fixtures/qb004 and another fresh output directory. This check uses Qiskit and NumPy.

Compile ModuleRecovery.cs as a Windows .NET Framework program next to the unpacked application, referencing WindowsBase, PresentationCore, PresentationFramework and System.Xaml. For each module, copy its numerical test source graph to a fresh directory for each editor. Pass the entry filename, nested module filename, editor name (composer or classical) and a fresh output filename prefix to the driver. The fixture copies are temporarily changed by this recovery test. Each successful invocation exits with code zero and records both serialized states. The retained hashes and expected numerical outputs are in released-nested-editors.json.

DEV-16d diagnostic attribution and QB-004's full notebook and provider acceptance remain separate open items.

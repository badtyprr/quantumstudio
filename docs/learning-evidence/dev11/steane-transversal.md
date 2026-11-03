# DEV-11c: two encoded Steane blocks

Development evidence, 2026-11-02. The existing numerical circuit backend executes
the scoped two-block transversal CNOT. No product allocation limit or dense
constructor contract was changed. Final integrated package/release validation
remains pending. DEV-11 remains Partial: 16 rows inventoried, zero whole rows
certified.

## Source and adaptation

The pinned [source manifest](source-manifest.json) and [source map](source-map.json)
identify these official IBM notebook snapshots:

- IBM-062, cell 0 `bd74fbe8`, “Code spaces of CSS codes,” lines 418–437:
  explicit dual-code words and both Steane coset states. Notebook SHA-256
  `e8b1deec5f914fc07cd75fcf26051712116a936dc50d38ed2149032b8487b4f5`.
- IBM-067, cell 0 `816797bd`, “Examples of transversal gate implementations,”
  lines 40–50: bitwise CNOT between two CSS blocks. Notebook SHA-256
  `ea38373bb78b2e706adb458948e3a81225f41b49caf47ac61e0ca6ba64ed9ea6`.

These are mathematical-source adaptations, not original executable IBM code or
certification of the IBM-060 encoder drawing. The native oracle uses the literal
dual set `{0000000,0011110,0101101,0110011,1001011,1010101,1100110,1111000}`;
logical one is its complement. It does not generate expectations by replaying
the tested encoder gates.

Wires 0–6 form control block A, wires 7–13 target block B. Wire 0 is the most
significant bit; the ordered logical basis is 00,01,10,11. The adapted encoder
starts with the logical input on local wire 6 and six zero ancillas. Hadamards
and CNOTs generate the three independent words `1001011,0101101,0011110` and
the logical representative `0000111` (the complement representative modulo a
dual word). Transversal CNOT applies `CX(q,q+7)` for q=0,…,6.

## Existing routes investigated

`QuantumNumericalState` supports 0–25 qubits, a bounded pure-state vector and
one-to-three-wire unitary application. The worker's existing `QSAMPLE1` route
and the numerical composer also allow 25 qubits. `QuantumExactCircuit` and
`QuantumExactPhaseCircuit` instead have a 10-qubit circuit bound; the dense
Pauli constructor remains bounded to nine qubits. The preserved 14-qubit dense
constructor rejection is therefore not evidence that circuit execution was
missing, and remains an intentional rejection in the historical 286 fixtures.

## Independent checks

`src/quantum-steane-transversal-test.cc` runs the actual existing StateVector
kernel on all four encoded input columns. It checks every one of 16,384 complex
amplitudes before and after CNOT, logical overlaps, total norm and leakage
outside the code space. No per-column or common phase alignment is applied.
A fifth input has four nonzero coefficients
`(1,sqrt(2),i,i*sqrt(2))/sqrt(6)` and is compared in full after the same operation.
The fresh development run passed 163,910 checks. These are numerical comparisons
with absolute tolerance 1e-12, not exact-arithmetic product outputs. Independent
coset membership and the logical CNOT permutation are exact discrete oracles.
The two-block state uses 16,384 complex entries (262,144 bytes); no
16,384-by-16,384 operator is constructed.

[steane-probe.py](steane-probe.py) supplements that deterministic regression
with actual packaged-worker execution. Released worker `214e6866`, SHA-256
`42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d`, passed all
four encoded support/frequency cases (16,384 shots each, seed 674062) and a
complex coherent echo. The latter prepares logical `(1,i,i,1)/2`, encodes,
applies the physical transversal gadget, decodes, undoes the independent
logical CNOT and unprepares; all outcomes are zero. Sample counts supplement
the full-amplitude regression; they do not prove exact probabilities or zero
leakage on their own. No original fixture or historical result is rewritten.

## GUI and serialization

`windows/SteaneTransversalGuiTests.cs` loads the actual packaged application,
uses its frozen source importer and composer, checks import/undo/redo/edit,
saves and reopens `.qcircuit`, exports OpenQASM and raises the actual sampling
button. It compares all displayed outcome keys against the independent coset
oracle. File-dialog interaction is not claimed. The companion
`steane-verify-gui.py` checks saved source bytes and frozen reimports of the
complete exported gate sequence, allowing only the exporter's explicit leading
zero-initialization resets.

Failures are preserved. The initial driver used the driver's own application
base directory and could not locate the compiler; hosting against the package
base corrected this harness configuration without modifying package files.
The next attempt passed the first case but the existing application test hook
rejected Undo because JSON property order changed, although the captured
objects were semantically identical. The dedicated harness now compares JSON
structurally, preserving array order, values and source metadata. A fresh rerun
on unchanged released `214e6866` bytes passed 40 assertions across all five
cases, including actual sampling-button results. Independent frozen reimports
confirmed all five full exported circuits and retained source bytes. Four
captures were visually inspected (composer, minimum scrollable layout, a
64-outcome column and coherent all-zero echo). This is validation of the named
existing release, not the pending integrated release.

## Reproduction and provenance

Evidence is outside disposable checkouts at
`F:/src/libqalculate/cleanup-audit/dev11bc-20261102/steane/`: native compiler,
source and binary hashes in `native-provenance.json`; original fresh released
worker outputs and generated QASM/request fixtures in `released-214e6866/`;
separate GUI failure directories retain their original reports and snapshots.
The successful GUI rerun is `released-gui-214e6866-v3/`, with binary hashes checked
before and after, `serialization-verification.json` and `visual-inspection.json`.
The native development executable linked the existing StateVector source
directly; it is not represented as an already-tested final package executable.

```powershell
python docs/learning-evidence/dev11/steane-probe.py --worker <package>/quantum-worker.exe --sources <pinned-sources> --output <fresh-evidence>
pwsh -File windows/test-steane-transversal-gui.ps1 -Distribution <package> -Fixtures <fresh-evidence> -Evidence <fresh-gui-evidence>
python docs/learning-evidence/dev11/steane-verify-gui.py --helper <package>/qasm-import/qasm-import.exe --fixtures <fresh-evidence> --evidence <fresh-gui-evidence>
```

General decoders, fault propagation, noisy fault-tolerant gadgets, original
encoder diagrams and whole-source coverage remain separate. DEV-09's unresolved
symbolic case and DEV-10's limits are unchanged.

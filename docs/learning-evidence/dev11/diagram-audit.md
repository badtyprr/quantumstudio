# DEV-11e: original diagram tranche (Partial)

Base: `affdcc843916f1c4c40270135f9f7c2e4d83855f`, fetched from upstream on
2026-11-02. This is new audit evidence, not a product change or release. The
historical 286 inputs and expectations are unchanged. No full IBM row is certified.

## Sources and conventions

[diagram-media.json](diagram-media.json) pins 27 original SVGs linked by IBM-054,
IBM-055 and IBM-060, including original URLs, retrieval URLs, timestamps and
SHA-256. Initial direct requests returned HTTP 403; adding `?audit=dev11ef`
retrieved SVG bytes successfully. Both observations are retained. Original
notebooks and images remain outside this checkout at
`F:/src/libqalculate/cleanup-audit/dev11ef-20261102/media/` (images) and
`F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/sources/` (notebooks).
Every notebook hash is checked against the unchanged source manifest before a run.
These are markdown/media notebooks with **zero code cells**. None of the new
fixtures is original executable IBM notebook code.

Eighteen drawings were visually inspected: all 13 non-graph IBM-054 images,
the Shor encoder and both Shor phase-detection circuits, and both IBM-060 images.
The other nine retrieved images are not visually certified. SVGs were rendered
with CairoSVG 2.9.1 after setting width/height to viewBox dimensions in memory;
the original SVG bytes were not changed. The first percentage/auto-size rendering
was blank and was not used for inspection.

Numerical wire **0 is the top wire and the most significant state-vector bit**.
Time runs left to right. A filled dot is the control, circled plus the X target;
crossing an unrelated wire adds no control. Parallel gates on disjoint wires may
be serialized. IBM's repetition error output labels use the opposite ket display
order: the top-wire X example is labelled `001`, while our numerical vector is
`100`. The physical top-to-bottom syndrome stays `10`. Steane codeword expectations
reverse the IBM-062 seven-character words to match the IBM-060 physical drawing.
This is an explicit coordinate conversion, not a phase or wire fit to results.

`C(a,b)` below means control a, target b. All unmentioned workspace is |0>.
For |+> ancillas the fixture explicitly executes H on |0>. M is computational
basis measurement; a final H before M therefore measures the pre-H X observable.

| Original drawing / notebook section | Transcription in top-to-bottom coordinates |
|---|---|
| IBM-054 `repetition-encoder.svg`, Encoding qubits | Input on 0; 1,2 prepared |0>; C(0,1), C(0,2). No measurement/correction. |
| IBM-054 `repetition-encoder-modified.svg`, Modified repetition code for phase-flip errors | Same CNOTs followed by H(0), H(1), H(2). |
| IBM-054 `repetition-error-detection.svg`, Bit-flip errors | Data 0–2; ancillas 3,4 in |0>; C(0,3), C(1,3), C(1,4), C(2,4); M3,M4. |
| IBM-054 `three-bit-modified-error-detect.svg` | H on all three data wires, the four preceding parity CNOTs, H on all data wires; M3,M4. Ancillas start |0>. |
| IBM-054 `simplified-phase-error-detect.svg` | Ancillas 3,4 in |+>; C(3,0), C(3,1), C(4,1), C(4,2), H3,H4; M3,M4. Controls are ancillas, unlike the bit-flip circuit. |
| IBM-055 `Shor-encoder.svg`, Code description | Input 0; C(0,3), C(0,6); H(0,3,6); inner C(0,1), C(0,2), C(3,4), C(3,5), C(6,7), C(6,8). All eight other data wires start |0>. |
| IBM-055 `Shor-phase-error-detect-1.svg`, Correcting phase-flip errors | Original pink Z on wire 3 **before** inner encoding. After inner encoding, inverse inner CNOTs decode the blocks; ancillas 9,10 in |+>; C(9,0), C(9,3), C(10,3), C(10,6); reapply inner encoding; H9,H10; M9,M10 = 11. |
| IBM-055 `Shor-phase-error-detect-2.svg`, same section | Same original pre-inner Z3. Ancilla 9 controls X on wires 0–5; ancilla 10 controls X on 3–8. H9,H10; M9,M10 = 11. No decode/re-encode. |
| IBM-060 `Steane-encoder.svg`, Encoders for stabilizer codes | Input 0, six |0> ancillas. C(0,1); H4,H5,H6; C(0,2), C(6,3), C(6,1), C(6,0), C(5,3), C(5,2), C(5,0), C(4,3), C(4,2), C(4,1). No measurements or corrections. |

The eight IBM-054 worked error drawings (`repetition-decode-{no-error,e0,e1,e2}`
and `phase-error-{none,0,1,2}`) put no error or X/Z on the corresponding top,
middle or bottom data wire between encoder and extraction. Outcomes in that
order are 00,10,11,01. They retain the damaged data; the correction is in the
source table/prose, **not drawn as a conditional gate**. Our measured recovery
fixtures append X (bit code) or Z (phase code) on top/middle/bottom for 10/11/01.
For Shor, those same syndromes identify the top/middle/bottom **block**, and
correction is Z on that block's first wire, one of three degenerate choices.
Classical bit 0 stores the first/top measurement: the native integer record
for displayed 10 is 1, for 01 is 2. The fixtures check both conventions.

IBM-060 `lowest-weight-correction.svg` is a conceptual picture of syndrome
cosets and the distance argument, not an encoder or extraction circuit. It has
no concrete wires, ancilla preparation, measurements or correction gate list to
transcribe. Generic Steane syndrome synthesis is not claimed from this image.

## Execution and independent expectations

[diagram-audit.py](diagram-audit.py) owns the gate transcriptions. The native
adapter [diagram-native.cc](diagram-native.cc) calls the existing
`QuantumNumerics::StateVector::apply` and `measure` implementation from the pinned
base; it is not a replacement simulator. It is compiled independently of the
application and is **not a packaged GUI execution claim**. Numerical tolerance
is 1e-12. All amplitudes are scanned, including zeros. Comparisons do not discard
phases or fit each logical column independently.

Independent expectations are closed codeword formulas: repetition basis words,
plus/minus tensor coefficients, Shor GHZ-block parity signs, and the eight
explicit IBM-062 dual-code words plus their logical coset. They are not produced
by replaying the transcribed gates. Both complete logical basis columns and
`(|0>+i|1>)/sqrt(2)` are compared. Syndrome expectations come from the source
table/block location. Recovery compares the full physical vector with measured
ancillas retained, not just a logical overlap or zero syndrome.

The finite suite includes 216 manual cases: 12 encoder checks; 6 literal Shor
pink-Z drawings; 192 premeasurement/measured-recovery cases for both logical
columns and the complex witness across the three repetition extraction forms
and two Shor extraction forms; and 6 coherent-error/branch checks. The last six
insert H as a labeled **audit adaptation**, yielding two outcomes of probability
1/2. They check each actual collapsed branch. The uncorrectable logical component
in the zero-syndrome branch is retained; H is not falsely called correctable.
The generalized Shor sweep places Z after encoding; the six literal cases
separately retain the original pre-inner-encoding error location.

Fifty unitary-prefix cases undergo a real round trip:
manual circuit → product `QasmGateSerializer.Append` → OpenQASM 3 → released
`qasm-import.exe` → returned circuit → native core. The resulting full amplitudes
are checked against the **same independent expectations**, not only string or
gate-list equality. [diagram-export.cs](diagram-export.cs) calls the product
serializer; it does not reimplement its gate mapping. Original and returned
QASM/JSON are retained externally. This establishes finite manual-transcription
import/export compatibility. It does **not** import an SVG or a notebook, test
the GUI composer, or round-trip the dynamic measurement/correction suffixes.
Those suffixes are tested directly against the native measurement core.

`test_diagram_audit.py` proves the comparator rejects control/target reversal,
a relative-phase error with unchanged probabilities, and leakage, while passing
the correct control. Historical algebraic adaptations remain separate evidence.

## Reproduction and retained evidence

Use Python 3.12 and the retained UCRT compiler. Compile `diagram-native.cc` with
`libqalculate/QuantumNumericalState.cc`, `-std=c++17 -O2 -Ilibqalculate`.
Compile `diagram-export.cs`, `windows/QasmGateSerializer.cs`, and
`windows/QasmAngle.cs` with .NET Framework csc and `System.Web.Extensions.dll`.
Put both executables **outside** the checkout. Csc requires Windows-style source
paths. Compiler setup mistakes are not product failures.

Run `diagram-audit.py` with required `--native`, `--exporter`, `--helper`,
`--sources`, `--media`, `--toolchain`, and a new `--output` directory. The helper
used here is from `dist/releases/214e6866/QuantumStudio/qasm-import/`.
The run records source-file and executable hashes. `family-audit.py` shares this
adapter; its distinct source-prose adaptations are described in
[remaining-source-triage.md](remaining-source-triage.md).

Portable results and fixtures are in `diagram-results.json.gz` and
`diagram-fixtures.json.gz`; they are **saved fresh-run evidence**, not a new run
when decompressed. External raw results, sources, builds and visual-inspection
record remain at `F:/src/libqalculate/cleanup-audit/dev11ef-20261102/`.
DEV-11 and DEV-11e remain Partial: no whole-row or all-media certification,
generic encoder synthesis, arbitrary noise, or formal proof claim is made.

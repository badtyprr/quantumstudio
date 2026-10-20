# Local OpenQASM source bundles (DEV-16 prerequisite)

`windows/qasm_source_bundle.py` captures a selected source file and relative
include dependencies into an immutable snapshot. The compiler CLI supports it;
editor integration and persistence remain incomplete.

The selected source directory is the default root. A caller can explicitly
choose a wider root. Includes resolve against the including file's resolved
directory, never the process working directory. Absolute, drive-relative,
backslash-separated and alternate-stream paths reject; portable filenames use
`/`. Both lexical paths and resolved targets must stay inside the chosen root.
Standard `stdgates.inc` and `qelib1.inc` directives remain for the compiler.

The pinned OpenQASM lexer locates include statements without treating comments,
pragmas, or calibration text as dependencies. Expansion follows the
[OpenQASM include semantics](https://openqasm.com/versions/3.0/language/comments.html#included-files):
repeated includes expand repeatedly. Duplicate definitions are compiler errors,
not silently deduplicated. Newlines separate inserted text from its surroundings
so an included trailing line comment cannot consume the next source statement.

The component bounds total captured and expanded UTF-8 bytes to 262,144,
unique source/dependency paths to 64, and active nesting to 16. It reports
missing files, cycles and invalid includes with their including file and line.
Expansion pieces retain original source names and starting lines for a later
compiler diagnostic mapper. SHA-256 hashes refer to the captured bytes,
including any UTF-8 BOM. `changed_files()` checks both content hashes and
dependency target identities; it never mutates the captured program.

This is a local-file snapshot, not a sandbox for a filesystem being concurrently
modified by an adversary. Capturing and later checking changes are distinct
operations; no atomic multi-file snapshot is claimed.

Remaining DEV-16 work: persist source/dependency
identity in both editors and history, surface changed dependencies, map compiler
errors to original files, and verify standalone export and failure recovery.
No notebook execution or provider compatibility is established by this change.

## Source-aware compiler CLI

`qasm-import.exe --source-file "path/to/main.qasm"` reads the selected file with
its relative dependencies. `--source-root "path"` explicitly selects a wider
allowed root. These options do not consume stdin. The JSON response is an
envelope with `Version: 1`, `Circuit` (the existing compiled circuit document),
and `Source` (the versioned source snapshot). The snapshot includes root, entry,
dependency bindings, original UTF-8 text, BOM flags and hashes. The editor must
retain this provenance before this route replaces its current import path.
Stdin-only imports retain the existing circuit response and reject unresolved
local includes.

`--module-headers` explicitly enables a generated-module adapter: included
version headers must match the entry file's explicit major/minor version;
matching included headers and repeated standard-library includes are omitted
from the expanded compilation text. Original source remains in the snapshot.
Only `stdgates.inc` and `qelib1.inc` are treated as repeatable libraries in this
mode; custom declarations and repeated custom includes are never deduplicated.
Without this flag, strict textual include behavior applies.

The unchanged QB-004 `oracle.qasm` and `bernvaz.qasm` fixtures compile through
this mode to the same circuit documents as explicitly inlined definitions
(three and ten operations respectively). This does not establish notebook or
GUI import coverage. The eight file-import test methods also run against the
frozen compiler in CI and packaging.

## Saved documents and the classical editor

`SourceCircuitDocument` is an immutable C# wrapper for the circuit and its source
snapshot. The editor must provide its circuit validator/normalizer; the wrapper
invokes it during import, loading and every circuit replacement. The wrapper
validates snapshot fields, relative dependency paths, targets, UTF-8 byte
limits, BOM flags and source hashes. It performs no filesystem access:
the stored root is provenance metadata, not authorization to read that path.

Saved documents carry `Format: "QuantumStudio.SourceCircuit"`, `Version: 1`,
`Circuit`, `Source`, `PublishedU`, `Classical` and `OriginalCircuitSha256`.
The original fingerprint detects changes to the normalized circuit JSON after
import, independent of object-key ordering. It is informational metadata, not
a signature or a proof that the circuit was compiled from those sources.
Source text and hashes remain unchanged when the circuit is edited.

The document limits are 4 MiB for saved JSON, 256 KiB for normalized circuit
JSON, and 256 KiB total captured source bytes, with 64 files/bindings. Invalid
or unsavable replacements reject before returning a new object; the previous
document remains intact. Both editors use this wrapper for save/load and history
while keeping runtime circuit requests separate.
Source diagnostic mapping and standalone export acceptance
for both QB-004 generated subroutines remain unfinished.

`ClassicalProgramHistory` now retains the source wrapper with each history
entry. `ImportSource` validates a compiler envelope before creating an undo
step; `Serialize` writes the full saved document, while `Current.Serialize()`
continues to provide only the runtime circuit. Ordinary edits preserve source,
and undo/redo restores circuit, source and import options together. `Open`
accepts both legacy circuits and the saved wrapper and resets history only
after validation succeeds.

The classical editor imports through the file-based compiler route, using the
selected file's directory as the source root. Relative includes must remain in
that directory tree. The optional **Generated module headers** checkbox enables
the matching-header adapter described above; strict mode is the default.
Save retains the circuit and original sources together in `.qcircuit` files;
Open accepts these documents and legacy circuit-only files. Neither opening nor
saving reads the recorded source root. Sampling and exact evaluation continue
to receive the current circuit only.

The classical editor displays whether the circuit matches the imported snapshot or has
been edited since import. Undo/redo includes source and import options, and
the unsaved-changes check compares the complete saved document. The numerical
composer also uses the source-bearing document model as described below.

`windows/test-source-import-bridge.ps1` runs eleven checks against the frozen
compiler through the C# bridge, including Unicode/spaced paths, BOM,
local includes, the explicit module-header option, and unchanged history after
rejected imports. Both OpenQASM CI and packaging run this small integration test.

## Checking and reimporting retained source

In the numerical composer, choose **Import OpenQASM → Check / reimport source
files…**. In the classical editor, choose **Source files…**. These actions require
a circuit with retained source, imported or reopened from a source-bearing
`.qcircuit` document.

Select or enter the source folder containing the displayed entry path. The folder
starts blank: opening a saved document never grants access to its recorded root.
**Check files** reports each retained dependency as unchanged, changed, missing,
retargeted, or unavailable. It compares original bytes, including a UTF-8 BOM,
and dependency identity. It never changes the circuit, saved source, or history.
Unavailable includes inaccessible files, oversized files, and links outside the
selected folder. Checks are a point-in-time comparison, not a filesystem watch
or an atomic guarantee against concurrent file changes.

**Reimport from folder** compiles the current files with the original U convention,
module-header option, and editor mode. It replaces the current circuit only after
successful compilation and document validation. This intentionally replaces
circuit edits made since import; **Undo** restores the prior circuit and sources.
A failed reimport leaves them intact. Closing the dialog without reimporting
also preserves the current document. Reimport resolves the current include graph,
so new dependencies are captured even though a check compares only retained paths.

The equivalent compiler check is `qasm-import.exe --check-source --source-root
SELECTED_FOLDER`, with the saved `Source` object as UTF-8 JSON on stdin. It accepts
at most 4 MiB of JSON, validates all snapshot paths and hashes before filesystem
access, and returns a versioned report. Compilation flags cannot be combined with
checking. The selected folder, never the saved `Root`, supplies the read boundary.

`windows/test-source-files-ui.py` exercises both real editor dialogs with the
frozen compiler: blank selection, unchanged/changed/missing files, failed
reimport preservation, and undo after successful reimport. CI and packaging run
it and retain six screenshots; generating screenshots alone is not visual review.

## Numerical circuit composer

The composer's OpenQASM import menu uses the file-aware compiler route and offers
an explicit **Allow generated module headers** option. Imported source and U
convention remain attached through edits, save/open and undo/redo. Opening a
legacy circuit detaches the current source; undo restores the previous document.
State inspection, sampling and OpenQASM export use the current circuit.

Saved documents are validated before replacing controls. If an edit would exceed
the source-document save limit, the composer restores the previous snapshot and
reports that the change was not applied. No undo step is created by that rejected
edit. The source status distinguishes the original circuit from later edits.

Seventeen source-preservation checks run with the 102 existing circuit-file
checks, including wrong document kinds, source hash failures, legacy loading,
source-bearing save/reopen, and an edit against a document one byte below the
4 MiB limit. Packaged GUI validation and publication of this composer change
remain separate release gates.

`windows/test-composer-source-import.py` exercises the actual GUI with the frozen
compiler for a strict local include and both unchanged QB-004 generated
subroutines. It verifies original bytes/hashes, save/reopen and history, and
recompiles standalone exports. Export comparison requires the explicit initial
reset of each qubit followed by identical operations and wire order; it does not
ignore arbitrary reset differences. OpenQASM CI and packaging run these three
cases. This remains scoped circuit coverage, not a complete notebook audit.

Run `python windows/test-qasm-source-bundle.py` in the pinned compiler environment.
Tests cover nested and repeated includes, comments, spaces and Unicode paths,
UTF-8/BOM, missing/cyclic files, path boundaries and link retargeting, limits,
snapshot stability, and equivalence to explicitly inlined gate definitions.

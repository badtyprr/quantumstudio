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

## Saved-document model (not yet connected to the editors)

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
document remains intact. Future editor wiring must use this wrapper for
save/load and history while keeping runtime circuit requests separate.
Changed-file checks, source diagnostic mapping, GUI integration and standalone
export verification remain unfinished.

Run `python windows/test-qasm-source-bundle.py` in the pinned compiler environment.
Tests cover nested and repeated includes, comments, spaces and Unicode paths,
UTF-8/BOM, missing/cyclic files, path boundaries and link retargeting, limits,
snapshot stability, and equivalence to explicitly inlined gate definitions.

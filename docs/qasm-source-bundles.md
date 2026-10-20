# Local OpenQASM source bundles (DEV-16 prerequisite)

`windows/qasm_source_bundle.py` captures a selected source file and relative
include dependencies into an immutable snapshot. It is not yet connected to
the importer or editors; local-file include support remains incomplete.

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

Remaining DEV-16 work: define the import protocol, persist source/dependency
identity in both editors and history, surface changed dependencies, map compiler
errors to original files, and verify standalone export and failure recovery.
The QB-004 generated modules contain their own version headers; decide and test
compatible module-header handling explicitly before claiming those imports
work. This component preserves those headers rather than silently deleting them.
No notebook execution or provider compatibility is established by this change.

Run `python windows/test-qasm-source-bundle.py` in the pinned compiler environment.
Tests cover nested and repeated includes, comments, spaces and Unicode paths,
UTF-8/BOM, missing/cyclic files, path boundaries and link retargeting, limits,
snapshot stability, and equivalence to explicitly inlined gate definitions.

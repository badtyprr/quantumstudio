QuantumStudio for Windows 11 x64

Extract the entire ZIP, then run QuantumStudio.exe. Keep its DLLs, data,
licenses and qasm-import folder together. This is a portable application.

Choose Quantum notation for quantum expressions or Standard for ordinary
Qalculate! calculations and units. Enter or Ctrl+Enter calculates.
Shift+Enter adds a newline. Your example
  |<101|(H@H@H)|000>|^2
returns 0.125. Unicode bra-ket and tensor symbols work as well.

Browse examples, compose a circuit, or open the searchable Notation guide.
Save session preserves calculations; Save circuit preserves editable circuits.
For named states, choose States beside Calculate, then Add Bell example and
Apply states. This defines Bell as |Phi+> and after CZ as CZ|Bell>.
Now <Bell|Bell> returns 1 and <Bell|after CZ> returns 0. Save session keeps
the definitions, including those used by each history entry. Cancel discards
editor changes. Definitions may reference earlier rows and are not
automatically normalized; Calculate reports invalid vectors for correction.

OpenQASM import supports bounded static circuits through the bundled compiler.
Runtime feedback, timing and pulse program imports are not supported.

The guide documents operation limits, indexing and numerical conventions.
This release does not claim complete coverage of IBM Quantum Learning or
qBraid programming languages. Broader learning-notation coverage is ongoing.

build-manifest.json records the source revision and hashes of packaged files.
A filename containing "candidate" is a validation build, not a release.

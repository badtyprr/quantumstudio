# Practical near-term introduction and modern workflows

The practical introduction consists of 11 Markdown cells. The inventory found no standalone math inputs or code cells. The modern-workflows page has 14 standalone inputs and 14 illustrated figure references. Windows restored and re-entered 13 evaluated expressions. The CNOT conjugation arrow remains a diagnostic. The bare string ZZZZZZ defaults to sequential multiplication of six single-qubit Z gates. Use `pauli("ZZZZZZ")` to specify the six-qubit observable in the passage.

The two published layout tables retain each logical and physical index. Reusing a logical or physical qubit produces a diagnostic. Against an independent transcription of the connectivity and circuit in the exercise illustration, Qiskit transpiled both layouts with five CNOTs and zero SWAPs. Clifford conjugation of Z on qubit 5 through the published CNOT ladder produced the six-qubit Pauli string ZZZZZZ. Three independently generated six-qubit states gave the same expectation before and after the transformation to numerical precision.

Run replay-ibm139-layout.py with the pinned modern-workflows.mdx in the same directory. It checks the MDX digest and source layouts, then writes the Qiskit comparisons. The image manifest contains the hashes and dimensions of the source images. Course playback, external workflows and release acceptance remain open.

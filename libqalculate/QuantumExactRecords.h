// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_RECORDS_H
#define QUANTUM_EXACT_RECORDS_H
#include "MathStructure.h"
#include <cstdint>
#include <map>
#include <vector>

namespace QuantumExact {
// Each density matrix carries its own mass: never normalize individual records.
// These algebraic primitives do not certify positivity or physical operations.
using Records = std::map<std::uint64_t, MathStructure>;
// Qubit zero is leftmost; classical bit zero is the least significant bit.
// maxCells bounds stored matrix cells, not the size of symbolic expressions.
// Both functions leave inputs intact, including on cancellation or failure.
Records measure(const Records &input, unsigned qubits, unsigned classicalBits,
                unsigned wire, unsigned destination, std::size_t maxCells,
                const EvaluationOptions &options);
// First selected bit is most significant. Empty selection returns total mass.
std::map<std::uint64_t, MathStructure> weights(const Records &input,
                unsigned qubits, unsigned classicalBits,
                const std::vector<unsigned> &outputBits, std::size_t maxCells,
                const EvaluationOptions &options);
}
#endif

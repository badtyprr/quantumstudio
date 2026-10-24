// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_PHASE_CIRCUIT_H
#define QUANTUM_EXACT_PHASE_CIRCUIT_H
#include "QuantumExactCircuit.h"
#include "QuantumExactPhase.h"
#include <string>
namespace QuantumExact {
struct PhaseCircuitLimits {
 std::size_t maxTerms,maxProbabilityCharacters,maxTotalCharacters;
};
// Zero-input unitary circuits followed by computational measurements. Returns
// false for unsupported gates or circuit structure, without changing output.
// Invalid recognized inputs and resource/cancellation failures throw. No
// numerical substitution is used. Large probabilities retain exact |amplitude|²
// factors instead of expanding their products. Limits bound the compiled plan
// and each live state separately; at most two states coexist during a gate.
bool tryPhaseCircuitWeights(unsigned qubits,unsigned classicalBits,
 const std::vector<CircuitStep> &steps,const std::vector<unsigned> &outputBits,
 std::map<std::uint64_t,std::string> &output,PhaseBudget &budget,
 const PhaseCircuitLimits &limits);
}
#endif

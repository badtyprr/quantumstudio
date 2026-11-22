// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_INSTRUMENTS_H
#define QALCULATE_QUANTUM_INSTRUMENTS_H
class Calculator;
class MathStructure;
struct EvaluationOptions;
enum class QuantumValidity { Valid, Invalid, Unknown };
// The caller supplies a nonempty square matrix.
QuantumValidity quantumPositiveSemidefinite(MathStructure matrix,const EvaluationOptions &options);
void registerQuantumInstruments(Calculator &);
#endif

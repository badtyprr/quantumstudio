// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_STABILIZER_H
#define QALCULATE_QUANTUM_STABILIZER_H
#include <string>
class MathStructure;
class Calculator;
std::string quantumPauliTensorNotation(const MathStructure &);
void registerQuantumStabilizer(Calculator &);
#endif

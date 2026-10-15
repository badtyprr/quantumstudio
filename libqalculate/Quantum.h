// Quantum notation extension. GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_H
#define QALCULATE_QUANTUM_H
#include <string>
class Calculator;
// Byte offset after a leading quantum: marker, allowing pasted whitespace/BOM.
// Returns zero when the marker is absent.
size_t quantumPrefixLength(const std::string &expression);
// Throws std::runtime_error for invalid/unsupported quantum syntax.
std::string translateQuantum(const std::string &expression);
void registerQuantumFunctions(Calculator &calculator);
#endif

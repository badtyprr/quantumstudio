// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_BINARY_H
#define QALCULATE_QUANTUM_BINARY_H
class Calculator;
class MathStructure;
bool isQuantumBitLabel(const MathStructure &);
struct EvaluationOptions;
bool pendingQuantumGraphLookup(const MathStructure &,const MathStructure &,const EvaluationOptions &);
int applyQuantumBinaryGraph(MathStructure &,const MathStructure &,const MathStructure &,const EvaluationOptions &);
void registerQuantumBinary(Calculator &);
#endif

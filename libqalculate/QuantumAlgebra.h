// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_ALGEBRA_H
#define QALCULATE_QUANTUM_ALGEBRA_H
class Calculator;
class MathStructure;
struct EvaluationOptions;
// Global conjugation definitions must be loaded. Preserves singleton matrices.
MathStructure quantumAdjoint(const MathStructure &value, const EvaluationOptions &options);
// Infer shape only from concrete matrices or explicit matrix declarations.
bool quantumMatrixShape(const MathStructure &value, MathStructure &rows, MathStructure &columns, const EvaluationOptions &options);
void registerQuantumAlgebra(Calculator &calculator);
#endif

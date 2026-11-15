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
// Supply an ambient column dimension only to pending arithmetic basis labels
// in linear expressions. Never assign it to tensor factors or named states.
bool quantumResolveBasisDimension(MathStructure &value, const MathStructure &dimension);
void registerQuantumAlgebra(Calculator &calculator);
#endif

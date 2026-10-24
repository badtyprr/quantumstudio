// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_OPERATOR_DOMAIN_H
#define QALCULATE_QUANTUM_OPERATOR_DOMAIN_H
class Calculator;
class MathStructure;
struct EvaluationOptions;
// Domains are expression values, so substitution and canonical copy keep them.
void registerQuantumOperatorDomain(Calculator &calculator);
bool quantumOperatorDimension(const MathStructure &value, MathStructure &dimension,
                              const EvaluationOptions &options);
#endif

// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_BASIS_DOMAIN_H
#define QALCULATE_QUANTUM_BASIS_DOMAIN_H
class Calculator;
class MathStructure;
struct EvaluationOptions;
void registerQuantumBasisDomain(Calculator &calculator);
bool quantumBasisProduct(const MathStructure &left,const MathStructure &right,MathStructure &result);
bool quantumBasisSum(const MathStructure &body,const MathStructure &first,const MathStructure &last,
                     const MathStructure &index,MathStructure &result,const EvaluationOptions &options);
#endif

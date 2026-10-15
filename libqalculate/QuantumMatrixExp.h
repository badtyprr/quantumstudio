// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_MATRIX_EXP_H
#define QALCULATE_QUANTUM_MATRIX_EXP_H
#include "MathStructure.h"
class Calculator;
bool quantumMatrixExp(MathStructure &, const MathStructure &, const EvaluationOptions &);
void registerQuantumMatrixExp(Calculator &);
#endif

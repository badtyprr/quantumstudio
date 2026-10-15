// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_MATRIX_POWER_H
#define QALCULATE_QUANTUM_MATRIX_POWER_H
#include "MathStructure.h"
class Calculator;
bool quantumMatrixPower(MathStructure &,const MathStructure &,const MathStructure &,const EvaluationOptions &);
bool quantumMatrixLog(MathStructure &,const MathStructure &,const EvaluationOptions &);
void registerQuantumMatrixPower(Calculator &);
#endif

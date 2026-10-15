// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_MATRIX_H
#define QALCULATE_QUANTUM_MATRIX_H
#include "MathStructure.h"
bool quantumMatrixExp(MathStructure &out, const MathStructure &matrix, const EvaluationOptions &eo);
bool quantumMatrixPower(MathStructure &out,const MathStructure &matrix,const MathStructure &exponent,const EvaluationOptions &eo);
bool quantumMatrixLog(MathStructure &out,const MathStructure &matrix,const EvaluationOptions &eo);
bool quantumEntropy(MathStructure &out, const MathStructure &state, const EvaluationOptions &eo);
bool quantumNegativity(MathStructure &out, const MathStructure &partialTranspose, const EvaluationOptions &eo, bool logarithmic);
bool quantumTraceDistance(MathStructure &out, const MathStructure &first, const MathStructure &second, const EvaluationOptions &eo, bool fidelity=false);
bool quantumSchmidt(MathStructure &out,const MathStructure &state,const MathStructure &indices,const MathStructure *dimensions,const EvaluationOptions &eo);
bool quantumSchattenNorm(MathStructure &out,const MathStructure &matrix,const MathStructure &order,const EvaluationOptions &eo);
#endif

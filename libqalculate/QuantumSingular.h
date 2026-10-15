// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_SINGULAR_H
#define QALCULATE_QUANTUM_SINGULAR_H
#include "MathStructure.h"
// Internal finite-dimensional numerical routines; not parser entry points.
// Schmidt coefficients normalize the input ket and use leftmost subsystem 0.
// A null dimensions pointer selects qubits; otherwise their product must match.
// Results use double-precision Jacobi rotations, not arbitrary precision.
bool quantumSchmidt(MathStructure &out,const MathStructure &state,const MathStructure &indices,const MathStructure *dimensions,const EvaluationOptions &eo);
bool quantumSchattenNorm(MathStructure &out,const MathStructure &matrix,const MathStructure &order,const EvaluationOptions &eo);
#endif

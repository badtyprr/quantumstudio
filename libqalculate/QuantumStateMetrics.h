// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_STATE_METRICS_H
#define QALCULATE_QUANTUM_STATE_METRICS_H
#include "MathStructure.h"
// Internal numerical state metrics; inputs are normalized before comparison.
// Fidelity is squared. The numerical interface always returns a Number.
bool quantumEntropy(MathStructure &out,const MathStructure &state,const EvaluationOptions &eo);
bool quantumTraceDistance(MathStructure &out,const MathStructure &first,const MathStructure &second,const EvaluationOptions &eo,bool fidelity=false);
// The calculator can retain exact algebraic results for subsequent operations.
bool quantumStateMetric(MathStructure &out,const MathStructure &first,const MathStructure &second,const EvaluationOptions &eo,bool fidelity,bool allowExactExpressions);
#endif

// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_INDEXED_H
#define QALCULATE_QUANTUM_INDEXED_H
class Calculator;
class MathStructure;
struct EvaluationOptions;
#include <string>
#include <vector>
// The first argument of these operations names a coefficient or register family.
inline bool quantumHasIndexedNameArgument(const std::string &name) {
 return name=="qstatecall" || name=="qstatecalls" || name=="qindexedcolumn" ||
        name=="qdescendingcolumn" || name=="qindexedmatrix" || name=="qsamplebitmatrix" ||
        name=="qsampledotcolumn" || name=="qsamplewordrows" || name=="qindexedcoefficient" ||
        name=="qregisterfamily" || name=="qregisterword" || name=="qfamilymembers";
}
void registerQuantumIndexed(Calculator &);
void defineQuantumStateFamily(Calculator &,const std::string &,const MathStructure &,const MathStructure &);
void defineQuantumStateFamily(Calculator &,const std::string &,const MathStructure &,const std::vector<MathStructure> &);
// Lower a complex declaration in free occurrences, respecting nested binders.
void declareQuantumComplexParameter(Calculator &,MathStructure &,const MathStructure &);
enum class QuantumBitLabelState { Invalid, Symbolic, Concrete };
// Evaluate and validate both fields before deciding whether a label must defer.
QuantumBitLabelState validateQuantumBitLabel(MathStructure &,MathStructure &,const EvaluationOptions &);
// Return false when equality of the finite sets is still undecided.
bool compareQuantumSets(const MathStructure &,const MathStructure &,bool &equal,const EvaluationOptions &);
// Internal shape inputs. Preserve the original expression's domain constraints;
// never expand a series or evaluate a factor merely to obtain its dimensions.
bool quantumTensorSeriesShapeInput(const MathStructure &,MathStructure &factor,MathStructure &count,const EvaluationOptions &);
bool quantumSetSumShapeInput(const MathStructure &,MathStructure &term,const EvaluationOptions &);
bool quantumRegisterSumShapeInput(const MathStructure &,MathStructure &term,MathStructure &dependentMarkers,const EvaluationOptions &);
bool quantumReplacementShapeInput(const MathStructure &,MathStructure &term,const EvaluationOptions &);
bool quantumScalarExpression(const MathStructure &);
#endif

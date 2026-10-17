// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_INDEXED_H
#define QALCULATE_QUANTUM_INDEXED_H
class Calculator;
class MathStructure;
#include <string>
#include <vector>
void registerQuantumIndexed(Calculator &);
void defineQuantumStateFamily(Calculator &,const std::string &,const MathStructure &,const MathStructure &);
void defineQuantumStateFamily(Calculator &,const std::string &,const MathStructure &,const std::vector<MathStructure> &);
// Lower a complex declaration in free occurrences, respecting nested binders.
void declareQuantumComplexParameter(Calculator &,MathStructure &,const MathStructure &);
#endif

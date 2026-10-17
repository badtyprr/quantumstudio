// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_INDEXED_H
#define QALCULATE_QUANTUM_INDEXED_H
class Calculator;
class MathStructure;
#include <string>
void registerQuantumIndexed(Calculator &);
void defineQuantumStateFamily(Calculator &,const std::string &,const MathStructure &,const MathStructure &);
#endif

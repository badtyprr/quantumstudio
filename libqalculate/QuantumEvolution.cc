// GPL-2.0-or-later; see COPYING.
#include "QuantumEvolution.h"
#include "QuantumMatrixExp.h"
#include "Calculator.h"
#include "Function.h"
namespace {
class QuantumEvolutionFunction: public MathFunction {
 public:
 QuantumEvolutionFunction():MathFunction("qevolution",2) {}
 ExpressionItem *copy() const {return new QuantumEvolutionFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure h=raw[0],time=raw[1];h.eval(eo);time.eval(eo);
  if(!h.isMatrix() || h.rows()!=h.columns() || h.rows()>64 || !time.representsReal()) {
   CALCULATOR->error(true,"evolution(H,t) requires a square Hamiltonian of dimension at most 64 and real scalar time (hbar=1).",NULL);return 0;
  }
  auto conjugate=CALCULATOR->getFunction("conj");
  if(!conjugate) {CALCULATOR->error(true,"Load global functions before Hamiltonian evolution.",NULL);return 0;}
  for(size_t r=1;r<=h.rows();++r)for(size_t c=r;c<=h.columns();++c) {
   if(CALCULATOR->aborted())return 0;
   MathStructure value=*h.getElement(c,r),difference(conjugate,&value,NULL);
   difference-=*h.getElement(r,c);difference.eval(eo);
   if(!difference.isZero()) {CALCULATOR->error(true,"Evolution requires a Hermitian Hamiltonian; use qexp for general matrix exponentials.",NULL);return 0;}
  }
  Number minusI;minusI.setImaginaryPart(-1);
  h*=time;h*=minusI;h.eval(eo);
  return quantumMatrixExp(out,h,eo) ? 1 : 0;
 }
};
}
void registerQuantumEvolution(Calculator &calculator) {calculator.addFunction(new QuantumEvolutionFunction());}

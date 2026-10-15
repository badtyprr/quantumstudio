// GPL-2.0-or-later; see COPYING.
#include "QuantumReset.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure dagger(const MathStructure &a, const EvaluationOptions &eo) {
 MathStructure out=a;
 if(out.isMatrix()) {
  out.transposeMatrix();
  for(size_t r=0;r<out.rows();++r) for(size_t c=0;c<out.columns();++c) {
   MathStructure v=element(out,r,c); element(out,r,c).set(CALCULATOR->getFunction("conj"), &v, NULL); element(out,r,c).eval(eo);
  }
 } else { out.set(CALCULATOR->getFunction("conj"), &a, NULL); out.eval(eo); }
 return out;
}
class QuantumResetFunction: public MathFunction {
 std::string op;
 public:
 QuantumResetFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumResetFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  const MathStructure &a=args[0];
  if(!a.isMatrix()){CALCULATOR->error(true,"Reset and conditional channels require a ket or density matrix.",NULL);return 0;}
  if((op=="qfeedforward" || op=="qindexedchannel") && !CALCULATOR->getFunction("qapply")){CALCULATOR->error(true,"Targeted gate application is unavailable.",NULL);return 0;}
  if(op=="qreset" || op=="qresetall" || op=="qdephase" || op=="qdephaseall") {
   bool dephase=op=="qdephase" || op=="qdephaseall";
   if(!a.isMatrix() || a.rows()<2 || a.rows()>512 || (a.columns()!=1 && a.columns()!=a.rows())) {
    CALCULATOR->error(true,"Reset and dephasing require a qubit ket or square density matrix with 2 to 512 rows.",NULL); return 0;
   }
   size_t n=a.rows(), bits=0, mask=0; while((size_t(1)<<bits)<n) ++bits;
   if(n!=(size_t(1)<<bits)) { CALCULATOR->error(true,"Reset and dephasing require a power-of-two state dimension.",NULL); return 0; }
   if(op=="qresetall" || op=="qdephaseall") mask=n-1;
   else {
    size_t count=args[1].isVector() ? args[1].size() : 1;
    for(size_t k=0;k<count;++k) {
     const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
     if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) {
      CALCULATOR->error(true,"Channel indices must be integers inside the register (leftmost is 0).",NULL); return 0;
     }
     size_t bit=size_t(1)<<(bits-1-index.number().intValue());
     if(mask & bit) { CALCULATOR->error(true,"Channel indices must be unique.",NULL); return 0; } mask|=bit;
    }
   }
   MathStructure adjoint;
   if(a.columns()==1) {
    if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global functions before converting a ket to a density matrix.",NULL); return 0; }
    adjoint=dagger(a,eo);
   }
   out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   // Retain matching outcome blocks. Reset additionally maps those outcomes to zero.
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) if((r & mask)==(c & mask)) {
     MathStructure term;
     if(a.columns()==1) {
      if(element(a,r,0).isZero() || element(adjoint,0,c).isZero())continue;
      term=element(a,r,0);term*=element(adjoint,0,c);term.eval(eo);
     } else term=element(a,r,c);
     element(out,dephase ? r : r & ~mask,dephase ? c : c & ~mask)+=term;
    }
   }
   return 1;
  }
  if(op=="qfeedforward") {
   // Sum every measured branch, replacing only the requested outcome by U rho U†.
   QuantumResetFunction dephase("qdephase",2);
   MathFunction &apply=*CALCULATOR->getFunction("qapply");
   MathStructure parameters; parameters.clearVector(); parameters.addChild(a); parameters.addChild(args[1]);
   if(!dephase.calculate(out,parameters,eo)) return 0;
   size_t count=args[1].isVector() ? args[1].size() : 1;
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>=Number(size_t(1)<<count)) {
    CALCULATOR->error(true,"Feedforward outcome must be an integer from zero to 2^k-1 for k measured qubits.",NULL); return 0;
   }
   size_t n=out.rows(), bits=0, mask=0, pattern=0, outcome=args[2].number().intValue();
   while((size_t(1)<<bits)<n) ++bits;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    size_t bit=size_t(1)<<(bits-1-index.number().intValue()); mask|=bit;
    if(outcome & (size_t(1)<<(count-1-k))) pattern|=bit;
   }
   MathStructure selected; selected.clearMatrix(); selected.resizeMatrix(n,n,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    if((r & mask)!=pattern) continue;
    for(size_t c=0;c<n;++c) if((c & mask)==pattern) {
     element(selected,r,c)=element(out,r,c); element(out,r,c)=m_zero;
    }
   }
   parameters.clearVector(); parameters.addChild(args[3]); parameters.addChild(selected); parameters.addChild(args[4]);
   MathStructure corrected; if(!apply.calculate(corrected,parameters,eo)) return 0;
   out+=corrected; return 1;
  }
  if(op=="qindexedchannel") {
   if(a.rows()!=a.columns() || a.rows()>512 || !args[1].isVector() || args[1].size()==0 || args[1].size()>256) { CALCULATOR->error(true,"Indexed channel requires a square density matrix of at most 512 rows and 1 to 256 Kraus matrices.",NULL); return 0; }
   MathFunction &apply=*CALCULATOR->getFunction("qapply");
   out.clearMatrix(); out.resizeMatrix(a.rows(),a.columns(),m_zero);
   for(size_t k=0;k<args[1].size();++k) {
    if(CALCULATOR->aborted()) return 0;
    MathStructure parameters, branch; parameters.clearVector();
    parameters.addChild(args[1][k]); parameters.addChild(a); parameters.addChild(args[2]);
    if(!apply.calculate(branch,parameters,eo)) return 0;
    out+=branch;
   }
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumReset(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qreset",2),{"qresetall",1},{"qdephase",2},{"qdephaseall",1},{"qfeedforward",5},{"qindexedchannel",3}})
  calculator.addFunction(new QuantumResetFunction(entry.first,entry.second));
}

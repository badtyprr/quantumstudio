// GPL-2.0-or-later; see COPYING.
#include "QuantumMeasurement.h"
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Function.h"
#include <vector>
#include <string>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo) {
 a*=b; a.eval(eo);
 if(a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
MathStructure trace(const MathStructure &matrix,const EvaluationOptions &eo) {
 MathStructure value;
 for(size_t r=0;r<matrix.rows();++r) value+=element(matrix,r,r);
 value.eval(eo); return value;
}
bool zeroMatrix(MathStructure matrix,const EvaluationOptions &eo) {
 matrix.eval(eo);
 if(!matrix.isMatrix()) return matrix.isZero();
 for(size_t r=0;r<matrix.rows();++r) for(size_t c=0;c<matrix.columns();++c) if(!element(matrix,r,c).isZero()) return false;
 return true;
}
class QuantumMeasurementFunction: public MathFunction {
 std::string op;
 public:
 QuantumMeasurementFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumMeasurementFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before quantum measurements.",NULL);return 0;}
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  const MathStructure &a=args[0];
  if(!a.isMatrix()){CALCULATOR->error(true,"Quantum measurement requires a matrix (kets are column matrices).",NULL);return 0;}
  if(op=="qprobsub") {
   size_t n=a.rows(), bits=0, mask=0;
   while(bits<11 && (size_t(1)<<bits)<n) ++bits;
   if(n<2 || n>1024 || n!=(size_t(1)<<bits)) { CALCULATOR->error(true,"Selected probabilities require a qubit state with 2 to 1024 rows.",NULL); return 0; }
   size_t count=args[1].isVector() ? args[1].size() : 1;
   if(count==0 || count>bits) { CALCULATOR->error(true,"Select between one and all qubits for probabilities.",NULL); return 0; }
   std::vector<size_t> selected;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) { CALCULATOR->error(true,"Probability indices must be integers in range (leftmost qubit is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-index.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Probability indices must be unique.",NULL); return 0; }
    mask|=bit; selected.push_back(bit);
   }
   MathStructure parameters, probabilities; parameters.clearVector(); parameters.addChild(a);
   QuantumMeasurementFunction full("qprobs",1);
   if(!full.calculate(probabilities,parameters,eo)) return 0;
   out.clearMatrix(); out.resizeMatrix(size_t(1)<<count,1,m_zero);
   for(size_t j=0;j<n;++j) {
    if(CALCULATOR->aborted()) return 0;
    size_t outcome=0; for(size_t bit:selected) outcome=(outcome<<1) | ((j & bit) ? 1 : 0);
    element(out,outcome,0)+=element(probabilities,j,0);
   }
   return 1;
  }
  if(op=="qprobs") {
   bool ket=a.columns()==1;
   if(!ket && a.rows()!=a.columns()) { CALCULATOR->error(true,"probs requires a column ket or a square density matrix.",NULL); return 0; }
   MathStructure norm=ket ? multiply(quantumAdjoint(a,eo),a,eo) : trace(a,eo);
   if(norm.isZero()) { CALCULATOR->error(true,"A zero-norm/zero-trace state has no normalized measurement distribution.",NULL); return 0; }
   MathStructure bra; if(ket) bra=quantumAdjoint(a,eo);
   out.clearMatrix(); out.resizeMatrix(a.rows(),1,m_zero);
   for(size_t r=0;r<a.rows();++r) {
    element(out,r,0)=ket ? element(a,r,0) : element(a,r,r);
    if(ket) element(out,r,0)*=element(bra,0,r);
    element(out,r,0)/=norm;
   }
   return 1;
  }
  if(op=="qpurity") {
   bool ket=a.columns()==1;
   if((!ket && a.rows()!=a.columns()) || a.rows()>1024 || a.rows()*a.columns()>1048576) { CALCULATOR->error(true,"purity requires a ket or square density matrix, with at most 1024 rows and 1048576 elements.",NULL); return 0; }
   if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global definitions before evaluating state purity.",NULL); return 0; }
   MathStructure normalization=ket ? multiply(quantumAdjoint(a,eo),a,eo) : trace(a,eo);
   if(normalization.isZero()) { CALCULATOR->error(true,"Purity requires nonzero state norm or trace.",NULL); return 0; }
   if(ket) {out=1; return 1;}
   out.clear();
   for(size_t r=0;r<a.rows();++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<a.columns();++c) {MathStructure term=element(a,r,c); term*=element(a,c,r); out+=term;}
   }
   normalization.raise(2); out/=normalization; return 1;
  }
  if(op=="qexpect" || op=="qborn" || op=="qpostselect" || op=="qvariance") {
   const MathStructure &state=args[1];
   bool ket=state.isMatrix() && state.columns()==1;
   if(!state.isMatrix() || (!ket && state.rows()!=state.columns()) || a.rows()!=a.columns() || a.columns()!=state.rows()) { CALCULATOR->error(true,"Measurement requires a square operator and a compatible ket or density matrix.",NULL); return 0; }
   if(op=="qvariance") {
    if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global definitions before evaluating variance.",NULL); return 0; }
    MathStructure difference=a; difference-=quantumAdjoint(a,eo);
    if(!zeroMatrix(difference,eo)) { CALCULATOR->error(true,"variance requires a Hermitian observable.",NULL); return 0; }
    MathStructure normalization=ket ? multiply(quantumAdjoint(state,eo),state,eo) : trace(state,eo);
    if(normalization.isZero()) { CALCULATOR->error(true,"Variance requires nonzero state norm or trace.",NULL); return 0; }
    MathStructure first=ket ? multiply(quantumAdjoint(state,eo),multiply(a,state,eo),eo) : trace(multiply(a,state,eo),eo);
    MathStructure square=multiply(a,a,eo);
    out=ket ? multiply(quantumAdjoint(state,eo),multiply(square,state,eo),eo) : trace(multiply(square,state,eo),eo);
    out/=normalization; first/=normalization; first.raise(2); out-=first; return 1;
   }
   if(op=="qpostselect") {
    MathStructure difference=a; difference-=quantumAdjoint(a,eo);
    MathStructure squared=multiply(a,a,eo); squared-=a;
    if(!zeroMatrix(difference,eo) || !zeroMatrix(squared,eo)) { CALCULATOR->error(true,"postselect requires a Hermitian projector P with P^2=P.",NULL); return 0; }
    out=multiply(a,state,eo);
    if(!ket) out=multiply(out,a,eo);
    MathStructure probability=ket ? multiply(quantumAdjoint(out,eo),out,eo) : trace(out,eo);
    if(probability.isZero()) { CALCULATOR->error(true,"Cannot postselect an outcome with zero probability.",NULL); return 0; }
    if(ket) { probability.raise(Number(1,2)); probability.eval(eo); }
    out/=probability; return 1;
   }
   out=ket ? multiply(quantumAdjoint(state,eo),multiply(a,state,eo),eo) : trace(multiply(a,state,eo),eo);
   if(op=="qborn") {
    MathStructure normalization=ket ? multiply(quantumAdjoint(state,eo),state,eo) : trace(state,eo);
    if(normalization.isZero()) { CALCULATOR->error(true,"The Born expression requires nonzero norm or trace.",NULL); return 0; }
    out/=normalization;
   }
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumMeasurement(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qprobs",1),{"qprobsub",2},{"qpurity",1},{"qexpect",2},{"qborn",2},{"qpostselect",2},{"qvariance",2}})
  calculator.addFunction(new QuantumMeasurementFunction(entry.first,entry.second));
}

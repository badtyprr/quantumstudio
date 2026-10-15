// GPL-2.0-or-later; see COPYING.
#include "QuantumGates.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c){return *m.getElement(r+1,c+1);}
class QuantumGateFunction: public MathFunction {
 std::string op;
 public:
 QuantumGateFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumGateFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qmodmul") {
   const MathStructure &modulus=args[1];
   if(!a.isNumber() || !a.number().isInteger() || !modulus.isNumber() || !modulus.number().isInteger() || modulus.number()<2 || modulus.number()>512 || a.number()<1 || a.number()>=modulus.number()) {
    CALCULATOR->error(true,"modmul(a,N) requires integer N from 2 to 512 and an integer multiplier 1 <= a < N.",NULL);return 0;
   }
   size_t multiplier=a.number().intValue(), mod=modulus.number().intValue(), u=multiplier, v=mod;
   while(v) {size_t remainder=u%v;u=v;v=remainder;}
   if(u!=1) {CALCULATOR->error(true,"A reversible modular multiplier requires gcd(a,N)=1.",NULL);return 0;}
   size_t dimension=1;while(dimension<mod)dimension*=2;
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t x=0;x<dimension;++x) {
    if(CALCULATOR->aborted())return 0;
    element(out,x<mod ? multiplier*x%mod : x,x)=m_one;
   }
   return 1;
  }
  if(op=="qoracle") {
   const MathStructure &bits=args[1];
   if(!a.isVector() || a.isMatrix() || a.size()<2 || a.size()>256 || (a.size() & (a.size()-1)) || !bits.isNumber() || !bits.number().isInteger() || bits.number()<1 || bits.number()>8) {
    CALCULATOR->error(true,"oracle requires a flat truth table of power-of-two length 2 to 256 and an output-qubit count from 1 to 8.",NULL); return 0;
   }
   size_t outputs=size_t(1)<<bits.number().intValue(), n=a.size()*outputs;
   if(n>512) {CALCULATOR->error(true,"Oracle input and output registers together must not exceed 9 qubits.",NULL);return 0;}
   std::vector<size_t> values;
   for(size_t x=0;x<a.size();++x) {
    if(!a[x].isNumber() || !a[x].number().isInteger() || a[x].number()<0 || a[x].number()>=Number(outputs)) {CALCULATOR->error(true,"Oracle table entries must be integer output values from 0 to 2^m-1.",NULL);return 0;}
    values.push_back(a[x].number().intValue());
   }
   out.clearMatrix();out.resizeMatrix(n,n,m_zero);
   for(size_t x=0;x<a.size();++x) {
    if(CALCULATOR->aborted())return 0;
    for(size_t y=0;y<outputs;++y)element(out,x*outputs+(y^values[x]),x*outputs+y)=m_one;
   }
   return 1;
  }
  if(op=="qphaseoracle" || op=="qdiffusion") {
   if(!a.isNumber() || !a.number().isInteger() || a.number()<1 || a.number()>9) {
    CALCULATOR->error(true,"phaseoracle and diffusion require an integer qubit count from 1 to 9.",NULL); return 0;
   }
   size_t n=size_t(1)<<a.number().intValue();
   std::vector<bool> marked(n,false);
   if(op=="qphaseoracle") {
    const MathStructure &indices=args[1]; size_t count=indices.isVector() ? indices.size() : 1;
    if(count==0 || count>n) {CALCULATOR->error(true,"A phase oracle requires 1 to 2^n distinct marked indices.",NULL);return 0;}
    for(size_t k=0;k<count;++k) {
     const MathStructure &index=indices.isVector() ? indices[k] : indices;
     if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(n)) {CALCULATOR->error(true,"Marked indices must be integers from 0 to 2^n-1; the leftmost bit is most significant.",NULL);return 0;}
     size_t value=index.number().intValue();
     if(marked[value]) {CALCULATOR->error(true,"Marked phase-oracle indices must be distinct.",NULL);return 0;}
     marked[value]=true;
    }
   }
   MathStructure entry(2); entry/=Number(n); entry.eval(eo);
   out.clearMatrix(); out.resizeMatrix(n,n,op=="qdiffusion" ? entry : m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted())return 0;
    if(op=="qdiffusion")element(out,r,r)-=m_one;
    else element(out,r,r)=marked[r] ? MathStructure(-1) : m_one;
   }
   return 1;
  }
  if(op=="qsumgate") {
   const MathStructure &target=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<2 || a.number()>64 || !target.isNumber() || !target.number().isInteger() || target.number()<2 || target.number()>64) {
    CALCULATOR->error(true,"SUM requires one or two integer qudit dimensions from 2 to 64.",NULL); return 0;
   }
   size_t dc=a.number().intValue(), dt=target.number().intValue(), n=dc*dt;
   if(n>512) { CALCULATOR->error(true,"SUM gate dimension product must not exceed 512.",NULL); return 0; }
   out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   for(size_t control=0;control<dc;++control) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t value=0;value<dt;++value) element(out,control*dt+(value+control)%dt,control*dt+value)=m_one;
   }
   return 1;
  }
  if(op=="qft" || op=="qfourier" || op=="qshift" || op=="qclock") {
   bool qubits=op=="qft";
   if(!a.isNumber() || !a.number().isInteger() || a.number()<(qubits ? 1 : 2) || a.number()>(qubits ? 6 : 64)) { CALCULATOR->error(true,"QFT requires 1 to 6 qubits; shift, clock, and fourier require an integer dimension from 2 to 64.",NULL); return 0; }
   size_t n=qubits ? size_t(1)<<a.number().intValue() : a.number().intValue(); out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   if(op=="qshift") { for(size_t c=0;c<n;++c) element(out,(c+1)%n,c)=m_one; return 1; }
   if(op=="qclock") {
    for(size_t r=0;r<n;++r) {
     if(CALCULATOR->aborted()) return 0;
     element(out,r,r)=CALCULATOR->calculate("exp(2*pi*i*"+std::to_string(r)+"/"+std::to_string(n)+")",eo);
    } return 1;
   }
   for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) {
    if(CALCULATOR->aborted()) return 0;
    element(out,r,c)=CALCULATOR->calculate("exp(2*pi*i*"+std::to_string((r*c)%n)+"/"+std::to_string(n)+")/sqrt("+std::to_string(n)+")",eo);
   } return 1;
  }
  return 0;
 }
};
}
void registerQuantumGates(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qmodmul",2),{"qoracle",2},{"qphaseoracle",2},{"qdiffusion",1},{"qsumgate",2},{"qft",1},{"qfourier",1},{"qshift",1},{"qclock",1}})
  calculator.addFunction(new QuantumGateFunction(entry.first,entry.second));
}

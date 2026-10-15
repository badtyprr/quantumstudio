// GPL-2.0-or-later; see COPYING.
#include "QuantumHellinger.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
namespace {
const MathStructure &element(const MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
class QuantumHellingerFunction: public MathFunction {
 std::string op;
 public:
 QuantumHellingerFunction(const char *name):MathFunction(name,2),op(name) {}
 ExpressionItem *copy() const {return new QuantumHellingerFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  if(op=="qhellingerfidelity" || op=="qhellingerdistance") {
   std::vector<MathStructure> weights[2];MathStructure totals[2]={m_zero,m_zero};
   EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t side=0;side<2;++side) {
    const MathStructure &v=args[side];
    if(v.isMatrix()) {
     if(v.rows()!=1 && v.columns()!=1) {CALCULATOR->error(true,"Hellinger measures require aligned vectors, not general matrices.",NULL);return 0;}
     size_t count=v.rows()*v.columns();
     if(count>1024) {CALCULATOR->error(true,"Hellinger vectors support at most 1024 outcomes.",NULL);return 0;}
     for(size_t j=0;j<count;++j)weights[side].push_back(element(v,v.rows()==1 ? 0 : j,v.rows()==1 ? j : 0));
    } else if(v.isVector()) {
     if(v.size()==0 || v.size()>1024) {CALCULATOR->error(true,"Hellinger vectors require 1 to 1024 outcomes.",NULL);return 0;}
     for(size_t j=0;j<v.size();++j)weights[side].push_back(v[j]);
    } else weights[side].push_back(v);
    for(const auto &weight:weights[side]) {
     MathStructure check=weight;check.eval(numeric);
     if(!check.isNumber() || check.number().isComplex() || check.number().isUndefined() || check.number().isInfinite(false) || !check.number().isNonNegative()) {
      CALCULATOR->error(true,"Hellinger weights must be finite nonnegative real numbers.",NULL);return 0;
     }
     Number value=check.number();
     if(value.isInterval() && !value.intervalToPrecision(12)) {CALCULATOR->error(true,"Hellinger weights cannot have broad uncertainty.",NULL);return 0;}
     totals[side]+=weight;
    }
    totals[side].eval(eo);
    MathStructure check=totals[side];check.eval(numeric);
    if(!check.isNumber() || !check.number().isPositive()) {CALCULATOR->error(true,"Each Hellinger distribution must have positive total weight.",NULL);return 0;}
   }
   if(weights[0].size()!=weights[1].size()) {CALCULATOR->error(true,"Hellinger vectors must have the same outcome order and length; pad missing outcomes with zero.",NULL);return 0;}
   out=m_zero;
   for(size_t j=0;j<weights[0].size();++j) {
    if(CALCULATOR->aborted())return 0;
    if(op=="qhellingerdistance") {
     MathStructure left=weights[0][j],right=weights[1][j];left*=totals[1];right*=totals[0];left.eval(eo);right.eval(eo);
     if(left.equals(right))continue;
    }
    MathStructure p=weights[0][j],q=weights[1][j];p/=totals[0];q/=totals[1];
    if(op=="qhellingerdistance" && p.equals(q))continue;
    if(op=="qhellingerfidelity") {p*=q;p.raise(Number(1,2));}
    else {p.raise(Number(1,2));q.raise(Number(1,2));p-=q;p.raise(2);p/=2;}
    p.eval(eo);out+=p;
   }
   out.eval(eo);out.raise(op=="qhellingerfidelity" ? Number(2) : Number(1,2));out.eval(eo);return 1;
  }
  return 0;
 }
};
}
void registerQuantumHellinger(Calculator &calculator) {
 for(const char *name:{"qhellingerfidelity","qhellingerdistance"})calculator.addFunction(new QuantumHellingerFunction(name));
}

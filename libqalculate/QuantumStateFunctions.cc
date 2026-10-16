// GPL-2.0-or-later; see COPYING.
#include "QuantumStateFunctions.h"
#include "QuantumStateMetrics.h"
#include "QuantumSingular.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <utility>
namespace {
class QuantumStateFunction: public MathFunction {
 std::string op;
 public:
 QuantumStateFunction(const std::string &name,int n):MathFunction(name,n),op(name) {}
 ExpressionItem *copy() const {return new QuantumStateFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;
  EvaluationOptions stateOptions=eo;
  if(op=="qschatten")args[1].eval(eo);
  if(op=="qfrobeniusnorm" || (op=="qschatten" && args[1].isNumber() && args[1].number()==Number(2)))
   stateOptions.interval_calculation=INTERVAL_CALCULATION_INTERVAL_ARITHMETIC;
  for(size_t k=0;k<args.size();++k)args[k].eval(k==0 ? stateOptions : eo);
  const MathStructure &state=args[0];
  if(op=="qentropy")return quantumEntropy(out,state,eo) ? 1 : 0;
  if(op=="qtracedistance" || op=="qfidelity" || op=="qrootfidelity") {
   if(!quantumTraceDistance(out,state,args[1],eo,op!="qtracedistance"))return 0;
   if(op=="qrootfidelity") {
    // Do not round a tiny squared fidelity to double before taking its root.
    Number value=out.number();if(!value.sqrt())return 0;
    value.intervalToMidValue();value.setApproximate(true);value.setPrecision(12);out=value;
   }
   return 1;
  }
  if(op=="qschmidt" || op=="qschmidtdim")
   return quantumSchmidt(out,state,args[1],op=="qschmidtdim" ? &args[2] : nullptr,eo) ? 1 : 0;
  if(op=="qentropybase") {
   EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   MathStructure base=args[1];base.eval(numeric);
   if(!base.isNumber() || base.number().isComplex() || base.number().isUndefined() || base.number().isInfinite(false) || base.number()<=1) {
    CALCULATOR->error(true,"Entropy logarithm base must be a finite real number greater than one.",NULL);return 0;
   }
   Number logarithm=base.number();
   if((logarithm.isInterval() && !logarithm.intervalToPrecision(12)) || !logarithm.log(Number(2)) || !logarithm.isPositive()) {
    CALCULATOR->error(true,"Entropy logarithm base requires a positive logarithm without broad uncertainty.",NULL);return 0;
   }
   if(!quantumEntropy(out,state,eo))return 0;
   if(!out.isZero()) {out/=logarithm;out.eval(eo);}
   return 1;
  }
  MathStructure order(1);
  if(op=="qschatten")order=args[1];
  else if(op=="qfrobeniusnorm")order=2;
  else if(op=="qspectralnorm") {Number infinity;infinity.setPlusInfinity();order=infinity;}
  return quantumSchattenNorm(out,state,order,eo) ? 1 : 0;
 }
};
}
void registerQuantumStateFunctions(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qentropy",1),{"qentropybase",2},{"qtracedistance",2},{"qfidelity",2},{"qrootfidelity",2},{"qschmidt",2},{"qschmidtdim",3},{"qschatten",2},{"qtracenorm",1},{"qspectralnorm",1},{"qfrobeniusnorm",1}})
  calculator.addFunction(new QuantumStateFunction(entry.first,entry.second));
}

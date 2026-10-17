// GPL-2.0-or-later; see COPYING.
#include "QuantumNoise.h"
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Function.h"
#include <string>
#include <utility>
namespace {
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo) {
 a*=b; a.eval(eo);
 if(a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
bool noiseParameter(const MathStructure &a,const Number &upper,const EvaluationOptions &eo) {
 MathStructure parameter=a;EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;parameter.eval(numeric);
 if(!parameter.isNumber() || parameter.number().isComplex() || parameter.number().isUndefined() || parameter.number().isInfinite(false)) {
  CALCULATOR->error(true,"Noise parameters must be finite real numbers.",NULL);return false;
 }
 Number value=parameter.number();
 if((a.isNumber() && (a.number()<0 || a.number()>upper)) || (value.isInterval() && !value.intervalToPrecision(12)) || value<0 || value>upper) {
  CALCULATOR->error(true,"Damping parameters and equilibrium populations must be in [0,1], with amplitude+phase <= 1; depolarizing lambda must be in [0,4/3], without broad uncertainty.",NULL);return false;
 }
 return true;
}
class QuantumNoiseFunction: public MathFunction {
 std::string op;
 public:
 QuantumNoiseFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumNoiseFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  if(op=="qchannel" && (args[0].representsScalar() || (args[0].isVector() && args[0].size()==1 && !args[0][0].isVector()))) {
   MathStructure value=args[0].isVector() ? args[0][0] : args[0];
   args[0].clearMatrix();args[0].resizeMatrix(1,1,m_zero);element(args[0],0,0)=value;
  }
  const MathStructure &a=args[0];
  if(op=="qthermalrelaxation") {
   Number times[3];EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t k=0;k<3;++k) {
    MathStructure parameter=args[k];parameter.eval(numeric);
    if(!parameter.isNumber() || parameter.number().isComplex() || parameter.number().isUndefined()) {
     CALCULATOR->error(true,"Relaxation times must be real numbers in consistent time units.",NULL);return 0;
    }
    times[k]=parameter.number();
    if((times[k].isInterval() && !times[k].intervalToPrecision(12)) || (k<2 ? !times[k].isPositive() : times[k].isInfinite(false) || times[k]<0)) {
     CALCULATOR->error(true,"T1 and T2 must be positive (or infinity); elapsed time must be finite and nonnegative, without broad uncertainty.",NULL);return 0;
    }
   }
   Number twiceT1=times[0];twiceT1*=2;
   bool invalid=times[1]>twiceT1;
   if(a.isNumber() && args[1].isNumber()) {Number exactTwice=a.number();exactTwice*=2;invalid=invalid || args[1].number()>exactTwice;}
   if(invalid) {CALCULATOR->error(true,"Physical thermal relaxation requires T2 <= 2*T1.",NULL);return 0;}
   if(!noiseParameter(args[3],Number(1),eo))return 0;
   auto decay=[&](size_t index,int multiplier) {
    if(times[index].isPlusInfinity() || args[2].isZero())return MathStructure(1);
    MathStructure exponent=args[2];exponent*=Number(-multiplier);exponent/=args[index];exponent.eval(eo);
    MathStructure result;result.set(CALCULATOR->getFunction("exp"),&exponent,NULL);result.eval(eo);return result;
   };
   if(!CALCULATOR->getFunction("exp")) {CALCULATOR->error(true,"Load global functions before constructing thermal relaxation.",NULL);return 0;}
   MathStructure populationDecay=decay(0,1),coherenceSquared=decay(1,2);
   MathStructure amplitude(1);amplitude-=populationDecay;amplitude.eval(eo);
   MathStructure phase=populationDecay;phase-=coherenceSquared;phase.eval(eo);
   MathStructure parameters;parameters.clearVector();parameters.addChild(amplitude);parameters.addChild(phase);parameters.addChild(args[3]);
   QuantumNoiseFunction combined("qcombineddamping",3);return combined.calculate(out,parameters,eo);
  }
  if(op=="qgeneralizeddamping" || op=="qcombineddamping") {
   MathStructure phase=op=="qcombineddamping" ? args[1] : MathStructure(0);
   const MathStructure &population=args[op=="qcombineddamping" ? 2 : 1];
   MathStructure total=a;total+=phase;total.eval(eo);
   if(!noiseParameter(a,Number(1),eo) || !noiseParameter(phase,Number(1),eo) || !noiseParameter(population,Number(1),eo) || !noiseParameter(total,Number(1),eo))return 0;
   auto squareRoot=[&eo](MathStructure value) {value.raise(Number(1,2));value.eval(eo);return value;};
   MathStructure remaining(1);remaining-=total;remaining.eval(eo);
   MathStructure coherence=squareRoot(remaining),relaxation=squareRoot(a),dephasing=squareRoot(phase);
   MathStructure zero;zero.clearMatrix();zero.resizeMatrix(2,2,m_zero);out.clearVector();
   for(size_t excited=0;excited<2;++excited) {
    MathStructure weight=population;
    if(!excited) {weight=1;weight-=population;weight.eval(eo);}
    weight=squareRoot(weight);
    MathStructure k=zero;element(k,excited,excited)=m_one;element(k,1-excited,1-excited)=coherence;
    k*=weight;k.eval(eo);out.addChild(k);
    k=zero;element(k,excited,1-excited)=relaxation;k*=weight;k.eval(eo);out.addChild(k);
    if(op=="qcombineddamping") {
     k=zero;element(k,1-excited,1-excited)=dephasing;k*=weight;k.eval(eo);out.addChild(k);
    }
   }
   return 1;
  }
  if(op=="qamplitudedamping" || op=="qphasedamping" || op=="qdepolarizing") {
   Number upper=op=="qdepolarizing" ? Number(4,3) : Number(1);
   if(!noiseParameter(a,upper,eo))return 0;
   auto squareRoot=[&eo](MathStructure value) {value.raise(Number(1,2));value.eval(eo);return value;};
   MathStructure zero;zero.clearMatrix();zero.resizeMatrix(2,2,m_zero);
   out.clearVector();
   if(op=="qdepolarizing") {
    MathStructure weight=a;weight*=Number(1,4);weight.eval(eo);
    MathStructure identityWeight(1);identityWeight-=weight*Number(3);identityWeight.eval(eo);
    MathStructure k=zero,root=squareRoot(identityWeight);element(k,0,0)=root;element(k,1,1)=root;out.addChild(k);
    root=squareRoot(weight);k=zero;element(k,0,1)=root;element(k,1,0)=root;out.addChild(k);
    Number imaginary;imaginary.setImaginaryPart(1);MathStructure imaginaryRoot=root;imaginaryRoot*=imaginary;imaginaryRoot.eval(eo);
    k=zero;element(k,1,0)=imaginaryRoot;imaginaryRoot*=Number(-1);imaginaryRoot.eval(eo);element(k,0,1)=imaginaryRoot;out.addChild(k);
    k=zero;element(k,0,0)=root;root*=Number(-1);root.eval(eo);element(k,1,1)=root;out.addChild(k);
   } else {
    MathStructure remaining(1);remaining-=a;remaining.eval(eo);
    MathStructure k=zero;element(k,0,0)=m_one;element(k,1,1)=squareRoot(remaining);out.addChild(k);
    k=zero;element(k,op=="qamplitudedamping" ? 0 : 1,1)=squareRoot(a);out.addChild(k);
   }
   return 1;
  }
  if(!a.isMatrix() || !CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Channel application requires a density matrix and global conjugation function.",NULL);return 0;}
  if(op=="qchannel") {
   if(a.rows()!=a.columns() || a.rows()>512 || !args[1].isVector() || args[1].size()==0 || args[1].size()>256) { CALCULATOR->error(true,"channel requires a square density matrix of at most 512 rows and 1 to 256 Kraus matrices.",NULL); return 0; }
   size_t output=0;
   for(size_t k=0;k<args[1].size();++k) {
    if(CALCULATOR->aborted()) return 0;
    MathStructure v=args[1][k];
    if(a.rows()==1 && v.representsScalar()) {
     MathStructure value=v;v.clearMatrix();v.resizeMatrix(1,1,m_zero);element(v,0,0)=value;
    }
    if(v.isVector() && !v.isMatrix() && v.size()==a.rows()) {
     bool flat=true; for(size_t j=0;j<v.size();++j) if(v[j].isVector())flat=false;
     if(flat) {
      MathStructure row;row.clearMatrix();row.resizeMatrix(1,v.size(),m_zero);
      for(size_t j=0;j<v.size();++j)element(row,0,j)=v[j];
      v=row;
     }
    }
    if(!v.isMatrix() || v.columns()!=a.rows() || v.rows()==0 || v.rows()>512 || (k && v.rows()!=output)) { CALCULATOR->error(true,"Kraus matrices must have one column per input dimension and a common output dimension of 1 to 512.",NULL); return 0; }
    if(k==0) {output=v.rows();out.clearMatrix();out.resizeMatrix(output,output,m_zero);}
    MathStructure term=multiply(multiply(v,a,eo),quantumAdjoint(v,eo),eo);
    if(output==1 && !term.isMatrix())element(out,0,0)+=term;
    else out+=term;
   } return 1;
  }
  return 0;
 }
};
}
void registerQuantumNoise(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qthermalrelaxation",4),{"qgeneralizeddamping",2},{"qcombineddamping",3},{"qamplitudedamping",1},{"qphasedamping",1},{"qdepolarizing",1},{"qchannel",2}})
  calculator.addFunction(new QuantumNoiseFunction(entry.first,entry.second));
}

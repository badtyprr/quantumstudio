// GPL-2.0-or-later; see COPYING.
#include "QuantumGeometry.h"
#include "QuantumStateMetrics.h"
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
class QuantumGeometryFunction: public MathFunction {
 std::string op;
 public:
 QuantumGeometryFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumGeometryFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qblochsub") {
   size_t n=a.rows(),bits=0;while((size_t(1)<<bits)<n && bits<11)++bits;
   if(!a.isMatrix() || n<2 || n>1024 || n!=(size_t(1)<<bits) || (a.columns()!=1 && a.columns()!=n) || a.rows()*a.columns()>262144 || !args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0 || args[1].number()>=Number(bits)) {
    CALCULATOR->error(true,"bloch(state,wire) requires a qubit ket/density matrix with at most 262144 entries and a zero-based wire index; wire 0 is leftmost.",NULL);return 0;
   }
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before calculating Bloch coordinates.",NULL);return 0;}
   size_t mask=size_t(1)<<(bits-1-args[1].number().intValue());
   MathStructure reduced;reduced.clearMatrix();reduced.resizeMatrix(2,2,m_zero);
   MathStructure adjoint;if(a.columns()==1)adjoint=dagger(a,eo);
   for(size_t base=0;base<n;++base) {
    if(CALCULATOR->aborted())return 0;
    if(base & mask)continue;
    for(size_t r=0;r<2;++r)for(size_t c=0;c<2;++c) {
     size_t row=base|(r ? mask : 0),column=base|(c ? mask : 0);
     if(a.columns()==1) {MathStructure term=element(a,row,0);term*=element(adjoint,0,column);element(reduced,r,c)+=term;}
     else element(reduced,r,c)+=element(a,row,column);
    }
   }
   reduced.eval(eo);MathStructure parameters;parameters.clearVector();parameters.addChild(reduced);
   QuantumGeometryFunction single("qbloch",1);return single.calculate(out,parameters,eo);
  }
  if(op=="qbloch") {
   if(!a.isMatrix() || a.rows()!=2 || (a.columns()!=1 && a.columns()!=2)) {
    CALCULATOR->error(true,"bloch requires a two-component ket or a 2-by-2 density matrix.",NULL);return 0;
   }
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before calculating Bloch coordinates.",NULL);return 0;}
   MathStructure checked;
   if(!quantumEntropy(checked,a,eo))return 0;
   MathStructure rho=a.columns()==1 ? multiply(a,dagger(a,eo),eo) : a;
   MathStructure difference=rho;difference-=dagger(rho,eo);
   if(!rho.isApproximate() && !zeroMatrix(difference,eo)) {CALCULATOR->error(true,"bloch requires a Hermitian density matrix.",NULL);return 0;}
   // Numeric validation above permits rounding-sized Hermiticity residuals.
   // Use the Hermitian part rather than rejecting floating-point states.
   rho+=dagger(rho,eo);rho*=Number(1,2);rho.eval(eo);
   MathStructure weight=trace(rho,eo);
   if(weight.isNumber())weight=weight.number().realPart();
   out.clearMatrix();out.resizeMatrix(3,1,m_zero);
   element(out,0,0)=element(rho,0,1);element(out,0,0)+=element(rho,1,0);
   element(out,1,0)=element(rho,0,1);element(out,1,0)-=element(rho,1,0);
   Number imaginary;imaginary.setImaginaryPart(1);element(out,1,0)*=imaginary;
   element(out,2,0)=element(rho,0,0);element(out,2,0)-=element(rho,1,1);
   out/=weight;out.eval(eo);
   for(size_t k=0;k<3;++k)if(element(out,k,0).isNumber())element(out,k,0)=element(out,k,0).number().realPart();
   return 1;
  }
  if(op=="qreflection" || op=="qphasereflection") {
   if(!CALCULATOR->getFunction("conj") || !a.isMatrix() || a.columns()!=1 || a.rows()<2 || a.rows()>512) {
    CALCULATOR->error(true,"State reflections require global functions and a nonzero column ket with 2 to 512 amplitudes.",NULL);return 0;
   }
   EvaluationOptions stateNumeric=eo;stateNumeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t k=0;k<a.rows();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=element(a,k,0);value.eval(stateNumeric);
    if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false)) {
     CALCULATOR->error(true,"State reflections require finite numeric amplitudes.",NULL);return 0;
    }
    Number re=value.number().realPart(),im=value.number().imaginaryPart();
    if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12))) {
     CALCULATOR->error(true,"State reflections do not accept broad amplitude uncertainty.",NULL);return 0;
    }
   }
   MathStructure factor(-2);
   if(op=="qphasereflection") {
    EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
    MathStructure angle=args[1];angle.eval(numeric);
    if(!angle.isNumber() || angle.number().isComplex() || angle.number().isUndefined() || angle.number().isInfinite(false)) {
     CALCULATOR->error(true,"A phase reflection requires a finite real angle in radians.",NULL);return 0;
    }
    Number check=angle.number();if(check.isInterval() && !check.intervalToPrecision(12)) {
     CALCULATOR->error(true,"A phase reflection angle cannot have broad uncertainty.",NULL);return 0;
    }
    if(!CALCULATOR->getFunction("cos") || !CALCULATOR->getFunction("sin"))return 0;
    // Euler's form retains familiar exact trigonometric values, including
    // pi/6, instead of leaving fractional powers of -1 in compositions.
    Number imaginary;imaginary.setImaginaryPart(1);
    MathStructure sine(CALCULATOR->getFunction("sin"),&args[1],NULL);sine.eval(eo);sine*=imaginary;
    factor.set(CALCULATOR->getFunction("cos"),&args[1],NULL);factor.eval(eo);factor+=sine;factor-=m_one;factor.eval(eo);
   }
   MathStructure bra=dagger(a,eo),weight=multiply(bra,a,eo);
   if(weight.isZero()) {CALCULATOR->error(true,"Cannot reflect in a zero state.",NULL);return 0;}
   out=multiply(a,bra,eo);out/=weight;out*=factor;out.eval(eo);
   for(size_t k=0;k<a.rows();++k)element(out,k,k)+=m_one;
   out.eval(eo);return 1;
  }
  return 0;
 }
};
}
void registerQuantumGeometry(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qbloch",1),{"qblochsub",2},{"qreflection",1},{"qphasereflection",2}})
  calculator.addFunction(new QuantumGeometryFunction(entry.first,entry.second));
}

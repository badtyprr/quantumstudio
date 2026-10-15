// GPL-2.0-or-later; see COPYING.
#include "QuantumMatrixExp.h"
#include "Calculator.h"
#include <algorithm>
#include <vector>

namespace {
const MathStructure &entry(const MathStructure &m,size_t r,size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &entry(MathStructure &m,size_t r,size_t c) { return *m.getElement(r+1,c+1); }
MathStructure scalarFunction(const char *name,const MathStructure &value,const EvaluationOptions &eo) {
 MathStructure out(CALCULATOR->getFunction(name), &value, NULL); out.eval(eo); return out;
}
typedef std::vector<Number> Matrix;
Matrix identity(size_t n) { Matrix out(n*n); for(size_t i=0;i<n;++i) out[i*n+i]=1; return out; }
bool product(const Matrix &a,const Matrix &b,size_t n,Matrix &out) {
 out.assign(n*n,Number(0));
 for(size_t r=0;r<n;++r) {
  if(CALCULATOR->aborted()) return false;
  for(size_t k=0;k<n;++k) if(!a[r*n+k].isZero()) for(size_t c=0;c<n;++c) if(!b[k*n+c].isZero()) {
   Number term=a[r*n+k]; if(!term.multiply(b[k*n+c]) || !out[r*n+c].add(term)) return false;
  }
 }
 return true;
}
// |Re z|+|Im z| is an upper bound on |z|, so this is a conservative
// induced 1-norm bound without introducing square-root rounding.
Number normBound(const Matrix &a,size_t n) {
 Number bound(0);
 for(size_t c=0;c<n;++c) {
  Number sum(0);
  for(size_t r=0;r<n;++r) { Number real=a[r*n+c].realPart(), imag=a[r*n+c].imaginaryPart(); real.abs(); imag.abs(); sum+=real; sum+=imag; }
  if(sum>bound) bound=sum;
 }
 return bound;
}
bool numericalExp(MathStructure &out,const MathStructure &a,const EvaluationOptions &eo) {
 size_t n=a.rows(); Matrix scaled(n*n);
 int precision=CALCULATOR->getPrecision();
 EvaluationOptions numeric=eo; numeric.approximation=APPROXIMATION_APPROXIMATE;
 Number floatingOne; floatingOne.setFloat(1.0L);
 for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) {
  MathStructure v=entry(a,r,c); v.eval(numeric);
  if(!v.isNumber() || v.number().isUndefined() || v.number().isInfinite(false)) {
   CALCULATOR->error(true,"General matrix exponentials require finite numeric entries; symbolic diagonal and quadratic cases are supported exactly.",NULL); return false;
  }
  Number value=v.number();
  if(value.isInterval(false)) {
   // Irrational constants are represented internally by narrow rounding
   // intervals. Accept their precision-limited midpoints, but do not silently
   // turn broad uncertain user inputs into point estimates.
   Number real=value.realPart(), imag=value.imaginaryPart();
   if(!real.intervalToPrecision(std::max(2,precision-2)) || !imag.intervalToPrecision(std::max(2,precision-2))) {
    CALCULATOR->error(true,"General matrix exponentials do not accept broad uncertainty intervals.",NULL); return false;
   }
   value=real; value.setImaginaryPart(imag);
  }
  value.setPrecision(-1);
  scaled[r*n+c]=value; scaled[r*n+c]*=floatingOne;
 }
 Number bound=normBound(scaled,n); unsigned squarings=0;
 // Taylor convergence is fast after scaling to norm <= 1/2. The finite
 // scaling limit avoids hiding unusably ill-conditioned/huge inputs.
 while(bound>Number(1,2)) {
  if(++squarings>64) { CALCULATOR->error(true,"Matrix exponential exceeds the numerical scaling limit.",NULL); return false; }
  bound/=2; for(auto &v:scaled) v/=2;
 }
 if(precision>1000) { CALCULATOR->error(true,"General matrix exponentials currently support up to 1000 decimal digits.",NULL); return false; }
 Number tolerance(1,1,-std::max(precision,16)-10);
 for(unsigned i=0;i<squarings;++i) tolerance/=2;
 Matrix sum=identity(n), term=sum, next;
 bool converged=false;
 for(int k=1;k<=4096;++k) {
  if(!product(term,scaled,n,next)) { CALCULATOR->error(true,"Matrix exponential arithmetic failed or was interrupted.",NULL); return false; }
  for(auto &v:next) v/=k;
  term.swap(next);
  for(size_t j=0;j<sum.size();++j) sum[j]+=term[j];
  // At norm <= 1/2, the remaining tail is smaller than the last
  // included term for k >= 1. Scaling also tightens the tolerance.
  if(normBound(term,n)<=tolerance) { converged=true; break; }
 }
 if(!converged) { CALCULATOR->error(true,"Matrix exponential did not converge within the iteration limit.",NULL); return false; }
 for(unsigned k=0;k<squarings;++k) { if(!product(sum,sum,n,next)) { CALCULATOR->error(true,"Matrix exponential squaring failed or was interrupted.",NULL); return false; } sum.swap(next); }
 out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
 for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) {
  Number value=sum[r*n+c];
  if(value.isUndefined() || value.isInfinite(false)) { CALCULATOR->error(true,"Matrix exponential overflowed.",NULL); return false; }
  // This routine computes a point approximation, not an uncertainty model.
  // Keep the approximate flag but avoid treating internal rounding intervals
  // as independent measured uncertainties in subsequent norm calculations.
  Number real=value.realPart(), imag=value.imaginaryPart();
  real.intervalToMidValue(); imag.intervalToMidValue();
  real.setPrecision(-1); imag.setPrecision(-1);
  value=real; value.setImaginaryPart(imag); value.setApproximate(true);
  entry(out,r,c)=value;
 }
 out.setApproximate(true,true);
 CALCULATOR->error(false,"Matrix exponential evaluated numerically by scaling and squaring; the result is approximate.",NULL);
 return true;
}
}

bool quantumMatrixExp(MathStructure &out,const MathStructure &a,const EvaluationOptions &eo) {
 if(!a.isMatrix() || a.rows()!=a.columns() || a.rows()>64 || a.rows()==0) {
  CALCULATOR->error(true,"Matrix exponential requires a square matrix of dimension at most 64.",NULL); return false;
 }
 const size_t n=a.rows();
 for(const char *name:{"exp","cosh","qsinhc"}) if(!CALCULATOR->getFunction(name)) { CALCULATOR->error(true,"Load global function definitions before calculating matrix exponentials.",NULL); return false; }
 bool diagonal=true;
 for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) if(r!=c && !entry(a,r,c).isZero()) diagonal=false;
 if(diagonal) {
  out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
  for(size_t r=0;r<n;++r) entry(out,r,r)=scalarFunction("exp",entry(a,r,r),eo);
  return true;
 }
 // Exact Cayley-Hamilton form when B=A-tr(A)/n I obeys B^2=lambda I.
 // This includes every 2x2 matrix and arbitrary-dimensional Pauli strings
 // and many Hamiltonians composed of anticommuting Paulis.
 if(n<=16) {
  MathStructure center; for(size_t r=0;r<n;++r) center+=entry(a,r,r); center/=Number(n); center.eval(eo);
  MathStructure b=a; for(size_t r=0;r<n;++r) entry(b,r,r)-=center; b.eval(eo);
  MathStructure squared=b; squared*=b; squared.eval(eo);
  if(!squared.isMatrix()) { CALCULATOR->error(true,"Matrix exponential could not form the quadratic reduction.",NULL); return false; }
  MathStructure lambda=entry(squared,0,0); bool quadratic=true;
  for(size_t r=0;r<n && quadratic;++r) for(size_t c=0;c<n;++c) {
   MathStructure difference=entry(squared,r,c); if(r==c) difference-=lambda; difference.eval(eo);
   if(!difference.isZero()) { quadratic=false; break; }
  }
  if(quadratic) {
   MathStructure root=lambda; root.raise(Number(1,2)); root.eval(eo);
   MathStructure co=scalarFunction("cosh",root,eo), si=scalarFunction("qsinhc",root,eo), factor=scalarFunction("exp",center,eo);
   out=b; out*=si; out.eval(eo);
   for(size_t r=0;r<n;++r) entry(out,r,r)+=co;
   out*=factor; out.eval(eo); return true;
  }
 }
 return numericalExp(out,a,eo);
}

#include "Function.h"
namespace {
class QuantumExpFunction: public MathFunction {
 bool sinhc;
 public:
 QuantumExpFunction(bool s):MathFunction(s ? "qsinhc" : "qexp",1),sinhc(s) {}
 ExpressionItem *copy() const { return new QuantumExpFunction(*this); }
 int calculate(MathStructure &out,const MathStructure &args,const EvaluationOptions &eo) {
  MathStructure a=args[0];a.eval(eo);
  if(sinhc) {
   if(a.isZero()) {out=1;return 1;}
   if(!a.isNumber() && !a.representsNonZero())return 0;
   auto f=CALCULATOR->getFunction("sinh");if(!f)return 0;
   out.set(f,&a,NULL);out/=a;out.eval(eo);return 1;
  }
  if(a.isMatrix())return quantumMatrixExp(out,a,eo) ? 1 : 0;
  if(a.isVector()){CALCULATOR->error(true,"A matrix exponential requires a square matrix.",NULL);return 0;}
  auto f=CALCULATOR->getFunction("exp");if(!f)return 0;
  out.set(f,&a,NULL);out.eval(eo);return 1;
 }
};
}
void registerQuantumMatrixExp(Calculator &calculator) {
 calculator.addFunction(new QuantumExpFunction(false));
 calculator.addFunction(new QuantumExpFunction(true));
}

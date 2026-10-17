// GPL-2.0-or-later; see COPYING.
#include "QuantumNegativity.h"
#include "QuantumStateMetrics.h"
#include "QuantumSingular.h"
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
#include <algorithm>
#include <cmath>
#include <complex>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure trace(const MathStructure &matrix,const EvaluationOptions &eo) {
 MathStructure value;
 for(size_t r=0;r<matrix.rows();++r) value+=element(matrix,r,r);
 value.eval(eo); return value;
}
bool hermitianEigenvalues(std::vector<double> a,size_t size,std::vector<double> &values,std::vector<double> *vectors=nullptr) {
 if(vectors) {vectors->assign(size*size,0);for(size_t k=0;k<size;++k)(*vectors)[k*size+k]=1;}
 bool converged=false;
 for(unsigned sweep=0;sweep<100;++sweep) {
  if(CALCULATOR->aborted())return false;
  double largest=0;
  for(size_t p=0;p<size;++p)for(size_t q=p+1;q<size;++q) {
   double off=a[p*size+q];largest=std::max(largest,std::abs(off));
   if(std::abs(off)<1e-15)continue;
   double tau=(a[q*size+q]-a[p*size+p])/(2*off);
   double t=std::copysign(1/(std::abs(tau)+std::hypot(1.0,tau)),tau),c=1/std::sqrt(1+t*t),s=t*c;
   a[p*size+p]-=t*off;a[q*size+q]+=t*off;a[p*size+q]=a[q*size+p]=0;
   if(vectors)for(size_t k=0;k<size;++k) {
    double x=(*vectors)[k*size+p],y=(*vectors)[k*size+q];
    (*vectors)[k*size+p]=c*x-s*y;(*vectors)[k*size+q]=s*x+c*y;
   }
   for(size_t k=0;k<size;++k)if(k!=p && k!=q) {
    double x=a[k*size+p],y=a[k*size+q];
    a[k*size+p]=a[p*size+k]=c*x-s*y;a[k*size+q]=a[q*size+k]=s*x+c*y;
   }
  }
  if(largest<1e-14) {converged=true;break;}
 }
 if(!converged) {CALCULATOR->error(true,"Hermitian eigensolver did not converge.",NULL);return false;}
 values.resize(size);for(size_t k=0;k<size;++k)values[k]=a[k*size+k];return true;
}
bool logNegativity(Number &value);
bool mixedNegativity(MathStructure &out,const MathStructure &partialTranspose,const EvaluationOptions &eo,bool logarithmic) {
 if(!partialTranspose.isMatrix() || partialTranspose.rows()!=partialTranspose.columns() || partialTranspose.rows()<2 || partialTranspose.rows()>64)return false;
 size_t n=partialTranspose.rows();std::vector<Number> values(n*n);
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  MathStructure v=element(partialTranspose,r,c);v.eval(numeric);
  if(!v.isNumber() || v.number().isUndefined() || v.number().isInfinite(false))return false;
  Number re=v.number().realPart(),im=v.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12)))return false;
  values[r*n+c]=v.number();values[r*n+c].intervalToMidValue();
 }
 Number negativity(0);std::vector<bool> visited(n,false);
 // Exact zero edges identify invariant blocks. Treat small blocks with Number
 // arithmetic so a weak entangled block is not rounded against a large one.
 for(size_t seed=0;seed<n;++seed) {
  if(visited[seed])continue;
  std::vector<size_t> block(1,seed);visited[seed]=true;
  for(size_t k=0;k<block.size();++k)for(size_t j=0;j<n;++j)
   if(!visited[j] && !values[block[k]*n+j].isZero()) {visited[j]=true;block.push_back(j);}
  if(block.size()==1) {
   Number v=values[seed*n+seed].realPart();if(v.isNegative())negativity-=v;
  } else if(block.size()==2) {
   size_t p=block[0],q=block[1];Number a=values[p*n+p].realPart(),d=values[q*n+q].realPart();
   Number magnitude=values[p*n+q];magnitude.abs();magnitude.square();
   Number discriminant=a;discriminant-=d;discriminant.square();Number term=magnitude;term*=4;discriminant+=term;
   if(!discriminant.sqrt())return false;
   Number trace=a;trace+=d;Number low,high=trace;high+=discriminant;high/=2;
   if(trace.isNonNegative() && !high.isZero()) {
    // det/high avoids cancellation in (trace-discriminant)/2.
    low=a;low*=d;low-=magnitude;low/=high;
   } else {low=trace;low-=discriminant;low/=2;}
   if(low.isNegative())negativity-=low;
   if(high.isNegative())negativity-=high;
  } else {
   Number scale(0);for(size_t r:block)for(size_t c:block){Number v=values[r*n+c];v.abs();if(v>scale)scale=v;}
   if(scale.isZero())continue;
   size_t m=block.size(),size=2*m;std::vector<double> matrix(size*size,0),eigenvalues;
   for(size_t r=0;r<m;++r)for(size_t c=0;c<m;++c) {
    Number v=values[block[r]*n+block[c]];v/=scale;
    double re=v.realPart().floatValue(),im=v.imaginaryPart().floatValue();
    if(!std::isfinite(re) || !std::isfinite(im))return false;
    matrix[r*size+c]=matrix[(r+m)*size+c+m]=re;matrix[r*size+c+m]=-im;matrix[(r+m)*size+c]=im;
   }
   if(!hermitianEigenvalues(matrix,size,eigenvalues))return false;
   // General blocks have double-precision eigenvalues; suppress unresolved
   // roundoff relative to this block, never relative to the entire state.
   double sum=0;for(double v:eigenvalues)if(v < -1e-13)sum-=v/2;
   Number contribution;contribution.setFloat(sum);contribution*=scale;negativity+=contribution;
  }
  if(CALCULATOR->aborted())return false;
 }
 if(logarithmic && !logNegativity(negativity))return false;
 negativity.intervalToMidValue();negativity.setApproximate(true);negativity.setPrecision(12);out=negativity;return true;
}
bool logNegativity(Number &value) {
 // log1p retains a weak entanglement signal without rounding 1+2N to 1.
 value*=2;value.intervalToMidValue();if(!value.setToFloatingPoint())return false;
 mpfr_t result,ln2;mpfr_init2(result,128);mpfr_init2(ln2,128);
 mpfr_log1p(result,value.internalLowerFloat(),MPFR_RNDN);
 mpfr_const_log2(ln2,MPFR_RNDN);mpfr_div(result,result,ln2,MPFR_RNDN);
 value.setInternal(result);mpfr_clear(result);mpfr_clear(ln2);
 return !value.isUndefined() && !value.isInfinite(false);
}
class QuantumNegativityFunction: public MathFunction {
 std::string op;
 public:
 QuantumNegativityFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumNegativityFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  const MathStructure &a=args[0];bool dimensions=op=="qnegativitydim" || op=="qlognegativitydim";
  bool logarithmic=op=="qlognegativity" || op=="qlognegativitydim";
  if(!a.isMatrix() || a.rows()<2 || a.rows()>64 || (a.columns()!=1 && a.columns()!=a.rows())) {
   CALCULATOR->error(true,"Negativity requires a ket or density matrix of dimension 2 to 64.",NULL);return 0;
  }
  if(a.columns()==1) {
   MathStructure coefficients;
   if(!quantumSchmidt(coefficients,a,args[1],dimensions ? &args[2] : nullptr,eo))return 0;
   Number value(0);
   for(size_t i=1;i<=coefficients.rows();++i)for(size_t j=i+1;j<=coefficients.rows();++j) {
    Number product=coefficients.getElement(i,1)->number();product*=coefficients.getElement(j,1)->number();value+=product;
   }
   if(logarithmic && !logNegativity(value))return 0;
   value.intervalToMidValue();value.setApproximate(true);value.setPrecision(12);out=value;return 1;
  }
  if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before calculating negativity.",NULL);return 0;}
  MathStructure validation;if(!quantumEntropy(validation,a,eo))return 0;
  MathStructure rho=a;rho+=quantumAdjoint(a,eo);rho/=2;rho.eval(eo);rho/=trace(rho,eo);rho.eval(eo);
  auto transpose=CALCULATOR->getFunction(dimensions ? "qptransposedim" : "qptranspose");
  if(!transpose) {CALCULATOR->error(true,"Partial transpose is unavailable.",NULL);return 0;}
  MathStructure transposed;
  if(dimensions)transposed.set(transpose,&rho,&args[1],&args[2],NULL);
  else transposed.set(transpose,&rho,&args[1],NULL);
  transposed.eval(eo);
  return mixedNegativity(out,transposed,eo,logarithmic) ? 1 : 0;
 }
};
}
void registerQuantumNegativity(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qnegativity",2),{"qnegativitydim",3},{"qlognegativity",2},{"qlognegativitydim",3}})calculator.addFunction(new QuantumNegativityFunction(entry.first,entry.second));
}

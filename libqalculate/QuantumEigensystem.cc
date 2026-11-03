// GPL-2.0-or-later; see COPYING.
#include "QuantumEigensystem.h"
#include "Calculator.h"
#include "Function.h"
#include <algorithm>
#include <cmath>
#include <complex>
#include <numeric>
#include <vector>

namespace {
using Complex = std::complex<double>;
struct Eigensystem {
 size_t size;
 std::vector<double> values;
 std::vector<Complex> vectors; // Row major; eigenvectors are columns.
};
bool fail(const char *message) {
 CALCULATOR->error(true,message,NULL);return false;
}
bool finitePart(Number part,double &value) {
 if(part.isInterval() && !part.intervalToPrecision(12))return false;
 value=part.floatValue();
 return std::isfinite(value) && (value!=0 || part.isZero());
}
bool diagonalize(const MathStructure &input,const EvaluationOptions &eo,Eigensystem &result) {
 if(!input.isMatrix() || input.rows()!=input.columns() || input.rows()==0 || input.rows()>64)
  return fail("Hermitian eigensystems require a square matrix of dimension 1 to 64.");
 const size_t n=input.rows();
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 std::vector<Complex> original(n*n);
 double scale=0;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  MathStructure entry=*input.getElement(r+1,c+1);entry.eval(numeric);
  double re,im;
  if(!entry.isNumber() || entry.number().isUndefined() || entry.number().isInfinite(false) ||
     !finitePart(entry.number().realPart(),re) || !finitePart(entry.number().imaginaryPart(),im))
   return fail("Hermitian eigensystems require finite numeric entries representable in double precision, without broad uncertainty.");
  original[r*n+c]=Complex(re,im);scale=std::max(scale,std::max(std::abs(re),std::abs(im)));
 }
 if(scale==0)scale=1;
 for(auto &z:original) {
  const Complex scaled=z/scale;
  if((z.real()!=0 && scaled.real()==0) || (z.imag()!=0 && scaled.imag()==0))
   return fail("Hermitian matrix scaling exceeds double precision range.");
  z=scaled;
 }
 std::vector<Complex> a(n*n),v(n*n,0);
 for(size_t r=0;r<n;++r) {
  v[r*n+r]=1;
  for(size_t c=0;c<n;++c) {
   if(std::abs(original[r*n+c]-std::conj(original[c*n+r]))>1e-12)
    return fail("Hermitian eigensystems require a Hermitian matrix (scaled tolerance 1e-12).");
   a[r*n+c]=(original[r*n+c]+std::conj(original[c*n+r]))/2.0;
  }
 }
 // Complex cyclic Jacobi rotations. Unlike a real embedding, this retains
 // exactly n orthonormal complex vectors even for degenerate eigenvalues.
 bool converged=false;
 for(unsigned sweep=0;sweep<100;++sweep) {
  if(CALCULATOR->aborted())return false;
  double largest=0;
  for(size_t p=0;p<n;++p)for(size_t q=p+1;q<n;++q) {
   const double off=std::abs(a[p*n+q]);largest=std::max(largest,off);
   if(off<1e-15)continue;
   const Complex phase=a[p*n+q]/off;
   const double tau=(a[q*n+q].real()-a[p*n+p].real())/(2*off);
   const double t=std::copysign(1/(std::abs(tau)+std::hypot(1.0,tau)),tau);
   const double cosine=1/std::sqrt(1+t*t),sine=t*cosine;
   a[p*n+p]=a[p*n+p].real()-t*off;a[q*n+q]=a[q*n+q].real()+t*off;
   a[p*n+q]=a[q*n+p]=0;
   for(size_t k=0;k<n;++k) {
    Complex x=v[k*n+p],y=v[k*n+q];
    v[k*n+p]=cosine*x-sine*std::conj(phase)*y;
    v[k*n+q]=sine*phase*x+cosine*y;
    if(k==p || k==q)continue;
    x=a[k*n+p];y=a[k*n+q];
    a[k*n+p]=cosine*x-sine*std::conj(phase)*y;
    a[k*n+q]=sine*phase*x+cosine*y;
    a[p*n+k]=std::conj(a[k*n+p]);a[q*n+k]=std::conj(a[k*n+q]);
   }
  }
  if(largest<1e-14){converged=true;break;}
 }
 if(!converged)return fail("Hermitian eigensolver did not converge.");
 std::vector<size_t> order(n);std::iota(order.begin(),order.end(),0);
 std::stable_sort(order.begin(),order.end(),[&](size_t p,size_t q){return a[p*n+p].real()<a[q*n+q].real();});
 result.size=n;result.values.resize(n);result.vectors.resize(n*n);
 for(size_t j=0;j<n;++j) {
  const size_t col=order[j];const double lambda=a[col*n+col].real();
  result.values[j]=lambda*scale;
  if(!std::isfinite(result.values[j]) || (lambda!=0 && result.values[j]==0))
   return fail("Hermitian eigenvalue is outside double precision range.");
  double residual=0;size_t pivot=0;
  for(size_t r=0;r<n;++r) {
   Complex av=0;for(size_t c=0;c<n;++c)av+=original[r*n+c]*v[c*n+col];
   residual+=std::norm(av-lambda*v[r*n+col]);
   if(std::abs(v[r*n+col])>std::abs(v[pivot*n+col]))pivot=r;
  }
  if(!std::isfinite(residual) || std::sqrt(residual)>1e-10)
   return fail("Hermitian eigensystem failed its scaled residual check.");
  const Complex phase=std::conj(v[pivot*n+col])/std::abs(v[pivot*n+col]);
  for(size_t r=0;r<n;++r)result.vectors[r*n+j]=v[r*n+col]*phase;
 }
 for(size_t p=0;p<n;++p)for(size_t q=0;q<n;++q) {
  Complex dot=0;for(size_t r=0;r<n;++r)dot+=std::conj(result.vectors[r*n+p])*result.vectors[r*n+q];
  const double error=std::abs(dot-Complex(p==q ? 1 : 0));
  if(!std::isfinite(error) || error>1e-10)return fail("Hermitian eigensystem failed its orthonormality check.");
 }
 return true;
}
class HermitianEigenFunction: public MathFunction {
 bool vectors;
 public:
 HermitianEigenFunction(const char *name,bool eigenvectors):MathFunction(name,1),vectors(eigenvectors) {}
 ExpressionItem *copy() const {return new HermitianEigenFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure input=raw[0];input.eval(eo);Eigensystem eig;
  if(!diagonalize(input,eo,eig))return 0;
  out.clearMatrix();out.resizeMatrix(eig.size,vectors ? eig.size : 1,m_zero);
  for(size_t r=0;r<eig.size;++r)for(size_t c=0;c<(vectors ? eig.size : 1);++c) {
   const Complex value=vectors ? eig.vectors[r*eig.size+c] : Complex(eig.values[r]);
   Number re,im;re.setFloat(value.real());im.setFloat(value.imag());re.setImaginaryPart(im);
   re.setApproximate(true);re.setPrecision(12);*out.getElement(r+1,c+1)=re;
  }
  out.setApproximate(true,true);return 1;
 }
};
}
void registerQuantumEigensystem(Calculator &calculator) {
 calculator.addFunction(new HermitianEigenFunction("qheigenvalues",false));
 calculator.addFunction(new HermitianEigenFunction("qheigenvectors",true));
}

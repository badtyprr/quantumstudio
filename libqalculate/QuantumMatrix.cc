// GPL-2.0-or-later; see COPYING.
#include "QuantumMatrix.h"
#include "Calculator.h"
#include <algorithm>
#include <vector>
#include <cmath>
#include <complex>

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

namespace {
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
}

static bool spectralMatrixFunction(MathStructure &out,const MathStructure &a,const MathStructure &exponent,const EvaluationOptions &eo,bool logarithm) {
 if(!a.isMatrix() || a.rows()!=a.columns() || a.rows()==0 || a.rows()>64) {
  CALCULATOR->error(true,"Matrix powers and logarithms require a square matrix of dimension at most 64.",NULL);return false;
 }
 if(logarithm && !CALCULATOR->getFunction("ln")){CALCULATOR->error(true,"Load global functions before calculating matrix logarithms.",NULL);return false;}
 size_t n=a.rows();bool diagonal=true;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)if(r!=c && !entry(a,r,c).isZero())diagonal=false;
 if(diagonal) {
  out=a;for(size_t k=0;k<n;++k) {
   if(logarithm) {
    const MathStructure &value=entry(a,k,k);
    if(value.isZero() || (value.isNumber() && (value.number().isUndefined() || value.number().isInfinite(false)))) {CALCULATOR->error(true,"A matrix logarithm requires finite nonzero eigenvalues.",NULL);return false;}
    entry(out,k,k)=scalarFunction("ln",value,eo);
   } else {entry(out,k,k).raise(exponent);entry(out,k,k).eval(eo);}
  }return true;
 }
 // Involutions have projectors (I+A)/2 and (I-A)/2. Use the +pi
 // argument for the eigenvalue -1, preserving the usual SX/SWAP roots.
 if(n<=16) {
  MathStructure squared=a;squared*=a;squared.eval(eo);bool involution=squared.isMatrix();
  for(size_t r=0;r<n && involution;++r)for(size_t c=0;c<n;++c) {
   MathStructure difference=entry(squared,r,c);if(r==c)difference-=m_one;difference.eval(eo);
   if(!difference.isZero()){involution=false;break;}
  }
  if(involution) {
   if(logarithm) {
    // ln(-1)=i*pi on the chosen branch. Form it directly so numerical
    // evaluation does not introduce an uncertainty interval around Re=0.
    MathStructure half=CALCULATOR->calculate("i*pi/2",eo);
    // Form the projector before multiplying by pi: subtracting two
    // floating copies of pi later would create uncertainty at zero entries.
    out=a;out.negate();out.eval(eo);
    for(size_t k=0;k<n;++k)entry(out,k,k)+=m_one;
    out.eval(eo);out*=half;out.eval(eo);return true;
   }
   MathStructure phase(-1);phase.raise(exponent);phase.eval(eo);
   MathStructure same(1);same+=phase;same/=2;same.eval(eo);
   MathStructure opposite(1);opposite-=phase;opposite/=2;opposite.eval(eo);
   out=a;out*=opposite;out.eval(eo);for(size_t k=0;k<n;++k)entry(out,k,k)+=same;out.eval(eo);return true;
  }
 }
 auto fail=[logarithm](){CALCULATOR->error(true,logarithm ? "General matrix logarithms require a finite numeric nonsingular unitary or Hermitian matrix, without broad uncertainty." : "General fractional matrix powers require a finite numeric unitary or Hermitian matrix and a real exponent of magnitude at most 1000000; singular negative powers, broad uncertainty, and numerical overflow are unsupported. Diagonal and involutory matrices also support exact powers.",NULL);return false;};
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 MathStructure power=exponent;power.eval(numeric);
 if(!power.isNumber() || !power.number().isReal() || power.number().isUndefined() || power.number().isInfinite(false))return fail();
 Number p=power.number();if(p.isInterval() && !p.intervalToPrecision(12))return fail();
 double t=p.floatValue();if(!std::isfinite(t) || std::abs(t)>1e6)return fail();
 using Complex=std::complex<double>;
 std::vector<Complex> u(n*n);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  MathStructure value=entry(a,r,c);value.eval(numeric);
  if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false))return fail();
  Number re=value.number().realPart(),im=value.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12)))return fail();
  u[r*n+c]={re.floatValue(),im.floatValue()};
  if(!std::isfinite(u[r*n+c].real()) || !std::isfinite(u[r*n+c].imag()))return fail();
 }
 double scale=0;for(auto z:u)scale=std::max(scale,std::max(std::abs(z.real()),std::abs(z.imag())));
 if(scale==0 || !std::isfinite(scale))return fail();
 bool hermitian=true;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)if(std::abs(u[r*n+c]/scale-std::conj(u[c*n+r]/scale))>1e-12)hermitian=false;
 if(hermitian) {for(auto &z:u)z/=scale;}
 else for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  Complex dot=0;for(size_t k=0;k<n;++k)dot+=std::conj(u[k*n+r])*u[k*n+c];
  double error=std::abs(dot-Complex(r==c ? 1 : 0));if(!std::isfinite(error) || error>1e-11)return fail();
 }
 // The Hermitian real/imaginary parts of a unitary commute. First
 // diagonalize Re(U), then Im(U) within its degenerate eigenspaces.
 // Real embeddings avoid losing the +/- phase pairs that share a cosine.
 size_t size=2*n;
 std::vector<double> real(size*size),imag(size*size),values,vectors;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  Complex h=(u[r*n+c]+std::conj(u[c*n+r]))/2.0;
  Complex b=(u[r*n+c]-std::conj(u[c*n+r]))/Complex(0,2);
  for(auto item:{std::make_pair(&real,h),std::make_pair(&imag,b)}) {
   auto &m=*item.first;auto z=item.second;
   m[r*size+c]=m[(r+n)*size+c+n]=z.real();m[r*size+c+n]=-z.imag();m[(r+n)*size+c]=z.imag();
  }
 }
 if(!hermitianEigenvalues(real,size,values,&vectors))return false;
 std::vector<size_t> order(size);for(size_t k=0;k<size;++k)order[k]=k;
 std::sort(order.begin(),order.end(),[&](size_t x,size_t y){return values[x]<values[y];});
 std::vector<double> basis(size*size);
 for(size_t start=0;start<size;) {
  size_t end=start+1;while(end<size && std::abs(values[order[end]]-values[order[start]])<1e-10)++end;
  size_t count=end-start;std::vector<double> block(count*count,0),rotated(size*count,0),blockValues,blockVectors;
  for(size_t r=0;r<size;++r)for(size_t j=0;j<count;++j)for(size_t k=0;k<size;++k)rotated[r*count+j]+=imag[r*size+k]*vectors[k*size+order[start+j]];
  for(size_t i=0;i<count;++i)for(size_t j=0;j<count;++j)for(size_t r=0;r<size;++r)block[i*count+j]+=vectors[r*size+order[start+i]]*rotated[r*count+j];
  if(!hermitianEigenvalues(block,count,blockValues,&blockVectors))return false;
  for(size_t r=0;r<size;++r)for(size_t j=0;j<count;++j)for(size_t k=0;k<count;++k)basis[r*size+start+j]+=vectors[r*size+order[start+k]]*blockVectors[k*count+j];
  start=end;
 }
 std::vector<Complex> result(n*n,0),v(n),uv(n);
 bool unitaryLog=logarithm;
 for(size_t j=0;j<size;++j) {
  if(CALCULATOR->aborted())return false;
  for(size_t r=0;r<n;++r)v[r]={basis[r*size+j],basis[(r+n)*size+j]};
  Complex eigenvalue=0;
  for(size_t r=0;r<n;++r){uv[r]=0;for(size_t c=0;c<n;++c)uv[r]+=u[r*n+c]*v[c];eigenvalue+=std::conj(v[r])*uv[r];}
  double residual=0;for(size_t r=0;r<n;++r)residual+=std::norm(uv[r]-eigenvalue*v[r]);
  if(!std::isfinite(residual) || std::sqrt(residual)>1e-10 || (!hermitian && std::abs(std::abs(eigenvalue)-1)>1e-10))return fail();
  double phase=std::arg(eigenvalue);
  if(eigenvalue.real()<0 && std::abs(eigenvalue.imag())<1e-12)phase=std::acos(-1.0);
  double radius=0.5,logMagnitude=0;
  if(hermitian) {
   double eigen=eigenvalue.real();phase=eigen<0 ? std::acos(-1.0) : 0;
   if(std::abs(eigen)<1e-13) {if(logarithm || t<0)return fail();radius=0;}
   else {logMagnitude=std::log(std::abs(eigen))+std::log(scale);if(std::abs(logMagnitude)>1e-11)unitaryLog=false;if(!logarithm)radius=0.5*std::exp(t*logMagnitude);}
  }
  if(!std::isfinite(radius))return fail();
  Complex factor=logarithm ? Complex(logMagnitude/2,phase/2) : std::polar(radius,t*phase);
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)result[r*n+c]+=factor*v[r]*std::conj(v[c]);
 }
 if(unitaryLog)for(size_t r=0;r<n;++r)for(size_t c=r;c<n;++c) {
  Complex skew=(result[r*n+c]-std::conj(result[c*n+r]))/2.0;
  result[r*n+c]=skew;result[c*n+r]=-std::conj(skew);
 }
 out.clearMatrix();out.resizeMatrix(n,n,m_zero);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  if(!std::isfinite(result[r*n+c].real()) || !std::isfinite(result[r*n+c].imag()))return fail();
  Number re,im;re.setFloat(result[r*n+c].real());im.setFloat(result[r*n+c].imag());
  re.setImaginaryPart(im);re.setApproximate(true);re.setPrecision(std::max(2,12-int(std::ceil(std::log10(std::max(1.0,std::abs(t)))))));entry(out,r,c)=re;
 }
 out.setApproximate(true,true);return true;
}

bool quantumMatrixPower(MathStructure &out,const MathStructure &a,const MathStructure &exponent,const EvaluationOptions &eo) {
 return spectralMatrixFunction(out,a,exponent,eo,false);
}
bool quantumMatrixLog(MathStructure &out,const MathStructure &a,const EvaluationOptions &eo) {
 return spectralMatrixFunction(out,a,m_one,eo,true);
}

// Von Neumann entropy in bits. Real symmetric embedding duplicates every
// Hermitian eigenvalue; cyclic Jacobi rotations therefore need no eigenvectors.
bool quantumEntropy(MathStructure &out,const MathStructure &state,const EvaluationOptions &eo) {
 if(!state.isMatrix() || state.rows()<2 || (state.columns()!=1 && state.columns()!=state.rows()) || (state.columns()==1 ? state.rows()>1024 : state.rows()>64)) {
  CALCULATOR->error(true,"entropy requires a column ket (2-1024 entries) or a square density matrix of dimension 2-64.",NULL);return false;
 }
 size_t n=state.rows();bool pure=state.columns()==1;
 std::vector<std::complex<double>> entries(n*state.columns());double scale=0;
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<state.columns();++c) {
  MathStructure v=entry(state,r,c);v.eval(numeric);
  if(!v.isNumber() || v.number().isUndefined() || v.number().isInfinite(false)) {
   CALCULATOR->error(true,"entropy requires finite numeric state entries.",NULL);return false;
  }
  Number re=v.number().realPart(), im=v.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12))) {
   CALCULATOR->error(true,"entropy does not accept broad uncertainty intervals.",NULL);return false;
  }
  double real=re.floatValue(),imag=im.floatValue();
  if(!std::isfinite(real) || !std::isfinite(imag)) {CALCULATOR->error(true,"entropy entries exceed its floating-point range.",NULL);return false;}
  entries[r*state.columns()+c]={real,imag};scale=std::max(scale,std::max(std::abs(real),std::abs(imag)));
 }
 if(scale==0) {CALCULATOR->error(true,"entropy requires a nonzero state.",NULL);return false;}
 if(pure) {out=0;return true;}
 for(auto &v:entries)v/=scale;
 const double tolerance=1e-12;
 double weight=0;
 for(size_t r=0;r<n;++r) {
  weight+=entries[r*n+r].real();
  for(size_t c=0;c<n;++c)if(std::abs(entries[r*n+c]-std::conj(entries[c*n+r]))>tolerance) {
   CALCULATOR->error(true,"entropy requires a Hermitian density matrix.",NULL);return false;
  }
 }
 if(weight<=tolerance) {CALCULATOR->error(true,"entropy requires positive trace.",NULL);return false;}
 size_t size=2*n;std::vector<double> a(size*size,0);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  auto v=(entries[r*n+c]+std::conj(entries[c*n+r]))/(2*weight);
  a[r*size+c]=a[(r+n)*size+c+n]=v.real();a[r*size+c+n]=-v.imag();a[(r+n)*size+c]=v.imag();
 }
 std::vector<double> eigenvalues;
 if(!hermitianEigenvalues(a,size,eigenvalues))return false;
 double entropy=0;
 for(size_t k=0;k<size;++k) {
  double probability=eigenvalues[k];
  if(probability < -tolerance || probability>1+tolerance) {CALCULATOR->error(true,"entropy requires a positive semidefinite density matrix.",NULL);return false;}
  probability=std::max(0.0,std::min(1.0,probability));
  if(probability>0)entropy-=0.5*probability*std::log2(probability);
 }
 if(std::abs(entropy)<1e-13)entropy=0;
 Number result;result.setFloat(entropy);result.setApproximate(true);result.setPrecision(12);out=result;
 return true;
}

bool quantumNegativity(MathStructure &out,const MathStructure &partialTranspose,const EvaluationOptions &eo,bool logarithmic) {
 if(!partialTranspose.isMatrix() || partialTranspose.rows()!=partialTranspose.columns() || partialTranspose.rows()<2 || partialTranspose.rows()>64)return false;
 size_t n=partialTranspose.rows(),size=2*n;
 std::vector<std::complex<double>> values(n*n);
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  MathStructure value=entry(partialTranspose,r,c);value.eval(numeric);
  if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false))return false;
  Number re=value.number().realPart(),im=value.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12)))return false;
  double real=re.floatValue(),imag=im.floatValue();if(!std::isfinite(real) || !std::isfinite(imag))return false;
  values[r*n+c]={real,imag};
 }
 std::vector<double> matrix(size*size,0),eigenvalues;
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  auto z=(values[r*n+c]+std::conj(values[c*n+r]))/2.0;
  matrix[r*size+c]=matrix[(r+n)*size+c+n]=z.real();matrix[r*size+c+n]=-z.imag();matrix[(r+n)*size+c]=z.imag();
 }
 if(!hermitianEigenvalues(matrix,size,eigenvalues))return false;
 double negativity=0;for(double value:eigenvalues)if(value<0)negativity-=value/2;
 if(negativity<1e-13)negativity=0;
 double value=logarithmic ? std::log2(1+2*negativity) : negativity;
 if(!std::isfinite(value))return false;
 Number result;result.setFloat(value);result.setApproximate(true);result.setPrecision(12);out=result;return true;
}

bool quantumTraceDistance(MathStructure &out,const MathStructure &first,const MathStructure &second,const EvaluationOptions &eo,bool fidelity) {
 if(!first.isMatrix() || !second.isMatrix() || first.rows()!=second.rows() || first.rows()<2 || first.rows()>64) {
  CALCULATOR->error(true,"State distance and fidelity require two states of matching dimension from 2 to 64.",NULL);return false;
 }
 // Reuse the entropy path's finite/Hermitian/PSD validation and tolerances.
 MathStructure validation;
 if(!quantumEntropy(validation,first,eo) || !quantumEntropy(validation,second,eo))return false;
 size_t n=first.rows();EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 auto normalized=[&](const MathStructure &state) {
  std::vector<std::complex<double>> values(n*state.columns()),rho(n*n);double scale=0;
  for(size_t r=0;r<n;++r)for(size_t c=0;c<state.columns();++c) {
   MathStructure v=entry(state,r,c);v.eval(numeric);
   Number re=v.number().realPart(),im=v.number().imaginaryPart();re.intervalToMidValue();im.intervalToMidValue();
   auto z=std::complex<double>(re.floatValue(),im.floatValue());values[r*state.columns()+c]=z;
   scale=std::max(scale,std::max(std::abs(z.real()),std::abs(z.imag())));
  }
  for(auto &z:values)z/=scale;
  if(state.columns()==1) {
   double weight=0;for(auto z:values)weight+=std::norm(z);
   for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)rho[r*n+c]=values[r]*std::conj(values[c])/weight;
  } else {
   double weight=0;for(size_t r=0;r<n;++r)weight+=values[r*n+r].real();
   for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)rho[r*n+c]=(values[r*n+c]+std::conj(values[c*n+r]))/(2*weight);
  }
  return rho;
 };
 auto rho=normalized(first),sigma=normalized(second);size_t size=2*n;std::vector<double> matrix(size*size,0),eigenvalues;
 if(fidelity) {
  double value=0;
  if(first.columns()==1 || second.columns()==1) {
   for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)value+=(rho[r*n+c]*sigma[c*n+r]).real();
  } else {
   auto embed=[&](const std::vector<std::complex<double>> &state) {
    std::vector<double> real(size*size,0);
    for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
     auto z=state[r*n+c];real[r*size+c]=real[(r+n)*size+c+n]=z.real();real[r*size+c+n]=-z.imag();real[(r+n)*size+c]=z.imag();
    }
    return real;
   };
   std::vector<double> vectors,root(size*size,0);
   if(!hermitianEigenvalues(embed(rho),size,eigenvalues,&vectors))return false;
   for(size_t k=0;k<size;++k) {
    double eigenvalue=eigenvalues[k];
    if(eigenvalue < -1e-12) {CALCULATOR->error(true,"Fidelity requires positive semidefinite states.",NULL);return false;}
    double factor=std::sqrt(std::max(0.0,eigenvalue));
    for(size_t r=0;r<size;++r)for(size_t c=0;c<size;++c)root[r*size+c]+=vectors[r*size+k]*factor*vectors[c*size+k];
   }
   auto multiplyReal=[&](const std::vector<double> &a,const std::vector<double> &b) {
    std::vector<double> product(size*size,0);
    for(size_t r=0;r<size;++r) {
     if(CALCULATOR->aborted())return std::vector<double>();
     for(size_t k=0;k<size;++k)for(size_t c=0;c<size;++c)product[r*size+c]+=a[r*size+k]*b[k*size+c];
    }
    return product;
   };
   auto middle=multiplyReal(root,embed(sigma));if(middle.empty())return false;
   matrix=multiplyReal(middle,root);if(matrix.empty())return false;
   for(size_t r=0;r<size;++r)for(size_t c=r+1;c<size;++c)matrix[r*size+c]=matrix[c*size+r]=(matrix[r*size+c]+matrix[c*size+r])/2;
   if(!hermitianEigenvalues(matrix,size,eigenvalues))return false;
   for(double eigenvalue:eigenvalues) {
    if(eigenvalue < -1e-12) {CALCULATOR->error(true,"Fidelity square root exceeded its numerical positivity tolerance.",NULL);return false;}
    value+=std::sqrt(std::max(0.0,eigenvalue))/2;
   }
   value*=value;
  }
  if(!std::isfinite(value) || value < -1e-10 || value>1+1e-6) {CALCULATOR->error(true,"Fidelity exceeded its numerical validity tolerance.",NULL);return false;}
  value=std::max(0.0,std::min(1.0,value));if(value<1e-13)value=0;
  Number result;result.setFloat(value);result.setApproximate(true);result.setPrecision(12);out=result;return true;
 }
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  auto z=rho[r*n+c]-sigma[r*n+c];
  matrix[r*size+c]=matrix[(r+n)*size+c+n]=z.real();matrix[r*size+c+n]=-z.imag();matrix[(r+n)*size+c]=z.imag();
 }
 if(!hermitianEigenvalues(matrix,size,eigenvalues))return false;
 double distance=0;for(double eigenvalue:eigenvalues)distance+=std::abs(eigenvalue)/4;
 if(distance>1+1e-10 || !std::isfinite(distance)) {CALCULATOR->error(true,"Trace distance exceeded its numerical validity tolerance.",NULL);return false;}
 if(distance<1e-13)distance=0;distance=std::min(1.0,distance);
 Number result;result.setFloat(distance);result.setApproximate(true);result.setPrecision(12);out=result;return true;
}


// Schmidt coefficients are singular values of the bipartite amplitude matrix.
// Work on the amplitudes directly: squaring them into a Gram matrix loses
// relative accuracy for small, nonzero Schmidt coefficients.
bool quantumSchmidt(MathStructure &out,const MathStructure &state,const MathStructure &indices,const MathStructure *dims,const EvaluationOptions &eo) {
 if(!state.isMatrix() || state.columns()!=1 || state.rows()<2 || state.rows()>1024) {
  CALCULATOR->error(true,"schmidt_coeffs requires a pure column ket with 2 to 1024 amplitudes.",NULL);return false;
 }
 size_t n=state.rows(),total=1;std::vector<size_t> dimensions;
 if(dims) {
  if(!dims->isVector() || dims->size()==0 || dims->size()>32) {CALCULATOR->error(true,"Schmidt dimensions require a list of 1 to 32 factors.",NULL);return false;}
  for(size_t k=0;k<dims->size();++k) {
   const MathStructure &v=(*dims)[k];
   if(!v.isNumber() || !v.number().isInteger() || v.number()<1 || v.number()>1024) {CALCULATOR->error(true,"Subsystem dimensions must be integers from 1 to 1024.",NULL);return false;}
   size_t d=v.number().intValue();if(total>1024/d)return false;total*=d;dimensions.push_back(d);
  }
 } else while(total<n) {dimensions.push_back(2);total*=2;}
 if(total!=n) {CALCULATOR->error(true,"Subsystem dimensions must multiply to the ket dimension; non-qubit states need explicit dimensions.",NULL);return false;}
 std::vector<bool> selected(dimensions.size(),false);size_t count=indices.isVector() ? indices.size() : 1;
 for(size_t k=0;k<count;++k) {
  const MathStructure &index=indices.isVector() ? indices[k] : indices;
  if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(dimensions.size())) {CALCULATOR->error(true,"Schmidt subsystem index is out of range; the leftmost subsystem is 0.",NULL);return false;}
  size_t which=index.number().intValue();if(selected[which]) {CALCULATOR->error(true,"Schmidt subsystem indices must be unique.",NULL);return false;}selected[which]=true;
 }
 size_t left=1;for(size_t k=0;k<dimensions.size();++k)if(selected[k])left*=dimensions[k];
 size_t right=n/left,rows=std::max(left,right),cols=std::min(left,right);
 std::vector<std::complex<double>> matrix(n);double scale=0;
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 for(size_t k=0;k<n;++k) {
  if(CALCULATOR->aborted())return false;
  MathStructure value=entry(state,k,0);value.eval(numeric);
  if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false)) {CALCULATOR->error(true,"Schmidt coefficients require finite numerical amplitudes.",NULL);return false;}
  Number re=value.number().realPart(),im=value.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12))) {CALCULATOR->error(true,"Schmidt coefficients do not accept broad uncertainty intervals.",NULL);return false;}
  double x=re.floatValue(),y=im.floatValue();if(!std::isfinite(x) || !std::isfinite(y)) {CALCULATOR->error(true,"Schmidt amplitudes exceed floating-point range.",NULL);return false;}
  scale=std::max(scale,std::max(std::abs(x),std::abs(y)));
  size_t a=0,b=0,stride=n;
  for(size_t j=0;j<dimensions.size();++j) {stride/=dimensions[j];size_t digit=(k/stride)%dimensions[j];if(selected[j])a=a*dimensions[j]+digit;else b=b*dimensions[j]+digit;}
  matrix[left>=right ? a*cols+b : b*cols+a]={x,y};
 }
 if(scale==0) {CALCULATOR->error(true,"Schmidt coefficients require a nonzero ket.",NULL);return false;}
 double weight=0;for(auto &z:matrix){z/=scale;weight+=std::norm(z);}weight=std::sqrt(weight);for(auto &z:matrix)z/=weight;
 // Cyclic one-sided complex Jacobi rotations. The small side has at most 32
 // columns for our 1024-amplitude limit. No external BLAS dependency is needed.
 bool converged=false;
 for(size_t sweep=0;sweep<100;++sweep) {
  if(CALCULATOR->aborted())return false;
  bool changed=false;
  for(size_t p=0;p<cols;++p)for(size_t q=p+1;q<cols;++q) {
   double a=0,b=0;std::complex<double> g=0;
   for(size_t r=0;r<rows;++r){auto x=matrix[r*cols+p],y=matrix[r*cols+q];a+=std::norm(x);b+=std::norm(y);g+=std::conj(x)*y;}
   double magnitude=std::abs(g);
   if(a<1e-30 || b<1e-30 || magnitude<=1e-14*std::sqrt(a)*std::sqrt(b))continue;
   double zeta=(b-a)/(2*magnitude),t=std::copysign(1.0,zeta)/(std::abs(zeta)+std::hypot(1.0,zeta));
   double c=1/std::hypot(1.0,t),s=t*c;auto phase=g/magnitude;
   for(size_t r=0;r<rows;++r){auto x=matrix[r*cols+p],y=matrix[r*cols+q];matrix[r*cols+p]=c*x-s*std::conj(phase)*y;matrix[r*cols+q]=s*phase*x+c*y;}
   changed=true;
  }
  if(!changed){converged=true;break;}
 }
 if(!converged) {CALCULATOR->error(true,"Schmidt singular-value iteration did not converge.",NULL);return false;}
 std::vector<double> coefficients(cols,0);
 for(size_t c=0;c<cols;++c)for(size_t r=0;r<rows;++r)coefficients[c]=std::hypot(coefficients[c],std::abs(matrix[r*cols+c]));
 std::sort(coefficients.rbegin(),coefficients.rend());out.clearMatrix();out.resizeMatrix(cols,1,m_zero);
 for(size_t k=0;k<cols;++k){double v=coefficients[k]<1e-14 ? 0 : coefficients[k];Number result;result.setFloat(v);result.setApproximate(true);result.setPrecision(12);entry(out,k,0)=result;}
 return true;
}


bool quantumSchattenNorm(MathStructure &out,const MathStructure &matrix,const MathStructure &order,const EvaluationOptions &eo) {
 if(matrix.isVector() && !matrix.isMatrix()) {
  if(matrix.size()==0 || matrix.size()>1024)return false;
  MathStructure row;row.clearMatrix();row.resizeMatrix(1,matrix.size(),m_zero);
  for(size_t k=0;k<matrix.size();++k){if(matrix[k].isVector())return false;entry(row,0,k)=matrix[k];}
  return quantumSchattenNorm(out,row,order,eo);
 }
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 MathStructure p=order;p.eval(numeric);
 if(!p.isNumber() || p.number().isComplex() || p.number().isUndefined() || p.number()<1) {CALCULATOR->error(true,"Schatten norm order must be a real number at least 1 or positive infinity.",NULL);return false;}
 Number pn=p.number();if(pn.isInterval() && !pn.intervalToPrecision(12)) {CALCULATOR->error(true,"Schatten norm order cannot have broad uncertainty.",NULL);return false;}
 bool spectral=pn.isPlusInfinity();double exponent=spectral ? 1 : pn.floatValue();
 if(!spectral && (!std::isfinite(exponent) || exponent<1)) {CALCULATOR->error(true,"Finite Schatten norm order exceeds floating-point range.",NULL);return false;}
 size_t rows=matrix.isMatrix() ? matrix.rows() : 1,cols=matrix.isMatrix() ? matrix.columns() : 1,n=rows*cols;
 if((!matrix.isMatrix() && !matrix.isNumber()) || n==0 || n>1024) {CALCULATOR->error(true,"Operator norms require a numeric matrix with at most 1024 entries, or a scalar.",NULL);return false;}
 MathStructure ket;ket.clearMatrix();ket.resizeMatrix(n,1,m_zero);Number weight(0);
 for(size_t r=0;r<rows;++r)for(size_t c=0;c<cols;++c) {
  MathStructure value=matrix.isMatrix() ? entry(matrix,r,c) : matrix;value.eval(numeric);
  if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false)) {CALCULATOR->error(true,"Operator norms require finite numeric entries.",NULL);return false;}
  Number re=value.number().realPart(),im=value.number().imaginaryPart();
  if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12)) || !std::isfinite(re.floatValue()) || !std::isfinite(im.floatValue())) {CALCULATOR->error(true,"Operator norm entries must fit floating-point range without broad uncertainty.",NULL);return false;}
  re.square();im.square();re.add(im);weight.add(re);entry(ket,r*cols+c,0)=value;
 }
 if(!weight.sqrt())return false;
 if(weight.isZero() || n==1 || (!spectral && exponent==2)) {weight.intervalToMidValue();weight.setApproximate(true);weight.setPrecision(12);out=weight;return true;}
 MathStructure dimensions;dimensions.clearVector();dimensions.addChild(MathStructure(Number(rows)));dimensions.addChild(MathStructure(Number(cols)));
 MathStructure coefficients,index(0);if(!quantumSchmidt(coefficients,ket,index,&dimensions,eo))return false;
 double largest=entry(coefficients,0,0).number().floatValue(),factor=largest;
 if(!spectral) {
  double sum=0;for(size_t k=0;k<coefficients.rows();++k)sum+=std::pow(entry(coefficients,k,0).number().floatValue()/largest,exponent);
  factor*=std::pow(sum,1/exponent);
 }
 Number multiplier;multiplier.setFloat(factor);if(!weight.multiply(multiplier))return false;
 weight.intervalToMidValue();weight.setApproximate(true);weight.setPrecision(12);out=weight;return true;
}

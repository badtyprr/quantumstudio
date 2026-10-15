// GPL-2.0-or-later; see COPYING.
#include "QuantumMatrixPower.h"
#include "Calculator.h"
#include "Function.h"
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
 // A rank-one matrix satisfies A^2=tr(A) A. Keep its zero eigenspace
 // exact instead of taking square roots of eigensolver roundoff.
 if(!logarithm && n<=16 && exponent.representsPositive()) {
  EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  MathStructure trace;for(size_t k=0;k<n;++k)trace+=entry(a,k,k);trace.eval(exact);
  if(trace.representsNonZero()) {
   MathStructure squared=a;squared*=a;squared.eval(exact);bool rankOne=squared.isMatrix();
   for(size_t r=0;r<n && rankOne;++r)for(size_t c=0;c<n;++c) {
    MathStructure term=entry(a,r,c);term*=trace;
    MathStructure difference=entry(squared,r,c);difference-=term;difference.eval(exact);
    if(!difference.isZero()){rankOne=false;break;}
   }
   if(rankOne) {
    MathStructure factor=trace;factor.raise(exponent);factor/=trace;factor.eval(eo);
    out=a;out*=factor;out.eval(eo);return true;
   }
  }
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
  auto embed=[&](std::vector<double> &m,Complex z) {
   m[r*size+c]=m[(r+n)*size+c+n]=z.real();m[r*size+c+n]=-z.imag();m[(r+n)*size+c]=z.imag();
  };
  embed(real,h);embed(imag,b);
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
   // Inversion and logarithms remain conservative near numerical singularity.
   // Positive powers must not erase a small but nonzero eigenvalue.
   if((logarithm || t<0) && std::abs(eigen)<1e-13)return fail();
   if(std::abs(eigen)<1e-13 && std::sqrt(residual)>std::abs(eigen)*1e-6) {
    CALCULATOR->error(true,"Matrix power cannot resolve a near-zero eigenvalue at numerical precision.",NULL);return false;
   }
   if(eigen==0)radius=0;
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

namespace {
class QuantumPowerFunction: public MathFunction {
 std::string op;
 public:
 QuantumPowerFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumPowerFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  // Preserve algebraic projector identities before numerical eigendecomposition.
  EvaluationOptions input=eo;
  if(op=="qpower" || op=="qsqrt")input.approximation=APPROXIMATION_EXACT;
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(input);
  const MathStructure &a=args[0];
  if(op=="qlogm")return quantumMatrixLog(out,a,eo) ? 1 : 0;
  if(op=="qpower" || op=="qsqrt") {
   MathStructure exponent=op=="qsqrt" ? MathStructure(Number(1,2)) : args[1];
   if(!a.isMatrix() && a.containsType(STRUCT_VECTOR,true)>0 && !(exponent.isNumber() && exponent.number().isInteger())) {
    CALCULATOR->error(true,"Fractional matrix powers require a resolved square matrix, without broad matrix uncertainty.",NULL);return 0;
   }
   if(a.isMatrix() && exponent.isZero()) {
    if(a.rows()!=a.columns()) {CALCULATOR->error(true,"A zero matrix power requires a square matrix.",NULL);return 0;}
    out.clearMatrix();out.resizeMatrix(a.rows(),a.columns(),m_zero);
    for(size_t k=0;k<a.rows();++k)entry(out,k,k)=m_one;
   } else if(a.isMatrix() && !(exponent.isNumber() && exponent.number().isInteger())) {
    return quantumMatrixPower(out,a,exponent,eo) ? 1 : 0;
   } else {out=a;out.raise(exponent);out.eval(eo);}
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumMatrixPower(Calculator &calculator) {
 calculator.addFunction(new QuantumPowerFunction("qpower",2));
 calculator.addFunction(new QuantumPowerFunction("qsqrt",1));
 calculator.addFunction(new QuantumPowerFunction("qlogm",1));
}

// GPL-2.0-or-later; see COPYING.
#include "QuantumStateMetrics.h"
#include "Calculator.h"
#include <algorithm>
#include <vector>
#include <cmath>
#include <complex>
namespace {
const MathStructure &entry(const MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
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

bool quantumTraceDistance(MathStructure &out,const MathStructure &first,const MathStructure &second,const EvaluationOptions &eo,bool fidelity) {
 if(!first.isMatrix() || !second.isMatrix() || first.rows()!=second.rows() || first.rows()<2 || first.rows()>64) {
  CALCULATOR->error(true,"State distance and fidelity require two states of matching dimension from 2 to 64.",NULL);return false;
 }
 // Reuse the entropy path's finite/Hermitian/PSD validation and tolerances.
 MathStructure validation;
 if(!quantumEntropy(validation,first,eo) || !quantumEntropy(validation,second,eo))return false;
 size_t n=first.rows();EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 // For two kets, form the inner product before squaring. Density matrices
 // introduce cancellation and double underflow for nearly orthogonal states.
 if(fidelity && first.columns()==1 && second.columns()==1) {
  Number overlap(0),firstWeight(0),secondWeight(0);
  for(size_t r=0;r<n;++r) {
   if(CALCULATOR->aborted())return false;
   MathStructure a=entry(first,r,0),b=entry(second,r,0);a.eval(numeric);b.eval(numeric);
   if(!a.isNumber() || !b.isNumber())return false;
   Number x=a.number(),y=b.number();x.intervalToMidValue();y.intervalToMidValue();
   Number wx=x,wy=y;
   if(!wx.abs() || !wx.square() || !wy.abs() || !wy.square() || !firstWeight.add(wx) || !secondWeight.add(wy))return false;
   Number imaginary=x.imaginaryPart();imaginary.negate();x.setImaginaryPart(imaginary);
   if(!x.multiply(y) || !overlap.add(x))return false;
  }
  if(!overlap.abs() || !overlap.square() || !overlap.divide(firstWeight) || !overlap.divide(secondWeight))return false;
  overlap.intervalToMidValue();overlap.setApproximate(true);overlap.setPrecision(12);out=overlap;return true;
 }

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
  value=std::max(0.0,std::min(1.0,value));
  Number result;result.setFloat(value);result.setApproximate(true);result.setPrecision(12);out=result;return true;
 }
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  auto z=rho[r*n+c]-sigma[r*n+c];
  matrix[r*size+c]=matrix[(r+n)*size+c+n]=z.real();matrix[r*size+c+n]=-z.imag();matrix[(r+n)*size+c]=z.imag();
 }
 if(!hermitianEigenvalues(matrix,size,eigenvalues))return false;
 double distance=0;for(double eigenvalue:eigenvalues)distance+=std::abs(eigenvalue)/4;
 if(distance>1+1e-10 || !std::isfinite(distance)) {CALCULATOR->error(true,"Trace distance exceeded its numerical validity tolerance.",NULL);return false;}
 if(distance<1e-13)distance=0;
 distance=std::min(1.0,distance);
 Number result;result.setFloat(distance);result.setApproximate(true);result.setPrecision(12);out=result;return true;
}

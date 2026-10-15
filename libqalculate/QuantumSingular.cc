// GPL-2.0-or-later; see COPYING.
#include "QuantumSingular.h"
#include "Calculator.h"
#include <algorithm>
#include <vector>
#include <cmath>
#include <complex>

namespace {
const MathStructure &entry(const MathStructure &m,size_t r,size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &entry(MathStructure &m,size_t r,size_t c) { return *m.getElement(r+1,c+1); }
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
   double normP=0,normQ=0;
   for(size_t r=0;r<rows;++r) {
    normP=std::hypot(normP,std::abs(matrix[r*cols+p]));
    normQ=std::hypot(normQ,std::abs(matrix[r*cols+q]));
   }
   if(normP==0 || normQ==0)continue;
   // Compare normalized columns: squaring tiny norms would underflow and
   // incorrectly suppress the rotations needed to detect rank-one states.
   std::complex<double> overlap=0;
   for(size_t r=0;r<rows;++r)
    overlap+=std::conj(matrix[r*cols+p]/normP)*(matrix[r*cols+q]/normQ);
   double magnitude=std::abs(overlap);
   if(magnitude<=1e-14)continue;
   double scale=std::max(normP,normQ),a=normP/scale,b=normQ/scale;
   double cross=magnitude*a*b,delta=b*b-a*a;
   if(cross==0)continue; // Rotation is below the floating-point range.
   double t=2*cross/(delta+std::copysign(std::hypot(delta,2*cross),delta));
   double c=1/std::hypot(1.0,t),s=t*c;auto phase=overlap/magnitude;
   for(size_t r=0;r<rows;++r){auto x=matrix[r*cols+p],y=matrix[r*cols+q];matrix[r*cols+p]=c*x-s*std::conj(phase)*y;matrix[r*cols+q]=s*phase*x+c*y;}
   changed=true;
  }
  if(!changed){converged=true;break;}
 }
 if(!converged) {CALCULATOR->error(true,"Schmidt singular-value iteration did not converge.",NULL);return false;}
 std::vector<double> coefficients(cols,0);
 for(size_t c=0;c<cols;++c)for(size_t r=0;r<rows;++r)coefficients[c]=std::hypot(coefficients[c],std::abs(matrix[r*cols+c]));
 std::sort(coefficients.rbegin(),coefficients.rend());out.clearMatrix();out.resizeMatrix(cols,1,m_zero);
 for(size_t k=0;k<cols;++k){double v=coefficients[k];Number result;result.setFloat(v);result.setApproximate(true);result.setPrecision(12);entry(out,k,0)=result;}
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

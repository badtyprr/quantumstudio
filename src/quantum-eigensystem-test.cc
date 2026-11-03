// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumEigensystem.h"
#include <cmath>
#include <complex>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using Complex=std::complex<double>;
unsigned checks=0;
void require(bool ok,const char *message) {if(!ok)throw std::runtime_error(message);++checks;}
Complex number(const MathStructure &value) {
 require(value.isNumber(),"Expected numeric entry");
 return {value.number().realPart().floatValue(),value.number().imaginaryPart().floatValue()};
}
void close(Complex actual,Complex expected,double tolerance=2e-10) {
 require(std::isfinite(std::abs(actual-expected)) && std::abs(actual-expected)<=tolerance,"Numerical mismatch");
}
struct Spectrum {MathStructure values,vectors;};
Spectrum check(Calculator &calculator,MathStructure matrix,const std::vector<double> &expected,const EvaluationOptions &eo) {
 const size_t n=matrix.rows();
 Spectrum spectrum;
 for(bool vectors:{false,true}) {
  MathStructure args;args.clearVector();args.addChild(matrix);
  MathStructure &out=vectors ? spectrum.vectors : spectrum.values;
  require(calculator.getFunction(vectors ? "qheigenvectors" : "qheigenvalues")->calculate(out,args,eo)==1,"Eigensolver failed");
  require(out.isMatrix() && out.rows()==n && out.columns()==(vectors ? n : 1),"Output dimensions");
  require(out.isApproximate(),"Numerical result must be approximate");
 }
 double scale=0;for(size_t r=1;r<=n;++r)for(size_t c=1;c<=n;++c)scale=std::max(scale,std::abs(number(*matrix.getElement(r,c))));
 if(scale==0)scale=1;
 for(size_t j=1;j<=n;++j) {
  Complex lambda=number(*spectrum.values.getElement(j,1));
  close(lambda/scale,expected[j-1]/scale);
  if(j>1)require(lambda.real()>=number(*spectrum.values.getElement(j-1,1)).real(),"Eigenvalues unsorted");
  for(size_t r=1;r<=n;++r) {
   Complex av=0;for(size_t c=1;c<=n;++c)av+=number(*matrix.getElement(r,c))/scale*number(*spectrum.vectors.getElement(c,j));
   close(av,lambda/scale*number(*spectrum.vectors.getElement(r,j)));
  }
  for(size_t k=1;k<=n;++k) {
   Complex dot=0;for(size_t r=1;r<=n;++r)dot+=std::conj(number(*spectrum.vectors.getElement(r,j)))*number(*spectrum.vectors.getElement(r,k));
   close(dot,j==k ? 1 : 0);
  }
 }
 return spectrum;
}
MathStructure complexMatrix(const std::vector<Complex> &data,size_t n) {
 MathStructure matrix;matrix.clearMatrix();matrix.resizeMatrix(n,n,m_zero);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  Number re,im;re.setFloat(data[r*n+c].real());im.setFloat(data[r*n+c].imag());re.setImaginaryPart(im);
  *matrix.getElement(r+1,c+1)=re;
 }
 return matrix;
}
}
int main() {try {
 Calculator calculator;require(calculator.loadGlobalDefinitions(),"Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumEigensystem(calculator);
#endif
 calculator.setPrecision(40);EvaluationOptions eo;eo.approximation=APPROXIMATION_APPROXIMATE;
 auto literal=[&](const char *text){return calculator.calculate(text,eo);};
 // IBM-092 cell 4: correct code-output pairing, not swapped prose labels in cell 5.
 check(calculator,literal("[4,-1,0;-1,4,-1;0,-1,4]"),{4-std::sqrt(2.0),4,4+std::sqrt(2.0)},eo);
 check(calculator,literal("[0,-i;i,0]"),{-1,1},eo);
 check(calculator,literal("[1,1+i;1-i,2]"),{0,3},eo);
 check(calculator,complexMatrix({7},1),{7},eo);
 for(const char *name:{"qheigenvalues","qheigenvectors"}) {
  MathStructure singleton=complexMatrix({7},1);
  MathStructure evaluated(calculator.getFunction(name),&singleton,NULL);evaluated.eval(eo);
  require(evaluated.isMatrix() && evaluated.rows()==1 && evaluated.columns()==1,"Singleton evaluation collapsed");
 }
 check(calculator,literal("[0,0;0,0]"),{0,0},eo);
 check(calculator,literal("[3,0,0;0,3,0;0,0,3]"),{3,3,3},eo);
 check(calculator,literal("[1.000000005,0.000000005;0.000000005,1.000000005]"),{1,1.00000001},eo);
 check(calculator,literal("[4e200,-1e200,0;-1e200,4e200,-1e200;0,-1e200,4e200]"),{(4-std::sqrt(2.0))*1e200,4e200,(4+std::sqrt(2.0))*1e200},eo);
 check(calculator,literal("[4e-200,-1e-200,0;-1e-200,4e-200,-1e-200;0,-1e-200,4e-200]"),{(4-std::sqrt(2.0))*1e-200,4e-200,(4+std::sqrt(2.0))*1e-200},eo);
 // Fourier-conjugated spectra: independently known eigenvalues and degenerate
 // projectors. Never compare individual vectors in the repeated eigenspace.
 for(size_t n:{4,16,64}) {
  std::vector<Complex> basis(n*n),matrix(n*n,0);std::vector<double> diagonal(n);
  for(size_t j=0;j<n;++j)diagonal[j]=j<3 ? -2 : double(j);
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)basis[r*n+c]=std::polar(1/std::sqrt(double(n)),2*std::acos(-1.0)*r*c/n);
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c)for(size_t j=0;j<n;++j)matrix[r*n+c]+=basis[r*n+j]*diagonal[j]*std::conj(basis[c*n+j]);
  Spectrum spectrum=check(calculator,complexMatrix(matrix,n),diagonal,eo);
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
   Complex actual=0,expected=0;
   for(size_t j=0;j<3;++j) {
    actual+=number(*spectrum.vectors.getElement(r+1,j+1))*std::conj(number(*spectrum.vectors.getElement(c+1,j+1)));
    expected+=basis[r*n+j]*std::conj(basis[c*n+j]);
   }
   close(actual,expected);
  }
 }
 for(const char *expression:{"[1,2;0,1]","[i,0;0,1]","[1;2]","[1,0;0,x]","[inf,0;0,1]","[interval(1,2),0;0,1]","[1e400,0;0,1]","[1e-400,0;0,1]","[1e308,1e308;1e308,1e308]","[1e-200,0;0,1e200]"}) {
  MathStructure args;args.clearVector();args.addChild(literal(expression));
  for(const char *name:{"qheigenvalues","qheigenvectors"}) {
   while(calculator.message())calculator.nextMessage();MathStructure out;
   require(calculator.getFunction(name)->calculate(out,args,eo)==0,"Invalid input accepted");
   bool error=false;while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
   require(error,"Missing rejection diagnostic");
  }
 }
 MathStructure oversized;oversized.clearMatrix();oversized.resizeMatrix(65,65,m_zero);
 MathStructure args;args.clearVector();args.addChild(oversized);MathStructure out;
 require(calculator.getFunction("qheigenvalues")->calculate(out,args,eo)==0,"Dimension limit bypassed");
 std::cout<<checks<<" Hermitian eigensystem checks passed\n";return 0;
 } catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}

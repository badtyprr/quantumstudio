// GPL-2.0-or-later; see COPYING.
#include "QuantumSingular.h"
#include "Calculator.h"
#include <algorithm>
#include <cmath>
#include <complex>
#include <iostream>
#include <iomanip>
#include <random>
#include <sstream>
#include <stdexcept>
#include <vector>

static unsigned checks=0;
static EvaluationOptions eo;
static void checkNear(double value,double expected,double zeroTolerance=1e-12) {
 double tolerance=expected==0 ? zeroTolerance : std::max(1e-315,std::abs(expected)*1e-9);
 if(!std::isfinite(value) || std::abs(value-expected)>tolerance) {
  std::ostringstream message;message<<std::setprecision(17)<<"Numerical mismatch: "<<value<<" vs "<<expected;
  throw std::runtime_error(message.str());
 }
 ++checks;
}
static MathStructure parse(const std::string &source) {return CALCULATOR->calculate(source,eo);}
static void schmidt(const std::string &source,const std::string &indices,
                    const std::vector<double> &expected,const std::string &dimensions="",
                    double zeroTolerance=1e-12) {
 MathStructure out,state=parse(source),index=parse(indices),dims;
 if(!dimensions.empty())dims=parse(dimensions);
 if(!quantumSchmidt(out,state,index,dimensions.empty() ? nullptr : &dims,eo))
  throw std::runtime_error("Schmidt calculation failed: "+source);
 if(out.rows()!=expected.size() || out.columns()!=1)throw std::runtime_error("Unexpected coefficient shape");
 for(size_t k=0;k<expected.size();++k)checkNear(out.getElement(k+1,1)->number().floatValue(),expected[k],zeroTolerance);
}
static void norm(const std::string &source,const std::string &order,double expected) {
 MathStructure out,matrix=parse(source),p=parse(order);
 if(!quantumSchattenNorm(out,matrix,p,eo) || !out.isNumber())throw std::runtime_error("Norm calculation failed: "+source);
 checkNear(out.number().floatValue(),expected);
}
int main() {
 try {
  Calculator calculator;
  if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Cannot load definitions");
  calculator.setPrecision(30);
  eo.approximation=APPROXIMATION_EXACT;
  const double half=1/std::sqrt(2.0);
  schmidt("[1;0;0;1]","0",{half,half});
  schmidt("[1;0;0;i]","1",{half,half});
  schmidt("[1;2;2;4]","0",{1,0});
  schmidt("[1;0;0;0;0;0;0;1]","vector(0,2)",{half,half});
  schmidt("[1;0;0;0;2;0]","0",{2/std::sqrt(5.0),1/std::sqrt(5.0)},"vector(2,3)");
  schmidt("[1;0;0;0;2;0]","1",{2/std::sqrt(5.0),1/std::sqrt(5.0)},"vector(2,3)");
  schmidt("[1;2;3;4]","vector()",{1});
  schmidt("[1;2;3;4]","vector(0,1)",{1});
  double phi=(1+std::sqrt(5.0))/2;
  schmidt("[1;i;0;1]","0",{phi/std::sqrt(3.0),1/(phi*std::sqrt(3.0))});
  for(int exponent:{8,16,40,100,200,300}) {
   std::string tiny="1e-"+std::to_string(exponent);
   double t=std::pow(10.0,-exponent),weight=std::hypot(1.0,t);
   schmidt("[1;0;0;"+tiny+"]","0",{1/weight,t/weight});
   schmidt("[1;0;0;i*"+tiny+"]","1",{1/weight,t/weight});
   // Parallel columns must remain rank one, even far below the old cutoff.
   schmidt("[1;"+tiny+";1;"+tiny+"]","0",{1,0},"",std::max(1e-315,t*1e-10));
   schmidt("[1;i*"+tiny+";1;i*"+tiny+"]","0",{1,0},"",std::max(1e-315,t*1e-10));
  }
  // Independent closed forms for a matrix with singular values 3 and 4.
  for(const auto &matrix:{"[3,0;0,4]","[0,3i;4,0]","[3,0,0;0,4,0]"}) {
   norm(matrix,"1",7);norm(matrix,"2",5);norm(matrix,"infinity",4);
   norm(matrix,"3",std::cbrt(91.0));
  }
  norm("[3,4]","1",5);norm("3+4i","infinity",5);norm("[0,0;0,0]","1",0);
  norm("[1e-200,0;0,2e-200]","1",3e-200);
  norm("[1e200,0;0,2e200]","infinity",2e200);
  // Prescribed spectra are invariant under independent complex unitary
  // transformations on each side; this avoids deriving the oracle from A*A.
  std::mt19937 random(1731);
  using Complex=std::complex<double>;
  for(size_t n:{2U,3U,4U,5U,8U})for(unsigned trial=0;trial<6;++trial) {
   size_t rows=n+1;std::vector<Complex> a(rows*n,0);double weight=0;
   for(size_t j=0;j<n;++j){a[j*n+j]=double(j+1);weight+=double((j+1)*(j+1));}
   for(unsigned turn=0;turn<30;++turn) {
    double angle=(random()%1000)/137.0,c=std::cos(angle),s=std::sin(angle);
    Complex phase=std::polar(1.0,(random()%1000)/173.0);
    size_t p=random()%rows,q=(p+1+random()%(rows-1))%rows;
    for(size_t j=0;j<n;++j){auto x=a[p*n+j],y=a[q*n+j];a[p*n+j]=c*x-s*phase*y;a[q*n+j]=s*std::conj(phase)*x+c*y;}
    p=random()%n;q=(p+1+random()%(n-1))%n;
    for(size_t i=0;i<rows;++i){auto x=a[i*n+p],y=a[i*n+q];a[i*n+p]=c*x-s*phase*y;a[i*n+q]=s*std::conj(phase)*x+c*y;}
   }
   MathStructure state,out,dims,index(0),matrix;
   state.clearMatrix();state.resizeMatrix(rows*n,1,m_zero);
   matrix.clearMatrix();matrix.resizeMatrix(rows,n,m_zero);
   dims.clearVector();dims.addChild(MathStructure(Number(rows)));dims.addChild(MathStructure(Number(n)));
   for(size_t j=0;j<a.size();++j) {
    Number real,imag;real.setFloat(a[j].real());imag.setFloat(a[j].imag());real.setImaginaryPart(imag);
    *state.getElement(j+1,1)=real;*matrix.getElement(j/n+1,j%n+1)=real;
   }
   if(!quantumSchmidt(out,state,index,&dims,eo) || out.rows()!=n)throw std::runtime_error("Transformed Schmidt state failed");
   for(size_t j=0;j<n;++j)checkNear(out.getElement(j+1,1)->number().floatValue(),(n-j)/std::sqrt(weight));
   MathStructure order(1);
   if(!quantumSchattenNorm(out,matrix,order,eo))throw std::runtime_error("Transformed trace norm failed");
   checkNear(out.number().floatValue(),double(n*(n+1))/2);
  }
  for(const auto &source:{"[0;0;0;0]","[1,0;0,1]","[1;2;3]","[infinity;0]","[interval(0,1);1]"}) {
   MathStructure out,state=parse(source),index(0);
   if(quantumSchmidt(out,state,index,nullptr,eo))throw std::runtime_error("Accepted invalid ket");
   ++checks;
  }
  for(const auto &indices:{"-1","2","1/2","vector(0,0)"}) {
   MathStructure out,state=parse("[1;0;0;1]"),index=parse(indices);
   if(quantumSchmidt(out,state,index,nullptr,eo))throw std::runtime_error("Accepted invalid partition");
   ++checks;
  }
  for(const auto &dimensions:{"2","vector()","vector(2,3)","vector(0,4)","vector(-2,-2)","vector(1/2,8)","vector(1024,2)"}) {
   MathStructure out,state=parse("[1;0;0;1]"),index(0),dims=parse(dimensions);
   if(quantumSchmidt(out,state,index,&dims,eo))throw std::runtime_error("Accepted invalid dimensions");
   ++checks;
  }
  for(const auto &order:{"0","1/2","i","-infinity","interval(1,2)"}) {
   MathStructure out,matrix=parse("[1,0;0,1]"),p=parse(order);
   if(quantumSchattenNorm(out,matrix,p,eo))throw std::runtime_error("Accepted invalid norm order");
   ++checks;
  }
  MathStructure state,out,index(0),matrix,order(1);
  state.clearMatrix();state.resizeMatrix(1024,1,m_zero);*state.getElement(1,1)=1;
  if(!quantumSchmidt(out,state,index,nullptr,eo))throw std::runtime_error("Maximum ket rejected");
  checkNear(out.getElement(1,1)->number().floatValue(),1);checkNear(out.getElement(2,1)->number().floatValue(),0);
  state.resizeMatrix(1025,1,m_zero);
  if(quantumSchmidt(out,state,index,nullptr,eo))throw std::runtime_error("Oversized ket accepted");
  ++checks;
  matrix.clearMatrix();matrix.resizeMatrix(32,32,m_zero);
  for(size_t i=1;i<=32;++i)*matrix.getElement(i,i)=1;
  if(!quantumSchattenNorm(out,matrix,order,eo))throw std::runtime_error("Maximum operator rejected");
  checkNear(out.number().floatValue(),32);
  matrix.resizeMatrix(33,33,m_zero);
  if(quantumSchattenNorm(out,matrix,order,eo))throw std::runtime_error("Oversized operator accepted");
  ++checks;
  MathStructure secondOrder(2),complexEntry=parse("3+4i");
  for(size_t r=1;r<=33;++r)for(size_t c=1;c<=33;++c)*matrix.getElement(r,c)=complexEntry;
  if(!quantumSchattenNorm(out,matrix,secondOrder,eo))throw std::runtime_error("Large Frobenius matrix rejected");
  checkNear(out.number().floatValue(),165);
  matrix.clearMatrix();matrix.resizeMatrix(1024,1024,m_zero);
  *matrix.getElement(1024,1024)=complexEntry;
  if(!quantumSchattenNorm(out,matrix,secondOrder,eo))throw std::runtime_error("Maximum Frobenius matrix rejected");
  checkNear(out.number().floatValue(),5);
  *matrix.getElement(1,1)=parse("infinity");
  if(quantumSchattenNorm(out,matrix,secondOrder,eo))throw std::runtime_error("Nonfinite Frobenius entry accepted");
  ++checks;
  matrix.clearMatrix();matrix.resizeMatrix(1025,1,m_zero);
  if(quantumSchattenNorm(out,matrix,secondOrder,eo))throw std::runtime_error("Oversized Frobenius dimension accepted");
  ++checks;
  std::cout<<"PASS: "<<checks<<" Schmidt and Schatten checks\n";return 0;
 } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}

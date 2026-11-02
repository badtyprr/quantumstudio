// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Variable.h"
#include "Function.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void matrixProduct(const MathStructure &left, const MathStructure &right) {
 if(!left.isMatrix() || !right.isMatrix())throw std::runtime_error("Reference requires matrices: "+left.print()+" / "+right.print());
 MathStructure expected;expected.clearMatrix();expected.resizeMatrix(left.rows(),right.columns(),m_zero);
 // Independent scalar reference: include every zero term and preserve order.
 for(size_t r=0;r<left.rows();++r)for(size_t c=0;c<right.columns();++c)
  for(size_t k=0;k<left.columns();++k) {
   MathStructure term=left[r][k];term.calculateMultiply(right[k][c],eo);
   expected[r][c].calculateAdd(term,eo,&expected[r],c);
  }
 MathStructure actual=left;actual*=right;actual.eval(eo);
 if(left.rows()==1 && right.columns()==1) { MathStructure scalar=expected[0][0];expected=scalar; }
 if(!actual.equals(expected,true,true))throw std::runtime_error("Matrix product differs from scalar reference: "+left.print()+" * "+right.print()+" => "+actual.print()+" expected "+expected.print());
 if(actual.isMatrix())for(size_t r=0;r<actual.rows();++r)for(size_t c=0;c<actual.columns();++c)
  if(actual[r][c].isApproximate()!=expected[r][c].isApproximate() || actual[r][c].precision()!=expected[r][c].precision())
   throw std::runtime_error("Matrix product changed cell precision metadata");
 ++checks;
}
static void matrixProducts() {
 for(const auto &pair : {std::pair<const char *,const char *>("[1,0,0;0,-2,0]","[1,i;2,3;4,5]"),
   {"[1,2,3;-4,5,6]","[0,1;0,0;i,0]"},
   {"[1,2,3;4,5,6]","[7,8;9,10;11,12]"},
   {"[0,0;0,0]","[1,i;0,-1]"}, {"[1,i;0,-1]","[0,0;0,0]"},
   {"[1,i;-i,1]","[1,-i;i,1]"}, {"[1,-1;2,-2]","[1,3;1,3]"},
   {"[1/3,0;0,-2/7]","[0,i/5;3/2,0]"},
   {"[1,0;0,1]","[x,0;0,sqrt(2)]"},
   {"[1,0;0,1]","[infinity,0;0,1]"},
   {"[0,1;1,0]","[1,0;0,-infinity]"}})
  matrixProduct(CALCULATOR->calculate(pair.first,eo),CALCULATOR->calculate(pair.second,eo));
 MathStructure a=CALCULATOR->calculate("[1,0;0,1]",eo),b=a;
 a[0][1].setApproximate();a[0][1].setPrecision(7);matrixProduct(a,b);matrixProduct(b,a);
 MathStructure interrupted=CALCULATOR->calculate("[1,0;0,2]",eo),before=interrupted;
 MathStructure factor=CALCULATOR->calculate("[3,0;0,4]",eo);
 CALCULATOR->startControl();CALCULATOR->abort();
 int merged=interrupted.merge_multiplication(factor,eo);
 CALCULATOR->stopControl();
 if(merged!=-1 || !interrupted.equals(before))throw std::runtime_error("Aborted product accepted a partial matrix");++checks;
 matrixProduct(before,factor);
 // Deterministic rectangular, signed and sparse/dense combinations.
 for(unsigned seed=1;seed<=24;++seed) {
  MathStructure l,r;l.clearMatrix();r.clearMatrix();l.resizeMatrix(2+seed%3,2+seed%4,m_zero);r.resizeMatrix(l.columns(),2+seed%5,m_zero);
  for(size_t i=0;i<l.rows();++i)for(size_t j=0;j<l.columns();++j)l[i][j]=MathStructure(int((i*7+j*3+seed)%7)-3);
  for(size_t i=0;i<r.rows();++i)for(size_t j=0;j<r.columns();++j)r[i][j]=MathStructure(int((i*3+j*5+seed)%5)-2);
  matrixProduct(l,r);
 }
 MathStructure identity;identity.clearMatrix();identity.resizeMatrix(512,512,m_zero);
 for(size_t i=0;i<512;++i)identity[i][i]=m_one;
 MathStructure product=identity;product*=identity;product.eval(eo);
 if(!product.equals(identity))throw std::runtime_error("Full 512-dimensional identity product mismatch");++checks;
}
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate("("+expression+")==("+expected+")",eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;

}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumAlgebra(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 matrixProducts();
 equal("matrix(1,2,[1,2])*matrix(2,1,[3,4])","11");
 for(const char *source:{"qmul(qdag(operatorparam(\"A\",2,unitary)),operatorparam(\"A\",2,unitary))",
                         "qmul(operatorparam(\"A\",2,unitary),qdag(operatorparam(\"A\",2,unitary)))"}) {
  MathStructure guarded=calculator.calculate(source,eo);
  if(!guarded.isFunction() || guarded.function()->referenceName()!="qunitaryidentity")throw std::runtime_error("Unitary product did not retain a guarded identity");++checks;
  MathStructure valid=guarded;valid.replace(MathStructure("A",true),calculator.calculate("[0,1;1,0]",eo));valid.eval(eo);
  valid.transform(COMPARISON_EQUALS,calculator.calculate("identity(2)",eo));valid.eval(eo);
  if(!valid.isOne())throw std::runtime_error("Guard rejected a valid unitary replacement");++checks;
  for(const char *replacement:{"[1,0;0,2]","identity(3)"}) {
   while(calculator.message())calculator.nextMessage();MathStructure invalid=guarded;
   invalid.replace(MathStructure("A",true),calculator.calculate(replacement,eo));invalid.eval(eo);bool error=false;
   while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
   if(!error)throw std::runtime_error("Unitary simplification lost its substitution constraint");++checks;
  }
 }
 for(const char *property:{"hermitian","projector"}) {
  std::string domain=std::string("operatorparam(\"A\",2,")+property+")";
  MathStructure expected=calculator.calculate(domain,eo),adjoint=calculator.calculate("qdag("+domain+")",eo);
  if(!adjoint.equals(expected))throw std::runtime_error("Declared Hermitian adjoint did not simplify");++checks;
 }
 MathStructure projector=calculator.calculate("operatorparam(\"A\",2,projector)",eo);
 MathStructure squared=calculator.calculate("qmul(operatorparam(\"A\",2,projector),operatorparam(\"A\",2,projector))",eo);
 if(!squared.equals(projector))throw std::runtime_error("Declared projector square did not simplify");++checks;
 for(const char *source:{"qmul(operatorparam(\"A\",2,hermitian),operatorparam(\"A\",2,hermitian))",
   "qmul(operatorparam(\"A\",2,projector),operatorparam(\"B\",2,projector))",
   "qmul(qdag(matrixparam(\"A\",2,2)),matrixparam(\"A\",2,2))"}) {
  MathStructure retained=calculator.calculate(source,eo);
  if(!retained.isFunction() || retained.function()->referenceName()!="qmul")throw std::runtime_error("Unjustified operator identity applied");++checks;
 }
 // Operator properties are explicit domains, not inferred from symbol names.
 equal("operatorparam([0,1;1,0],2,unitary)","[0,1;1,0]");
 equal("operatorparam([1,i;-i,2],2,hermitian)","[1,i;-i,2]");
 equal("operatorparam([1,0;0,0],2,projector)","[1,0;0,0]");
 equal("operatorparam([1,1;1,1]/2,2,projector)","[1,1;1,1]/2");
 equal("operatorparam(qidentity(1),1,unitary)","qidentity(1)");
 equal("operatorparam(qidentity(1),1,projector)","qidentity(1)");
 equal("replace(operatorparam([0,1;1,0],n,unitary),n,2)","[0,1;1,0]");
 equal("replace(operatorparam(\"A\",2,unitary),\"A\",[0,i;i,0])","[0,i;i,0]");
 for(const char *source:{"operatorparam([1,0;0,2],2,unitary)",
      "operatorparam([1,0;0,2],2,projector)","operatorparam([1,1;0,1],2,hermitian)",
      "operatorparam([1,0,0;0,1,0],2,unitary)","operatorparam(identity(3),2,unitary)",
      "operatorparam(\"A\",0,unitary)","operatorparam(\"A\",1/2,unitary)",
      "operatorparam(\"A\",2,unknown)",
      "replace(operatorparam([0,1;1,0],n,unitary),n,3)",
      "replace(operatorparam(\"A\",2,unitary),\"A\",[1,0;0,2])"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(source,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid operator domain accepted: ")+source);++checks;
 }
 MathStructure operatorDomain=calculator.calculate("operatorparam(\"A\",2,unitary)",eo),operatorRows,operatorColumns;
 if(!operatorDomain.isFunction() || operatorDomain.function()->referenceName()!="operatorparam" ||
    !quantumMatrixShape(operatorDomain,operatorRows,operatorColumns,eo) ||
    !operatorRows.equals(Number(2)) || !operatorColumns.equals(Number(2)))throw std::runtime_error("Operator domain lost its shape");
 ++checks;
 // Custom functions (id zero) must sort consistently against built-ins.
 for(const char *component:{"re","im","abs"}) {
  std::string part=std::string(component)+"(complexparam(x))";
  equal(part+"*complexparam(x)-complexparam(x)*"+part,"0");
  equal("complexparam(x)*"+part+"-"+part+"*complexparam(x)","0");
 }
 equal("re(complexparam(x))*complexparam(y)*im(complexparam(z))-im(complexparam(z))*re(complexparam(x))*complexparam(y)","0");
 equal("qdensity(exp(i*\"theta\")*[complexparam(x);0])-qdensity([complexparam(x);0])","[0,0;0,0]");

 for(const char *symbol:{"x","\"alpha\""}) {
  std::string parameter=std::string("complexparam(")+symbol+")";
  equal("qconj("+parameter+")","re("+parameter+")-i*im("+parameter+")");
  equal("replace(qconj("+parameter+"),"+symbol+",1+i)","1-i");
 }
 equal("complexparam(sqrt(2)/3)","sqrt(2)/3");
 equal("complexparam(0)","0");
 equal("complexparam(i)","i");
 equal("replace(replace(qdensity([complexparam(\"alpha\");complexparam(\"beta\")]),\"alpha\",1/sqrt(2)),\"beta\",i/sqrt(2))","[1,-i;i,1]/2");
 equal("qconj(exp(i*x))","exp(-i*x)");
 equal("qconj(exp(x+i*y))","exp(x-i*y)");
 equal("qconj(i*exp(i*x))","-i*exp(-i*x)");
 equal("qconj(1+i*exp(i*x))","1-i*exp(-i*x)");
 equal("qconj(2^(i*x))","2^(-i*x)");
 equal("qdag([exp(i*x),0;0,exp(-i*x)])","[exp(-i*x),0;0,exp(i*x)]");
 equal("qmul(qdag([1,0;0,exp(i*x)]),[1,0;0,exp(i*x)])","identity(2)");
 equal("qnorm([1;exp(i*x)]/sqrt(2))","1");
 equal("qdensity([1;exp(i*x)]/sqrt(2))","[1,exp(-i*x);exp(i*x),1]/2");
 equal("qconj((-1)^i)","exp(-pi)");
 equal("qconj(sqrt(-2))","-i*sqrt(2)");
 auto complexPhase=new UnknownVariable("","complexphase");
 auto complexAssumptions=new Assumptions;complexAssumptions->setType(ASSUMPTION_TYPE_COMPLEX);
 complexPhase->setAssumptions(complexAssumptions);calculator.addVariable(complexPhase);
 equal("qconj(exp(complexphase))","exp(conj(complexphase))");
 MathStructure phaseSymbol(complexPhase);
 for(const char *value:{"i","1+i","-1+2*i"}) {
  MathStructure expression=calculator.calculate("qconj(exp(i*complexphase))*exp(i*complexphase)",eo);
  expression.replace(phaseSymbol,calculator.calculate(value,eo));expression.eval(eo);
  MathStructure expected=calculator.calculate(std::string("exp(-2*im(")+value+"))",eo);
  expression.transform(COMPARISON_EQUALS,expected);expression.eval(eo);
  if(!expression.isOne())throw std::runtime_error("Conjugation assumed a complex phase was real");++checks;
 }
 for(const char *gate:{"Rz(x)","Rx(x)","Ry(x)"}) {
  MathStructure value=calculator.calculate(std::string("quantum: dagger(")+gate+")*("+gate+")",eo);
  value.transform(COMPARISON_EQUALS,calculator.calculate("identity(2)",eo));value.eval(eo);
  if(!value.isOne())throw std::runtime_error(std::string("Symbolic gate adjoint failed: ")+gate);++checks;
 }
 MathStructure unitBasis=calculator.calculate("qbasis(0,1)",eo);
 if(!unitBasis.isMatrix() || unitBasis.rows()!=1 || unitBasis.columns()!=1 || !unitBasis.getElement(1,1)->isOne())throw std::runtime_error("Unit basis lost matrix shape");
 ++checks;
 equal("qbasis(0,1)","qketstate(qbitlabel(0,0))");
 equal("qtensor(qbasis(0,1),qbasis(1,2))","qbasis(1,2)");
 equal("qdensity(qbasis(0,1))","qbasis(0,1)");
 equal("qnorm(qbasis(0,1))","1");
 equal("qmul(qdag(qbasis(0,1)),qbasis(0,1))","1");
 for(bool approximate:{false,true})for(const char *operation:{"qdag","qconj","qtranspose"})for(const char *operand:{"qketstate(x)","qbasis(x,4)","qfourier(x)","qmul(qfourier(x),qketstate(y))"}) {
  EvaluationOptions options=eo;options.approximation=approximate ? APPROXIMATION_APPROXIMATE : APPROXIMATION_EXACT;
  std::string twice=std::string(operation)+"("+operation+"("+operand+"))";
  while(calculator.message())calculator.nextMessage();
  MathStructure simplified=calculator.calculate(twice,options),expected=calculator.calculate(operand,options);
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error("Symbolic involution produced an error");calculator.nextMessage();}
  if(!simplified.equals(expected))throw std::runtime_error(std::string("Symbolic involution did not cancel: ")+twice);++checks;
  MathStructure triple=calculator.calculate(std::string(operation)+"("+twice+")",options),single=calculator.calculate(std::string(operation)+"("+operand+")",options);
  if(!triple.equals(single))throw std::runtime_error("Triple symbolic involution did not simplify");++checks;

 }
 for(const char *operation:{"qdag","qconj","qtranspose"})for(const char *operand:{"[1,i;2,3]","[1;i]","2+3i"})
  equal(std::string(operation)+"("+operation+"("+operand+"))",operand);

 for(const char *source:{"qketstate(x)","qbasis(x,4)","qbasis(1,x)","qmul(qfourier(x),qbasis(1,x))","qadjacent(qfourier(x),qketstate(y))","qdag(qketstate(x))"}) {
  while(calculator.message())calculator.nextMessage();MathStructure value=calculator.calculate(source,eo);
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error(std::string("Symbolic state rejected: ")+source);calculator.nextMessage();}
  if(!value.isFunction() || !value.containsUnknowns())throw std::runtime_error("Symbolic operation lost its structure");++checks;
 }
 MathStructure symbolicX=calculator.calculate("x",eo),symbolicY=calculator.calculate("y",eo);
 for(const char *source:{"qmul(qfourier(x),qbasis(1,x))","qadjacent(qfourier(x),qbasis(1,x))"}) {
  MathStructure value=calculator.calculate(source,eo);
  if(!value.isFunction() || value.function()->referenceName()!="qfourierdomain" || !value.containsFunction(calculator.getFunction("qsum")))throw std::runtime_error("Fourier action did not retain a guarded finite sum");++checks;
  value.replace(symbolicX,MathStructure(4));value.eval(eo);
  MathStructure expected=calculator.calculate("[1;i;-1;-i]/2",eo);value.transform(COMPARISON_EQUALS,expected);value.eval(eo);
  if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Symbolic Fourier application substitution failed");++checks;
 }
 MathStructure delayedKet=calculator.calculate("qmul([0,1;1,0],qketstate(x))",eo),zeroKet=calculator.calculate("[1;0]",eo);
 delayedKet.replace(symbolicX,zeroKet);delayedKet.eval(eo);delayedKet.transform(COMPARISON_EQUALS,calculator.calculate("[0;1]",eo));delayedKet.eval(eo);
 if(!delayedKet.isNumber() || !delayedKet.number().isOne())throw std::runtime_error("Named ket substitution failed");++checks;
 for(const char *source:{"qbasis(-1,x)","qbasis(x,0)","qbasis(x,1025)","qbasis(x,1/2)","qbasis([1,2],x)"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(source,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error("Symbolic parameter hid an invalid basis argument");++checks;
 }

 for(AngleUnit mode:{ANGLE_UNIT_NONE,ANGLE_UNIT_RADIANS,ANGLE_UNIT_DEGREES}) {
  eo.parse_options.angle_unit=mode;
  equal("qasin(1/2)","pi/6");equal("qacos(1/2)","pi/3");equal("qatan(1)","pi/4");
  equal("qasin(-1)","-pi/2");equal("qacos(-1)","pi");equal("qatan(-1)","-pi/4");
 }
 eo.parse_options.angle_unit=ANGLE_UNIT_NONE;
 MathStructure symbol=calculator.calculate("x",eo),delayed=calculator.calculate("qasin(x)",eo);
 delayed.replace(symbol,MathStructure(Number(1,2)));eo.parse_options.angle_unit=ANGLE_UNIT_DEGREES;delayed.eval(eo);
 MathStructure reference=calculator.calculate("pi/6",eo);delayed.transform(COMPARISON_EQUALS,reference);delayed.eval(eo);
 if(!delayed.isNumber() || !delayed.number().isOne())throw std::runtime_error("Deferred inverse changed angle convention");++checks;
 equal("asin(1/2)","30");
 eo.parse_options.angle_unit=ANGLE_UNIT_NONE;
 equal("qasin(i)","i*asinh(1)");
 eo.approximation=APPROXIMATION_APPROXIMATE;
 equal("floor(pi/(4*qasin(sqrt(1/2))))","1");
 eo.approximation=APPROXIMATION_EXACT;
 equal("qketstate([1;i])","[1;i]");
 equal("qketstate([3;4])","[3;4]");
 MathStructure oversized;oversized.clearMatrix();oversized.resizeMatrix(1025,1,m_zero);
 calculator.addVariable(new KnownVariable("","oversizedstate",oversized));
 for(const char *expression:{"qketstate(3)","qketstate([1,0])","qketstate(identity(2))","qketstate(oversizedstate)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid named state accepted: ")+expression);
  ++checks;
 }
 equal("qconj([1;i;2])","[1;-i;2]");
 equal("qconj([1,i,2])","[1,-i,2]");
 equal("qconj(2+3i)","2-3i");
 equal("qconj([1,i,2;3,4i,5])","[1,-i,2;3,-4i,5]");
 equal("qconj(qconj([1;i;2]))","[1;i;2]");
 equal("qdag([1,i])","[1;-i]");equal("qconj([1,i;2,3])","[1,-i;2,3]");
 equal("qtranspose([1,2;3,4])","[1,3;2,4]");
 equal("qmul(qdag([1;i]),[1;i])","2");
 equal("qadjacent([1;-1],[1;0])","[1;0;-1;0]");
 equal("qadjacent([1,i],[1,-1])","[1,-1,i,-i]");
 equal("qadjacent([1,0;0,1],[2;3])","[2;3]");
 equal("qnorm([3;4])","5");equal("qnormalize([3;4])","[3/5;4/5]");
 equal("qdensity([1;i])","[1,-i;i,1]");equal("qtrace([1,2;3,4])","5");
 equal("qtensor([1;0],[0;1])","[0;1;0;0]");
 equal("qtensorpow([0;1],3)","[0;0;0;0;0;0;0;1]");
 equal("qdirectsum([1,0;0,1],[2,0;0,2])","[1,0,0,0;0,1,0,0;0,0,2,0;0,0,0,2]");
 equal("qcontrolled([0,1;1,0])","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]");
 equal("qcontrol([0,1;1,0],1,0)","[0,1,0,0;1,0,0,0;0,0,1,0;0,0,0,1]");
 equal("qcontrolpattern([0,1;1,0],1,1,1)","qcontrolled([0,1;1,0])");
 equal("qcomm([0,1;1,0],[0,-i;i,0])","[2i,0;0,-2i]");
 equal("qanticomm([0,1;1,0],[0,-i;i,0])","[0,0;0,0]");
 for(unsigned i=0;i<8;++i)for(unsigned j=0;j<8;++j)
  equal("qmul(qdag(qbasis("+std::to_string(i)+",8)),qbasis("+std::to_string(j)+",8))",i==j ? "1" : "0");
 for(const auto &expression:{"complexparam(x+y)","complexparam([1;2])","complexparam(inf)","complexparam(1 m)","qadjacent([1,0;0,1],[1;2;3])","qadjacent(qbasis(0,64),qbasis(0,64))","qbasis(8,8)","qbasis(0,1025)","qnormalize([0;0])","qcontrol([0,1;1,0],9,0)","qcontrolpattern([0,1;1,0],1,1,2)","qtrace([1;2])","qmul([1,0;0,1],[1;2;3])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid algebra accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum algebra checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Variable.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
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
  MathStructure value=calculator.calculate(source,eo);value.replace(symbolicX,MathStructure(4));value.eval(eo);
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

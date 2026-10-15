// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumOrder.h"
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
 registerQuantumOrder(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 for(int a=-2;a<=2;++a)for(int b=-2;b<=2;++b)for(int d=-2;d<=2;++d) {
  std::string m="["+std::to_string(a)+","+std::to_string(b)+";"+std::to_string(b)+","+std::to_string(d)+"]";
  bool psd=a>=0 && d>=0 && a*d>=b*b,pd=a>0 && a*d>b*b;
  equal("qcompare("+m+",0,3)",psd ? "1" : "0");
  equal("qcompare(0,"+m+",2)",psd ? "1" : "0");
  equal("qcompare("+m+",0,1)",pd ? "1" : "0");
  equal("qcompare(0,"+m+",0)",pd ? "1" : "0");
 }
 equal("qcompare([1,i;-i,1],0,3)","1");
 equal("qcompare([1,i;-i,1],0,1)","0");
 equal("qcompare([1,0;0,10^-400],0,1)","1");
 equal("qcompare([1,0;0,-10^-400],0,3)","0");
 equal("qcompare([1,1,1;1,1,1;1,1,1],0,3)","1");
 equal("qcompare([1,1,1;1,1,1;1,1,1],0,1)","0");
 equal("qcompare(identity(3),1,4)","0");
 equal("qcompare(identity(3),1,3)","1");
 equal("qcompare(identity(3),1,2)","1");
 equal("qcompare(identity(3),identity(3),4)","1");
 equal("qcompare([1,2],[1,3],5)","1");
 for(int kind=0;kind<6;++kind) {
  const char *operators[]={"<",">","<=",">=","==","!="};
  equal("qcompare(2,3,"+std::to_string(kind)+")",std::string("2")+operators[kind]+"3");
 }
 for(const auto &expression:{"qcompare([1,1;0,1],0,3)","qcompare([1,2,3;4,5,6],0,3)","qcompare(identity(2),identity(3),3)","qcompare(identity(65),0,3)","qcompare([1,i;i,1],0,3)","qcompare(identity(2),0,6)","qcompare(identity(2),0,-1)","qcompare([infinity,0;0,1],0,3)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid matrix comparison accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" matrix order checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

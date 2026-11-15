// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include <iostream>
#include <string>

// Original IBM-020 cell17463a96, UTF-8 code points 4683:4817.
// Fragment SHA256 7ae5c0bf313cb9f9612b1adcce52785cca9951a7d8955014895f385b4e0f7cd9.
static const char *source=R"T4(\frac{1}{\sqrt{2^n}} \sum_{y_{n-1}\cdots y_0 \in \Sigma^n}
  (-1)^{x_{n-1}y_{n-1} + \cdots + x_0 y_0} \vert y_{n-1} \cdots y_0 \rangle)T4";
static bool errors(Calculator &calculator,bool report=false) {
 bool error=false;
 while(calculator.message()) {if(report)std::cerr << calculator.message()->message() << '\n';error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}
 return error;
}
int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned checks=0,failures=0;
 auto equal=[&](const std::string &expression,const std::string &expected,bool quantum=true) {
  errors(calculator);MathStructure value=calculator.calculate((quantum ? "quantum:" : "")+expression,options);
  bool error=errors(calculator);MathStructure reference=calculator.calculate(expected,options);
  value.transform(COMPARISON_EQUALS,reference);value.eval(options);
  if(error || errors(calculator) || !value.isNumber() || !value.number().isOne()) {
   std::cerr << "Register sum mismatch: " << expression << '\n';++failures;
  }++checks;
 };
 errors(calculator);MathStructure pending=calculator.calculate(std::string("quantum:")+source,options),sigma("Σ",true);
 if(errors(calculator,true) || pending.isNumber() || pending.isVector() || !pending.contains(sigma)) {
  std::cerr << "Unspecified register-sum domain was not retained: " << pending.print() << '\n';++failures;
 }++checks;
 equal("replace("+std::string(source)+",n,0)","matrix(1,1,[1])");
 for(unsigned n=1;n<=3;++n)for(unsigned x=0;x<(1U<<n);++x)for(bool widthFirst:{true,false}) {
  std::string expression=source;
  auto width=[&]() {expression="replace(replace("+expression+",n,"+std::to_string(n)+"),\\Sigma,vector(0,1))";};
  if(widthFirst)width();
  for(unsigned bit=0;bit<n;++bit)
   expression="replace("+expression+",x_"+std::to_string(bit)+","+std::to_string((x>>bit)&1)+")";
  if(!widthFirst)width();
  std::string entries;
  for(unsigned y=0;y<(1U<<n);++y) {
   unsigned common=x&y;bool parity=false;while(common) {parity=!parity;common&=common-1;}
   if(y)entries+=",";entries+=parity ? "-1" : "1";
  }
  equal(expression,"matrix("+std::to_string(1U<<n)+",1,["+entries+"])/sqrt("+std::to_string(1U<<n)+")");
 }
 equal("replace(replace(replace("+std::string(source)+",n,1),\\Sigma,vector(0,1,2)),x_0,1)","[1;-1;1]/sqrt(2)");
 equal("replace(replace(replace(replace("+std::string(source)+",x_1,1),x_0,0),n,2),\\Sigma,vector(0,1,2))",
       "[1;1;1;-1;-1;-1;1;1;1]/2");
 equal(R"(qregistersum(qsumset("y_0",vector(2,3),"y_0"),vector(0,1),0,0,"y_",1,vector()))","10",false);
 equal(R"(qregistersum(qsumset("y_0",vector("y_0"),"y_0"),vector(0,1),0,0,"y_",1,vector()))","1",false);
 equal(R"(qregistersum(qsum(qscalarproductsum("y_","x_",1,vector(1,0,1)),2,3,"y_0"),vector(0,1),0,0,"y_",1,vector()))","10",false);
 equal(R"(qreplace(qregistersum("x_0",vector(0,1),0,0,"y_",1,vector()),"x_0","y_0"))",R"(2*"y_0")",false);
 equal(R"(qregistersum(qadd(qregistersum("y_0",vector(2,3),0,0,"y_",1,vector()),"y_0"),vector(0,1),0,0,"y_",1,vector()))","11",false);
 equal(R"(qregistersum(qsumset(qadd("y_0","__qregister_local_a"),vector(2,3),"y_0"),vector(0,1),0,0,"y_",1,vector()))",R"(10+4*"__qregister_local_a")",false);
 equal(R"(qregistersum(qsumset(qadd("y_0",qindexedlabel("__qregister_local_","k","")),vector(2,3),"y_0"),vector(0,1),0,0,"y_",1,vector("k",0)))",R"(10+4*"__qregister_local_0")",false);
 equal(R"(qregistersum("y_0",vector(-1,0),0,0,"y_",1,vector()))","-1",false);
 equal(R"(qregistersum("y_0",vector(0,-1),0,0,"y_",1,vector()))","-1",false);
 equal(R"(qregistersum(qregisterfamily("y_",999999999999,0,vector()),vector(),999999999999,0,"y_",1000000000000,vector()))","0",false);
 for(const char *expression:{
  R"(qregistersum(1,vector(0,1),63,0,"y_",64,vector()))",
  R"(qregistersum(qketstate("y_0"),vector(0,2),32,0,"y_",33,vector()))",
  R"(qregistersum(qregisterfamily("y_",32,0,vector(0,1)),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum("y_0",vector(-1,0),32,0,"y_",33,vector()))",
  R"(qregistersum(qsumset(qketstate("y_33"),vector(0,1),"y_33"),vector(-1),32,0,"y_",33,vector()))",
  R"(qregistersum("x",vector(0,1),32,0,"y_",33,vector("x","y_33")))",
  R"(qregistersum(1,vector(0,1),999999999999,0,"y_",1000000000000,vector()))",
  R"(qregistersum(qregisterfamily("y_",0,0,vector()),vector(0,2),0,0,"y_",1,vector()))"
 }) {
  errors(calculator);MathStructure value=calculator.calculate(expression,options);
  if(errors(calculator) || !value.containsFunction(calculator.getFunction("qregistersum"))) {std::cerr << "Register sum failed to defer: " << expression << '\n';++failures;}++checks;
 }
 for(const char *expression:{
  R"(qregistersum(1,vector(0,1),1,0,"y_",1,vector()))",
  R"(qregistersum(qketstate("y_0"),vector(-1),32,0,"y_",33,vector()))",
  R"(qregistersum(qregisterfamily("y_",32,0,vector(0,2)),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qregisterfamily("y_",32,0,vector(0,-1)),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qregisterfamily("y_",32,0,vector(0,1/2)),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qketstate("y_0"),vector(-1,0),10,0,"y_",11,vector()))",
  R"(qregistersum(qketstate("y_0"),vector(0,1/2),32,0,"y_",33,vector()))",
  R"(qregistersum("y_33",vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qindexedlabel("y_",33,""),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qregisterfamily("y_",33,0,vector()),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum(qscalarproductsum("y_","x_",34,vector()),vector(0,1),32,0,"y_",33,vector()))",
  R"(qregistersum("y_999999999999",vector(0,1),999999999998,0,"y_",999999999999,vector()))",
  R"(qregistersum(qindexedlabel("y_","k",""),vector(0,1),32,0,"y_",33,vector("k",33)))",
  R"(qregistersum(1,vector(0,1),"n",0,"y_","n",vector()))",
  R"(qregistersum(1,vector(0,1),-2,0,"y_",0,vector()))",
  R"(qregistersum(1,vector(0,1),1/2,0,"y_",3/2,vector()))",
  R"(qregistersum(1,vector(0,1),0,0,"y_",1*m,vector()))",
  R"(qregistersum(qregisterfamily("y_",0,0,vector()),vector(-1,0),0,0,"y_",1,vector()))",
  R"(qregistersum(qregisterfamily("y_",0,0,vector()),vector(0,-1),0,0,"y_",1,vector()))",
  R"(qregistersum(qregisterfamily("y_",0,0,vector()),vector(0,1/2),0,0,"y_",1,vector()))",
  R"(qregistersum(qnamedket("y_0"),vector(0,i),0,0,"y_",1,vector()))",
  R"(qregistersum(1,3,63,0,"y_",64,vector()))",
  R"(qregistersum(1,m,63,0,"y_",64,vector()))",
  R"(qregistersum(1,3,999999999999,0,"y_",1000000000000,vector()))"
 }) {
  errors(calculator);calculator.calculate(expression,options);
  if(!errors(calculator)) {std::cerr << "Accepted invalid register sum: " << expression << '\n';++failures;}++checks;
 }
 if(failures)return 1;
 std::cout << "Register sum checks: " << checks << '\n';return 0;
}

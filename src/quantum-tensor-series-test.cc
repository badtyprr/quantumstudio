// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include <iostream>
#include <string>

// Unchanged UTF-8 IBM-020 notebook cell17463a96 code points4440:4666.
// SHA256 97400ad6d38e8eaaea07a73dd6e3fc2698048b14e7efb4d44efa5eb71c1087b4
static const char *source=R"T3(\Biggl( \frac{1}{\sqrt{2}} \sum_{y_{n-1}\in\Sigma} (-1)^{x_{n-1} y_{n-1}} \vert y_{n-1} \rangle \Biggr)
  \otimes \cdots \otimes
  \Biggl( \frac{1}{\sqrt{2}} \sum_{y_{0}\in\Sigma} (-1)^{x_{0} y_{0}} \vert y_{0} \rangle \Biggr))T3";
static bool errors(Calculator &calculator) {
 bool error=false;
 while(calculator.message()) {error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}
 return error;
}
int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned failures=0,checks=0;
 auto equal=[&](const std::string &expression,const std::string &expected) {
  errors(calculator);MathStructure value=calculator.calculate("quantum:"+expression,options);
  bool error=errors(calculator);MathStructure reference=calculator.calculate(expected,options);
  value.transform(COMPARISON_EQUALS,reference);value.eval(options);
  if(errors(calculator) || error || !value.isNumber() || !value.number().isOne()) {
   std::cerr << "Tensor series mismatch: " << expression << '\n';++failures;
  }
  ++checks;
 };
 errors(calculator);MathStructure pending=calculator.calculate(std::string("quantum:")+source,options);
 if(errors(calculator) || pending.isVector() || pending.isNumber() ||
    pending.containsFunction(calculator.getFunction("qsumset"))<=0) {
  std::cerr << "Undeclared tensor-series domain was not retained\n";++failures;
 }
 ++checks;
 // Empty products do not evaluate their still-unknown summation domains.
 equal("replace("+std::string(source)+",n,0)","matrix(1,1,[1])");
 for(unsigned n=1;n<=3;++n)for(unsigned x=0;x<(1U<<n);++x) {
  std::string expression="replace(replace("+std::string(source)+",n,"+std::to_string(n)+"),\\Sigma,vector(0,1))";
  for(unsigned bit=0;bit<n;++bit)
   expression="replace("+expression+",x_"+std::to_string(bit)+","+std::to_string((x>>bit)&1)+")";
  std::string entries;
  for(unsigned y=0;y<(1U<<n);++y) {
   unsigned common=x&y;bool parity=false;
   while(common) {parity=!parity;common&=common-1;}
   if(y)entries+=",";entries+=parity ? "-1" : "1";
  }
  equal(expression,"matrix("+std::to_string(1U<<n)+",1,["+entries+"])/sqrt("+std::to_string(1U<<n)+")");
 }
 // The displayed prefactor stays unchanged when the supplied domain differs.
 equal("replace(replace(replace("+std::string(source)+",n,1),\\Sigma,vector(0,1,2)),x_0,1)","matrix(3,1,[1,-1,1])/sqrt(2)");
 // Indexed assignments must survive while the series or its domain is still
 // unresolved; supplying a dimension/domain later must not discard them.
 equal("replace(replace(replace(replace("+std::string(source)+",x_1,1),x_0,0),n,2),\\Sigma,vector(0,1))",
       "[1;1;-1;-1]/2");
 equal("replace(replace(replace(replace("+std::string(source)+",n,2),x_1,1),x_0,0),\\Sigma,vector(0,1))",
       "[1;1;-1;-1]/2");
 equal("qtensorseries(qtensorseries([k;1],1,2,k,1),1,2,k,1)",
       "[4;2;4;2;2;1;2;1;4;2;4;2;2;1;2;1]");
 equal("replace(replace(replace(replace("+std::string(source)+",x_0,1),x_0,0),n,1),\\Sigma,vector(0,1))",
       "[1;-1]/sqrt(2)");
 equal("replace(replace(replace(replace("+std::string(source)+",x_0,x_0+1),x_0,0),n,1),\\Sigma,vector(0,1))",
       "[1;-1]/sqrt(2)");
 equal("replace(replace(replace("+std::string(source)+",x_0,n),n,1),\\Sigma,vector(0,1))",
       "[1;-1]/sqrt(2)");
 equal("replace(replace(replace(replace("+std::string(source)+",n,1),x_0,n),\\Sigma,vector(0,1)),n,2)",
       "[1;1]/sqrt(2)");
 equal("replace("+std::string(source)+",vector(x_1,x_0,n,\\Sigma),vector(1,0,2,vector(0,1)))",
       "[1;1;-1;-1]/2");
 // Direct native calls deliberately share the replacement's free name with
 // the binder; the quantum parser's earlier renaming cannot mask capture.
 for(const auto &item:{
      std::pair<const char *,const char *>(R"(qreplace(qtensorseries(["a";"slot"],1,2,"slot",1),"a","slot"))",R"(["slot"^2;2*"slot";"slot";2])"),
      {R"(qreplace(qreplace(qtensorseries(["a";"slot"],1,2,"slot",1),"a","b"),"b","slot"))",R"(["slot"^2;2*"slot";"slot";2])"},
      {R"(qreplace(qtensorseries([qindexedlabel("x_","slot","");1],0,0,"slot",1),"x_0","slot"))",R"(["slot";1])"}}) {
  errors(calculator);MathStructure value=calculator.calculate(item.first,options);
  bool error=errors(calculator);MathStructure reference=calculator.calculate(item.second,options);
  value.transform(COMPARISON_EQUALS,reference);value.eval(options);
  if(error || errors(calculator) || !value.isNumber() || !value.number().isOne()) {
   std::cerr << "Tensor series captured a free replacement: " << item.first << '\n';++failures;
  }++checks;
 }
 // Noncommuting tensor order is observable even for small column factors.
 equal("qtensorseries([k;1],1,2,k,1)","[2;1;2;1]");
 equal("qtensorseries([k;1],2,1,k,-1)","[2;2;1;1]");
 equal("qtensorseries([k;1],1000000000000,1000000000000,k,1)","[1000000000000;1]");
 equal("qtensorseries(1/0,0,-1,k,1)","matrix(1,1,[1])");
 equal("qtensorseries(1/0,-1,0,k,-1)","matrix(1,1,[1])");
 for(const auto *expression:{"qtensorseries([k;1],0,-2,k,1)","qtensorseries([k;1],-2,0,k,-1)",
      "qtensorseries([k;1],0,1,k,0)","qtensorseries([k;1],0,1/2,k,1)",
      R"(("a b"*x_{n-1}) \otimes \cdots \otimes ("ab"*x_{0}))",
      R"((a b*x_{n-1}) \otimes \cdots \otimes (ab*x_{0}))",
      R"((2*x_{n-1}) \otimes \cdots \otimes (3*x_{0}))"}) {
  errors(calculator);calculator.calculate(std::string("quantum:")+expression,options);
  if(!errors(calculator)) {std::cerr << "Invalid tensor series accepted: " << expression << '\n';++failures;}++checks;
 }
 if(failures)return 1;
 std::cout << "Tensor series checks: " << checks << '\n';return 0;
}

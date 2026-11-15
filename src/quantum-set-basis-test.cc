// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include <iostream>
#include <initializer_list>

static bool errors(Calculator &calculator) {
 bool found=false;
 while(calculator.message()) {
  found=found || calculator.message()->type()==MESSAGE_ERROR;
  calculator.nextMessage();
 }
 return found;
}

int main() {
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) {
  std::cerr << "Definitions unavailable\n";return 1;
 }
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned failures=0,checks=0;
 auto equal=[&](const char *expression,const char *expected) {
  errors(calculator);
  MathStructure value=calculator.calculate(expression,options);
  bool invalid=errors(calculator);
  MathStructure reference=calculator.calculate(expected,options);
  value.transform(COMPARISON_EQUALS,reference);value.eval(options);
  invalid=errors(calculator) || invalid;
  if(invalid || !value.isNumber() || !value.number().isOne()) {
   std::cerr << "Set basis value mismatch: " << expression << '\n';++failures;
  }
  ++checks;
 };
 equal("quantum:qsumset(qketstate(y),vector(1,0,1),y)","matrix(2,1,[1,1])");
 equal("quantum:qsumset(basis(y,4),vector(0,2),y)","matrix(4,1,[1,0,1,0])");
 equal("quantum:qsumset(y,vector(0,2),y)","2");
 equal("quantum:qsumset(qketstate(y),vector(),y)","0");
 equal("quantum:qsumset(qketstate(y),vector(0),y)","matrix(1,1,[1])");
 equal("quantum:qsumset(qsumset(qketstate(y),vector(0,1),y),vector(0,2),y)",
       "matrix(2,1,[2,2])");
 // Neither an undeclared alphabet nor a proper subset declares an ambient
 // basis. Retain the sum so later declarations can resolve that information.
 struct Pending {const char *expression;const char *domain;};
 const Pending pending[]={
  {R"(quantum:\sum_{y\in\Sigma} \vert y\rangle)",R"(quantum:\Sigma)"},
  {"quantum:qsumset(qketstate(y),vector(0,2),y)","vector(0,2)"},
  {"quantum:qsumset(qketstate(y),vector(2,0,2),y)","vector(2,0,2)"}
 };
 for(const auto &test:pending) {
  errors(calculator);
  MathStructure value=calculator.calculate(test.expression,options);
  bool invalid=errors(calculator);
  bool preserved=value.isFunction() && value.function()->referenceName()=="qsumset" && value.size()==3;
  if(preserved) {
   MathStructure domain=value[1],expectedDomain=calculator.calculate(test.domain,options);
   domain.eval(options);
   preserved=domain.equals(expectedDomain) && value[0].isFunction() &&
             value[0].function()->referenceName()=="qketstate" && value[0].size()==1 &&
             value[0][0].equals(value[2]) && (value[2].isSymbolic() || value[2].isVariable());
   invalid=errors(calculator) || invalid;
  }
  if(invalid || !preserved) {
   std::cerr << "Ambiguous set basis was not retained: " << test.expression << '\n';++failures;
  }
  ++checks;
 }
 equal(R"(quantum:replace(\sum_{y\in\Sigma}{\vert y\rangle},\Sigma,vector(0,1)))",
       "matrix(2,1,[1,1])");
 for(const char *expression:{
     "quantum:qsumset(qketstate(y)+basis(y,4),vector(0,2),y)",
     "quantum:qsumset(qketstate(y)+qsumset(basis(y,2),vector(),z),vector(0,2),y)"}) {
  errors(calculator);MathStructure value=calculator.calculate(expression,options);
  if(errors(calculator) || !value.isFunction() || value.function()->referenceName()!="qsumset") {
   std::cerr << "Valid mixed pending sum rejected: " << expression << '\n';++failures;
  }
  ++checks;
 }
 // A missing dimension does not make a known invalid numeric index valid.
 for(const char *expression:{
     "quantum:qsumset(qketstate(y),vector(-1,0),y)",
     "quantum:qsumset(qketstate(y),vector(0,1/2),y)",
     "quantum:qsumset(qketstate(y)+basis(y,2),vector(0,2),y)"}) {
  errors(calculator);calculator.calculate(expression,options);
  if(!errors(calculator)) {
   std::cerr << "Invalid basis index accepted: " << expression << '\n';++failures;
  }
  ++checks;
 }
 if(failures)return 1;
 std::cout << "Set basis checks: " << checks << '\n';return 0;
}

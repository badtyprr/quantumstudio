// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
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
 if(!calculator.loadGlobalDefinitions()) {std::cerr << "Definitions unavailable\n";return 1;}
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned failures=0,checks=0;
 struct Shape {const char *expression;int rows,columns;};
 for(const auto &test:{
     Shape{"quantum:|000000000001>",4096,1},
     Shape{"quantum:|000000000000>",4096,1},
     Shape{"quantum:<000000000001|",1,4096},
     Shape{"quantum:|++++++++++++>",4096,1},
     Shape{"quantum:tensor(|000000>,|000001>)",4096,1}}) {
  errors(calculator);
  MathStructure value=calculator.calculate(test.expression,options),rows,columns;
  bool shape=quantumMatrixShape(value,rows,columns,options);
  if(errors(calculator) || !shape || value.isVector() ||
     !rows.isNumber() || rows.number()!=test.rows ||
     !columns.isNumber() || columns.number()!=test.columns) {
   std::cerr << "Wide source shape mismatch: " << test.expression << '\n';++failures;
  }
  ++checks;
 }
 struct Domain {const char *expression;const char *width;};
 for(const auto &test:{Domain{"quantum:bitstrings(12)","12"},Domain{"quantum:bitstrings(10^12)","10^12"}}) {
  errors(calculator);MathStructure value=calculator.calculate(test.expression,options);
  MathStructure expected=calculator.calculate(test.width,options);
  bool preserved=value.isFunction() && value.function()->referenceName()=="qbitstrings" && value.size()==1;
  if(preserved) {MathStructure width=value[0];width.eval(options);preserved=width.equals(expected);}
  if(errors(calculator) || !preserved) {
   std::cerr << "Wide domain did not remain symbolic: " << test.expression << '\n';++failures;
  }
  ++checks;
 }
 errors(calculator);
 MathStructure cardinality=calculator.calculate("quantum:cardinality(bitstrings(12))",options);
 if(errors(calculator) || !cardinality.isNumber() || cardinality.number()!=4096) {
  std::cerr << "Wide domain cardinality mismatch\n";++failures;
 }
 ++checks;
 for(const char *expression:{
     "quantum:H*qketstate(bitstring(0,10^12))",
     "quantum:tensorpow(H,n)*qketstate(bitstring(k,n+1))",
     "quantum:bitstring(k,n+interval(0,1))",
     "quantum:replace(bitstrings(n),n,-1)",
     "quantum:replace(cardinality(bitstrings(n)),n,-1)"}) {
  errors(calculator);calculator.calculate(expression,options);
  if(!errors(calculator)) {std::cerr << "Invalid width relation accepted: " << expression << '\n';++failures;}
  ++checks;
 }
 // Equal or genuinely ambiguous symbolic widths must not become contradictions.
 for(const char *expression:{
     "quantum:tensorpow(H,n)*qketstate(bitstring(k,n))",
     "quantum:tensorpow(H,n)*qketstate(bitstring(k,m))",
     "quantum:tensorpow(H,n)*qketstate(bitstring(k,n+m))"}) {
  errors(calculator);MathStructure value=calculator.calculate(expression,options);
  if(errors(calculator) || value.isUndefined() || value.isNumber() ||
     value.containsFunction(calculator.getFunction("qtensorpow"))<=0 ||
     value.containsFunction(calculator.getFunction("qbitlabel"))<=0) {
   std::cerr << "Symbolic width relation rejected or lost: " << expression << '\n';++failures;
  }
  ++checks;
 }
 if(failures)return 1;
 std::cout << "Wide source checks: " << checks << '\n';return 0;
}

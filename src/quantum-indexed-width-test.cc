// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <initializer_list>

static bool errors(Calculator &calculator) {
 bool error=false;
 while(calculator.message()) {error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}
 return error;
}

int main() {
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) {std::cerr << "Definitions unavailable\n";return 1;}
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned failures=0,checks=0;
 struct Shape {const char *expression;const char *rows;bool deferred;};
 for(const auto &test:{
     Shape{"quantum:|x_(n-1) ... x_0>","2^n",true},
     Shape{"quantum:replace(|x_(n-1) ... x_0>,n,12)","4096",true},
     Shape{"quantum:replace(|x_(n-1) ... x_0>,n,0)","1",false}}) {
  errors(calculator);MathStructure value=calculator.calculate(test.expression,options),rows,columns;
  bool shape=quantumMatrixShape(value,rows,columns,options);
  if(shape) {rows-=calculator.calculate(test.rows,options);rows.eval(options);}
  if(errors(calculator) || !shape || !rows.isZero() || !columns.isOne() ||
     (test.deferred && value.isVector()) ||
     (!test.deferred && (!value.isMatrix() || value.rows()!=1 || value.columns()!=1 || !value.getElement(1,1)->isOne()))) {
   std::cerr << "Indexed width shape mismatch: " << test.expression << '\n';++failures;
  }
  ++checks;
 }
 errors(calculator);
 MathStructure huge=calculator.calculate("quantum:replace(|x_(n-1) ... x_0>,n,10^12)",options),rows,columns;
 bool shape=quantumMatrixShape(huge,rows,columns,options);
 MathStructure count=calculator.calculate("10^12",options);
 if(errors(calculator) || huge.isVector() || !shape || !columns.isOne() ||
    !rows.isPower() || rows.size()!=2 || !rows[0].isNumber() || rows[0].number()!=2 || !rows[1].equals(count)) {
  std::cerr << "Huge indexed width was not retained\n";++failures;
 }
 ++checks;
 for(const char *expression:{
     "quantum:replace(replace(|x_(n-1) ... x_0>,x_0,1),n,12)",
     "quantum:replace(replace(|x_(n-1) ... x_0>,n,12),x_0,1)"}) {
 errors(calculator);
 MathStructure bound=calculator.calculate(expression,options);
 bool retained=bound.isFunction() && bound.function()->referenceName()=="qregisterfamily" && bound.size()==4;
 if(retained) {
  MathStructure first=bound[1],last=bound[2];first.eval(options);last.eval(options);
  retained=bound[0].isSymbolic() && bound[0].symbol()=="x_" && first.isNumber() && first.number()==11 && last.isZero();
 }
 if(errors(calculator) || !retained ||
    bound.size()!=4 || !bound[3].isVector() || bound[3].size()!=2 ||
    !bound[3][0].isZero() || !bound[3][1].isOne()) {
  std::cerr << "Wide indexed bit assignment was lost\n";++failures;
 }
 ++checks;
 }
 errors(calculator);
 MathStructure finite=calculator.calculate("quantum:replace(replace(replace(|x_(n-1) ... x_0>,x_1,1),x_0,0),n,2)",options);
 MathStructure expected=calculator.calculate("matrix(4,1,[0,0,1,0])",options);
 if(errors(calculator) || !finite.equals(expected)) {std::cerr << "Finite indexed assignment mismatch\n";++failures;}
 ++checks;
 errors(calculator);
 MathStructure high=calculator.calculate("quantum:replace(|x_(10^12) ... x_(10^12)>,x_1000000000000,1)",options);
 expected=calculator.calculate("matrix(2,1,[0,1])",options);
 if(errors(calculator) || !high.equals(expected)) {std::cerr << "Large index assignment mismatch\n";++failures;}
 ++checks;
 // An unassigned canonical n-1..0 family has the empty n=0 identity.
 // Supplied bits and explicitly displayed trailing indices must still exist.
 for(const char *expression:{
     "quantum:replace(replace(|x_(n-1) ... x_0>,x_0,2),n,12)",
     "quantum:replace(|x_(n-1) ... x_0>,n,-1)",
     "quantum:replace(|x_(n-1) ... x_0>,n,1/2)",
     "quantum:replace(replace(|x_(n-1) ... x_0>,x_0,1),n,0)",
     "quantum:replace(|x_(n-1) ... x_1 x_0>,n,0)",
     "quantum:replace(|x_(n-1) ... x_1 x_0>,n,1)"}) {
  errors(calculator);calculator.calculate(expression,options);
  if(!errors(calculator)) {std::cerr << "Invalid indexed register accepted: " << expression << '\n';++failures;}
  ++checks;
 }
 if(failures)return 1;
 std::cout << "Indexed width checks: " << checks << '\n';return 0;
}

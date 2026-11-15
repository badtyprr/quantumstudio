// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <string>

// DEV-05: register shape is meaningful even when dense expansion is deferred.
// These checks exercise the public shape query, not a particular representation.
int main() {
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) {
  std::cerr << "Definitions unavailable\n";
  return 1;
 }
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 struct Case {const char *expression;const char *rows;const char *columns;bool deferred=false;};
 const Case cases[]={
  {"quantum:tensor(H,H)","4","4"},
  {"quantum:tensorpow(H,n)","2^n","2^n"},
  {"quantum:tensor(tensorpow(H,n),H)","2^(n+1)","2^(n+1)"},
  {"quantum:qketstate(bitstring(k,n))","2^n","1"},
  {"quantum:qketstate(bitstring(0,0))","1","1"},
  {"quantum:qketstate(bitstring(0,12))","4096","1",true},
  {"quantum:tensorpow(H,12)","4096","4096",true}
 };
 unsigned failures=0;
 unsigned extraChecks=0;
 for(const auto &test:cases) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(test.expression,options),rows,columns;
  bool error=false;
  while(calculator.message()) {
   if(calculator.message()->type()==MESSAGE_ERROR)error=true;
   calculator.nextMessage();
  }
  bool shape=quantumMatrixShape(value,rows,columns,options);
  if(shape) {
   rows-=calculator.calculate(test.rows,options);rows.eval(options);
   columns-=calculator.calculate(test.columns,options);columns.eval(options);
  }
  while(calculator.message()) {
   if(calculator.message()->type()==MESSAGE_ERROR)error=true;
   calculator.nextMessage();
  }
  if(error || !shape || !rows.isZero() || !columns.isZero() ||
     (test.deferred && value.isVector())) {
   std::cerr << "Register shape mismatch: " << test.expression
             << "; expected " << test.rows << " by " << test.columns << '\n';
   ++failures;
  }
 }
 for(const char *expression:{"quantum:tensorpow(H,10^12)","quantum:qketstate(bitstring(0,10^12))"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,options),rows,columns;
  bool shape=quantumMatrixShape(value,rows,columns,options);
  MathStructure exponent=calculator.calculate("10^12",options);
  bool error=false;
  while(calculator.message()) {if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(error || value.isVector() || !shape || !rows.isPower() || rows.size()!=2 ||
     !rows[0].isNumber() || rows[0].number()!=2 || !rows[1].equals(exponent) ||
     (std::string(expression).find("tensorpow")!=std::string::npos ? !columns.equals(rows) : !columns.isOne())) {
   std::cerr << "Huge register dimension was not retained: " << expression << '\n';++failures;
  }
  ++extraChecks;
 }
 struct BitCase {const char *expression;const char *expected;};
 for(const auto &test:{
     BitCase{"quantum:bitvalue(bitxor(bitstring(1,80),bitstring(2,80)))","3"},
     BitCase{"quantum:bitdot(bitstring(7,80),bitstring(3,80))","0"},
     BitCase{"quantum:bitdot(bitstring(7,80),bitstring(1,80))","1"},
     BitCase{"quantum:bitvalue(bitstring(0,0))","0"},
     BitCase{"quantum:bitvalue(bitstring(2^79,80))","2^79"},
     BitCase{"quantum:bitvalue(bitxor(bitstring(2^79,80),bitstring(1,80)))","2^79+1"},
     BitCase{"quantum:bitdot(bitstring(2^79,80),bitstring(2^79,80))","1"}}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(test.expression,options);
  MathStructure expected=calculator.calculate(test.expected,options);bool error=false;
  while(calculator.message()) {if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(error || !value.isNumber() || !value.equals(expected)) {
   std::cerr << "Wide bit operation mismatch: " << test.expression << '\n';++failures;
  }
  ++extraChecks;
 }
 // Widening the symbolic representation must retain value and shape checks.
 const char *invalid[]={
  "quantum:bitstring(0,-1)",
  "quantum:bitstring(0,1/2)",
  "quantum:bitstring(-1,12)",
  "quantum:bitstring(4096,12)",
  "quantum:H*qketstate(bitstring(k,2))",
  "quantum:bitxor(bitstring(k,80),bitstring(m,81))",
  "quantum:bitxor(bitstring(0,10^12),vector(0,0))",
  "quantum:bitstring(1,0)",
  "quantum:tensorpow(H,-1)",
  "quantum:tensorpow(H,1/2)"
 };
 for(const char *expression:invalid) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,options);
  bool error=false;
  while(calculator.message()) {
   if(calculator.message()->type()==MESSAGE_ERROR)error=true;
   calculator.nextMessage();
  }
  if(!error) {
   std::cerr << "Invalid register accepted: " << expression << '\n';
   ++failures;
  }
 }
 if(failures)return 1;
 std::cout << "Register width checks: "
           << sizeof(cases)/sizeof(cases[0])+sizeof(invalid)/sizeof(invalid[0])+extraChecks << '\n';
 return 0;
}

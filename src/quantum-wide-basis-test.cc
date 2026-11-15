// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <string>

int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned checks=0,failures=0;
 auto errors=[&]() {bool error=false;while(calculator.message()) {error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}return error;};
 struct Case {const char *source,*rows,*columns;bool deferred;};
 for(const auto &test:{Case{"qbasis(1024,1025)","1025","1",true},
  {"qbasis(x,1025)","1025","1",true},{"qbasis(999999999999,10^12)","10^12","1",true},
  {"qadjacent(qbasis(0,64),qbasis(0,64))","4096","1",true},
  {"qbasis(1023,1024)","1024","1",false},{"qfourier(65)","65","65",true},
  {"qfourier(10^12)","10^12","10^12",true},{"qft(7)","128","128",true},
  {"qft(0)","1","1",false},{"qft(n)","2^n","2^n",true},
  {"qmul(qfourier(1025),qbasis(0,1025))","1025","1",true},
  {"qfourierdomain(qbasis(0,65),0,65)","65","1",true},
  {"qfourierdomain(qbasis(0,10^12),0,10^12)","10^12","1",true},
  {"qmul(qfourier(65),qbasis(x,65))","65","1",true}}) {
  errors();MathStructure value=calculator.calculate(test.source,options),rows,columns;
  bool known=quantumMatrixShape(value,rows,columns,options);
  if(known) {rows-=calculator.calculate(test.rows,options);columns-=calculator.calculate(test.columns,options);rows.eval(options);columns.eval(options);}
  if(errors() || !known || !rows.isZero() || !columns.isZero() || value.isMatrix()==test.deferred) {++failures;std::cerr << "Wide basis shape: " << test.source << " => " << value.print() << '\n';}++checks;
 }
 for(const char *source:{"qbasis(1025,1025)","qbasis(-1,10^12)","qbasis(0,0)","qbasis(0,3/2)",
  "qfourier(0)","qft(-1)","qft(1/2)","qfourier(1/2)",
  "qfourierdomain(qbasis(0,65),65,65)","qfourierdomain(qbasis(0,65),-1,65)",
  "qfourierdomain([1;0],0,65)","qmul(qfourier(65),qbasis(0,66))"}) {
  errors();calculator.calculate(source,options);if(!errors()) {++failures;std::cerr << "Invalid wide basis accepted: " << source << '\n';}++checks;
 }
 errors();MathStructure huge=calculator.calculate("qft(10^12)",options),rows,columns;
 if(!quantumMatrixShape(huge,rows,columns,options) || errors() || !rows.isPower() || !rows.equals(columns) || huge.isMatrix()) {++failures;std::cerr << "Huge Fourier power expanded or lost shape\n";}++checks;
 // Instantiate the same symbolic Fourier action on either side of its dense
 // expansion threshold, then verify that the finite result is still exact.
 MathStructure symbolic=calculator.calculate("qmul(qfourier(n),qbasis(1,n))",options),n=calculator.calculate("n",options);
 MathStructure wide=symbolic;wide.replace(n,MathStructure(65));wide.eval(options);
 if(errors() || wide.isMatrix() || !quantumMatrixShape(wide,rows,columns,options) || !rows.equals(MathStructure(65))) {++failures;std::cerr << "Wide Fourier substitution failed\n";}++checks;
 symbolic.replace(n,MathStructure(4));symbolic.eval(options);
 MathStructure expected=calculator.calculate("[1;i;-1;-i]/2",options);symbolic-=expected;symbolic.eval(options);
 bool zero=symbolic.isMatrix();if(zero)for(size_t r=0;r<symbolic.rows();++r)zero=zero && symbolic[r][0].isZero();
 if(errors() || !zero) {++failures;std::cerr << "Finite Fourier reference mismatch\n";}++checks;
 if(failures)return 1;std::cout << "Wide basis checks: " << checks << '\n';return 0;
}

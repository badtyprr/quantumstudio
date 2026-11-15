// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <string>

static bool errors(Calculator &calculator) {
 bool error=false;
 while(calculator.message()) {error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}
 return error;
}
// Original IBM-020 cell17463a96, UTF-8 code points4440:4666.
static const char *source=R"T3(\Biggl( \frac{1}{\sqrt{2}} \sum_{y_{n-1}\in\Sigma} (-1)^{x_{n-1} y_{n-1}} \vert y_{n-1} \rangle \Biggr)
  \otimes \cdots \otimes
  \Biggl( \frac{1}{\sqrt{2}} \sum_{y_{0}\in\Sigma} (-1)^{x_{0} y_{0}} \vert y_{0} \rangle \Biggr))T3";
int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned checks=0,failures=0;
 auto shape=[&](const std::string &expression,const char *expectedRows,const char *expectedColumns) {
  errors(calculator);MathStructure value=calculator.calculate("quantum:"+expression,options),rows,columns;
  bool known=quantumMatrixShape(value,rows,columns,options),error=errors(calculator);
  if(known) {
   rows-=calculator.calculate(expectedRows,options);rows.eval(options);
   columns-=calculator.calculate(expectedColumns,options);columns.eval(options);
  }
  if(error || errors(calculator) || !known || !rows.isZero() || !columns.isZero() || value.isVector()) {
   std::cerr << "Tensor series shape mismatch: " << expression << '\n';++failures;
  }++checks;
 };
 shape("qtensorseries(qbasis(0,2),0,n-1,k,1)","2^n","1");
 shape("qtensorseries(qbasis(0,2),n-1,0,k,-1)","2^n","1");
 shape("qtensorseries(qbasis(0,2),0,63,k,1)","2^64","1");
 shape("replace(replace(qtensorseries(qbasis(0,d),0,n-1,k,1),d,3),n,64)","3^64","1");
 shape("replace(replace(qtensorseries(qbasis(0,d),0,n-1,k,1),n,64),d,3)","3^64","1");
 shape("qtensorseries(matrixparam(A,2,3),0,n-1,k,1)","2^n","3^n");
 shape("qtensorseries(1/0,n,n-1,k,1)","1","1");
 shape("tensorpow(H,n)*qtensorseries(qbasis(0,2),0,n-1,k,1)","2^n","1");
 shape("replace("+std::string(source)+",\\Sigma,vector(0,1))","2^n","1");
 shape("replace("+std::string(source)+",\\Sigma,vector(0,1,2))","3^n","1");
 shape("replace(replace("+std::string(source)+",\\Sigma,vector(0,1)),n,64)","2^64","1");
 shape("replace(replace("+std::string(source)+",n,64),\\Sigma,vector(0,1,2))","3^64","1");
 shape("replace(replace("+std::string(source)+",x_0,1),\\Sigma,vector(0,1))","2^n","1");
 shape("replace(replace(replace("+std::string(source)+",x_0,x_0+1),x_0,0),\\Sigma,vector(0,1))","2^n","1");
 const std::string coefficientSeries=R"(qtensorseries(qadjacent(qindexedlabel("A_",k,""),qbasis(0,2)),0,n-1,k,1))";
 shape("replace(replace("+coefficientSeries+",A_0,a),a,2)","2^n","1");
 // Never construct the astronomical expected row count as an integer.
 for(const char *expression:{"quantum:qtensorseries(qbasis(0,2),0,10^12-1,k,1)","quantum:tensorpow(|0>,10^12)"}) {
 errors(calculator);MathStructure huge=calculator.calculate(expression,options),rows,columns;
 bool known=quantumMatrixShape(huge,rows,columns,options);
 if(errors(calculator) || !known || huge.isVector() || !columns.isOne() || !rows.isPower() || rows.size()!=2 ||
    !rows[0].isNumber() || rows[0].number()!=2 || !rows[1].equals(calculator.calculate("10^12",options))) {
  std::cerr << "Huge tensor-series dimension was not retained\n";++failures;
 }++checks;
 }
 for(const std::string &expression:{std::string("qtensorseries(qbasis(0,k+1),0,n-1,k,1)"),
      std::string(source),"replace("+std::string(source)+",\\Sigma,vector())",
      "replace("+coefficientSeries+",A_0,[1,0;0,1;1,1])",
      "replace(replace("+coefficientSeries+",A_0,a),a,[1,0;0,1;1,1])",
      "replace(replace("+coefficientSeries+",A_0,qindexedlabel(\"B_\",j,\"\")),B_0,[1,0;0,1;1,1])",
      "replace(replace("+std::string(source)+",x_0,[1,0;0,1]),\\Sigma,vector(0,1))"}) {
  errors(calculator);MathStructure value=calculator.calculate("quantum:"+expression,options),r,c;
  if(quantumMatrixShape(value,r,c,options) || errors(calculator)) {
   std::cerr << "Ambiguous series dimension was guessed: " << expression << '\n';++failures;
  }++checks;
 }
 for(const char *expression:{"qtensorseries(qbasis(0,2),n,n-2,k,1)",
      "replace(qtensorseries(1/0,n,n-1,k,1),n,1/2)",
      "H*qtensorseries(qbasis(0,2),0,63,k,1)",
      "tensorpow(H,n+1)*qtensorseries(qbasis(0,2),0,n-1,k,1)"}) {
  errors(calculator);calculator.calculate(std::string("quantum:")+expression,options);
  if(!errors(calculator)) {std::cerr << "Invalid series constraint accepted: " << expression << '\n';++failures;}++checks;
 }
 errors(calculator);MathStructure ambiguous=calculator.calculate("quantum:tensorpow(H,m)*qtensorseries(qbasis(0,2),0,n-1,k,1)",options);
 if(errors(calculator) || ambiguous.isVector() || ambiguous.containsFunction(calculator.getFunction("qtensorseries"))<=0 ||
    ambiguous.containsFunction(calculator.getFunction("qtensorpow"))<=0) {
  std::cerr << "Ambiguous tensor-series product was not retained\n";++failures;
 }++checks;
 if(failures)return 1;
 std::cout << "Tensor series width checks: " << checks << '\n';return 0;
}

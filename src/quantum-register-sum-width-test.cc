// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <string>
// Original IBM-020 cell17463a96, UTF-8 code points4683:4817.
static const char *source=R"T4(\frac{1}{\sqrt{2^n}} \sum_{y_{n-1}\cdots y_0 \in \Sigma^n}
  (-1)^{x_{n-1}y_{n-1} + \cdots + x_0 y_0} \vert y_{n-1} \cdots y_0 \rangle)T4";
static bool errors(Calculator &calculator) {
 bool error=false;while(calculator.message()) {error=error || calculator.message()->type()==MESSAGE_ERROR;calculator.nextMessage();}return error;
}
int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 unsigned checks=0,failures=0;
 auto shape=[&](const std::string &expression,const char *expectedRows,const char *expectedColumns) {
  errors(calculator);MathStructure value=calculator.calculate("quantum:"+expression,options),rows,columns;
  bool known=quantumMatrixShape(value,rows,columns,options),error=errors(calculator);
  if(known) {rows-=calculator.calculate(std::string("quantum:")+expectedRows,options);columns-=calculator.calculate(std::string("quantum:")+expectedColumns,options);rows.eval(options);columns.eval(options);}
  if(error || errors(calculator) || !known || !rows.isZero() || !columns.isZero()) {
   std::cerr << "Register sum shape mismatch: " << expression << "\nknown=" << known << " error=" << error << " rows-difference=" << rows.print() << " columns-difference=" << columns.print() << "\nvalue=" << value.print() << '\n';
   if(value.size()==2) {
    MathStructure ar,ac,br,bc;bool left=quantumMatrixShape(value[0],ar,ac,options),right=quantumMatrixShape(value[1],br,bc,options);
    MathStructure difference=ac;difference-=br;difference.eval(options);
    std::cerr << "operands=" << left << ',' << right << " left=" << ar.print() << ',' << ac.print() << " right=" << br.print() << ',' << bc.print() << " inner-equal=" << ac.equals(br) << " inner-difference=" << difference.print() << '\n';
   }
   ++failures;
  }++checks;
 };
 const std::string binary="replace("+std::string(source)+",\\Sigma,vector(0,1))";
 const std::string qutrit="replace("+std::string(source)+",\\Sigma,vector(0,1,2))";
 shape(binary,"2^n","1");shape(qutrit,"3^n","1");
 shape("replace("+binary+",n,64)","2^64","1");
 shape("replace(replace("+std::string(source)+",n,64),\\Sigma,vector(0,1,2))","3^64","1");
 shape("replace("+std::string(source)+",n,0)","1","1");
 shape("replace("+binary+",x_0,1)","2^n","1");
 shape("replace(replace("+binary+",x_0,x_0+1),x_0,0)","2^n","1");
 shape("tensorpow(H,n)*"+binary,"2^n","1");
 shape("tensorpow(H,n)*replace("+binary+",x_0,1)","2^n","1");
 shape("tensorpow(H,64)*replace(qtensorseries(qbasis(0,2),0,n-1,k,1),n,64)","2^64","1");
 shape(R"(qregistersum(matrixparam(A,2,3),vector(0,1),n-1,0,"y_",n,vector()))","2","3");
 shape(R"(qregistersum(qregisterfamily("y_",n-1,0,vector()),vector(0),n-1,0,"y_",n,vector()))","1","1");
 shape(R"(qregistersum(qregisterfamily("y_",n-1,0,vector()),vector(2,0,1,1),n-1,0,"y_",n,vector()))","3^n","1");
 shape(R"(qregistersum(qadjacent(qscalarproductsum("x_","y_","n",vector()),qregisterfamily("y_",n-1,0,vector())),vector(0,1),n-1,0,"y_",n,vector()))","2^n","1");
 shape(R"(qregistersum(qadjacent(qscalarproductsum("x_","y_","n"+1,vector()),qregisterfamily("y_",n,0,vector())),vector(0,1),n,0,"y_",n+1,vector()))","2^(n+1)","1");
 shape(R"(qregistersum(qregistersum(qregisterfamily("y_",m-1,0,vector()),vector(0,1,2),m-1,0,"y_",m,vector()),vector(0,1),n-1,0,"y_",n,vector()))","3^m","1");
 shape(R"(qregistersum(qregisterfamily("y_",n,2,vector()),vector(0,1),n,1,"y_",n,vector()))","2^(n-1)","1");
 shape(R"(qregistersum(qregisterfamily("y_",63,0,vector(0,1)),vector(0,1),63,0,"y_",64,vector()))","2^64","1");
 errors(calculator);MathStructure huge=calculator.calculate("quantum:replace("+binary+",n,10^12)",options),r,c;
 bool known=quantumMatrixShape(huge,r,c,options);
 if(errors(calculator) || !known || huge.isVector() || !c.isOne() || !r.isPower() || r.size()!=2 ||
    !r[0].isNumber() || r[0].number()!=2 || !r[1].equals(calculator.calculate("10^12",options))) {std::cerr << "Huge register sum shape was not retained\n";++failures;}++checks;
 for(const std::string &expression:{std::string(source),
  "replace("+std::string(source)+",\\Sigma,vector(0,2))",
  "replace("+std::string(source)+",\\Sigma,vector())",
  "replace("+binary+",x_0,[1,0;0,1])",
  "replace(replace("+binary+",x_0,a),a,[1,0;0,1])",
  std::string(R"(qregistersum(matrixparam(A,y_0+1,1),vector(0,1),n-1,0,"y_",n,vector()))"),
  std::string(R"(qregistersum(matrixparam(A,y_0-y_1+1,1),vector(0,1),n-1,0,"y_",n,vector()))"),
  std::string(R"(qregistersum(qadjacent(qscalarproductsum("x_","y_","m",vector()),qregisterfamily("y_",n-1,0,vector())),vector(0,1),n-1,0,"y_",n,vector()))"),
  std::string(R"(qregistersum(qregisterfamily("y_",k,0,vector()),vector(0,1),n-1,0,"y_",n,vector()))"),
  std::string(R"(qregistersum(qregisterfamily("y_",n-1,0,vector()),vector(0,1),n-1,0,"y_",m,vector()))")}) {
  errors(calculator);MathStructure value=calculator.calculate("quantum:"+expression,options),rows,columns;
  if(quantumMatrixShape(value,rows,columns,options) || errors(calculator)) {std::cerr << "Ambiguous register sum shape was guessed: " << expression << '\n';++failures;}++checks;
 }
 for(const char *expression:{
  R"(qregistersum(qregisterfamily("y_",64,0,vector()),vector(0,1),63,0,"y_",64,vector()))",
  R"(qregistersum(qregisterfamily("y_",63,0,vector(0,3)),vector(0,1),63,0,"y_",64,vector()))"
 }) {
  errors(calculator);calculator.calculate(expression,options);
  if(!errors(calculator)) {std::cerr << "Contradictory bound register accepted: " << expression << '\n';++failures;}++checks;
 }
 errors(calculator);calculator.calculate("quantum:tensorpow(H,n+1)*"+binary,options);
 if(!errors(calculator)) {std::cerr << "Contradictory register sum product accepted\n";++failures;}++checks;
 errors(calculator);calculator.calculate("quantum:tensorpow(H,m)*"+binary,options);
 if(errors(calculator)) {std::cerr << "Ambiguous register product rejected\n";++failures;}++checks;
 if(failures)return 1;std::cout << "Register sum width checks: " << checks << '\n';return 0;
}

// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactPhase.h"
#include "libqalculate/Calculator.h"
#include "libqalculate/BuiltinFunctions.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumExact;
namespace {
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact phase expression check "+std::to_string(checks));}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());
 EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 exact.parse_options.angle_unit=ANGLE_UNIT_RADIANS;
 PhaseBudget budget(4096,4096,1000000);
 PrintOptions print;print.use_unicode_signs=false;print.number_fraction_format=FRACTION_FRACTIONAL;
 auto calc=[&](const std::string &s){return calculator.calculate(s,exact);};
 auto one=PhasePolynomial::term(0,1,0,budget);
 for(const char *gate:{"H","X","Y","Z","S","T","CNOT","SWAP","Rx(0.1)","Ry(-0.3)","Rz(3.1415926535897931)"}) {
  auto matrix=calc(std::string("quantum: ")+gate);check(matrix.isMatrix());
  for(std::size_t r=1;r<=matrix.rows();++r)for(std::size_t c=1;c<=matrix.columns();++c) {
   const auto &entry=*matrix.getElement(r,c);PhasePolynomial phase;
   check(PhasePolynomial::tryFromExpression(entry,phase,budget));
   auto expression=phase.toExpression(budget);PhasePolynomial restored;
   check(PhasePolynomial::tryFromExpression(expression,restored,budget));check(restored==phase);
   check(PhasePolynomial::tryFromExpression(calc(expression.print(print)),restored,budget));check(restored==phase);
   check(PhasePolynomial::tryFromExpression(calc(phase.toExactString(budget,100000)),restored,budget));
   check(restored==phase);
   // The independent general evaluator verifies the value, including signs.
   EvaluationOptions approximate=exact;approximate.approximation=APPROXIMATION_APPROXIMATE;
   auto difference=expression;difference-=entry;difference.eval(approximate);
   check(difference.isNumber());Number distance=difference.number();check(distance.abs());check(distance<Number(1,1,-12));
  }
 }
 auto rotation=calc("quantum: Rx(0.12345678901234567)");
 PhasePolynomial diagonal,offDiagonal;
 check(PhasePolynomial::tryFromExpression(*rotation.getElement(1,1),diagonal,budget));
 check(PhasePolynomial::tryFromExpression(*rotation.getElement(1,2),offDiagonal,budget));
 check(diagonal.times(diagonal.conjugated(budget),budget).plus(
       offDiagonal.times(offDiagonal.conjugated(budget),budget),budget)==one);
 auto sample=PhasePolynomial::term(Number(1,7),Number(2,3),Number(-1,2),budget);
 sample=sample.plus(PhasePolynomial::term(Number(-2,9),-1,0,budget),budget);
 PhasePolynomial restored;check(PhasePolynomial::tryFromExpression(sample.toExpression(budget),restored,budget));check(restored==sample);
 // Printing and reparsing must retain the exact supported expression.
 auto serialized=sample.toExpression(budget).print(print);
 auto reparsed=calc(serialized);
 check(PhasePolynomial::tryFromExpression(reparsed,restored,budget));
 if(!(restored==sample))std::cerr<<"Serialized: "<<serialized<<"\nParsed: "<<reparsed.print(print)<<'\n';
 check(restored==sample);
 Number gaussian(1,3);gaussian.setImaginaryPart(2,7);
 auto complex=PhasePolynomial::term(Number(1,7),gaussian,gaussian,budget);
 check(PhasePolynomial::tryFromExpression(calc(complex.toExpression(budget).print(print)),restored,budget));check(restored==complex);
 check(PhasePolynomial::tryFromExpression(calc(complex.toExactString(budget,100000)),restored,budget));check(restored==complex);
 auto exactText=sample.toExactString(budget,100000);
 check(sample.toExactString(budget,exactText.size())==exactText);
 rejects<std::length_error>([&]{sample.toExactString(budget,exactText.size()-1);});
 check(PhasePolynomial().toExactString(budget,1)=="0");
 rejects<std::length_error>([&]{PhasePolynomial().toExactString(budget,0);});
 auto square=calc("cos(1 rad)^2");
 check(PhasePolynomial::tryFromExpression(square,restored,budget));
 auto expected=PhasePolynomial::term(0,Number(1,2),0,budget).plus(
    PhasePolynomial::term(2,Number(1,4),0,budget),budget).plus(
    PhasePolynomial::term(-2,Number(1,4),0,budget),budget);
 check(restored==expected);
 for(const char *unsupported:{"sqrt(3)","exp(1)","cosh(1)","sin(x)","1 m","[1,2]","cos(1 degree)"}) {
  restored=sample;check(!PhasePolynomial::tryFromExpression(calc(unsupported),restored,budget));check(restored==sample);
 }
 Number approximate(1,3);approximate.setApproximate();restored=sample;
 check(!PhasePolynomial::tryFromExpression(MathStructure(approximate),restored,budget));check(restored==sample);
 MathStructure angle(1),bare;bare.set(calculator.getFunctionById(FUNCTION_ID_COS),&angle,NULL);
 check(!PhasePolynomial::tryFromExpression(bare,restored,budget));check(restored==sample);
 MathStructure zeroPower(0);zeroPower.raise(0);
 check(!PhasePolynomial::tryFromExpression(zeroPower,restored,budget));check(restored==sample);
 PhaseBudget noWork(4096,4096,0);
 rejects<std::length_error>([&]{PhasePolynomial::tryFromExpression(calc("1"),restored,noWork);});check(restored==sample);
 PhaseBudget cancelled(4096,4096,1000,[]{return true;});
 rejects<std::runtime_error>([&]{sample.toExpression(cancelled);});
 rejects<std::runtime_error>([&]{sample.toExactString(cancelled,100000);});
 MathStructure deep(1);
 for(unsigned k=0;k<130;++k) {MathStructure parent;parent.setType(STRUCT_ADDITION);parent.addChild(deep);deep=parent;}
 restored=sample;
 rejects<std::length_error>([&]{PhasePolynomial::tryFromExpression(deep,restored,budget);});check(restored==sample);
 std::cout<<"PASS: "<<checks<<" exact phase expression checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

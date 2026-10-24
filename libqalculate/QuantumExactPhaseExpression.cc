// GPL-2.0-or-later; see COPYING.
#include "QuantumExactPhase.h"
#include "MathStructure.h"
#include "Calculator.h"
#include "BuiltinFunctions.h"
#include "Variable.h"
#include <stdexcept>
#include <vector>

namespace QuantumExact {
namespace {
bool gaussianRational(const Number &number) {
 return !number.isApproximate() && number.realPart().isRational() && number.imaginaryPart().isRational();
}
bool imaginaryExponent(const MathStructure &value,Number &angle,PhaseBudget &budget) {
 budget.charge();
 if(value.isNumber() && gaussianRational(value.number()) && value.number().realPart().isZero()) {
  budget.check(value.number());angle=value.number().imaginaryPart();return true;
 }
 if(!value.isMultiplication())return false;
 angle=1;bool imaginary=false;
 for(std::size_t k=0;k<value.size();++k) {
  budget.charge();const auto &factor=value[k];
  if(factor.isVariable() && factor.variable()==CALCULATOR->v_i && !imaginary)imaginary=true;
  else if(factor.isNumber() && gaussianRational(factor.number()) && factor.number().isReal()) {
   budget.check(factor.number());angle*=factor.number();budget.check(angle);
  } else return false;
 }
 return imaginary;
}
bool rationalRadians(const MathStructure &value,Number &angle,PhaseBudget &budget) {
 budget.charge();angle=1;bool radians=false;
 const auto factor=[&](const MathStructure &item) {
  budget.charge();
  if(item.isUnit() && item.unit()==CALCULATOR->getRadUnit() && !item.prefix() && !radians) {
   radians=true;return true;
  }
  if(!item.isNumber() || !gaussianRational(item.number()) || !item.number().isReal())return false;
  budget.check(item.number());angle*=item.number();budget.check(angle);return true;
 };
 if(value.isMultiplication()) {
  for(std::size_t k=0;k<value.size();++k)if(!factor(value[k]))return false;
 } else if(!factor(value))return false;
 return radians;
}
bool convert(const MathStructure &value,PhasePolynomial &output,PhaseBudget &budget,unsigned depth) {
 budget.charge();if(depth>128)throw std::length_error("Exact phase expression nesting limit exceeded");
 if(value.isNumber()) {
  if(!gaussianRational(value.number()))return false;
  output=PhasePolynomial::term(0,value.number(),0,budget);return true;
 }
 if(value.isVariable() && value.variable()==CALCULATOR->v_i) {
  Number imaginary(0);imaginary.setImaginaryPart(1);
  output=PhasePolynomial::term(0,imaginary,0,budget);return true;
 }
 if(value.isAddition() || value.isMultiplication()) {
  auto result=PhasePolynomial::term(0,value.isMultiplication()?1:0,0,budget);
  for(std::size_t k=0;k<value.size();++k) {
   PhasePolynomial child;if(!convert(value[k],child,budget,depth+1))return false;
   result=value.isAddition()?result.plus(child,budget):result.times(child,budget);
  }
  output=std::move(result);return true;
 }
 if(value.isFunction() && value.size()==1 &&
    (value.function()->id()==FUNCTION_ID_SIN || value.function()->id()==FUNCTION_ID_COS)) {
  Number angle;if(!rationalRadians(value[0],angle,budget))return false;
  Number positive(1,2),negative(1,2);
  if(value.function()->id()==FUNCTION_ID_SIN) {
   positive=0;positive.setImaginaryPart(-1,2);
   negative=0;negative.setImaginaryPart(1,2);
  }
  output=PhasePolynomial::term(angle,positive,0,budget).plus(
         PhasePolynomial::term(-angle,negative,0,budget),budget);return true;
 }
 if(value.isPower() && value.size()==2 && value[0].isVariable() && value[0].variable()==CALCULATOR->v_e) {
  Number angle;if(!imaginaryExponent(value[1],angle,budget))return false;
  output=PhasePolynomial::term(angle,1,0,budget);return true;
 }
 if(value.isPower() && value.size()==2 && value[1].isNumber() && gaussianRational(value[1].number())) {
  const Number &power=value[1].number();budget.check(power);
  if(value[0].isNumber() && gaussianRational(value[0].number()) && value[0].number()==2 &&
     (power==Number(1,2) || power==Number(-1,2))) {
   output=PhasePolynomial::term(0,0,power.isNegative()?Number(1,2):Number(1),budget);return true;
  }
  // Evaluated numeric powers normally collapse before this seam. Bounded
  // positive powers also occur when importing an exact result AST again.
  // Leave 0^0 and other unevaluated zero powers to the general evaluator.
  if(power.isInteger() && power>=1 && power<=64) {
   PhasePolynomial base;if(!convert(value[0],base,budget,depth+1))return false;
   auto result=PhasePolynomial::term(0,1,0,budget);
   unsigned exponent=static_cast<unsigned>(power.intValue());
   while(exponent) {
    budget.charge();if(exponent&1)result=result.times(base,budget);
    exponent>>=1;if(exponent)base=base.times(base,budget);
   }
   output=std::move(result);return true;
  }
 }
 return false;
}
MathStructure gaussianExpression(const Number &number) {
 MathStructure result(number.realPart());
 if(!number.imaginaryPart().isZero()) {
  // Printing a complex Number such as (1/7)i can emit "1 / 7i", which
  // reparses as 1/(7i). Keep i and its rational coefficient as AST factors.
  MathStructure imaginary(CALCULATOR->v_i);imaginary*=number.imaginaryPart();result+=imaginary;
 }
 return result;
}
std::string rationalText(const Number &number) {
 const auto &value=number.internalRational();
 std::vector<char> buffer(mpz_sizeinbase(mpq_numref(value),10)+mpz_sizeinbase(mpq_denref(value),10)+4);
 mpq_get_str(buffer.data(),10,value);return buffer.data();
}
std::string gaussianText(const Number &number) {
 auto real=rationalText(number.realPart());
 if(number.imaginaryPart().isZero())return real;
 return "("+real+"+("+rationalText(number.imaginaryPart())+")*i)";
}
}
bool PhasePolynomial::tryFromExpression(const MathStructure &value,PhasePolynomial &output,PhaseBudget &budget) {
 PhasePolynomial result;if(!convert(value,result,budget,0))return false;
 output=std::move(result);return true;
}
MathStructure PhasePolynomial::toExpression(PhaseBudget &budget) const {
 validate(budget);MathStructure result(0);
 for(const auto &term:terms_) {
  budget.charge();MathStructure coefficient=gaussianExpression(term.second.a);
  if(!term.second.b.isZero()) {
   MathStructure radical(2);radical.raise(Number(1,2));radical*=gaussianExpression(term.second.b);
   coefficient+=radical;
  }
  if(!term.first.isZero()) {
   MathStructure exponent(CALCULATOR->v_i);exponent*=term.first;
   MathStructure phase(CALCULATOR->v_e);phase.raise(exponent);coefficient*=phase;
  }
  result+=coefficient;
 }
 return result;
}
std::string PhasePolynomial::toExactString(PhaseBudget &budget,std::size_t maxCharacters) const {
 validate(budget);std::string result;
 auto append=[&](const std::string &text) {
  budget.charge();
  if(text.size()>maxCharacters-result.size())throw std::length_error("Exact phase text budget exceeded");
  result+=text;
 };
 if(terms_.empty())append("0");
 bool first=true;
 for(const auto &term:terms_) {
  budget.charge();if(!first)append("+");first=false;
  append("(");append(gaussianText(term.second.a));
  if(!term.second.b.isZero()) {append("+(");append(gaussianText(term.second.b));append(")*sqrt(2)");}
  append(")");
  if(!term.first.isZero()) {append("*exp(i*(");append(rationalText(term.first));append("))");}
 }
 return result;
}
}

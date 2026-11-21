// GPL-2.0-or-later; see COPYING.
#include "QuantumOrder.h"
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
#include "QuantumBinary.h"
#include "QuantumIndexed.h"
#include "Variable.h"
#include "support.h"
#ifdef HAVE_FLINT
#include <flint/flint.h>
#if __FLINT_RELEASE >= 30000
#include <flint/fmpq.h>
#include <flint/qqbar.h>
#endif
#endif
#include <array>
namespace {
#if defined(HAVE_FLINT) && __FLINT_RELEASE >= 30000
// Exact algebraic comparison is a fallback for concrete matrices whose
// radical entries did not simplify. Bound the degree, height and total work.
struct AlgebraicValue {
 qqbar_t value;
 AlgebraicValue() {qqbar_init(value);}
 ~AlgebraicValue() {qqbar_clear(value);}
 AlgebraicValue(const AlgebraicValue &)=delete;
 AlgebraicValue &operator=(const AlgebraicValue &)=delete;
};
bool rationalValue(qqbar_t out,const Number &n) {
 if(!n.isRational() || n.isApproximate())return false;
 const mpq_t &q=n.internalRational();
 if(mpz_sizeinbase(mpq_numref(q),2)>256 || mpz_sizeinbase(mpq_denref(q),2)>256)return false;
 fmpq_t f;fmpq_init(f);fmpq_set_mpq(f,q);qqbar_set_fmpq(out,f);fmpq_clear(f);return true;
}
bool algebraicValue(qqbar_t out,const MathStructure &term,unsigned &remaining) {
 if(!remaining || CALCULATOR->aborted() || term.isApproximate())return false;
 --remaining;
 if(term.isNumber()) {
  const Number &n=term.number();
  if(!n.hasImaginaryPart())return rationalValue(out,n);
  AlgebraicValue imaginary,unit;
  if(!rationalValue(out,n.realPart()) || !rationalValue(imaginary.value,n.imaginaryPart()))return false;
  qqbar_i(unit.value);qqbar_mul(imaginary.value,imaginary.value,unit.value);qqbar_add(out,out,imaginary.value);
  return true;
 }
 if(!term.size() || !algebraicValue(out,term[0],remaining))return false;
 if(term.isPower() && term.size()==2 && term[1].isNumber()) {
  const Number &power=term[1].number();
  if(power.isApproximate() || !power.isRational())return false;
  // The principal value of (-1)^(p/q) is the root exp(2*pi*i*p/(2q)).
  // Reduce the numerator before construction and retain the degree budget.
  if(term[0].isMinusOne() && power.denominator()<=64) {
   const mpq_t &fraction=power.internalRational();
   unsigned long order=2*power.denominator().uintValue();
   qqbar_root_of_unity(out,mpz_fdiv_ui(mpq_numref(fraction),order),order);return true;
  }
  if(power.denominator()>8 ||
     power.numerator()>16 || power.numerator() < -16 || (qqbar_is_zero(out) && !power.isPositive()))return false;
  if(qqbar_degree(out)*power.denominator().intValue()>64 || qqbar_height_bits(out)>256)return false;
  fmpq_t exponent;fmpq_init(exponent);fmpq_set_mpq(exponent,power.internalRational());
  qqbar_pow_fmpq(out,out,exponent);fmpq_clear(exponent);return true;
 }
 if(term.isFunction() && term.size()==1) {
  const std::string &name=term.function()->referenceName();
  if(name=="re")qqbar_re(out,out);
  else if(name=="im")qqbar_im(out,out);
  else if(name=="conj")qqbar_conj(out,out);
  else return false;
  return true;
 }
 if(!term.isAddition() && !term.isMultiplication())return false;
 for(size_t k=1;k<term.size();++k) {
  AlgebraicValue child;
  if(!algebraicValue(child.value,term[k],remaining) || !qqbar_binop_within_limits(out,child.value,128,512))return false;
  if(term.isAddition())qqbar_add(out,out,child.value);else qqbar_mul(out,out,child.value);
 }
 return true;
}
bool algebraicMatricesEqual(const MathStructure &a,const MathStructure &b,bool &equal) {
 if(!a.isMatrix() || !b.isMatrix() || a.rows()!=b.rows() || a.columns()!=b.columns())return false;
 unsigned remaining=2048;
 for(size_t r=1;r<=a.rows();++r)for(size_t c=1;c<=a.columns();++c) {
  const MathStructure &left=*a.getElement(r,c),&right=*b.getElement(r,c);
  if(left.equals(right))continue;
  AlgebraicValue x,y;
  if(!algebraicValue(x.value,left,remaining) || !algebraicValue(y.value,right,remaining))return false;
  if(!qqbar_equal(x.value,y.value)) {equal=false;return true;}
 }
 equal=true;return true;
}
#endif
// A probability function stays symbolic until the caller supplies its value.
class QuantumProbabilityCall: public MathFunction {
 public:
 QuantumProbabilityCall():MathFunction("qprobabilitycall",2) {}
 ExpressionItem *copy() const {return new QuantumProbabilityCall(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure size=raw[0],marked=raw[1];
  size.eval(eo);marked.eval(eo);
  if(size.equals(raw[0]) && marked.equals(raw[1]))return 0;
  out.set(this,&size,&marked,NULL);return 1;
 }
};
// These descriptors retain symbolic costs (including their argument lists)
// for Copy and substitution when an asymptotic comparison is undecidable.
class QuantumScalarUpdate: public MathFunction {
 public:
 QuantumScalarUpdate(const char *name):MathFunction(name,2) {}
 ExpressionItem *copy() const {return new QuantumScalarUpdate(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(referenceName()=="qscalarupdate") {
   if(!raw[0].isSymbolic() || raw[0].symbol().size()!=1 ||
      !std::isalpha(static_cast<unsigned char>(raw[0].symbol()[0]))) {
    CALCULATOR->error(true,"A scalar update requires a single letter as its target.",NULL);
   }
   return 0;
  }
  MathStructure rule=raw[0],current=raw[1];
  rule.eval(eo);current.eval(eo);
  if(!rule.isFunction() || rule.function()->referenceName()!="qscalarupdate" ||
     rule.size()!=2 || !rule[0].isSymbolic()) {
   CALCULATOR->error(true,"Expected a scalar update rule.",NULL);return 0;
  }
  if(current.isVector()) {CALCULATOR->error(true,"A scalar update requires a scalar input.",NULL);return 0;}
  if(rule[1].contains(rule[0]))out.set(CALCULATOR->getFunction("qreplace"),&rule[1],&rule[0],&current,NULL);
  else out=rule[1];
  out.eval(eo);
  if(out.isVector()) {CALCULATOR->error(true,"A scalar update must produce a scalar.",NULL);return 0;}
  return 1;
 }
};
class QuantumCostDescriptor: public MathFunction {
 public:
 QuantumCostDescriptor(const char *name,int arity):MathFunction(name,arity) {}
 ExpressionItem *copy() const {return new QuantumCostDescriptor(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(referenceName()!="qcostcall" || raw[0].isSymbolic() || raw[0].isUnknown())return 0;
  // A later binding can identify the head as a scalar factor or a graph.
  // Delegate to the same operation used for other named applications.
  MathStructure argument=raw[1];
  if(argument.size()==1 && (argument.isVector() || (argument.isFunction() && argument.function()->referenceName()=="vector")))
   argument=raw[1][0];
  out.set(CALCULATOR->getFunction("qnamedapplication"),&raw[0],&argument,NULL);return 1;
 }
};
bool polynomialSymbols(const MathStructure &term,const MathStructure *&variable) {
 if(term.isNumber())return term.number().isRational() && !term.number().isApproximate();
 if(term.isUnknown()) {
  if(!variable)variable=&term;
  return term.equals(*variable);
 }
 if(!term.isAddition() && !term.isMultiplication() && !term.isPower())return false;
 for(size_t i=0;i<term.size();++i)if(!polynomialSymbols(term[i],variable))return false;
 return true;
}
// Positive-coefficient monomials in up to three independent input sizes.
// On positive input sizes, roots and rational powers have exact growth exponents.
using CostPowers = std::array<Number,3>;
bool costPowers(const MathStructure &factor,CostPowers &powers,std::vector<std::string> &axes,const Number &scale) {
 const std::string operation=factor.isFunction() ? factor.function()->referenceName() : "";
 if(factor.isMultiplication() || operation=="qmul") {
  for(size_t i=0;i<factor.size();++i)if(!costPowers(factor[i],powers,axes,scale))return false;
  return true;
 }
 if(factor.isNumber())
  return factor.number().isRational() && !factor.number().isApproximate() && factor.number().isPositive();
 if(operation=="qsqrt")return costPowers(factor[0],powers,axes,scale/Number(2));
 if(factor.isPower() || operation=="qpower") {
  if(!factor[1].isNumber())return false;
  const Number &exponent=factor[1].number();
  if(!exponent.isRational() || exponent.isNegative() || exponent.isApproximate())return false;
  return costPowers(factor[0],powers,axes,scale*exponent);
 }
 if(!factor.isUnknown())return false;
 const std::string &name=factor.isSymbolic() ? factor.symbol() : factor.variable()->referenceName();
 if(name.size()!=1 || std::string("nmkN").find(name)==std::string::npos)return false;
 size_t axis=0;
 while(axis<axes.size() && axes[axis]!=name)++axis;
 if(axis==powers.size())return false;
 if(axis==axes.size())axes.push_back(name);
 powers[axis]+=scale;
 return true;
}
bool costSupport(const MathStructure &polynomial,std::vector<CostPowers> &terms,std::vector<std::string> &axes) {
 if(polynomial.isZero())return true;
 for(size_t i=0;i<(polynomial.isAddition() ? polynomial.size() : 1);++i) {
  CostPowers powers{};
  if(!costPowers(polynomial.isAddition() ? polynomial[i] : polynomial,powers,axes,Number(1)))return false;
  terms.push_back(powers);
 }
 return true;
}
// Set the second axis weight to one. A remaining inequality has the form
// x * first_axis_weight + y > 0. Intersect it with the open interval (low,high).
bool restrictCostWeights(const Number &x,const Number &y,Number &low,Number &high,bool &bounded) {
 if(x.isZero())return y.isPositive();
 Number cutoff=(Number(0)-y)/x;
 if(x.isPositive()) {
  if(cutoff>low)low=cutoff;
 } else if(!bounded || cutoff<high) {
  high=cutoff;bounded=true;
 }
 return !bounded || low<high;
}
bool multivariateCostBound(MathStructure &out,const MathStructure &cost,const MathStructure &bound) {
 std::vector<CostPowers> numerator,denominator;
 std::vector<std::string> axes;
 if(!costSupport(cost,numerator,axes) || !costSupport(bound,denominator,axes))return false;
 for(const auto &a:numerator) {
  // A separating weight makes this monomial grow faster than every
  // denominator monomial along (floor(t^x),floor(t),floor(t^z)).
  // Conversely, any unbounded ratio needs a separating weight: take
  // logarithms of the inputs where this term exceeds every bound term.
  // A strict gap persists under perturbation to strictly positive weights.
  Number low(0),high;bool bounded=false,feasible=true;
  std::vector<CostPowers> lower{{Number(0),Number(0),Number(1)}},upper;
  for(const auto &b:denominator) {
   if(CALCULATOR->aborted())return false;
   CostPowers d{a[0]-b[0],a[1]-b[1],a[2]-b[2]};
   if(d[2].isPositive())lower.push_back(d);
   else if(d[2].isNegative())upper.push_back(d);
   else if(!restrictCostWeights(d[0],d[1],low,high,bounded)) {feasible=false;break;}
  }
  // Eliminate z by requiring every strict lower bound on z (including
  // zero) to be smaller than every strict upper bound.
  for(const auto &u:upper) {
   if(!feasible)break;
   for(const auto &l:lower) {
    if(CALCULATOR->aborted())return false;
    if(!restrictCostWeights(u[0]*l[2]-l[0]*u[2],u[1]*l[2]-l[1]*u[2],low,high,bounded)) {feasible=false;break;}
   }
  }
  if(feasible) {out=0;return true;}
 }
 out=1;return true;
}
bool polynomialCostBound(MathStructure &out,MathStructure cost,MathStructure bound,const EvaluationOptions &eo) {
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 cost.eval(exact);bound.eval(exact);
 const MathStructure *variable=NULL;
 if(!polynomialSymbols(cost,variable) || !polynomialSymbols(bound,variable))return multivariateCostBound(out,cost,bound);
 if((!cost.isZero() && !cost.isRationalPolynomial()) || (!bound.isZero() && !bound.isRationalPolynomial()))return multivariateCostBound(out,cost,bound);
 MathStructure a=cost,b=bound;
 if(variable) {
  cost.coefficient(*variable,cost.degree(*variable),a);
  bound.coefficient(*variable,bound.degree(*variable),b);
 }
 // The cost model is for eventually nonnegative functions of input size.
 if(!a.isNumber() || !b.isNumber() || a.number().isNegative() || b.number().isNegative())return false;
 out=cost.isZero() || (!bound.isZero() && (!variable || cost.degree(*variable)<=bound.degree(*variable))) ? 1 : 0;
 return true;
}
// A binary word is identified by both its bits and its register width.
bool compareBitLabels(const MathStructure &left,const MathStructure &right,bool &equal,const EvaluationOptions &eo) {
 if(!isQuantumBitLabel(left) || !isQuantumBitLabel(right) || left.size()!=2 || right.size()!=2)return false;
 MathStructure a=left[0],aw=left[1],b=right[0],bw=right[1];
 if(validateQuantumBitLabel(a,aw,eo)!=QuantumBitLabelState::Concrete ||
    validateQuantumBitLabel(b,bw,eo)!=QuantumBitLabelState::Concrete)return false;
 equal=a.equals(b) && aw.equals(bw);return true;
}
// For every complex matrix M, M†M and MM† are positive semidefinite,
// including rectangular and rank-deficient M. This does not prove strictness.
const MathStructure *gramFactor(const MathStructure &value) {
 if(!value.isFunction() || value.size()!=2)return NULL;
 const std::string &name=value.function()->referenceName();
 if(name!="qmul" && name!="qadjacent")return NULL;
 for(unsigned i=0;i<2;++i) {
  const MathStructure &adjoint=value[i],&factor=value[1-i];
  if(adjoint.isFunction() && adjoint.function()->referenceName()=="qdag" && adjoint.size()==1 && adjoint[0].equals(factor))return &factor;
 }
 return NULL;
}
bool symbolicGram(const MathStructure &value,const EvaluationOptions &eo) {
 const MathStructure *factor=gramFactor(value);
 MathStructure rows,columns;
 return factor && quantumMatrixShape(*factor,rows,columns,eo);
}
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
// Hermitian Loewner order via exact Schur complements. A zero diagonal in a
// PSD matrix must have a zero row; testing this also handles singular matrices
// without a numerical eigenvalue tolerance or division by a zero pivot.
bool quantumMatrixOrder(MathStructure &out,MathStructure left,MathStructure right,int kind,const EvaluationOptions &eo) {
 if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before comparing quantum matrices.",NULL);return false;}
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 left.eval(exact);right.eval(exact);
 size_t n=left.isMatrix() ? left.rows() : right.isMatrix() ? right.rows() : 0;
 if(n==0 || n>64) {CALCULATOR->error(true,"Matrix order requires square matrices of matching dimension, at most 64.",NULL);return false;}
 for(MathStructure *value:{&left,&right}) {
  if(!value->isVector() && value->representsScalar()) {
   MathStructure scalar=*value;value->clearMatrix();value->resizeMatrix(n,n,m_zero);
   for(size_t r=0;r<n;++r)element(*value,r,r)=scalar;
  }
  if(!value->isMatrix() || value->rows()!=n || value->columns()!=n) {CALCULATOR->error(true,"Matrix order requires square matrices of matching dimension; scalars mean scalar times identity.",NULL);return false;}
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
   MathStructure other=element(*value,c,r),conjugated;
   conjugated.set(CALCULATOR->getFunction("conj"),&other,NULL);
   MathStructure difference=element(*value,r,c);difference-=conjugated;difference.eval(exact);
   if(!difference.isZero()) {CALCULATOR->error(true,"Matrix order requires provably Hermitian operands with finite entries.",NULL);return false;}
  }
 }
 MathStructure matrix;matrix.clearMatrix();matrix.resizeMatrix(n,n,m_zero);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  element(matrix,r,c)=(kind==0 || kind==2) ? element(right,r,c) : element(left,r,c);
  element(matrix,r,c)-=(kind==0 || kind==2) ? element(left,r,c) : element(right,r,c);
  element(matrix,r,c).eval(exact);
 }
 bool strict=kind<2;
 for(size_t k=0;k<n;++k) {
  if(CALCULATOR->aborted())return false;
  MathStructure pivot=element(matrix,k,k);pivot.eval(exact);
  if(pivot.representsNegative()) {out=0;return true;}
  if(pivot.isZero()) {
   if(strict) {out=0;return true;}
   for(size_t r=k+1;r<n;++r) {
    const MathStructure &value=element(matrix,k,r);
    if(value.isZero())continue;
    if(value.representsNonZero()) {out=0;return true;}
    CALCULATOR->error(true,"Matrix order cannot determine whether an off-diagonal entry is zero.",NULL);return false;
   }
   continue;
  }
  if(!pivot.representsPositive()) {CALCULATOR->error(true,"Matrix order cannot determine a pivot sign; supply concrete values without unresolved uncertainty.",NULL);return false;}
  for(size_t r=k+1;r<n;++r)for(size_t c=k+1;c<n;++c) {
   MathStructure term=element(matrix,r,k);term*=element(matrix,k,c);term/=pivot;
   element(matrix,r,c)-=term;element(matrix,r,c).eval(exact);
  }
 }
 out=1;return true;
}
bool setPair(const MathStructure &left,const MathStructure &right) {
 return left.isFunction() && right.isFunction() && left.function()->referenceName()=="qset" && right.function()->referenceName()=="qset";
}
bool unassignedScalarMultiple(const MathStructure &term) {
 if(term.isMultiplication()) {
  // A nonzero, known scale leaves the domain of an unassigned amplitude open.
  bool unassigned=false;
  for(size_t k=0;k<term.size();++k) {
   if(unassignedScalarMultiple(term[k]))unassigned=true;
   else if(term[k].containsUnknowns() || !term[k].representsNumber() || !term[k].representsNonZero())return false;
  }
  return unassigned;
 }
 if(term.isSymbolic())return true;
 if(!term.isUnknown())return false;
 auto variable=static_cast<UnknownVariable *>(term.variable());
 return !variable->assumptions() && variable->interval().isUndefined();
}
bool explicitImaginary(const MathStructure &term) {
 if(term.isNumber())return term.number().hasImaginaryPart();
 for(size_t k=0;k<term.size();++k)if(explicitImaginary(term[k]))return true;
 return false;
}
bool unboundComplexComparison(const MathStructure &left,const MathStructure &right) {
 if(left.isMatrix() && right.isMatrix() && left.rows()==right.rows() && left.columns()==right.columns()) {
  for(size_t row=1;row<=left.rows();++row)for(size_t col=1;col<=left.columns();++col)
   if(unboundComplexComparison(*left.getElement(row,col),*right.getElement(row,col)))return true;
  return false;
 }
 auto complexConstant=[](const MathStructure &term) {
  return !term.containsUnknowns() && (term.representsComplex() || (!term.representsReal() && explicitImaginary(term)));
 };
 return (unassignedScalarMultiple(right) && complexConstant(left)) ||
        (unassignedScalarMultiple(left) && complexConstant(right));
}
// Isolating a periodic function can introduce an arbitrary integer. It is
// bound in the general solution, while Copy would turn it into a free input.
bool introducesUnknown(const MathStructure &result,const MathStructure &operands) {
 if(result.isVariable() && !result.variable()->isKnown())return !operands.contains(result);
 for(size_t k=0;k<result.size();++k)if(introducesUnknown(result[k],operands))return true;
 return false;
}
// Infer the dimension before evaluation turns an unsized identity into a
// two-dimensional matrix. Grouping parentheses are absent at this stage.
bool inferProductIdentity(MathStructure &identity,const MathStructure &product) {
 if(!identity.isFunction() || identity.function()->referenceName()!="qimplicitidentity" || !product.isFunction())return false;
 const std::string &op=product.function()->referenceName();
 if(op!="qindexedsum" && ((op!="qadjacent" && op!="qmul") || !product.containsFunction(CALCULATOR->getFunction("qdag"))))return false;
 identity.set(CALCULATOR->getFunction("qidentitylike"),&product,NULL);return true;
}
// Real inequality isolation is invalid inside the modulus of a complex
// expression. Wait for its parameters before evaluating the comparison.
bool pendingComplexMagnitude(const MathStructure &term) {
 if(term.isFunction() && term.function()->referenceName()=="abs" && term.size()==1 &&
    !term[0].representsReal() && term[0].containsUnknowns())return true;
 for(size_t k=0;k<term.size();++k)if(pendingComplexMagnitude(term[k]))return true;
 return false;
}
class QuantumOrderFunction: public MathFunction {
 public:
 QuantumOrderFunction():MathFunction("qcompare",3) {}
 ExpressionItem *copy() const {return new QuantumOrderFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;args[2].eval(eo);
  bool equality=args[2].isNumber() && args[2].number()==4;
  if(equality || (args[2].isNumber() && args[2].number()==5))for(unsigned k=0;k<2;++k) {
   const auto &pattern=args[k];
   if(pattern.isFunction() && pattern.function()->referenceName()=="qopenblockcolumn" && pattern.size()==2) {
    out.set(CALCULATOR->getFunction("qmatchblockcolumn"),&pattern[0],&pattern[1],&args[1-k],&args[2],NULL);return 1;
   }
  }
  if(equality && (inferProductIdentity(args[0],args[1]) || inferProductIdentity(args[1],args[0]))) {
   out.set(this,&args[0],&args[1],&args[2],NULL);out.eval(eo);return 1;
  }
  args[0].eval(eo);
  MathStructure rows,columns;
  if(equality && quantumMatrixShape(args[0],rows,columns,eo) && columns.isOne())
   quantumResolveBasisDimension(args[1],rows);
  args[1].eval(eo);
  if(equality)for(unsigned k=0;k<2;++k) {
   if(args[k].containsFunction(CALCULATOR->getFunction("qkrausapply")) ||
      args[k].containsFunction(CALCULATOR->getFunction("qoperatorref"))) {
    if(args.equals(raw))return 0;
    out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
   }
  }
  // A named probability can be defined by the squared magnitude of a
  // pending sum. Keep one copy of its binder until the limits are known.
  if(equality)for(unsigned k=0;k<2;++k) {
   if(args[k].isSymbolic() && args[1-k].containsFunction(CALCULATOR->getFunction("qbars")) &&
      args[1-k].containsFunction(CALCULATOR->getFunction("qsum")))return 0;
  }
  // Keep piecewise definitions intact while their bit value or named
  // state is unresolved. Concrete substitutions use ordinary comparison.
  if(equality)for(unsigned k=0;k<2;++k) {
   if(!raw[1-k].isFunction() || raw[1-k].function()->referenceName()!="if")continue;
   if(args[k].isFunction() && args[k].function()->referenceName()=="qgeometricsum")return 0;
   if(args[k].containsFunction(CALCULATOR->getFunction("qnamedket")) ||
      args[k].containsFunction(CALCULATOR->getFunction("qketstate")))return 0;
   if(!args[k].containsUnknowns())continue;
   if(args[k].isFunction() && args[k].function()->referenceName()=="qbitlength")return 0;
   if(args[k].containsFunction(CALCULATOR->getFunction("qbitvalue")))return 0;
  }
  for(unsigned k=0;k<2;++k)if(args[k].isFunction() && args[k].function()->referenceName()=="qbigorder") {
   if(k==1 && args[2].isNumber() && (args[2].number()==4 || args[2].number()==5) && args[k].size()==1 &&
      polynomialCostBound(out,args[0],args[k][0],eo)) {
    if(args[2].number()==5)out=out.isZero() ? 1 : 0;
    return 1;
   }
   return 0;
  }
  if(equality && (args[0].containsFunction(CALCULATOR->getFunction("qinversefunction")) ||
                  args[1].containsFunction(CALCULATOR->getFunction("qinversefunction"))))return 0;
  if(equality && (args[0].containsFunction(CALCULATOR->getFunction("qspectralsum")) ||
                  args[1].containsFunction(CALCULATOR->getFunction("qspectralsum"))))return 0;
  // A cost function's argument vector does not make its value a matrix.
  MathFunction *costCall=CALCULATOR->getFunction("qcostcall");
  if(args[0].containsFunction(costCall) || args[1].containsFunction(costCall)) {
   if(args[0].equals(args[1]) && (equality || (args[2].isNumber() && args[2].number()==5))) {out=equality ? 1 : 0;return 1;}
   return 0;
  }
  if(equality && quantumMatrixShape(args[1],rows,columns,eo) && columns.isOne() &&
     quantumResolveBasisDimension(args[0],rows))args[0].eval(eo);
  {
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>5) {
    CALCULATOR->error(true,"Invalid quantum comparison kind.",NULL);return 0;
   }
   static const ComparisonType kinds[]={COMPARISON_LESS,COMPARISON_GREATER,COMPARISON_EQUALS_LESS,COMPARISON_EQUALS_GREATER,COMPARISON_EQUALS,COMPARISON_NOT_EQUALS};
   int kind=args[2].number().intValue();
   if(kind<4 && (pendingComplexMagnitude(args[0]) || pendingComplexMagnitude(args[1])))return 0;
   // A deferred graph domain is a set: keep equality intact for later
   // substitution instead of reducing it to a scalar difference.
   if(kind==4 || kind==5)for(unsigned k=0;k<2;++k) {
    if(!args[k].isFunction())continue;
    const auto &name=args[k].function()->referenceName();
    if(name=="qresidues" || name=="qunitsmod" || name=="qfunctionrange" || name=="qpreimage" || (name=="qfiniteapply" && !args[0].equals(args[1])) || name=="qregisterword" || name=="qsamplebitmatrix" || name=="qnamedapplication" || name=="qcomparisonliteral" || name=="qcomparisonzero")return 0;
   }
   // A free name can denote the entire matrix. Keep it available for
   // substitution instead of broadcasting it across the matrix entries.
   if(kind>=4)for(unsigned k=0;k<2;++k) {
    const MathStructure &other=args[1-k];
    bool namedKet=other.isFunction() && other.function()->referenceName()=="qketstate";
    if(!args[k].isMatrix() || !(other.isSymbolic() || namedKet))continue;
    if(args[0].equals(raw[0]) && args[1].equals(raw[1]))return 0;
    out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
   }
   bool equal=false;
   // A state family can be defined later. Keep each matrix on its own
   // side of the comparison and retain evaluated arguments for re-entry.
   if(kind>=4 && !args[0].equals(args[1]))for(const char *state:{"qstatecall","qstatecalls","qspectralket","qspectralentry","qketstate","qnamedket"}) {
    const auto function=CALCULATOR->getFunction(state);
    if(!args[0].containsFunction(function) && !args[1].containsFunction(function))continue;
    if(args[0].equals(raw[0]) && args[1].equals(raw[1]))return 0;
    out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
   }
   // An unassigned eigenvalue can later be complex. The generic real
   // default for unknown scalars cannot decide this quantum comparison.
   if(kind>=4 && unboundComplexComparison(args[0],args[1])) {
    if(args[0].equals(raw[0]) && args[1].equals(raw[1]))return 0;
    out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
   }
   // Preserve products with adjoints until the factors have concrete values.
   // Scalar comparison would rewrite the equality as a difference from zero.
   if(kind>=4 && gramFactor(args[0]) && gramFactor(args[1]) && !args[0].equals(args[1]))return 0;
   if(kind>=4)for(unsigned k=0;k<2;++k) {
    const MathStructure &identity=args[k], &product=args[1-k];
    if(identity.isFunction() && identity.function()->referenceName()=="qidentitylike" &&
       identity.size()==1 && identity[0].equals(product) && (gramFactor(product) || (product.isFunction() && product.function()->referenceName()=="qindexedsum")))return 0;
   }
   if(kind>=4 && (quantumComplexDomain(args[0]) || quantumComplexDomain(args[1]))) {
    if(quantumComplexDomain(args[0]) && quantumComplexDomain(args[1])) {
     out=(args[0].function()==args[1].function())==(kind==4) ? 1 : 0;return 1;
    }
    // Preserve an equation with a free set name or a symbolic predicate.
    return 0;
   }
   if(kind>=4 && setPair(args[0],args[1])) {
    if(!compareQuantumSets(args[0],args[1],equal,eo))return 0;
    out=(kind==4)==equal ? 1 : 0;return 1;
   }
   // A computed XOR ket may acquire its width from a later word binding.
   // Preserve the two operator/state expressions until that ket is resolved.
   if(kind>=4)for(unsigned k=0;k<2;++k) {
    if(args[k].containsFunction(CALCULATOR->getFunction("qcomputationalket")) &&
       args[k].containsFunction(CALCULATOR->getFunction("qoplus"))) {
     if(args[0].equals(raw[0]) && args[1].equals(raw[1]))return 0;
     out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
    }
   }
   if(kind>=4 && compareBitLabels(args[0],args[1],equal,eo)) {out=(kind==4)==equal ? 1 : 0;return 1;}
   if(args[1].isZero() && symbolicGram(args[0],eo) && (kind==0 || kind==3)) {out=kind==3 ? 1 : 0;return 1;}
   if(args[0].isZero() && symbolicGram(args[1],eo) && (kind==1 || kind==2)) {out=kind==2 ? 1 : 0;return 1;}
   if(args[2].number()<4 && (args[0].containsType(STRUCT_VECTOR,true)>0 || args[1].containsType(STRUCT_VECTOR,true)>0))
    return quantumMatrixOrder(out,raw[0],raw[1],args[2].number().intValue(),eo) ? 1 : 0;
   out=args[0];out.transform(kinds[kind],args[1]);out.eval(eo);
   if(kind>=4 && !out.isNumber() && introducesUnknown(out,args)) {
    if(args[0].equals(raw[0]) && args[1].equals(raw[1]))return 0;
    out.set(this,&args[0],&args[1],&args[2],NULL);return 1;
   }
#if defined(HAVE_FLINT) && __FLINT_RELEASE >= 30000
   if(kind>=4 && eo.approximation==APPROXIMATION_EXACT && !out.isNumber() &&
      algebraicMatricesEqual(args[0],args[1],equal))out=(kind==4)==equal ? 1 : 0;
#endif
   return 1;
  }
 }
};
class QuantumSymbolicEstimate: public MathFunction {
 public:
 QuantumSymbolicEstimate(const char *name):MathFunction(name,2) {}
 ExpressionItem *copy() const {return new QuantumSymbolicEstimate(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(referenceName()=="qestimate")return 0;
  MathStructure rule=raw[0],tolerance=raw[1];
  rule.eval(eo);tolerance.eval(eo);
  if(!rule.isFunction() || rule.function()->referenceName()!="qestimate" || rule.size()!=2 ||
     !rule[0].isVector() || rule[0].isMatrix() || !rule[0].size() || rule[0].size()>128) {
   CALCULATOR->error(true,"Expected a symbolic estimate with 1 to 128 exact operands.",NULL);return 0;
  }
  if(tolerance.isVector() || tolerance.isUndefined() || tolerance.containsInfinity() ||
     tolerance.representsNegative() || (tolerance.isNumber() && !tolerance.number().isReal())) {
   CALCULATOR->error(true,"An absolute tolerance must be finite, real and nonnegative.",NULL);return 0;
  }
  if(!tolerance.representsNonNegative() || !tolerance.representsFinite())return 0;
  bool pending=false;
  for(size_t i=1;i<rule[0].size();++i) {
   MathStructure equality=rule[0][i-1];
   equality.transform(COMPARISON_EQUALS,rule[0][i]);equality.eval(eo);
   if(equality.isZero()) {out=0;return 1;}
   if(!equality.isOne())pending=true;
  }
  MathStructure delta=rule[0][rule[0].size()-1];delta-=rule[1];
  MathStructure bound(CALCULATOR->getFunction("abs"),&delta,NULL);
  bound.transform(COMPARISON_EQUALS_LESS,tolerance);bound.eval(eo);
  if(bound.isZero()) {out=0;return 1;}
  if(pending || !bound.isOne())return 0;
  out=1;return 1;
 }
};
class QuantumDecimalMatch: public MathFunction {
 public:
 QuantumDecimalMatch():MathFunction("qdecimalmatch",4) {}
 ExpressionItem *copy() const {return new QuantumDecimalMatch(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure value=raw[0],target=raw[1];value.eval(eo);target.eval(eo);
  if(value.isVector() || target.isVector()) {
   CALCULATOR->error(true,"Decimal comparison requires scalar operands.",NULL);return 0;
  }
  if(value.containsUnknowns() || target.containsUnknowns()) {
   if(value.equals(raw[0]) && target.equals(raw[1]))return 0;
   out.set(this,&value,&target,&raw[2],&raw[3],NULL);return 1;
  }
  bool pending=false;
  for(unsigned k=0;k<2;++k) {
   MathStructure places=raw[k+2];places.eval(eo);
   if(!places.isInteger() || places.number()<(k ? -1 : 0) || places.number()>100) {
    CALCULATOR->error(true,"Decimal places must be between 0 and 100; -1 denotes an exact imaginary component.",NULL);return 0;
   }
   auto part=CALCULATOR->getFunction(k ? "im" : "re");
   MathStructure component(part,&value,NULL),expected(part,&target,NULL);
   if(!places.number().isNegative()) {
    MathStructure rounded(CALCULATOR->getFunction("round"),&component,&places,&m_zero,NULL);
    component=rounded;
   }
   component.transform(COMPARISON_EQUALS,expected);component.eval(eo);
   if(component.isZero()) {out=m_zero;return 1;}
   if(!component.isOne())pending=true;
  }
  if(pending)return 0;
  out=m_one;return 1;
 }
};
class QuantumEquivalence: public MathFunction {
 public:
 QuantumEquivalence():MathFunction("qiff",2) {}
 ExpressionItem *copy() const {return new QuantumEquivalence(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  bool truth[2]={false,false},pending=false;
  for(unsigned k=0;k<2;++k) {
   MathStructure predicate=raw[k];predicate.eval(eo);
   if(predicate.isZero() || predicate.isOne())truth[k]=predicate.isOne();
   else if(predicate.containsUnknowns() && !predicate.isVector())pending=true;
   else {CALCULATOR->error(true,"Logical equivalence requires two Boolean predicates.",NULL);return 0;}
  }
  if(pending)return 0;
  out=truth[0]==truth[1] ? 1 : 0;return 1;
 }
};
class QuantumEqualityChain: public MathFunction {
 public:
 QuantumEqualityChain():MathFunction("qequalchain",1) {}
 ExpressionItem *copy() const {return new QuantumEqualityChain(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(!raw[0].isVector() || raw[0].size()<3 || raw[0].size()>128) {
   CALCULATOR->error(true,"An equality chain requires 3 to 128 operands.",NULL);return 0;
  }
  MathStructure operands=raw[0],dimension;bool known=false,consistent=true;
  for(size_t k=1;k<operands.size();++k) {
   inferProductIdentity(operands[k],operands[k-1]);
   inferProductIdentity(operands[k-1],operands[k]);
  }
  for(size_t k=0;k<operands.size();++k) {
   if(CALCULATOR->aborted())return 0;
   operands[k].eval(eo);MathStructure rows,columns;
   // A projector complement supplies the dimension of its identity only
   // after the ket is bound. Keep the original chain during that interval.
   if(operands[k].containsFunction(CALCULATOR->getFunction("qimplicitidentity")) &&
      operands[k].containsFunction(CALCULATOR->getFunction("qnorm")))return 0;
   if(quantumMatrixShape(operands[k],rows,columns,eo) && columns.isOne()) {
    if(!known) {dimension=rows;known=true;}
    else if(!dimension.equals(rows))consistent=false;
   }
  }
  // All operands belong to the same equality, but only a consistent known
  // column dimension supplies context. Tensor factors keep their own widths.
  if(known && consistent)for(size_t k=0;k<operands.size();++k)
   if(quantumResolveBasisDimension(operands[k],dimension))operands[k].eval(eo);
  operands.childrenUpdated();
  auto pending=CALCULATOR->getFunction("qcomputationalket");
  bool deferred=pending && operands.containsFunction(pending)>0;
  for(size_t k=0;k<operands.size();++k)
   if(!operands[k].representsScalar() && operands[k].containsUnknowns())deferred=true;
  bool equal=true;
  if(!deferred)for(size_t k=1;k<operands.size();++k) {
   if(CALCULATOR->aborted())return 0;
   bool same=false;
   if(setPair(operands[k-1],operands[k])) {
    if(!compareQuantumSets(operands[k-1],operands[k],same,eo))deferred=true;
    else if(!same)equal=false;
    continue;
   }
   if(compareBitLabels(operands[k-1],operands[k],same,eo)) {if(!same)equal=false;continue;}
   MathStructure comparison=operands[k-1];comparison.transform(COMPARISON_EQUALS,operands[k]);comparison.eval(eo);
   if(comparison.isNumber() && comparison.number().isZero())equal=false;
   else if(!comparison.isNumber() || !comparison.number().isOne())deferred=true;
  }
  // Keep the shared context through Copy and later substitutions until the
  // chain is decidable; separate native comparisons would discard it.
  if(deferred) {
   if(operands.equals(raw[0]))return 0;
   out.set(this,&operands,NULL);return 1;
  }
  out=equal ? 1 : 0;return 1;
 }
};
}
void registerQuantumOrder(Calculator &calculator) {
 calculator.addFunction(new QuantumProbabilityCall());
 calculator.addFunction(new QuantumScalarUpdate("qscalarupdate"));
 calculator.addFunction(new QuantumScalarUpdate("qstepvalue"));
 calculator.addFunction(new QuantumCostDescriptor("qbigorder",1));
 calculator.addFunction(new QuantumCostDescriptor("qcostcall",2));
 calculator.addFunction(new QuantumCostDescriptor("qcostparam",1));
 calculator.addFunction(new QuantumDecimalMatch());
 calculator.addFunction(new QuantumSymbolicEstimate("qestimate"));
 calculator.addFunction(new QuantumSymbolicEstimate("qestimatewithin"));
 calculator.addFunction(new QuantumEquivalence());
 calculator.addFunction(new QuantumOrderFunction());
 calculator.addFunction(new QuantumEqualityChain());
}

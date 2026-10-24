// GPL-2.0-or-later; see COPYING.
#include "QuantumOperatorDomain.h"
#include "Calculator.h"
#include "Function.h"

namespace {
bool hasProperty(const MathStructure &value,const char *property) {
 return value.isFunction() && value.function()->referenceName()=="operatorparam" &&
        value.size()==3 && value[2].isSymbolic() && value[2].symbol()==property;
}
class QuantumOperatorParameter: public MathFunction {
public:
 QuantumOperatorParameter():MathFunction("operatorparam",3) {
  setArgumentDefinition(3,new TextArgument());
 }
 ExpressionItem *copy() const {return new QuantumOperatorParameter(*this);}
 bool representsScalar(const MathStructure&) const {return false;}
 bool representsNonMatrix(const MathStructure&) const {return false;}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
  const std::string property=raw[2].symbol();
  if(property!="unitary" && property!="hermitian" && property!="projector") {
   CALCULATOR->error(true,"Operator property must be unitary, hermitian, or projector.",NULL);return 0;
  }
  EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
  MathStructure dimension=raw[1];dimension.eval(exact);
  const bool deferredDimension=!dimension.isNumber() && dimension.representsScalar() && dimension.containsUnknowns();
  if(!deferredDimension && (!dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<=0)) {
   CALCULATOR->error(true,"Operator dimensions must be positive integers.",NULL);return 0;
  }
  MathStructure value=raw[0];value.eval(exact);
  if(value.isUnknown())return 0;
  if(!value.isMatrix() || value.rows()!=value.columns()) {
   CALCULATOR->error(true,"An operator substitution must be a square matrix.",NULL);return 0;
  }
  if(!deferredDimension && dimension.number()!=Number(static_cast<long>(value.rows()))) {
   CALCULATOR->error(true,"Operator substitution does not match its declared dimension.",NULL);return 0;
  }
  MathStructure adjoint;adjoint.set(CALCULATOR->getFunction("qdag"),&value,NULL);adjoint.eval(exact);
  MathStructure check;
  if(property=="unitary") {
   check.set(CALCULATOR->getFunction("qmul"),&adjoint,&value,NULL);check.eval(exact);
   MathStructure identity;identity.set(CALCULATOR->getFunction("qidentity"),&dimension,NULL);identity.eval(exact);
   check.transform(COMPARISON_EQUALS,identity);
  } else {check=adjoint;check.transform(COMPARISON_EQUALS,value);}
  check.eval(exact);
  if(check.isZero()) {CALCULATOR->error(true,"Matrix substitution violates its declared operator property.",NULL);return 0;}
  if(!check.isOne() || deferredDimension)return 0;
  if(property=="projector") {
   check.set(CALCULATOR->getFunction("qmul"),&value,&value,NULL);check.eval(exact);
   check.transform(COMPARISON_EQUALS,value);check.eval(exact);
   if(check.isZero()) {CALCULATOR->error(true,"Projector substitution must be idempotent.",NULL);return 0;}
   if(!check.isOne())return 0;
  }
  out=value;return 1;
 }
};
// Retain the operator even though its displayed product becomes identity.
// Substitution must still validate the premise of unitary cancellation.
class QuantumUnitaryIdentity: public MathFunction {
public:
 QuantumUnitaryIdentity():MathFunction("qunitaryidentity",2) {}
 ExpressionItem *copy() const {return new QuantumUnitaryIdentity(*this);}
 bool representsScalar(const MathStructure&) const {return false;}
 bool representsNonMatrix(const MathStructure&) const {return false;}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
  MathStructure property("unitary",true),domain;
  domain.set(CALCULATOR->getFunction("operatorparam"),&raw[0],&raw[1],&property,NULL);
  domain.eval(options);
  if(!domain.isMatrix())return 0;
  out.set(CALCULATOR->getFunction("qidentity"),&raw[1],NULL);out.eval(options);return 1;
 }
};
}
bool quantumOperatorDimension(const MathStructure &value,MathStructure &dimension,const EvaluationOptions &options) {
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 if(!((name=="operatorparam" && value.size()==3) || (name=="qunitaryidentity" && value.size()==2)))return false;
 dimension=value[1];EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;dimension.eval(exact);return true;
}
bool quantumOperatorAdjoint(const MathStructure &value,MathStructure &result) {
 if(!hasProperty(value,"hermitian") && !hasProperty(value,"projector"))return false;
 result=value;return true;
}
bool quantumOperatorProduct(const MathStructure &left,const MathStructure &right,MathStructure &result) {
 if(hasProperty(left,"projector") && left.equals(right)) {result=left;return true;}
 const MathStructure *domain=NULL;
 if(left.isFunction() && left.function()->referenceName()=="qdag" && left.size()==1 && left[0].equals(right))domain=&right;
 else if(right.isFunction() && right.function()->referenceName()=="qdag" && right.size()==1 && right[0].equals(left))domain=&left;
 if(!domain || !hasProperty(*domain,"unitary"))return false;
 result.set(CALCULATOR->getFunction("qunitaryidentity"),&(*domain)[0],&(*domain)[1],NULL);return true;
}
void registerQuantumOperatorDomain(Calculator &calculator) {
 calculator.addFunction(new QuantumOperatorParameter());
 calculator.addFunction(new QuantumUnitaryIdentity());
}

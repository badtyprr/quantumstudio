// GPL-2.0-or-later; see COPYING.
#include "QuantumIndexed.h"
#include "QuantumBasisDomain.h"
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include <string>
#include <utility>
#include <vector>
#include <stdexcept>
#include <cctype>
#include <set>
QuantumBitLabelState validateQuantumBitLabel(MathStructure &index,MathStructure &width,const EvaluationOptions &eo) {
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 index.eval(exact);width.eval(exact);
 bool symbolicIndex=!index.isNumber() && index.representsScalar() && index.containsUnknowns();
 bool symbolicWidth=!width.isNumber() && width.representsScalar() && width.containsUnknowns();
 if((!symbolicWidth && (!width.isNumber() || !width.number().isInteger() || width.number()<0)) ||
    (!symbolicIndex && (!index.isNumber() || !index.number().isInteger() || index.number()<0)) ||
    (!symbolicIndex && !symbolicWidth && !index.number().isZero() && Number(index.number().integerLength())>width.number())) {
  CALCULATOR->error(true,"Binary-string labels require a nonnegative integer width and a nonnegative integer value fitting that width.",NULL);
  return QuantumBitLabelState::Invalid;
 }
 return symbolicIndex || symbolicWidth ? QuantumBitLabelState::Symbolic : QuantumBitLabelState::Concrete;
}
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
// A scalar family keeps assignments even before its width is known. Slots and
// indices are metadata; only the width and assignment values are expressions.
const unsigned scalarProductLimit=1024;
const unsigned scalarProductAssignmentLimit=2048;
bool scalarProductNode(const MathStructure &value) {
 return value.isFunction() && value.function()->referenceName()=="qscalarproductsum" && value.size()==4;
}
bool scalarProductPrefix(const MathStructure &value) {
 if(!value.isSymbolic())return false;
 const std::string &prefix=value.symbol();
 if(prefix.size()<2 || prefix.size()>128 || prefix.back()!='_')return false;
 for(size_t k=0;k+1<prefix.size();++k)if(!((prefix[k]>='a' && prefix[k]<='z') || (prefix[k]>='A' && prefix[k]<='Z')))return false;
 return true;
}
bool pendingScalar(const MathStructure &value) {
 return !value.isNumber() && value.representsScalar() && value.containsUnknowns() &&
  !value.isUndefined() && !value.containsType(STRUCT_UNIT,false,true,true) &&
  !value.containsInterval(true,false,false,0,true);
}
bool pendingRegisterIndex(const MathStructure &value) {
 // Unknown scalar variables have no declared unit yet. A semantic unit query
 // returns -1 for them, which is uncertainty, not evidence of a physical unit.
 // Retain the integer constraint until substitution, rejecting explicit units.
 return !value.isNumber() && value.representsScalar() && value.containsUnknowns() &&
  !value.isUndefined() && !value.containsType(STRUCT_UNIT,true,true,true) &&
  !value.containsInterval(true,false,false,0,true);
}
// Validate the entire representation before evaluating or substituting it.
// Equal prefixes describe one family, including when supplied via both slots.
bool scalarProductArguments(MathStructure &arguments,const EvaluationOptions &eo,bool &pendingWidth) {
 if(arguments.size()!=4 || !scalarProductPrefix(arguments[0]) || !scalarProductPrefix(arguments[1]) ||
    !arguments[3].isVector() || arguments[3].size()%3 || arguments[3].size()>3*scalarProductAssignmentLimit)return false;
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 arguments[2].eval(exact);pendingWidth=pendingRegisterIndex(arguments[2]);
 if(!pendingWidth && (!arguments[2].isNumber() || !arguments[2].number().isInteger() ||
    arguments[2].number()<0))return false;
 std::set<std::pair<unsigned,Number>> seen;
 for(size_t k=0;k<arguments[3].size();k+=3) {
  if(CALCULATOR->aborted())return false;
  auto &slot=arguments[3][k];auto &index=arguments[3][k+1];auto &value=arguments[3][k+2];
  if(!slot.isNumber() || !slot.number().isInteger() || slot.number()<0 || slot.number()>1 ||
     !index.isNumber() || !index.number().isInteger() || index.number()<0)return false;
  if(arguments[0].equals(arguments[1]))slot=MathStructure(0);
  if(!seen.insert({static_cast<unsigned>(slot.number().intValue()),index.number()}).second)return false;
  value.eval(exact);
  if(value.isNumber()) {
   if(value.number().isInfinite(false) || value.number().isInterval(false))return false;
  } else if(!pendingScalar(value))return false;
 }
 arguments.childrenUpdated();return true;
}
int calculateScalarProduct(MathStructure &out,const MathStructure &raw,MathFunction *function,const EvaluationOptions &eo) {
 MathStructure arguments=raw;bool pendingWidth=false;
 if(!scalarProductArguments(arguments,eo,pendingWidth)) {
  CALCULATOR->error(true,"Indexed scalar products require literal families, a nonnegative integer width, and at most 2048 unique finite dimensionless scalar assignments (without intervals).",NULL);return 0;
 }
 const MathStructure *values[2][scalarProductLimit]={};
 for(size_t k=0;k<arguments[3].size();k+=3)if(arguments[3][k+1].number()<Number(scalarProductLimit))
  values[arguments[3][k].number().intValue()][arguments[3][k+1].number().intValue()]=&arguments[3][k+2];
 // The finite expansion bound never restricts valid widths or assignment keys.
 // Retain large indices exactly, and convert only a bounded concrete width.
 bool pending=pendingWidth || arguments[2].number()>Number(scalarProductLimit);
 unsigned width=pending ? 0 : arguments[2].number().intValue();
 unsigned second=arguments[0].equals(arguments[1]) ? 0 : 1;
 for(unsigned k=0;k<width;++k)for(unsigned slot:{0u,second})
  pending=pending || !values[slot][k] || !values[slot][k]->isNumber();
 if(pending) {
  if(arguments.equals(raw))return 0;
  out.set(function,&arguments[0],&arguments[1],&arguments[2],NULL);out.addChild(arguments[3]);return 1;
 }
 Number sum(0);
 for(unsigned k=0;k<width;++k) {
  if(CALCULATOR->aborted())return 0;
  Number term=values[0][k]->number();
  if(!term.multiply(values[second][k]->number()) || !sum.add(term) || sum.isInfinite(false)) {
   CALCULATOR->error(true,"Indexed scalar product could not produce a finite result.",NULL);return 0;
  }
 }
 out=MathStructure(sum);return 1;
}
// Labels passed here have already been validated and canonicalized.
enum class SetEquality { Equal, Different, Unknown };
SetEquality setEquality(const MathStructure &left,const MathStructure &right) {
 if(left.equals(right))return SetEquality::Equal;
 bool leftTuple=left.isFunction() && left.function()->referenceName()=="qtuple";
 bool rightTuple=right.isFunction() && right.function()->referenceName()=="qtuple";
 if(leftTuple && rightTuple) {
  if(left[0].size()!=right[0].size())return SetEquality::Different;
  bool unknown=false;
  for(size_t k=0;k<left[0].size();++k) {
   SetEquality part=setEquality(left[0][k],right[0][k]);
   if(part==SetEquality::Different)return part;
   unknown=unknown || part==SetEquality::Unknown;
  }
  return unknown ? SetEquality::Unknown : SetEquality::Equal;
 }
 bool leftLabel=left.isFunction() && left.function()->referenceName()=="qbitlabel";
 bool rightLabel=right.isFunction() && right.function()->referenceName()=="qbitlabel";
 if(leftLabel && rightLabel)return SetEquality::Different;
 if(leftLabel || rightLabel || leftTuple || rightTuple) {
  const MathStructure &scalar=(leftLabel || leftTuple) ? right : left;
  if((leftLabel || leftTuple) && (rightLabel || rightTuple))return SetEquality::Different;
  return scalar.containsUnknowns() ? SetEquality::Unknown : SetEquality::Different;
 }
 ComparisonResult comparison=left.compare(right);
 if(comparison==COMPARISON_RESULT_EQUAL)return SetEquality::Equal;
 if(comparison==COMPARISON_RESULT_LESS || comparison==COMPARISON_RESULT_GREATER || comparison==COMPARISON_RESULT_NOT_EQUAL)return SetEquality::Different;
 return SetEquality::Unknown;
}
bool domainExpression(const MathStructure &value) {
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 return name=="qset" || name=="qfunctionrange" || name=="qpreimage" || name=="qbitstrings" || name=="qindexrange" || name=="qcartesian" || name=="qcartesianpower" || name=="qwordpower" || name=="qsetimage" || name=="qsetfilter" || name=="qsetunion" || name=="qsetintersect" || name=="qsetdiff";
}
bool collectionExpression(const MathStructure &value) {
 if(value.isVector() || domainExpression(value))return true;
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 return name=="vector" || name=="union" || name=="intersect" || name=="setdiff" || name=="unique" || name=="select" || name=="qdomainresult";
}
bool pendingDomain(const MathStructure &value) {
 return value.isSymbolic() || (value.isVariable() && !value.variable()->isKnown()) || domainExpression(value);
}
// Keep tuples distinct from vectors/matrices, including the zero-length tuple.
bool canonicalSetElement(MathStructure &value,const EvaluationOptions &eo,bool &pending,unsigned depth=0) {
 if(depth>32)return false;
 if(value.isFunction() && value.function()->referenceName()=="qtuple") {
  if(value.size()==1 && value[0].isFunction() && value[0].function()->referenceName()=="vector") {
   MathStructure fields;fields.clearVector();
   for(size_t k=0;k<value[0].size();++k)fields.addChild(value[0][k]);
   value[0]=fields;
  }
  if(value.size()!=1 || !value[0].isVector() || value[0].size()>32)return false;
  for(size_t k=0;k<value[0].size();++k)if(!canonicalSetElement(value[0][k],eo,pending,depth+1))return false;
  value.childrenUpdated();return true;
 }
 if(value.isFunction() && value.function()->referenceName()=="qbitlabel") {
  if(value.size()!=2)return false;
  MathStructure index=value[0],width=value[1];
  QuantumBitLabelState state=validateQuantumBitLabel(index,width,eo);
  pending=pending || state==QuantumBitLabelState::Symbolic;
  if(state==QuantumBitLabelState::Concrete) {auto function=value.function();value.set(function,&index,&width,NULL);}
  return state!=QuantumBitLabelState::Invalid;
 }
 value.eval(eo);
 return value.representsScalar() && !value.isUndefined();
}
enum class DomainState { Invalid, Pending, Finite };
bool normalizeSetEntries(MathStructure &members,const EvaluationOptions &eo,bool &pending) {
 for(size_t k=0;k<members.size();++k)if(!canonicalSetElement(members[k],eo,pending))return false;
 for(size_t k=members.size();k>0;--k)for(size_t j=0;j<k-1;++j)if(setEquality(members[k-1],members[j])==SetEquality::Equal) {members.delChild(k);break;}
 return true;
}
bool unresolvedSetEquality(const MathStructure &members) {
 for(size_t k=0;k<members.size();++k)for(size_t j=0;j<k;++j)if(setEquality(members[k],members[j])==SetEquality::Unknown)return true;
 return false;
}
// A power in a set-domain position can denote words over an alphabet.
void evaluateDomain(const MathStructure &raw,MathStructure &members,const EvaluationOptions &eo) {
 if(raw.size()==2 && (raw.isPower() || (raw.isFunction() && raw.function()->referenceName()=="qpower")) &&
    (pendingDomain(raw[0]) || collectionExpression(raw[0]))) {
  members.set(CALCULATOR->getFunction("qwordpower"),&raw[0],&raw[1],NULL);
 } else members=raw;
 members.eval(eo);
}
DomainState finiteDomain(const MathStructure &raw,MathStructure &members,const EvaluationOptions &eo) {
 evaluateDomain(raw,members,eo);
 if(members.isFunction() && members.function()->referenceName()=="qset" && members.size()==1) {MathStructure entries=members[0];members=entries;}
 if(!members.isVector() && collectionExpression(raw) && !domainExpression(members))members.transform(STRUCT_VECTOR);
 if(pendingDomain(members))return DomainState::Pending;
 if(!members.isVector() || members.size()>1024)return DomainState::Invalid;
 bool pending=false;
 if(!normalizeSetEntries(members,eo,pending))return DomainState::Invalid;
 return pending ? DomainState::Pending : DomainState::Finite;
}
// A register family retains bit assignments made before its width is known.
// The flat binding list contains alternating numeric indices and bit values.
// Numeric keys cannot be accidentally replaced along with a symbolic bit.
bool registerBitIndex(const MathStructure &label,const std::string &prefix,Number &index) {
 if(!label.isSymbolic() || label.symbol().compare(0,prefix.size(),prefix)!=0)return false;
 std::string suffix=label.symbol().substr(prefix.size());
 if(suffix.empty() || (suffix.size()>1 && suffix.front()=='0'))return false;
 for(char c:suffix)if(c<'0' || c>'9')return false;
 ParseOptions decimal;decimal.base=10;index=Number(suffix,decimal);
 return index.isInteger() && index>=0;
}
int quantumIndexBinder(const MathStructure &value,const MathStructure &index);
bool tensorSeriesNode(const MathStructure &value);
bool registerSumNode(const MathStructure &value) {
 return value.isFunction() && value.function()->referenceName()=="qregistersum" && value.size()==7;
}
bool hasRegisterSum(const MathStructure &value) {
 auto function=CALCULATOR->getFunction("qregistersum");
 return function && value.containsFunction(function,true,true);
}
bool bindRegisterBit(MathStructure &value,const MathStructure &label,const MathStructure &bit,bool scoped=false) {
 // A series owns ordered substitutions in its history. Mutating the original
 // factor here as well would apply an indexed assignment twice on expansion.
 if(tensorSeriesNode(value) || registerSumNode(value))return false;
 bool changed=false;
 const bool samples=value.isFunction() && value.function()->referenceName()=="qfamilymembers";
 if(value.isFunction() && (samples || value.function()->referenceName()=="qregisterfamily" || value.function()->referenceName()=="qregisterword") && value.size()==4 && value[0].isSymbolic()) {
  Number index;
  if(registerBitIndex(label,value[0].symbol(),index) && value[3].isVector() && value[3].size()%2==0) {
   // Do not claim an unrelated label when concrete bounds already exclude it.
   if(samples && (index<1 || (value[1].isNumber() && index>value[1].number())))return false;
   if(!samples && value[1].isNumber() && value[2].isNumber() &&
      (Number(index)>value[1].number() || Number(index)<value[2].number()))return false;
   for(size_t k=0;k<value[3].size();k+=2)if(value[3][k].isNumber() && value[3][k].number()==Number(index)) {
    // This label was already substituted. Later replacements act only on
    // free occurrences in its stored value, not on this metadata key.
    return false;
   }
   if(!samples && value[3].size()>=256) {CALCULATOR->error(true,"A register family supports at most 128 supplied bit values.",NULL);return false;}
   value[3].addChild(MathStructure(Number(index)));value[3].addChild(bit);value.childrenUpdated();return true;
  }
 }
 int bound=scoped ? quantumIndexBinder(value,label) : -1;
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  changed=bindRegisterBit(value[k],label,bit,scoped) || changed;
 }
 if(changed)value.childrenUpdated();return changed;
}
// These operations bind an index in their first argument only.
int quantumBinderPosition(const MathStructure &value) {
 int bound=-1;
 if(value.isFunction() && value.size()==5 && value.function()->referenceName()=="qtensorseries")bound=3;
 if(value.isFunction() && value.size()==6 && value.function()->referenceName()=="qboundtensorseries")bound=3;
 if(value.isFunction() && value.size()==4) {
  const std::string &name=value.function()->referenceName();
  if(name=="qtensorproduct" || name=="qblocksum" || name=="qoraclefunction" || name=="qsum" || name=="sum" || name=="product")bound=3;
 }
 if(value.isFunction() && value.size()==3 && (value.function()->referenceName()=="qphasefunction" || value.function()->referenceName()=="qsequence" || value.function()->referenceName()=="qsumset" || value.function()->referenceName()=="qsetimage" || value.function()->referenceName()=="qsetfilter"))bound=2;
 return bound;
}
int quantumIndexBinder(const MathStructure &value,const MathStructure &index) {
 int bound=quantumBinderPosition(value);
 return bound>=0 && value[bound].equals(index) ? bound : -1;
}
bool hasScalarProduct(const MathStructure &value) {
 auto function=CALCULATOR->getFunction("qscalarproductsum");
 return function && value.containsFunction(function,true,true);
}
bool tensorSeriesNode(const MathStructure &value) {
 return value.isFunction() && ((value.size()==5 && value.function()->referenceName()=="qtensorseries") ||
  (value.size()==6 && value.function()->referenceName()=="qboundtensorseries"));
}
bool hasTensorSeries(const MathStructure &value) {
 for(const char *name:{"qtensorseries","qboundtensorseries"}) {
  auto function=CALCULATOR->getFunction(name);
  if(function && value.containsFunction(function,true,true))return true;
 }
 return false;
}
bool tensorReplacementHistory(const MathStructure &raw,MathStructure &history) {
 history=raw;
 if(raw.isFunction() && raw.function()->referenceName()=="vector") {
  history.clearVector();for(size_t k=0;k<raw.size();++k)history.addChild(raw[k]);
 }
 if(!history.isVector() || history.size()%2 || history.size()>4096)return false;
 for(size_t k=0;k<history.size();k+=2)if(!history[k].isSymbolic() && (!history[k].isVariable() || history[k].variable()->isKnown()))return false;
 return true;
}
bool scalarExpression(const MathStructure &value,unsigned depth=0) {
 if(depth>64)return false;
 if(value.representsScalar())return true;
 if(value.isAddition() || value.isMultiplication() || value.isPower()) {
  for(size_t k=0;k<value.size();++k)if(!scalarExpression(value[k],depth+1))return false;
  return value.size()>0;
 }
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 // An indexed label resolves to a scalar symbol. Series history checks below
 // separately reject assignments that could make an implicit label a matrix.
 if(name=="qindexedlabel" && value.size()==3)return true;
 if(name=="qsqrt" && value.size()==1)return scalarExpression(value[0],depth+1);
 if(value.size()==2 && (name=="qadd" || name=="qsub" || name=="qmul" || name=="qadjacent" || name=="qpower"))
  return scalarExpression(value[0],depth+1) && scalarExpression(value[1],depth+1);
 return false;
}
bool implicitIndexedName(const MathStructure &value,const MathStructure &key,unsigned depth=0) {
 if(depth>64)return true; // Conservatively retain uncertainty beyond this view.
 if(value.isFunction() && value.function()->referenceName()=="qindexedlabel" && value.size()==3 &&
    value[0].isSymbolic() && value[2].isSymbolic() && value[1].containsUnknowns()) {
  std::string name;
  if(key.isSymbolic())name=key.symbol();
  else if(key.isVariable() && !key.variable()->isKnown())name=key.variable()->referenceName();
  const std::string &prefix=value[0].symbol(),&suffix=value[2].symbol();
  if(name.size()>prefix.size()+suffix.size() && name.compare(0,prefix.size(),prefix)==0 &&
     name.compare(name.size()-suffix.size(),suffix.size(),suffix)==0) {
   std::string index=name.substr(prefix.size(),name.size()-prefix.size()-suffix.size());
   size_t start=index[0]=='-' ? 1 : 0;
   if(start<index.size() && index.find_first_not_of("0123456789",start)==std::string::npos &&
      (index[start]!='0' || index.size()==1))return true;
  }
 }
 for(size_t k=0;k<value.size();++k)if(implicitIndexedName(value[k],key,depth+1))return true;
 return false;
}
bool tensorSeriesBounds(const MathStructure &raw,MathStructure &first,MathStructure &last,
                        MathStructure &step,MathStructure &count,const EvaluationOptions &eo,bool report) {
 auto invalid=[&](const char *message) {if(report)CALCULATOR->error(true,message,NULL);return false;};
 if((raw.size()!=5 && raw.size()!=6) || (!raw[3].isSymbolic() && !raw[3].isVariable()) ||
    (raw[3].isVariable() && raw[3].variable()->isKnown()))return invalid("A tensor series index must be a symbolic variable.");
 first=raw[1];last=raw[2];step=raw[4];first.eval(eo);last.eval(eo);step.eval(eo);
 if(!step.isNumber() || (step.number()!=1 && step.number()!=-1))return invalid("A tensor series direction must be 1 or -1.");
 for(const auto *endpoint:{&first,&last}) {
  if((endpoint->isNumber() && !endpoint->number().isInteger()) ||
     (!endpoint->isNumber() && (!endpoint->representsScalar() || !endpoint->containsUnknowns())))
   return invalid("Tensor series endpoints must be integers.");
 }
 count=last;count-=first;count*=step;count+=m_one;count.eval(eo);
 if((count.isNumber() && (!count.number().isInteger() || count.number()<0)) ||
    (!count.isNumber() && (!count.representsScalar() || !count.containsUnknowns())))
  return invalid("Tensor series bounds contradict their direction.");
 return true;
}
// Resolve generated scalar names without evaluating their surrounding sum or
// domain. Unexpanded series own their original body and replacement history.
void resolveIndexedLabels(MathStructure &value,const EvaluationOptions &eo) {
 if(tensorSeriesNode(value) || registerSumNode(value))return;
 for(size_t k=0;k<value.size();++k)resolveIndexedLabels(value[k],eo);
 value.childrenUpdated();
 if(value.isFunction() && value.function()->referenceName()=="qindexedlabel" && value.size()==3) {
  MathStructure resolved=value;resolved.eval(eo);
  if(resolved.isSymbolic())value=resolved;
 }
}
bool scalarProductKey(const MathStructure &value,const MathStructure &label,unsigned &slot,Number &index) {
 if(!scalarProductNode(value) || !scalarProductPrefix(value[0]) || !scalarProductPrefix(value[1]) ||
    !value[3].isVector() || value[3].size()%3)return false;
 std::string name;
 if(label.isSymbolic())name=label.symbol();
 else if(label.isVariable() && !label.variable()->isKnown())name=label.variable()->referenceName();
 else return false;
 for(slot=0;slot<2;++slot) {
  const std::string &prefix=value[slot].symbol();
  if(name.compare(0,prefix.size(),prefix)!=0)continue;
  std::string suffix=name.substr(prefix.size());
  if(suffix.empty() || (suffix.size()>1 && suffix.front()=='0'))continue;
  bool valid=true;for(char c:suffix)if(c<'0' || c>'9') {valid=false;break;}
  if(!valid)continue;
  ParseOptions decimal;decimal.base=10;index=Number(suffix,decimal);
  if(value[2].isNumber() && value[2].number().isInteger() && Number(index)>=value[2].number())return false;
  if(value[0].equals(value[1]))slot=0;
  for(size_t k=0;k<value[3].size();k+=3)
   if(value[3][k].isNumber() && value[3][k+1].isNumber() &&
      (value[0].equals(value[1]) || value[3][k].number()==Number(slot)) && value[3][k+1].number()==Number(index))return false;
  return true;
 }
 return false;
}
// Count implicit family labels as free occurrences, but not metadata or bound
// names. The same policy drives substitution and capture avoidance.
bool scalarSymbolEqual(const MathStructure &value,const MathStructure &name) {
 if(value.equals(name))return true;
 if(value.isSymbolic() && name.isVariable() && !name.variable()->isKnown())return value.symbol()==name.variable()->referenceName();
 if(name.isSymbolic() && value.isVariable() && !value.variable()->isKnown())return name.symbol()==value.variable()->referenceName();
 return false;
}
bool scalarProductFree(const MathStructure &value,const MathStructure &name,bool scalarNames=false) {
 if(scalarNames ? scalarSymbolEqual(value,name) : value.equals(name))return true;
 if(value.isVariable() && value.variable()->isKnown() && (hasScalarProduct(value) || hasTensorSeries(value)))
  return scalarProductFree(static_cast<KnownVariable *>(value.variable())->get(),name);
 if(scalarProductNode(value)) {
  unsigned slot;Number index;if(scalarProductKey(value,name,slot,index))return true;
  if(scalarProductFree(value[2],name,true))return true;
  if(value[3].isVector())for(size_t k=2;k<value[3].size();k+=3)if(scalarProductFree(value[3][k],name,true))return true;
  return false;
 }
 int bound=quantumIndexBinder(value,name);
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  if(scalarProductFree(value[k],name,scalarNames))return true;
 }
 return false;
}
// A register binds a family, including labels that only become explicit after
// its width is substituted. Rename the family before replaying external values
// so a free y_0 introduced by x_0 -> y_0 is never captured by a local y register.
bool containsFamilyPrefix(const MathStructure &value,const std::string &prefix) {
 if(value.isSymbolic() && value.symbol().compare(0,prefix.size(),prefix)==0)return true;
 if(value.isVariable()) {
  if(value.variable()->referenceName().compare(0,prefix.size(),prefix)==0)return true;
  if(value.variable()->isKnown())return containsFamilyPrefix(static_cast<KnownVariable *>(value.variable())->get(),prefix);
 }
 for(size_t k=0;k<value.size();++k)if(containsFamilyPrefix(value[k],prefix))return true;
 return false;
}
void replaceQuantumIndex(MathStructure &,const MathStructure &,const MathStructure &,bool,bool,bool);
// A nested scalar binder can shadow one component of an outer register. Give
// it a local name before traversing the surrounding family; its range remains
// in the outer scope, just as for ordinary scalar-index substitution.
bool protectRegisterComponentBinder(MathStructure &value,const MathStructure &prefix) {
 int position=quantumBinderPosition(value);Number index;
 if(position<0 || !registerBitIndex(value[position],prefix.symbol(),index))return true;
 unsigned serial=0;MathStructure local;
 do {
  if(CALCULATOR->aborted())return false;
  unsigned code=serial++;std::string name="__qregister_local_";
  do {name+=char('a'+code%26);code/=26;}while(code);
  local=MathStructure(name,true);
 }while(value.contains(local) || scalarProductFree(value,local) || implicitIndexedName(value,local));
 MathStructure old=value[position];
 replaceQuantumIndex(value[0],old,local,false,true,false);
 value[position]=local;value.childrenUpdated();return true;
}
void renameRegisterFamily(MathStructure &value,const MathStructure &old,const MathStructure &fresh) {
 if(registerSumNode(value) && value[4].equals(old)) {
  // The nested body shadows this declaration. Its domain and history values
  // still live in the surrounding scope; history keys are immutable metadata.
  for(unsigned k:{1u,2u,3u,5u})renameRegisterFamily(value[k],old,fresh);
  for(size_t k=1;k<value[6].size();k+=2)renameRegisterFamily(value[6][k],old,fresh);
  value.childrenUpdated();return;
 }
 if(!protectRegisterComponentBinder(value,old))return;
 Number index;
 if(registerBitIndex(value,old.symbol(),index)) {
  value=MathStructure(fresh.symbol()+value.symbol().substr(old.symbol().size()),true);return;
 }
 if(value.isFunction()) {
  const std::string &name=value.function()->referenceName();
  if((name=="qregisterfamily" || name=="qindexedlabel") && value.size() && value[0].equals(old))value[0]=fresh;
  if(scalarProductNode(value))for(unsigned k:{0u,1u})if(value[k].equals(old))value[k]=fresh;
 }
 for(size_t k=0;k<value.size();++k) {
  if(registerSumNode(value) && (k==4 || k==6)) {
   if(k==6)for(size_t j=1;j<value[k].size();j+=2)renameRegisterFamily(value[k][j],old,fresh);
   continue;
  }
  renameRegisterFamily(value[k],old,fresh);
 }
 value.childrenUpdated();
}
bool freshRegisterFamily(MathStructure &value,const MathStructure &key,const MathStructure &replacement) {
 if(!scalarProductPrefix(value[4]))return false;
 unsigned serial=0;std::string prefix;
 do {
  if(CALCULATOR->aborted())return false;
  unsigned code=serial++;prefix="qboundregister";
  do {prefix+=char('a'+code%26);code/=26;}while(code);
  prefix+='_';
 }while(containsFamilyPrefix(value,prefix) || containsFamilyPrefix(key,prefix) || containsFamilyPrefix(replacement,prefix));
 MathStructure fresh(prefix,true),old=value[4];
 renameRegisterFamily(value[0],old,fresh);value[4]=fresh;value.childrenUpdated();return true;
}
// Substitute a free index without capturing a nested finite-product/sum index.
void replaceQuantumIndex(MathStructure &value,const MathStructure &index,const MathStructure &replacement,bool preserveComplexDomain=false,bool scalarNames=false,bool genericReplacement=false) {
 if(preserveComplexDomain && value.isFunction() && value.function()->referenceName()=="complexparam")return;
 if(scalarNames ? scalarSymbolEqual(value,index) : value.equals(index)) {value=replacement;return;}
 if(genericReplacement && !scalarNames && !hasScalarProduct(value) && !hasScalarProduct(replacement) && !hasTensorSeries(value) && !hasRegisterSum(value)) {
  value.replace(index,replacement,false,false,index.containsUnknowns());return;
 }
 if(value.isVariable() && value.variable()->isKnown() && (hasScalarProduct(value) || hasTensorSeries(value) || hasRegisterSum(value))) {
  MathStructure body=static_cast<KnownVariable *>(value.variable())->get();
  replaceQuantumIndex(body,index,replacement,preserveComplexDomain,scalarNames,genericReplacement);value=body;return;
 }
 if(registerSumNode(value)) {
  MathStructure history;
  if(!tensorReplacementHistory(value[6],history) || !freshRegisterFamily(value,index,replacement)) {
   CALCULATOR->error(true,"Invalid register sum declaration or replacement history.",NULL);return;
  }
  for(unsigned k:{1u,2u,3u,5u})replaceQuantumIndex(value[k],index,replacement,preserveComplexDomain,scalarNames,genericReplacement);
  if(genericReplacement) {
   if(history.size()==4096) {CALCULATOR->error(true,"A register sum supports at most 2048 deferred replacements.",NULL);return;}
   history.addChild(index);history.addChild(replacement);
  } else {
   replaceQuantumIndex(value[0],index,replacement,preserveComplexDomain,scalarNames,false);
   for(size_t k=1;k<history.size();k+=2)replaceQuantumIndex(history[k],index,replacement,preserveComplexDomain,scalarNames,false);
  }
  value[6]=history;value.childrenUpdated();return;
 }
 if(scalarProductNode(value)) {
  unsigned slot;Number offset;bool bind=scalarProductKey(value,index,slot,offset);
  replaceQuantumIndex(value[2],index,replacement,preserveComplexDomain,true,genericReplacement);
  if(value[3].isVector())for(size_t k=2;k<value[3].size();k+=3)
   replaceQuantumIndex(value[3][k],index,replacement,preserveComplexDomain,true,genericReplacement);
  if(bind) {
   if(value[3].size()>=3*scalarProductAssignmentLimit) {CALCULATOR->error(true,"Too many indexed scalar assignments.",NULL);return;}
   value[3].addChild(MathStructure(Number(slot)));value[3].addChild(MathStructure(Number(offset)));value[3].addChild(replacement);
  }
  value.childrenUpdated();return;
 }
 int declaration=quantumBinderPosition(value);
 if(declaration>=0 && !value[declaration].equals(index) &&
    (value[declaration].isSymbolic() || value[declaration].isVariable()) &&
    (hasScalarProduct(replacement) ? scalarProductFree(replacement,value[declaration]) : replacement.contains(value[declaration])) &&
    (tensorSeriesNode(value) || (hasScalarProduct(value[0]) ? scalarProductFree(value[0],index) : value[0].contains(index)))) {
  // A free name in a symbolic replacement must not become a nested index.
  // Rename only its bound body; range endpoints and initial states are free.
  unsigned serial=0;MathStructure fresh;
  do {if(CALCULATOR->aborted())return;fresh=MathStructure("__qbound_index_"+std::to_string(serial++),true);}
  while(value.contains(fresh) || scalarProductFree(value,fresh) || replacement.contains(fresh) || scalarProductFree(replacement,fresh) || index.equals(fresh));
  MathStructure old=value[declaration];
  replaceQuantumIndex(value[0],old,fresh);value[declaration]=fresh;
 }
 int bound=quantumIndexBinder(value,index);
 if(tensorSeriesNode(value) && genericReplacement) {
  MathStructure body=value[0],first=value[1],last=value[2],binder=value[3],step=value[4],history;
  if(value.size()==5)history.clearVector();
  else if(!tensorReplacementHistory(value[5],history)) {
   CALCULATOR->error(true,"Invalid tensor series replacement history.",NULL);return;
  }
  replaceQuantumIndex(first,index,replacement,preserveComplexDomain,scalarNames,true);
  replaceQuantumIndex(last,index,replacement,preserveComplexDomain,scalarNames,true);
  replaceQuantumIndex(step,index,replacement,preserveComplexDomain,scalarNames,true);
  if(bound<0) {
   if(history.size()==4096) {CALCULATOR->error(true,"A tensor series supports at most 2048 deferred replacements.",NULL);return;}
   // Keep keys and values as originally supplied. Replaying these pairs in
   // order handles repeated keys and values that refer to later replacements.
   history.addChild(index);history.addChild(replacement);
  }
  value.set(CALCULATOR->getFunction("qboundtensorseries"),&body,&first,&last,&binder,&step,&history,NULL);return;
 }
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  if(tensorSeriesNode(value) && k==5) {
   // Internal index instantiation may affect replacement values, never keys.
   for(size_t j=1;j<value[k].size();j+=2)replaceQuantumIndex(value[k][j],index,replacement,preserveComplexDomain,scalarNames,genericReplacement);
   value[k].childrenUpdated();continue;
  }
  replaceQuantumIndex(value[k],index,replacement,preserveComplexDomain,scalarNames,genericReplacement);
 }
 value.childrenUpdated();
}
// A set supplies the same basis as a range only when its distinct values are
// exactly 0..d-1. Ordering and duplicate entries do not change that dimension.
unsigned completeSetBasisDimension(const MathStructure &members) {
 if(!members.isVector() || members.size()==0 || members.size()>1024)return 0;
 std::vector<bool> occupied(members.size(),false);
 unsigned distinct=0,maximum=0;
 for(size_t k=0;k<members.size();++k) {
  const MathStructure &member=members[k];
  if(!member.isNumber() || !member.number().isInteger() || member.number()<0 ||
     member.number()>=Number(static_cast<long>(members.size())))return 0;
  unsigned index=member.number().intValue();
  if(!occupied[index]) {occupied[index]=true;++distinct;}
  if(index>maximum)maximum=index;
 }
 return distinct==maximum+1 ? distinct : 0;
}
// Instantiate one Cartesian tuple. Digits are stored from the lowest index
// upward; tensor factors are emitted from the highest index downward.
struct RegisterTupleBinding {
 const MathStructure &prefix;
 const Number &first,&last;
 const MathStructure &digits,&alphabet;
 unsigned dimension;
 bool validateOnly=false;
};
bool bindRegisterTuple(MathStructure &value,const RegisterTupleBinding &binding,const EvaluationOptions &eo) {
 const auto &prefix=binding.prefix,&digits=binding.digits;
 const Number &first=binding.first,&last=binding.last;
 unsigned dimension=binding.dimension;
 if(CALCULATOR->aborted())return false;
 if(!protectRegisterComponentBinder(value,prefix))return false;
 auto digit=[&](const Number &index,MathStructure &out) {
  if(index<last || index>first) {
   CALCULATOR->error(true,"A bound register component lies outside its declared range.",NULL);return false;
  }
  if(binding.validateOnly)return true;
  Number offset=index;offset-=last;out=digits[offset.intValue()];return true;
 };
 auto basisAvailable=[&]() {
  // A sparse first tuple must not hide an invalid later alphabet member.
  for(size_t k=0;k<binding.alphabet.size();++k)if(!binding.alphabet[k].isNumber() || !binding.alphabet[k].number().isInteger() || binding.alphabet[k].number()<0) {
   CALCULATOR->error(true,"Register basis labels must be nonnegative integers.",NULL);return false;
  }
  return binding.validateOnly || dimension!=0;
 };
 Number index;
 if(registerBitIndex(value,prefix.symbol(),index)) {MathStructure result;if(!digit(index,result))return false;if(!binding.validateOnly)value=result;return true;}
 if(!value.isFunction()) {
  for(size_t k=0;k<value.size();++k)if(!bindRegisterTuple(value[k],binding,eo))return false;
  value.childrenUpdated();return true;
 }
 const std::string name=value.function()->referenceName();
 if(registerSumNode(value)) {
  for(unsigned k:{1u,2u,3u,5u})if(!bindRegisterTuple(value[k],binding,eo))return false;
  if(!value[4].equals(prefix) && !bindRegisterTuple(value[0],binding,eo))return false;
  for(size_t k=1;k<value[6].size();k+=2)if(!bindRegisterTuple(value[6][k],binding,eo))return false;
  value.childrenUpdated();return true;
 }
 if(name=="qindexedlabel" && value.size()==3 && value[0].equals(prefix)) {
  // A suffix denotes a different family, not a component of this register.
  if(!value[2].isSymbolic() || !value[2].symbol().empty())return false;
  MathStructure index=value[1];index.eval(eo);
  if(index.isNumber() && index.number().isInteger()) {MathStructure result;if(!digit(index.number(),result))return false;if(!binding.validateOnly)value=result;return true;}
  if(!pendingRegisterIndex(index)) {CALCULATOR->error(true,"Register component indices must be integers.",NULL);return false;}
  if(binding.validateOnly)return true;
  index-=MathStructure(last);index.eval(eo);
  value.set(CALCULATOR->getFunction("qregisterelement"),&digits,&index,NULL);return true;
 }
 if(scalarProductNode(value) && (value[0].equals(prefix) || value[1].equals(prefix))) {
  MathStructure width=value[2];width.eval(eo);
  if(pendingRegisterIndex(width))return binding.validateOnly;
  Number registerWidth=first;registerWidth-=last;registerWidth+=1;
  if(!last.isZero() || !width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>registerWidth) {
   CALCULATOR->error(true,"A bound scalar product must fit the zero-based register.",NULL);return false;
  }
  if(binding.validateOnly)return true;
  value[2]=width;
  for(size_t k=0;k<digits.size();++k) {
   MathStructure label(prefix.symbol()+std::to_string(k),true);
   replaceQuantumIndex(value,label,digits[k]);
  }
  value.childrenUpdated();return true;
 }
 if(name=="qregisterfamily" && value.size()==4 && value[0].equals(prefix)) {
  MathStructure begin=value[1],end=value[2],bindings=value[3];begin.eval(eo);end.eval(eo);
  if(pendingRegisterIndex(begin) || pendingRegisterIndex(end))return binding.validateOnly;
  if(!begin.isNumber() || !end.isNumber() || !begin.number().isInteger() || !end.number().isInteger() ||
     begin.number()<-1 || end.number()<0 || !bindings.isVector() || bindings.size()%2 || bindings.size()>256) {
   CALCULATOR->error(true,"Invalid bound register family.",NULL);return false;
  }
  Number span=begin.number();span-=end.number();
  if(span<-1 || begin.number()>first || end.number()<last) {CALCULATOR->error(true,"Register family lies outside its binder.",NULL);return false;}
  for(size_t k=0;k<bindings.size();k+=2) {
   if(!bindings[k].isNumber() || !bindings[k].number().isInteger() || bindings[k].number()<end.number() || bindings[k].number()>begin.number()) {
    CALCULATOR->error(true,"Invalid bound register assignment index.",NULL);return false;
   }
   for(size_t j=0;j<k;j+=2)if(bindings[k].equals(bindings[j])) {CALCULATOR->error(true,"Duplicate bound register assignment.",NULL);return false;}
   if(!bindRegisterTuple(bindings[k+1],binding,eo))return false;
  }
  if(span==-1) {value.setToIdentityMatrix(1);return true;}
  if(!basisAvailable())return false; // A sparse alphabet does not declare an ambient basis.
  for(size_t k=1;k<bindings.size();k+=2) {
   MathStructure assigned=bindings[k];assigned.eval(eo);
   if(pendingRegisterIndex(assigned))continue;
   if(!assigned.isNumber() || !assigned.number().isInteger() || assigned.number()<0 ||
      (dimension && assigned.number()>=Number(dimension))) {
    CALCULATOR->error(true,"A bound register assignment must be an integer basis index in range.",NULL);return false;
   }
  }
  if(binding.validateOnly)return true;
  MathStructure result;bool initial=true;Number at=begin.number();
  while(at>=end.number()) {
   if(CALCULATOR->aborted())return false;
   MathStructure component;if(!digit(at,component))return false;
   for(size_t k=0;k<bindings.size();k+=2)if(bindings[k].number()==at)component=bindings[k+1];
   MathStructure size{Number(dimension)},factor(CALCULATOR->getFunction("qbasis"),&component,&size,NULL);
   if(initial) {result=factor;initial=false;}
   else {MathStructure previous=result;result.set(CALCULATOR->getFunction("qtensor"),&previous,&factor,NULL);}
   at-=1;
  }
  value=result;return true;
 }
 if((name=="qnamedket" || name=="qketstate" || name=="qindexedket") && value.size()==1) {
  bool bound=registerBitIndex(value[0],prefix.symbol(),index) ||
   (value[0].isFunction() && value[0].function()->referenceName()=="qindexedlabel" && value[0].size()==3 && value[0][0].equals(prefix));
  if(bound) {
   if(!basisAvailable())return false;
   MathStructure component=value[0];if(!bindRegisterTuple(component,binding,eo))return false;
   if(binding.validateOnly)return true;
   MathStructure size{Number(dimension)};value.set(CALCULATOR->getFunction("qbasis"),&component,&size,NULL);return true;
  }
 }
 for(size_t k=0;k<value.size();++k)if(!bindRegisterTuple(value[k],binding,eo))return false;
 value.childrenUpdated();return true;
}
bool registerSumArguments(MathStructure &args,MathStructure &history,MathStructure &difference,
                          const EvaluationOptions &eo,bool report) {
 auto invalid=[&](const char *message) {if(report)CALCULATOR->error(true,message,NULL);return false;};
 if(args.size()!=7)return invalid("Invalid register sum argument count.");
 if(!scalarProductPrefix(args[4]) || !tensorReplacementHistory(args[6],history)) {
  return invalid("A register sum requires a literal family prefix and ordered replacement history.");
 }
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 for(unsigned k:{2u,3u,5u}) {
  args[k].eval(exact);
  if(pendingRegisterIndex(args[k]))continue;
  if(!args[k].isNumber() || !args[k].number().isInteger() || args[k].number()<(k==2 ? -1 : 0)) {
   return invalid("Register sum bounds and width must be nonnegative integers, allowing -1 for the empty leading endpoint.");
  }
 }
 difference=args[2];difference-=args[3];difference+=m_one;difference-=args[5];difference.eval(exact);
 if(difference.isNumber() && !difference.isZero()) {
  return invalid("Register sum bounds contradict its domain width.");
 }
 args.childrenUpdated();return true;
}
int calculateRegisterSum(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
 MathStructure args=raw,history,difference;
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 if(!registerSumArguments(args,history,difference,exact,true))return 0;
 if(!args[2].isNumber() || !args[3].isNumber() || !args[5].isNumber() || !difference.isZero())return 0;
 MathStructure members;members.clearVector();unsigned dimension=0;
 if(!args[5].isZero()) {
  DomainState state=finiteDomain(args[1],members,exact);
  if(state==DomainState::Invalid) {CALCULATOR->error(true,"A register sum requires a finite alphabet.",NULL);return 0;}
  if(state==DomainState::Pending || unresolvedSetEquality(members))return 0;
  if(!members.size()) {out.clear();return 1;}
  dimension=completeSetBasisDimension(members);
 }
 // Freshening excludes every saved replacement value before replay begins.
 if(!freshRegisterFamily(args,m_zero,m_zero))return 0;
 MathStructure body=args[0];
 for(size_t k=0;k<history.size();k+=2) {
  if(CALCULATOR->aborted())return 0;
  resolveIndexedLabels(body,exact);
  replaceQuantumIndex(body,history[k],history[k+1],false,false,true);
  bindRegisterBit(body,history[k],history[k+1],true);
 }
 // Validate bound uses before either expansion cutoff. This traverses the
 // scoped body without constructing a tuple or requiring a complete basis.
 MathStructure validationBody=body,emptyDigits;emptyDigits.clearVector();
 RegisterTupleBinding validation{args[4],args[2].number(),args[3].number(),emptyDigits,members,dimension,true};
 if(!bindRegisterTuple(validationBody,validation,exact))return 0;
 // Keep arbitrary-precision widths intact until bounded conversion is safe.
 if(args[5].number()>32)return 0;
 unsigned width=args[5].number().intValue();
 size_t count=1;
 for(unsigned k=0;k<width;++k) {if(count>1024/members.size())return 0;count*=members.size();}
 for(size_t ordinal=0;ordinal<count;++ordinal) {
  if(CALCULATOR->aborted())return 0;
  MathStructure digits;digits.clearVector();size_t index=ordinal;
  for(unsigned k=0;k<width;++k) {digits.addChild(members[index%members.size()]);index/=members.size();}
  MathStructure term=body;
  RegisterTupleBinding binding{args[4],args[2].number(),args[3].number(),digits,members,dimension};
  if(!bindRegisterTuple(term,binding,exact))return 0;
  term.eval(eo);
  if(!ordinal)out=term;
  else {MathStructure previous=out;out.set(CALCULATOR->getFunction("qadd"),&previous,&term,NULL);out.eval(eo);}
 }
 return 1;
}
struct RegisterShapeProjection {
 const MathStructure &prefix,&first,&last,&width;
 const std::string &markerPrefix;
 MathStructure &markers;
 unsigned dimension;
};
// Indexed substitution treats a literal name and an unknown variable with
// that name as the same parameter. Use that policy only in a comparison copy;
// never rewrite the retained expression or descend into arbitrary binders.
bool scalarComparisonNames(MathStructure &value,unsigned depth=0) {
 if(depth>64 || CALCULATOR->aborted())return false;
 if(value.isVariable() && !value.variable()->isKnown()) {
  value=MathStructure(value.variable()->referenceName(),true);return true;
 }
 bool algebra=value.isAddition() || value.isMultiplication() || value.isPower();
 if(value.isFunction()) {
  const std::string &name=value.function()->referenceName();
  algebra=name=="qadd" || name=="qsub" || name=="qmul" || name=="qadjacent" || name=="qpower" || name=="qsqrt";
 }
 if(!algebra)return true;
 for(size_t k=0;k<value.size();++k)if(!scalarComparisonNames(value[k],depth+1))return false;
 value.childrenUpdated();return true;
}
bool projectRegisterShape(MathStructure &value,const RegisterShapeProjection &context,
                          const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>64 || CALCULATOR->aborted())return false;
 const auto &prefix=context.prefix;
 if(!protectRegisterComponentBinder(value,prefix))return false;
 auto dependent=[&]() {
  value=MathStructure(context.markerPrefix+std::to_string(context.markers.size()),true);
  context.markers.addChild(value);return true;
 };
 auto componentInRange=[&](MathStructure index) {
  index.eval(eo);if(pendingRegisterIndex(index))return true;
  if(!index.isNumber() || !index.number().isInteger())return false;
  MathStructure low=index;low-=context.last;low.eval(eo);
  MathStructure high=context.first;high-=index;high.eval(eo);
  return !(low.isNumber() && low.number()<0) && !(high.isNumber() && high.number()<0);
 };
 Number index;
 if(registerBitIndex(value,prefix.symbol(),index)) {
  if(!componentInRange(MathStructure(index)))return false;
  return dependent();
 }
 if(value.isFunction()) {
  const std::string name=value.function()->referenceName();
  if(registerSumNode(value)) {
   for(unsigned k:{1u,2u,3u,5u})if(!projectRegisterShape(value[k],context,eo,depth+1))return false;
   if(!value[4].equals(prefix) && !projectRegisterShape(value[0],context,eo,depth+1))return false;
   for(size_t k=1;k<value[6].size();k+=2)if(!projectRegisterShape(value[6][k],context,eo,depth+1))return false;
   value.childrenUpdated();return true;
  }
  if(name=="qindexedlabel" && value.size()==3 && value[0].equals(prefix)) {
   if(!value[2].isSymbolic() || !value[2].symbol().empty() || !componentInRange(value[1]))return false;
   return dependent();
  }
  if(scalarProductNode(value)) {
   MathStructure arguments=value;bool pendingWidth=false;
   if(!scalarProductArguments(arguments,eo,pendingWidth))return false;
   if(value[0].equals(prefix) || value[1].equals(prefix)) {
    MathStructure excess=arguments[2],registerWidth=context.width;
    if(!scalarComparisonNames(excess) || !scalarComparisonNames(registerWidth))return false;
    excess-=registerWidth;excess.eval(eo);
    if(!context.last.isZero() || (!excess.isZero() && (!excess.isNumber() || excess.number()>0)))return false;
    return dependent();
   }
  }
  if(name=="qregisterfamily" && value.size()==4 && value[0].equals(prefix)) {
   MathStructure begin=value[1],end=value[2];begin.eval(eo);end.eval(eo);
   for(const auto *bound:{&begin,&end})if(!pendingRegisterIndex(*bound) &&
      (!bound->isNumber() || !bound->number().isInteger() || bound->number()<(bound==&begin ? -1 : 0)))return false;
   MathStructure low=end;low-=context.last;low.eval(eo);
   MathStructure high=context.first;high-=begin;high.eval(eo);
   // An unproved subrange relation must not become a declared matrix shape.
   if(!low.isNumber() || low.number()<0 || !high.isNumber() || high.number()<0)return false;
   MathStructure count=begin;count-=end;count+=m_one;count.eval(eo);
   if((count.isNumber() && count.number()<0) || (!count.isNumber() && !pendingRegisterIndex(count)))return false;
   if(!value[3].isVector() || value[3].size()%2 || value[3].size()>256)return false;
   for(size_t k=0;k<value[3].size();k+=2) {
    const MathStructure &key=value[3][k];MathStructure assigned=value[3][k+1];assigned.eval(eo);
    if(!key.isNumber() || !key.number().isInteger())return false;
    MathStructure lower=key;lower-=end;lower.eval(eo);MathStructure upper=begin;upper-=key;upper.eval(eo);
    if(!lower.isNumber() || lower.number()<0 || !upper.isNumber() || upper.number()<0)return false;
    for(size_t j=0;j<k;j+=2)if(key.equals(value[3][j]))return false;
    if(!pendingScalar(assigned) && (!assigned.isNumber() || !assigned.number().isInteger() || assigned.number()<0 || assigned.number()>=Number(context.dimension)))return false;
   }
   MathStructure dimension{Number(context.dimension)};
   if(count.isZero())dimension=m_one;else if(!dimension.isOne())dimension.raise(count);
   // This is shape metadata only. Never evaluate this potentially huge basis.
   value.set(CALCULATOR->getFunction("qbasis"),&m_zero,&dimension,NULL);return true;
  }
  if((name=="qnamedket" || name=="qketstate" || name=="qindexedket") && value.size()==1) {
   bool bound=registerBitIndex(value[0],prefix.symbol(),index) ||
    (value[0].isFunction() && value[0].function()->referenceName()=="qindexedlabel" && value[0].size()==3 && value[0][0].equals(prefix));
   if(bound) {
    MathStructure component=value[0];if(!projectRegisterShape(component,context,eo,depth+1))return false;
    MathStructure dimension{Number(context.dimension)};
    value.set(CALCULATOR->getFunction("qbasis"),&component,&dimension,NULL);return true;
   }
  }
 }
 for(size_t k=0;k<value.size();++k)if(!projectRegisterShape(value[k],context,eo,depth+1))return false;
 value.childrenUpdated();return true;
}
// The complete range 0..d-1 supplies a basis for bare kets/bras of its index.
// Explicit basis dimensions and nested declarations retain their own meaning.
// With no dimension, report whether a free bare basis reference needs one.
bool inferSumBasis(MathStructure &value,const MathStructure &index,const MathStructure *dimension) {
 if(value.isFunction() && value.size()==1 && value[0].equals(index) &&
    (value.function()->referenceName()=="qketstate" || value.function()->referenceName()=="qnamedket")) {
  auto basis=CALCULATOR->getFunction("qbasis");
  if(dimension && basis)value.set(basis,&index,dimension,NULL);
  return true;
 }
 bool found=false;
 int bound=quantumIndexBinder(value,index);
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  found=inferSumBasis(value[k],index,dimension) || found;
 }
 if(dimension)value.childrenUpdated();
 return found;
}
// Validate the ordinary evaluation path with an unknown ambient dimension.
// The validation result is discarded: the original scoped sum stays intact.
// Evaluating the whole body also preserves empty sums and conditional branches.
void validatePendingSum(const MathStructure &value,const MathStructure &index,
                        const MathStructure &members,const EvaluationOptions &eo) {
 unsigned serial=0;MathStructure dimension;
 do {dimension=MathStructure("__qpending_basis_"+std::to_string(serial++),true);}
 while(value.contains(dimension) || members.contains(dimension) || index.equals(dimension));
 MathStructure body=value;
 inferSumBasis(body,index,&dimension);
 for(size_t k=0;k<members.size();++k) {
  if(CALCULATOR->aborted())return;
  MathStructure term=body;
  replaceQuantumIndex(term,index,members[k]);term.eval(eo);
 }
}
class QuantumStateFamilyFunction: public MathFunction {
 MathStructure body;std::vector<MathStructure> parameters;
 public:
 QuantumStateFamilyFunction(const std::string &name,const MathStructure &value,const std::vector<MathStructure> &indices):MathFunction("__qstate_family_"+name,indices.size()),body(value),parameters(indices) {}
 ExpressionItem *copy() const {return new QuantumStateFamilyFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(raw.size()!=parameters.size()) {CALCULATOR->error(true,"Wrong number of state-family arguments.",NULL);return 0;}
  MathStructure arguments=raw;arguments.eval(eo);std::vector<MathStructure> placeholders;
  for(size_t k=0;k<arguments.size();++k)if(!arguments[k].representsScalar() || arguments[k].isUndefined() || (arguments[k].isNumber() && arguments[k].number().isInfinite(false))) {CALCULATOR->error(true,"State-family arguments must be finite scalars.",NULL);return 0;}
  out=body;unsigned serial=0;
  // Substitute simultaneously: an argument may contain another parameter's
  // name. Fresh placeholders prevent later replacements from rewriting it.
  for(const auto &parameter:parameters) {
   MathStructure fresh;bool used;
   do {
    fresh=MathStructure("__qstate_argument_"+std::to_string(serial++),true);
    used=out.contains(fresh) || arguments.contains(fresh);
    for(const auto &other:parameters)used=used || other.contains(fresh);
   }while(used);
   placeholders.push_back(fresh);replaceQuantumIndex(out,parameter,fresh);
  }
  for(size_t k=0;k<parameters.size();++k)replaceQuantumIndex(out,placeholders[k],arguments[k]);
  out.eval(eo);
  if(!out.isMatrix() || out.columns()!=1 || !out.rows() || out.rows()>1024) {CALCULATOR->error(true,"A state family must produce a column vector of at most 1024 rows.",NULL);return 0;}
  for(size_t r=1;r<=out.rows();++r) {
   const MathStructure &cell=*out.getElement(r,1);
   if(!cell.representsScalar() || cell.isUndefined() || (cell.isNumber() && cell.number().isInfinite(false))) {CALCULATOR->error(true,"State-family amplitudes must be finite scalar expressions.",NULL);return 0;}
  }
  return 1;
 }
};
class QuantumIndexedFunction: public MathFunction {
 std::string op;
 public:
 QuantumIndexedFunction(const char *name,int count):MathFunction(name,count),op(name) {if(op=="qstatecall" || op=="qstatecalls" || op=="qindexedcolumn" || op=="qdescendingcolumn" || op=="qindexedmatrix" || op=="qindexedcoefficient" || op=="qregisterfamily" || op=="qregisterword" || op=="qfamilymembers")setArgumentDefinition(1,new TextArgument());if(op=="qscalarproductsum") {setArgumentDefinition(1,new TextArgument());setArgumentDefinition(2,new TextArgument());}if(op=="qregistersum")setArgumentDefinition(5,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumIndexedFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 bool representsScalar(const MathStructure &value) const {return op=="qscalarproductsum" || MathFunction::representsScalar(value);}
 bool representsNonMatrix(const MathStructure &value) const {return op=="qscalarproductsum" || MathFunction::representsNonMatrix(value);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(op=="qscalarproductsum")return calculateScalarProduct(out,raw,this,eo);
  if(op=="qregistersum")return calculateRegisterSum(out,raw,eo);
  if(op=="qregisterelement") {
   MathStructure digits=raw[0],index=raw[1];digits.eval(eo);index.eval(eo);
   if(!digits.isVector()) {CALCULATOR->error(true,"Register elements require a vector of components.",NULL);return 0;}
   if(pendingRegisterIndex(index))return 0;
   if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(digits.size())) {
    CALCULATOR->error(true,"Register component index is outside its bounds.",NULL);return 0;
   }
   out=digits[index.number().intValue()];return 1;
  }
  if(op=="qfunctionrange" || op=="qpreimage" || op=="qfunctiontype") {
   bool signature=op=="qfunctiontype";
   bool inverse=op=="qpreimage";
   MathStructure graph=raw[0];graph.eval(eo);
   if(!graph.isFunction() || graph.function()->referenceName()!="qset") {
    if(pendingDomain(graph))return 0;
    if(signature) {CALCULATOR->error(true,"A function signature requires a finite graph.",NULL);return 0;}
    if(inverse) {CALCULATOR->error(true,"An inverse image requires a finite function graph.",NULL);return 0;}
    // Preserve the ordinary statistical range for data vectors.
    auto range=CALCULATOR->getFunction("range");
    if(!range)return 0;
    out.set(range,&graph,NULL);out.eval(eo);return 1;
   }
   MathStructure pairs;DomainState state=finiteDomain(graph,pairs,eo);
   if(state==DomainState::Pending)return 0;
   if(state!=DomainState::Finite) {CALCULATOR->error(true,"A function range requires a finite graph.",NULL);return 0;}
   MathStructure target;
   if(inverse || signature) {
    DomainState targetState=finiteDomain(raw[signature ? 2 : 1],target,eo);
    if(targetState==DomainState::Pending)return 0;
    if(targetState!=DomainState::Finite) {CALCULATOR->error(true,"A finite target set is required.",NULL);return 0;}
   }
   MathStructure outputs;outputs.clearVector();
   for(size_t k=0;k<pairs.size();++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &pair=pairs[k];
    if(!pair.isFunction() || pair.function()->referenceName()!="qtuple" || pair[0].size()!=2) {
     CALCULATOR->error(true,"A function graph requires ordered pairs.",NULL);return 0;
    }
    for(size_t j=0;j<k;++j) {
     SetEquality keys=setEquality(pair[0][0],pairs[j][0][0]);
     if(keys==SetEquality::Different)continue;
     SetEquality values=setEquality(pair[0][1],pairs[j][0][1]);
     if(values==SetEquality::Equal)continue;
     if(keys==SetEquality::Unknown || values==SetEquality::Unknown)return 0;
     if(signature) {out=0;return 1;}
     CALCULATOR->error(true,"The function graph has conflicting outputs for this input.",NULL);return 0;
    }
    if(inverse || signature) {
     bool found=false,uncertain=false;
     for(size_t j=0;j<target.size();++j) {
      SetEquality match=setEquality(pair[0][1],target[j]);
      if(match==SetEquality::Equal) {found=true;break;}
      if(match==SetEquality::Unknown)uncertain=true;
     }
     if(!found && uncertain)return 0;
     if(signature && !found) {out=0;return 1;}
     if(found)outputs.addChild(pair[0][0]);
    } else outputs.addChild(pair[0][1]);
   }
   out.set(CALCULATOR->getFunction("qset"),&outputs,NULL);
   if(signature) {
    MathStructure domain;DomainState state=finiteDomain(raw[1],domain,eo);
    if(state==DomainState::Invalid) {CALCULATOR->error(true,"A function signature requires a finite domain.",NULL);return 0;}
    if(state==DomainState::Pending)return 0;
    bool total=false;
    if(!compareQuantumSets(out,domain,total,eo))return 0;
    out=total ? 1 : 0;return 1;
   }
   out.eval(eo);return 1;
  }
  if(op=="qsetunion" || op=="qsetintersect" || op=="qsetdiff") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure left,right;DomainState first=finiteDomain(raw[0],left,exact),second=finiteDomain(raw[1],right,exact);
   if(first==DomainState::Invalid || second==DomainState::Invalid) {CALCULATOR->error(true,"Set operations require finite sets of valid entries.",NULL);return 0;}
   if(first==DomainState::Pending || second==DomainState::Pending)return 0;
   MathStructure entries;entries.clearVector();
   for(size_t k=0;k<left.size();++k) {
    if(CALCULATOR->aborted())return 0;
    bool found=false,unknown=false;
    for(size_t j=0;j<right.size();++j) {
     SetEquality equality=setEquality(left[k],right[j]);found=found || equality==SetEquality::Equal;unknown=unknown || equality==SetEquality::Unknown;
    }
    if(op!="qsetunion" && !found && unknown)return 0;
    if(op=="qsetunion" || (op=="qsetintersect" ? found : !found))entries.addChild(left[k]);
   }
   if(op=="qsetunion")for(size_t k=0;k<right.size();++k) {
    bool found=false;for(size_t j=0;j<entries.size();++j)found=found || setEquality(right[k],entries[j])==SetEquality::Equal;
    if(!found)entries.addChild(right[k]);
   }
   if(entries.size()>1024) {CALCULATOR->error(true,"Set operations support at most 1024 entries.",NULL);return 0;}
   out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;
  }
  if(op=="qdomainresult") {
   MathStructure source=raw[1];source.eval(eo);
   if((source.isSymbolic() || (source.isVariable() && !source.variable()->isKnown())))return 0;
   if(domainExpression(source) && raw[0].isFunction()) {
    const MathStructure &call=raw[0];const std::string name=call.function()->referenceName();
    if(name=="unique") {out=source;return 1;}
    if(name=="select" && call.size()==4) {
     MathStructure firstOnly=call[3];firstOnly.eval(eo);
     if(firstOnly.isZero()) {
      MathStructure index=call[2];
      if(index.isUndefined()) {
       index=MathStructure("__qselect_index",true);
       while(call.contains(index))index=MathStructure(index.symbol()+"_",true);
      }
      out.set(CALCULATOR->getFunction("qsetfilter"),&call[1],&source,&index,NULL);out.eval(eo);return 1;
     }
    }
   }
   out=raw[0];out.eval(eo);return 1;
  }
  if(op=="qdomainvector") {
   // Legacy vector consumers retain their own validation and multiset rules.
   // Only erase the set descriptor at this explicit compatibility boundary.
   out=raw[0];out.eval(eo);
   if(out.isFunction() && out.function()->referenceName()=="qset" && out.size()==1) {
    MathStructure entries=out[0];out=entries;
   }
   return 1;
  }
  if(op=="qset") {
   MathStructure entries=raw[0];
   if(entries.isFunction() && entries.function()->referenceName()=="vector") {
    entries.clearVector();for(size_t k=0;k<raw[0].size();++k)entries.addChild(raw[0][k]);
   }
   if(!entries.isVector() || entries.size()>1024) {CALCULATOR->error(true,"A set requires a vector of at most 1024 valid entries.",NULL);return 0;}
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;bool pending=false;
   if(!normalizeSetEntries(entries,exact,pending)) {CALCULATOR->error(true,"Invalid set entry.",NULL);return 0;}
   if(!entries.equals(raw[0])) {out.set(this,&entries,NULL);return 1;}
   return 0;
  }
  if(op=="qtuple") {
   MathStructure value;value.set(this,&raw[0],NULL);bool pending=false;
   if(!canonicalSetElement(value,eo,pending)) {CALCULATOR->error(true,"Tuples require at most 32 valid scalar, binary-string or tuple entries.",NULL);return 0;}
   if(!value[0].equals(raw[0])) {out=value;return 1;}
   return 0;
  }
  if(op=="qwordpower") {
   MathStructure alphabet;DomainState state=finiteDomain(raw[0],alphabet,eo);
   if(state==DomainState::Invalid) {CALCULATOR->error(true,"A word power requires a finite alphabet.",NULL);return 0;}
   if(state==DomainState::Finite && alphabet.size()==2) {
    const MathStructure *first=&alphabet[0],*second=&alphabet[1];
    auto bit=[](const MathStructure &entry) {
     return entry.isFunction() && entry.function()->referenceName()=="qbitlabel" &&
            entry.size()==2 && entry[1].isOne();
    };
    if(bit(*first) && bit(*second)) {first=&(*first)[0];second=&(*second)[0];}
    if((first->isZero() && second->isOne()) || (first->isOne() && second->isZero())) {
     out.set(CALCULATOR->getFunction("qbitstrings"),&raw[1],NULL);out.eval(eo);return 1;
    }
   }
   if(state==DomainState::Pending) {
    MathStructure count=raw[1];count.eval(eo);
    if(count.isNumber() && (!count.number().isInteger() || count.number()<0))
     CALCULATOR->error(true,"A word length must be a nonnegative integer.",NULL);
    return 0;
   }
   out.set(CALCULATOR->getFunction("qcartesianpower"),&raw[0],&raw[1],NULL);out.eval(eo);return 1;
  }
  if(op=="qcartesian" || op=="qcartesianpower") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure count=raw[1];bool pendingCount=false;
   if(op=="qcartesianpower") {
    count.eval(exact);
    pendingCount=!count.isNumber() && count.representsScalar() && count.containsUnknowns();
    if(!pendingCount && (!count.isNumber() || !count.number().isInteger() || count.number()<0 || count.number()>32)) {
     CALCULATOR->error(true,"Cartesian powers require a nonnegative integer count of at most 32.",NULL);return 0;
    }
   }
   MathStructure left,right;
   DomainState first=finiteDomain(raw[0],left,exact),second=DomainState::Finite;
   if(op=="qcartesian")second=finiteDomain(raw[1],right,exact);
   if(first==DomainState::Invalid || second==DomainState::Invalid) {CALCULATOR->error(true,"Cartesian factors must be finite sets of at most 1024 valid entries.",NULL);return 0;}
   if(pendingCount || first==DomainState::Pending || second==DomainState::Pending)return 0;
   int repetitions=op=="qcartesianpower" ? count.number().intValue() : 2;
   MathStructure tuples;tuples.clearVector();MathStructure empty;empty.clearVector();
   MathStructure initial(CALCULATOR->getFunction("qtuple"),&empty,NULL);tuples.addChild(initial);
   for(int axis=0;axis<repetitions;++axis) {
    const MathStructure &factor=op=="qcartesian" && axis==1 ? right : left;
    if(factor.size() && tuples.size()>1024/factor.size()) {
     if(unresolvedSetEquality(left) || (op=="qcartesian" && unresolvedSetEquality(right)))return 0;
     CALCULATOR->error(true,"Cartesian materialization supports at most 1024 tuples.",NULL);return 0;
    }
    MathStructure next;next.clearVector();
    for(size_t a=0;a<tuples.size();++a)for(size_t b=0;b<factor.size();++b) {
     if(CALCULATOR->aborted())return 0;
     MathStructure fields=tuples[a][0];fields.addChild(factor[b]);
     MathStructure tuple(CALCULATOR->getFunction("qtuple"),&fields,NULL);next.addChild(tuple);
    }
    tuples=next;
   }
   out.set(CALCULATOR->getFunction("qset"),&tuples,NULL);return 1;
  }
  if(op=="qsetimage" || op=="qsetfilter") {
   if((!raw[2].isSymbolic() && !raw[2].isVariable()) || (raw[2].isVariable() && raw[2].variable()->isKnown())) {
    CALCULATOR->error(true,"An indexed image requires a symbolic index.",NULL);return 0;
   }
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure members;DomainState state=finiteDomain(raw[1],members,exact);
   if(state==DomainState::Invalid) {CALCULATOR->error(true,"An indexed image requires a finite domain of at most 1024 entries.",NULL);return 0;}
   if(state==DomainState::Pending)return 0;
   out.clearVector();bool pending=false;
   for(size_t k=0;k<members.size();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure term=raw[0];replaceQuantumIndex(term,raw[2],members[k]);term.eval(exact);
    if(op=="qsetfilter") {
     if(term.isZero())continue;
     if(!term.isOne()) {
      if(term.representsScalar() && term.containsUnknowns()) {pending=true;continue;}
      CALCULATOR->error(true,"A set filter predicate must evaluate to zero or one, or remain symbolic.",NULL);return 0;
     }
     term=members[k];
    }
    if(!canonicalSetElement(term,exact,pending)) {CALCULATOR->error(true,"Indexed images must contain scalar, binary-string or tuple entries.",NULL);return 0;}
    bool duplicate=false;
    for(size_t j=0;j<out.size();++j) {
     SetEquality equality=setEquality(term,out[j]);
     duplicate=duplicate || equality==SetEquality::Equal;
     pending=pending || equality==SetEquality::Unknown;
    }
    if(!duplicate)out.addChild(term);
   }
   if(pending)return 0;
   MathStructure entries=out;out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;
  }
  if(op=="qfamilymembers") {
   if(!raw[0].isSymbolic() || raw[0].symbol().size()!=2 || raw[0].symbol()[0]<'a' ||
      raw[0].symbol()[0]>'z' || raw[0].symbol()[1]!='^' || !raw[3].isVector() || raw[3].size()%2) {
    CALCULATOR->error(true,"Invalid measurement family or assignments.",NULL);return 0;
   }
   MathStructure count=raw[1];count.eval(eo);
   if(!count.isNumber() && count.containsUnknowns())return 0;
   if(!count.isNumber() || !count.number().isInteger() || count.number()<1) {
    CALCULATOR->error(true,"A measurement count must be a positive integer.",NULL);return 0;
   }
   std::set<Number> supplied;
   size_t matched=0;
   for(size_t k=0;k<raw[3].size();k+=2) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &index=raw[3][k];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<1 || !supplied.insert(index.number()).second) {
     CALCULATOR->error(true,"Measurement assignments require distinct positive indices.",NULL);return 0;
    }
    if(index.number()>count.number())continue;
    MathStructure member(CALCULATOR->getFunction("qmember"),&raw[3][k+1],&raw[2],NULL);member.eval(eo);
    if(member.isZero()) {out=m_zero;return 1;}
    if(member.isOne())++matched;
   }
   if(Number(matched)==count.number()) {out=m_one;return 1;}
   return 0;
  }
  if(op=="qregisterfamily" || op=="qregisterword") {
   if(!raw[0].isSymbolic()) {CALCULATOR->error(true,"A register family requires an indexed name prefix.",NULL);return 0;}
   const std::string prefix=raw[0].symbol();
   bool valid=prefix.size()>1 && prefix.size()<=128 && prefix.back()=='_' && !std::isdigit((unsigned char)prefix.front());
   for(unsigned char c:prefix)if(c<128 && !std::isalnum(c) && c!='_')valid=false;
   if(!valid || !raw[3].isVector() || raw[3].size()%2 || raw[3].size()>256) {
    CALCULATOR->error(true,"Invalid register family prefix or bit assignments.",NULL);return 0;
   }
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure first=raw[1],last=raw[2],bindings=raw[3];first.eval(exact);last.eval(exact);
   bool deferred=false;
   for(const auto *bound:{&first,&last}) {
    if(!bound->isNumber() && bound->representsScalar() && bound->containsUnknowns()) {deferred=true;continue;}
    if(!bound->isNumber() || !bound->number().isInteger() || bound->number()<(bound==&first ? -1 : 0)) {
     CALCULATOR->error(true,"Register indices require nonnegative integers, with -1 allowed as an empty leading endpoint.",NULL);return 0;
    }
   }
   for(size_t k=0;k<bindings.size();k+=2) {
    if(!bindings[k].isNumber() || !bindings[k].number().isInteger() || bindings[k].number()<0) {CALCULATOR->error(true,"Invalid register bit index.",NULL);return 0;}
    Number index=bindings[k].number();
    for(size_t j=0;j<k;j+=2)if(bindings[j].equals(bindings[k])) {CALCULATOR->error(true,"Duplicate register bit assignment.",NULL);return 0;}
    bindings[k+1].eval(exact);const MathStructure &bit=bindings[k+1];
    if(!(bit.isNumber() && (bit.isZero() || bit.isOne())) &&
       !(!bit.isNumber() && bit.representsScalar() && bit.containsUnknowns())) {
     CALCULATOR->error(true,"Register bits must be zero or one.",NULL);return 0;
    }
    if(!deferred && (Number(index)>first.number() || Number(index)<last.number())) {
     CALCULATOR->error(true,"Supplied bit lies outside the register bounds.",NULL);return 0;
    }
   }
   if(deferred) {
    if(!first.equals(raw[1]) || !last.equals(raw[2]) || !bindings.equals(raw[3])) {
     out.set(this,&raw[0],&first,&last,NULL);out.addChild(bindings);return 1;
    }
    return 0;
   }
   Number span=first.number();span-=last.number();
   if(span<-1) {CALCULATOR->error(true,"A descending register family cannot have negative width.",NULL);return 0;}
   // Adjacent reversed endpoints denote an empty register. Every supplied or
   // explicitly displayed bit was checked above and cannot be discarded here.
   if(op=="qregisterword") {
    Number width=span;width.add(1);
    if(width!=Number(bindings.size()/2))return 0;
    Number word(0);
    for(size_t k=0;k<bindings.size();k+=2) {
     const MathStructure &bit=bindings[k+1];
     if(!bit.isNumber())return 0;
     if(bit.isOne()) {
      Number place=bindings[k].number();place-=last.number();
      Number weight(1);weight.shiftLeft(place);word+=weight;
     }
    }
    MathStructure index(word),length(width);
    out.set(CALCULATOR->getFunction("qbitlabel"),&index,&length,NULL);return 1;
   }
   if(span==-1) {out.setToIdentityMatrix(1);return 1;}
   if(span>9) {
    if(!first.equals(raw[1]) || !last.equals(raw[2]) || !bindings.equals(raw[3])) {
     out.set(this,&raw[0],&first,&last,NULL);out.addChild(bindings);return 1;
    }
    return 0;
   }
   bool initial=true;
   Number index=first.number();PrintOptions print;print.use_unicode_signs=false;print.min_exp=EXP_NONE;
   for(int offset=0;offset<=span.intValue();++offset,index-=1) {
    if(CALCULATOR->aborted())return 0;
    MathStructure bit(prefix+index.print(print),true),dimension(2);
    for(size_t k=0;k<bindings.size();k+=2)if(bindings[k].number()==Number(index)) {bit=bindings[k+1];break;}
    MathStructure factor(CALCULATOR->getFunction("qbasis"),&bit,&dimension,NULL);
    if(initial) {out=factor;initial=false;}
    else {MathStructure previous=out;out.set(CALCULATOR->getFunction("qtensor"),&previous,&factor,NULL);}
   }
   out.eval(eo);return 1;
  }
  if(op=="qindexedket") {
   MathStructure label=raw[0];label.eval(eo);
   if(!label.isSymbolic())return 0;
   out.set(CALCULATOR->getFunction("qnamedket"),&label,NULL);out.eval(eo);return 1;
  }
  if(op=="qreplace") {
   if(hasScalarProduct(raw[0]) || hasTensorSeries(raw[0]) || hasRegisterSum(raw[0])) {
    // Validate the complete chain, including vector assignments, before
    // changing any expression. Unsupported forms must not silently fall back
    // to generic replacement, which cannot see implicit coefficient labels.
    std::vector<std::pair<MathStructure,MathStructure>> replacements;
    MathStructure body=raw;
    do {
     MathStructure from=body[1],to=body[2];
     auto literalVector=[](MathStructure &value) {
      if(value.isFunction() && value.function()->referenceName()=="vector") {
       MathStructure entries;entries.clearVector();
       for(size_t k=0;k<value.size();++k)entries.addChild(value[k]);value=entries;
      }
     };
     literalVector(from);literalVector(to);
     std::vector<std::pair<MathStructure,MathStructure>> group;
     if(from.isVector()) {
      if(!to.isVector() || from.size()!=to.size() || from.size()>2049) {
       CALCULATOR->error(true,"Indexed scalar substitution requires matching vectors of at most 2049 assignments.",NULL);return 0;
      }
      for(size_t k=0;k<from.size();++k)group.push_back({from[k],to[k]});
     } else group.push_back({from,to});
     for(const auto &entry:group)if((!entry.first.isSymbolic() && (!entry.first.isVariable() || entry.first.variable()->isKnown())) ||
        entry.second.containsInterval(true,false,false,0,true)) {
      CALCULATOR->error(true,"Indexed scalar substitution requires plain symbols and values without intervals.",NULL);return 0;
     }
     // The outer call is collected first. Reverse groups but preserve each
     // vector's existing left-to-right replacement semantics.
     replacements.insert(replacements.begin(),group.begin(),group.end());
     MathStructure next=body[0];body=next;
    } while(body.isFunction() && body.function()==this && body.size()==3);
    out=body;
    for(const auto &entry:replacements) {
     if(CALCULATOR->aborted())return 0;
     resolveIndexedLabels(out,eo);
     // An uninstantiated series may contain this name implicitly. This
     // conservative retention decision is not free-name/collision analysis.
     bool found=hasTensorSeries(out) || hasRegisterSum(out) || scalarProductFree(out,entry.first);
     replaceQuantumIndex(out,entry.first,entry.second,false,false,true);
     found=bindRegisterBit(out,entry.first,entry.second,true) || found;
     if(!found) {
      out.eval(eo);found=scalarProductFree(out,entry.first);
      if(found)replaceQuantumIndex(out,entry.first,entry.second,false,false,true);
      found=bindRegisterBit(out,entry.first,entry.second,true) || found;
     }
     if(!found)CALCULATOR->error(false,"Original value was not found during quantum substitution.",NULL);
    }
    return 1;
   }
   // Apply a chain of ordinary symbol substitutions before evaluating its
   // partial results. Otherwise an as-yet unknown matrix can be broadcast as
   // a scalar when an earlier replacement introduces the first matrix.
   auto plain=[](const MathStructure &arguments) {
    return (arguments[1].isSymbolic() || arguments[1].isVariable()) && !arguments[2].containsInterval(true,false,false,0,true);
   };
   if(!plain(raw)) {
    MathStructure arguments=raw;arguments.addChild(m_zero);
    return CALCULATOR->getFunction("replace")->calculate(out,arguments,eo);
   }
   std::vector<std::pair<MathStructure,MathStructure>> replacements;
   replacements.push_back({raw[1],raw[2]});out=raw[0];
   while(out.isFunction() && out.function()==this && out.size()==3 && plain(out)) {
    replacements.push_back({out[1],out[2]});MathStructure body=out[0];out=body;
   }
   for(auto at=replacements.rbegin();at!=replacements.rend();++at) {
    if(CALCULATOR->aborted())return 0;
    resolveIndexedLabels(out,eo);
    // Replace existing occurrences before storing a new assignment: otherwise
    // x_0 -> x_0+1 would be applied twice inside the newly stored value.
    bool replaced=out.replace(at->first,at->second,false,false,at->first.containsUnknowns());
    bool bound=bindRegisterBit(out,at->first,at->second);
    if(replaced || bound)continue;
    // Indexed labels may not exist until a finite sum has been expanded.
    out.eval(eo);
    if(!out.replace(at->first,at->second,false,false,at->first.containsUnknowns()))CALCULATOR->error(false,"Original value was not found during quantum substitution.",NULL);
   }
   return 1;
  }
  if(op=="qindexedcoefficient") {
   if(!raw[0].isSymbolic()) {CALCULATOR->error(true,"An indexed coefficient requires a name prefix.",NULL);return 0;}
   const std::string prefix=raw[0].symbol();bool valid=prefix.size()>1 && prefix.size()<=128 && prefix.back()=='_';
   for(unsigned char c:prefix)if(c<128 && !std::isalnum(c) && c!='_')valid=false;
   if(!valid) {CALCULATOR->error(true,"An indexed coefficient prefix must be a name ending in an underscore.",NULL);return 0;}
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure indices[2]={raw[1],raw[2]};bool deferred=false;
   for(auto &index:indices) {
    index.eval(exact);
    if(!index.isNumber() && !index.isVector() && index.containsUnknowns()) {deferred=true;continue;}
    if(!index.isNumber() || !index.number().isInteger()) {CALCULATOR->error(true,"A coefficient index must be an integer.",NULL);return 0;}
   }
   if(deferred)return 0;
   PrintOptions print;print.use_unicode_signs=false;print.min_exp=EXP_NONE;
   out.set(prefix+indices[0].print(print)+","+indices[1].print(print),true);return 1;
  }
  if(op=="qindexedcolumn" || op=="qdescendingcolumn" || op=="qindexedmatrix") {
   const bool matrix=op=="qindexedmatrix";
   if(!raw[0].isSymbolic()) {CALCULATOR->error(true,"An indexed array requires a coefficient-name prefix.",NULL);return 0;}
   const std::string prefix=raw[0].symbol();
   bool valid=prefix.size()>=2 && prefix.size()<=128 && prefix.back()=='_';
   for(unsigned char c:prefix)if(c<128 && !std::isalnum(c) && c!='_')valid=false;
   if(!valid) {CALCULATOR->error(true,"An indexed array prefix must be a name ending in an underscore.",NULL);return 0;}
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   int dimensions[2]={1,1};bool deferred=false;
   // Validate every axis even when another dimension is still symbolic.
   // Endpoint bounds also cap the product at 1024 * 1024 matrix cells.
   for(int axis=0;axis<(matrix ? 2 : 1);++axis) {
    MathStructure last=raw[1+axis],minimum=raw[(matrix ? 3 : 2)+axis];last.eval(exact);minimum.eval(exact);
    if(!minimum.isNumber() || !minimum.number().isInteger() || minimum.number()<0 || minimum.number()>1023) {
     CALCULATOR->error(true,"An indexed array minimum must be an integer from 0 to 1023.",NULL);return 0;
    }
    if(!last.isNumber() && !last.isVector() && last.containsUnknowns()) {deferred=true;continue;}
    if(!last.isNumber() || !last.number().isInteger() || last.number()<minimum.number() || last.number()>1023) {
     CALCULATOR->error(true,"An indexed array endpoint must be an integer respecting its displayed entries and the 1024-axis limit.",NULL);return 0;
    }
    dimensions[axis]=last.number().intValue()+1;
   }
   if(deferred)return 0;
   out.clearMatrix();out.resizeMatrix(dimensions[0],dimensions[1],m_zero);
   for(int row=0;row<dimensions[0];++row)for(int col=0;col<dimensions[1];++col) {
    if(CALCULATOR->aborted())return 0;
    int index=op=="qdescendingcolumn" ? dimensions[0]-1-row : row;
    element(out,row,col).set(prefix+std::to_string(index)+(matrix ? ","+std::to_string(col) : ""),true);
   }
   return 1;
  }
  if(op=="qindexedlabel") {
   MathStructure prefix=raw[0],index=raw[1],suffix=raw[2];
   prefix.eval(eo);index.eval(eo);suffix.eval(eo);
   if(!prefix.isSymbolic() || !suffix.isSymbolic() || !index.isNumber() || !index.number().isInteger())return 0;
   PrintOptions print;print.use_unicode_signs=false;print.min_exp=EXP_NONE;
   out.set(prefix.symbol()+index.print(print)+suffix.symbol(),true);return 1;
  }
  if(op=="qstatecalls") {
   MathStructure arguments=raw[1];arguments.eval(eo);
   if(!arguments.isVector() || arguments.isMatrix() || arguments.size()<2 || arguments.size()>16) {CALCULATOR->error(true,"A state-family argument list requires 2 to 16 scalars.",NULL);return 0;}
   for(size_t k=0;k<arguments.size();++k)if(!arguments[k].representsScalar() || arguments[k].isUndefined() || (arguments[k].isNumber() && arguments[k].number().isInfinite(false))) {CALCULATOR->error(true,"State-family arguments must be finite scalars.",NULL);return 0;}
   MathFunction *family=CALCULATOR->getFunction("__qstate_family_"+raw[0].symbol());
   if(!family) {if(arguments.equals(raw[1]))return 0;out.set(this,&raw[0],&arguments,NULL);return 1;}
   if(family->args()!=int(arguments.size())) {CALCULATOR->error(true,"Wrong number of state-family arguments.",NULL);return 0;}
   out.set(family,&arguments[0],NULL);for(size_t k=1;k<arguments.size();++k)out.addChild(arguments[k]);out.eval(eo);return 1;
  }
  if(op=="qstatecall") {
   MathStructure argument=raw[1];argument.eval(eo);
   if(!argument.representsScalar() || argument.isUndefined() || (argument.isNumber() && argument.number().isInfinite(false))) {CALCULATOR->error(true,"A state-family argument must be a finite scalar expression.",NULL);return 0;}
   MathFunction *family=CALCULATOR->getFunction("__qstate_family_"+raw[0].symbol());
   if(!family) {
    if(argument.equals(raw[1]))return 0;
    out.set(this,&raw[0],&argument,NULL);return 1;
   }
   out.set(family,&argument,NULL);out.eval(eo);return 1;
  }
  if(op=="qsum") {
   if((!raw[3].isSymbolic() && !raw[3].isVariable()) || (raw[3].isVariable() && raw[3].variable()->isKnown())) {
    CALCULATOR->error(true,"A finite sum index must be a symbolic variable.",NULL);return 0;
   }
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure first=raw[1],last=raw[2];first.eval(exact);last.eval(exact);
   if(quantumBasisSum(raw[0],first,last,raw[3],out,eo))return 1;
   bool pending=false;
   for(const MathStructure *bound:{&first,&last}) {
    if(bound->isNumber() && bound->number().isInteger())continue;
    if(!bound->isNumber() && !bound->isVector() && bound->containsUnknowns()) {pending=true;continue;}
    CALCULATOR->error(true,"Finite sum bounds must be integers or unresolved symbolic expressions.",NULL);return 0;
   }
   // Keep the scoped body intact until both endpoints have numerical values.
   if(pending || CALCULATOR->aborted())return 0;
   if(last.number()<first.number()) {CALCULATOR->error(true,"Finite sum bounds must be ascending.",NULL);return 0;}
   MathStructure parameters=raw;parameters[1]=first;parameters[2]=last;
   if(first.number().isZero()) {
    Number dimension=last.number();dimension+=1;
    MathStructure basisDimension(dimension);
    inferSumBasis(parameters[0],raw[3],&basisDimension);
   }
   // The generic sum substitutes recursively. Give this binder a fresh name
   // first, so it cannot replace a nested sum's declaration or bound body.
   unsigned serial=0;MathStructure index;
   do {
    if(CALCULATOR->aborted())return 0;
    index=MathStructure("__qsum_index_"+std::to_string(serial++),true);
   } while(raw.contains(index));
   replaceQuantumIndex(parameters[0],raw[3],index);parameters[3]=index;parameters.childrenUpdated();
   auto sum=CALCULATOR->getFunction("sum");if(!sum)return 0;
   return sum->calculate(out,parameters,eo);
  }
  if(op=="qbitstrings" || op=="qbitlabel") {
   if(op=="qbitlabel") {
    MathStructure index=raw[0],width=raw[1];
    validateQuantumBitLabel(index,width,eo);
    // Retain the descriptor and its constraints until all fields are concrete.
    return 0;
   }
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure width=raw[op=="qbitlabel" ? 1 : 0];width.eval(exact);
   if(!width.isNumber() && width.representsScalar() && width.containsUnknowns())return 0;
   if(!width.isNumber() || !width.number().isInteger() || width.number()<0) {CALCULATOR->error(true,"Binary-string widths must be nonnegative integers.",NULL);return 0;}
   if(width.number()>10)return 0;
   int count=1<<width.number().intValue();
   auto label=CALCULATOR->getFunction("qbitlabel");if(!label)return 0;
   out.clearVector();
   for(int k=0;k<count;++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure index(k),entry;entry.set(label,&index,&width,NULL);out.addChild(entry);
   }
   MathStructure entries=out;out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;
  }
  if(op=="qindexrange") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure first=raw[0],last=raw[1];first.eval(exact);last.eval(exact);
   bool pending=false;
   for(const MathStructure *bound:{&first,&last}) {
    if(!bound->isNumber() && bound->representsScalar() && bound->containsUnknowns()) {pending=true;continue;}
    if(!bound->isNumber() || !bound->number().isInteger()) {CALCULATOR->error(true,"Finite index ranges require integer endpoints.",NULL);return 0;}
   }
   if(pending)return 0;
   if(CALCULATOR->aborted())return 0;
   out.clearVector();Number span=last.number();span-=first.number();
   if(span.isNegative()) {MathStructure entries=out;out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;}
   if(span>1023) {CALCULATOR->error(true,"Finite index ranges support at most 1024 entries.",NULL);return 0;}
   int count=span.intValue()+1;Number value=first.number();
   for(int k=0;k<count;++k) {
    if(CALCULATOR->aborted())return 0;
    out.addChild(MathStructure(value));value+=1;
   }
   MathStructure entries=out;out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;
  }
  if(op=="qbars") {
   MathStructure source=raw[0];
   for(unsigned depth=0;eo.calculate_variables && depth<128 && source.isVariable() && source.variable()->isKnown();++depth) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=((KnownVariable*)source.variable())->get();
    if(value.equals(source))break;
    source=value;
   }
   bool collection=collectionExpression(source);
   MathStructure value=raw[0];value.eval(eo);
   // A bare unknown may later denote a collection or a scalar. Preserve the
   // overloaded bars until substitution determines cardinality or magnitude.
   if(!collection && (value.isSymbolic() || (value.isVariable() && !value.variable()->isKnown())))return 0;
   if(collection || value.isVector()) {
    MathStructure parameters;parameters.clearVector();parameters.addChild(m_one);parameters.addChild(raw[0]);parameters.addChild(MathStructure("__cardinality_index",true));
    auto sum=CALCULATOR->getFunction("qsumset");if(!sum)return 0;
    return sum->calculate(out,parameters,eo);
   }
   // A sum over an unresolved domain can later produce a scalar or a
   // collection. Retain the bars so substitution can determine the result.
   if(value.isFunction() && value.function()->referenceName()=="qsumset" && value.containsUnknowns())return 0;
   if(!value.representsScalar()) {CALCULATOR->error(true,"Bars require a scalar or finite flat collection.",NULL);return 0;}
   auto absolute=CALCULATOR->getFunction("abs");if(!absolute)return 0;
   out.set(absolute,&value,NULL);out.eval(eo);return 1;
  }
  if(op=="qsumset" || op=="qmember") {
   if(op=="qsumset" && ((!raw[2].isSymbolic() && !raw[2].isVariable()) || (raw[2].isVariable() && raw[2].variable()->isKnown()))) {CALCULATOR->error(true,"A set sum index must be a symbolic variable.",NULL);return 0;}
   MathStructure collection=raw[1];
   for(unsigned depth=0;eo.calculate_variables && depth<128 && collection.isVariable() && collection.variable()->isKnown();++depth) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=((KnownVariable*)collection.variable())->get();
    if(value.equals(collection))break;
    collection=value;
   }
   MathStructure members;
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   evaluateDomain(raw[1],members,exact);
   if(members.isFunction() && members.function()->referenceName()=="qset" && members.size()==1) {MathStructure entries=members[0];members=entries;}
   // The generic evaluator collapses a singleton function-result vector.
   // Preserve the collection type of the set operations used by TeX builders.
   bool bitLabel=members.isFunction() && members.function()->referenceName()=="qbitlabel";
   bool tuple=members.isFunction() && members.function()->referenceName()=="qtuple";
   if(!members.isVector() && (members.representsScalar() || bitLabel || tuple) && collectionExpression(collection))
    members.transform(STRUCT_VECTOR);
   // Distinct symbolic labels may become equal after substitution. Do not
   // count, deduplicate, or test membership before their domains are known.
   bool deferredLabels=false;
   auto validateLabel=[&](MathStructure &value)->bool {
    return canonicalSetElement(value,exact,deferredLabels);
   };
   MathStructure probe=raw[0];
   if(op=="qmember") {
    probe.eval(exact);
    if(!validateLabel(probe)) {CALCULATOR->error(true,"Membership requires a scalar or binary-string label.",NULL);return 0;}
   }
   // Validate the probe even when its domain is not yet specified.
   // Count a concrete binary-string domain without enumerating its elements.
   // Unknown widths retain the domain so later substitution still validates it.
   if(op=="qsumset" && raw[0].isOne() && members.isFunction() &&
      members.function()->referenceName()=="qbitstrings" && members.size()==1) {
    MathStructure width=members[0];width.eval(exact);
    if(width.isNumber() && width.number().isInteger() && width.number()>=0 && width.number()<=4096) {
     Number count(1);if(!count.shiftLeft(width.number()))return 0;
     out=MathStructure(count);return 1;
    }
   }
   if(pendingDomain(members))return 0;
   if(!members.isVector() || members.size()>1024) {CALCULATOR->error(true,"A set sum requires a finite flat vector of at most 1024 scalar indices.",NULL);return 0;}
   for(size_t k=0;k<members.size();++k)if(!validateLabel(members[k])) {
    CALCULATOR->error(true,"Set entries must be scalars or valid binary-string labels.",NULL);return 0;
   }
   if(deferredLabels)return 0;
   if(op=="qmember") {
    bool found=false,unknown=false;
    for(size_t k=0;k<members.size();++k) {
     if(CALCULATOR->aborted())return 0;
     SetEquality equality=setEquality(probe,members[k]);
     found=found || equality==SetEquality::Equal;
     unknown=unknown || equality==SetEquality::Unknown;
    }
    if(!found && unknown)return 0;
    out=found ? m_one : m_zero;return 1;
   }
   MathStructure body=raw[0];
   unsigned dimension=completeSetBasisDimension(members);
   if(dimension) {
    MathStructure basisDimension(static_cast<int>(dimension));
    inferSumBasis(body,raw[2],&basisDimension);
   } else if(members.size() && inferSumBasis(body,raw[2],NULL)) {
    // A proper subset of nonnegative indices does not determine the ambient
    // basis. Keep the scoped sum intact; invalid indices still reach validation.
    bool numericIndices=true;
    for(size_t k=0;k<members.size();++k)
     numericIndices=numericIndices && members[k].isNumber() &&
                    members[k].number().isInteger() && members[k].number()>=0;
    if(numericIndices) {
     validatePendingSum(body,raw[2],members,eo);
     return 0;
    }
   }
   std::vector<MathStructure> seen;
   out=m_zero;
   for(size_t k=0;k<members.size();++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &member=members[k];
    bool duplicate=false;
    for(const auto &previous:seen) {
     SetEquality equality=setEquality(member,previous);
     if(equality==SetEquality::Equal) {duplicate=true;break;}
     if(equality==SetEquality::Unknown)return 0;
    }
    if(duplicate)continue;
    seen.push_back(member);
    MathStructure term=body;replaceQuantumIndex(term,raw[2],member);term.eval(eo);
    if(seen.size()==1)out=term;else {out.add(term);out.eval(eo);}
   }
   return 1;
  }
  if(op=="qsequence") {
   if((!raw[2].isSymbolic() && !raw[2].isVariable()) || (raw[2].isVariable() && raw[2].variable()->isKnown())) {CALCULATOR->error(true,"A sequence state placeholder must be a symbolic variable.",NULL);return 0;}
   const MathStructure &steps=raw[0];
   if((!steps.isVector() && !(steps.isFunction() && (steps.function()->referenceName()=="vector" || steps.function()->referenceName()=="horzcat"))) || steps.size()>512) {CALCULATOR->error(true,"A sequence requires a flat list of at most 512 transformations.",NULL);return 0;}
   out=raw[1];out.eval(eo);
   auto validState=[](const MathStructure &state) {
    if(state.isMatrix()) {
     if(state.rows()==0 || state.columns()==0 || state.rows()>1024 || state.columns()>1024 || state.rows()*state.columns()>1048576)return false;
     for(size_t r=0;r<state.rows();++r)for(size_t c=0;c<state.columns();++c)if(!state.getElement(r+1,c+1)->representsScalar())return false;
     return true;
    }
    if(!state.isVector() || state.size()==0 || state.size()>1024)return false;
    for(size_t k=0;k<state.size();++k)if(!state[k].representsScalar())return false;
    return true;
   };
   if(!validState(out)) {CALCULATOR->error(true,"A sequence requires a bounded state vector or matrix.",NULL);return 0;}
   for(size_t k=0;k<steps.size();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure next=steps[k];replaceQuantumIndex(next,raw[2],out);next.eval(eo);
    if(!validState(next)) {CALCULATOR->error(true,"A sequence transformation did not produce a bounded state vector or matrix.",NULL);return 0;}
    out=next;
   }
   return 1;
  }
  if(op=="qphasefunction") {
   if((!raw[2].isSymbolic() && !raw[2].isVariable()) || (raw[2].isVariable() && raw[2].variable()->isKnown())) {CALCULATOR->error(true,"A phase function index must be a symbolic variable.",NULL);return 0;}
   MathStructure width=raw[1];width.eval(eo);
   if(!width.isNumber() || !width.number().isInteger() || width.number()<1 || width.number()>9) {CALCULATOR->error(true,"Phase functions require an integer width from 1 to 9 qubits.",NULL);return 0;}
   int count=1<<width.number().intValue();
   out.clearMatrix();out.resizeMatrix(count,count,m_zero);
   for(int x=0;x<count;++x) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=raw[0],index(x);replaceQuantumIndex(value,raw[2],index);value.eval(eo);
    if(!value.isNumber() || (!value.number().isZero() && !value.number().isOne())) {CALCULATOR->error(true,"A phase function must evaluate to 0 or 1 at every input index.",NULL);return 0;}
    element(out,x,x)=MathStructure(value.number().isOne() ? -1 : 1);
   }
   return 1;
  }
  if(op=="qoraclefunction") {
   if((!raw[3].isSymbolic() && !raw[3].isVariable()) || (raw[3].isVariable() && raw[3].variable()->isKnown())) {CALCULATOR->error(true,"An oracle function index must be a symbolic variable.",NULL);return 0;}
   MathStructure inputBits=raw[1],outputBits=raw[2];inputBits.eval(eo);outputBits.eval(eo);
   if(!inputBits.isNumber() || !outputBits.isNumber() || !inputBits.number().isInteger() || !outputBits.number().isInteger() || inputBits.number()<1 || outputBits.number()<1 || inputBits.number()>8 || outputBits.number()>8 || inputBits.number()+outputBits.number()>9) {CALCULATOR->error(true,"Oracle register widths must be positive integers with at most 9 total qubits.",NULL);return 0;}
   int count=1<<inputBits.number().intValue(),outputs=1<<outputBits.number().intValue();
   MathStructure table;table.clearVector();
   for(int x=0;x<count;++x) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=raw[0],index(x);replaceQuantumIndex(value,raw[3],index);value.eval(eo);
    if(!value.isNumber() || !value.number().isInteger() || value.number()<0 || value.number()>=Number(outputs)) {CALCULATOR->error(true,"Each oracle function value must be an integer from 0 to 2^m-1.",NULL);return 0;}
    table.addChild(value);
   }
   MathStructure parameters;parameters.clearVector();parameters.addChild(table);parameters.addChild(outputBits);
   auto oracle=CALCULATOR->getFunction("qoracle");
   if(!oracle) {CALCULATOR->error(true,"The quantum oracle function is unavailable.",NULL);return 0;}
   return oracle->calculate(out,parameters,eo);
  }
  if(op=="qtensorseries" || op=="qboundtensorseries") {
   MathStructure history;history.clearVector();
   if(op=="qboundtensorseries" && !tensorReplacementHistory(raw[5],history)) {
    CALCULATOR->error(true,"Invalid tensor series replacement history.",NULL);return 0;
   }
   MathStructure first,last,step,length;
   if(!tensorSeriesBounds(raw,first,last,step,length,eo,true))return 0;
   // Bounds, not the body, determine whether a product is empty. In
   // particular an empty product must not evaluate an unresolved domain.
   if(!first.isNumber() || !last.isNumber())return 0;
   Number count=length.number();
   if(count.isZero()) {out.setToIdentityMatrix(1);return 1;}
   // Large valid series remain intact, so later substitutions and Copy keep
   // the original factor and order without enumerating an arbitrary range.
   if(count>32)return 0;
   Number index=first.number();
   for(int k=0;k<count.intValue();++k,index+=step.number()) {
    if(CALCULATOR->aborted())return 0;
    MathStructure factor=raw[0],value(index);replaceQuantumIndex(factor,raw[3],value);
    for(size_t j=0;j<history.size();j+=2) {
     if(CALCULATOR->aborted())return 0;
     resolveIndexedLabels(factor,eo);
     replaceQuantumIndex(factor,history[j],history[j+1],false,false,true);
     bindRegisterBit(factor,history[j],history[j+1],true);
    }
    factor.eval(eo);
    if(k==0)out=factor;
    else {MathStructure previous=out;out.set(CALCULATOR->getFunction("qtensor"),&previous,&factor,NULL);out.eval(eo);}
   }
   return 1;
  }
  if(op=="qtensorproduct" || op=="qblocksum") {
   if((!raw[3].isSymbolic() && !raw[3].isVariable()) || (raw[3].isVariable() && raw[3].variable()->isKnown())) {CALCULATOR->error(true,"An indexed operation index must be a symbolic variable.",NULL);return 0;}
   MathStructure first=raw[1],last=raw[2];first.eval(eo);last.eval(eo);
   if(!first.isNumber() || !last.isNumber() || !first.number().isInteger() || !last.number().isInteger() || first.number() < -1000000 || last.number()>1000000 || last.number()<first.number()) {
    CALCULATOR->error(true,"Indexed operations require ascending integer bounds within -1000000 to 1000000.",NULL);return 0;
   }
   Number span=last.number();span-=first.number();
   if(span>31) {CALCULATOR->error(true,"Indexed operations support at most 32 terms.",NULL);return 0;}
   out.setToIdentityMatrix(1);
   for(int k=first.number().intValue();k<=last.number().intValue();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure factor=raw[0],index(k);replaceQuantumIndex(factor,raw[3],index);factor.eval(eo);
    if(op=="qblocksum") {
     // Scalar blocks denote one-dimensional linear maps, not state labels.
     if(factor.representsScalar()) {
      MathStructure scalar=factor;factor.clearMatrix();factor.resizeMatrix(1,1,m_zero);element(factor,0,0)=scalar;
     }
     if(factor.isVector() && !factor.isMatrix() && factor.size()>0 && factor.size()<=1024) {
      bool flat=true;for(size_t c=0;c<factor.size();++c)if(factor[c].isVector())flat=false;
      if(flat) {MathStructure row=factor;factor.clearMatrix();factor.resizeMatrix(1,row.size(),m_zero);for(size_t c=0;c<row.size();++c)element(factor,0,c)=row[c];}
     }
     if(!factor.isMatrix()) {CALCULATOR->error(true,"Block sums require matrix or scalar blocks.",NULL);return 0;}
     if(factor.rows()>1024 || factor.columns()>1024 || factor.rows()*factor.columns()>1048576) {CALCULATOR->error(true,"Block sum matrix allocation limit exceeded.",NULL);return 0;}
     if(k==first.number().intValue()) {out=factor;continue;}
     // Evaluation can collapse a 1x1 matrix to its scalar entry.
     if(!out.isVector()) {MathStructure scalar=out;out.clearMatrix();out.resizeMatrix(1,1,m_zero);element(out,0,0)=scalar;}
     // Build directly so a one-row rectangular block keeps its matrix shape.
     size_t rows=out.rows()+factor.rows(),cols=out.columns()+factor.columns();
     if(rows>1024 || cols>1024 || rows*cols>1048576) {CALCULATOR->error(true,"Block sum matrix allocation limit exceeded.",NULL);return 0;}
     MathStructure previous=out;out.clearMatrix();out.resizeMatrix(rows,cols,m_zero);
     for(size_t r=0;r<previous.rows();++r)for(size_t c=0;c<previous.columns();++c)element(out,r,c)=element(previous,r,c);
     for(size_t r=0;r<factor.rows();++r)for(size_t c=0;c<factor.columns();++c)element(out,r+previous.rows(),c+previous.columns())=element(factor,r,c);
    } else {
     MathStructure previous=out;out.set(CALCULATOR->getFunction("qtensor"),&previous,&factor,NULL);out.eval(eo);
    }
    if(!out.isMatrix() && !out.isVector())return 0;
   }
   return 1;
  }
  return 0;
 }
};
}
namespace {
bool replayShapeHistory(MathStructure &factor,const MathStructure &history,const EvaluationOptions &eo) {
 std::vector<MathStructure> indexedDependencies;
 for(size_t k=0;k<history.size();k+=2) {
  if(CALCULATOR->aborted())return false;
  resolveIndexedLabels(factor,eo);
  bool affectsIndexed=implicitIndexedName(factor,history[k]);
  for(const auto &dependency:indexedDependencies)
   affectsIndexed=affectsIndexed || scalarProductFree(dependency,history[k],true) || implicitIndexedName(dependency,history[k]);
  if(affectsIndexed) {
   // The bound index has not been instantiated, so ordinary replacement
   // cannot apply this key yet. Never infer a uniform scalar coefficient if
   // its deferred replacement (including a later dependency) may be a matrix.
   if(!scalarExpression(history[k+1]))return false;
   indexedDependencies.push_back(history[k+1]);
  }
  replaceQuantumIndex(factor,history[k],history[k+1],false,false,true);
  bindRegisterBit(factor,history[k],history[k+1],true);
 }
 return true;
}
}
bool quantumTensorSeriesShapeInput(const MathStructure &value,MathStructure &factor,MathStructure &count,const EvaluationOptions &eo) {
 if(!tensorSeriesNode(value))return false;
 MathStructure first,last,step,history;history.clearVector();
 if(value.size()==6 && !tensorReplacementHistory(value[5],history))return false;
 if(!tensorSeriesBounds(value,first,last,step,count,eo,false))return false;
 factor=value[0];
 return count.isZero() || replayShapeHistory(factor,history,eo);
}
bool quantumRegisterSumShapeInput(const MathStructure &value,MathStructure &term,MathStructure &markers,const EvaluationOptions &eo) {
 if(!registerSumNode(value))return false;
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 MathStructure args=value,history,difference;
 if(!registerSumArguments(args,history,difference,exact,false) || !difference.isZero())return false;
 unsigned dimension=1;
 if(!args[5].isZero()) {
  MathStructure members;
  if(finiteDomain(args[1],members,exact)!=DomainState::Finite || unresolvedSetEquality(members))return false;
  dimension=completeSetBasisDimension(members);if(!dimension)return false;
 }
 if(!freshRegisterFamily(args,m_zero,m_zero))return false;
 unsigned serial=0;std::string markerPrefix;
 do {
  if(CALCULATOR->aborted())return false;
  unsigned code=serial++;std::string name="__qregister_shape_";
  do {name+=char('a'+code%26);code/=26;}while(code);
  markerPrefix=name+"_";
 }while(containsFamilyPrefix(args,markerPrefix));
 markers.clearVector();
 term=args[0];
 if(!replayShapeHistory(term,history,exact))return false;
 RegisterShapeProjection projection{args[4],args[2],args[3],args[5],markerPrefix,markers,dimension};
 return projectRegisterShape(term,projection,exact);
}
bool compareQuantumSets(const MathStructure &left,const MathStructure &right,bool &equal,const EvaluationOptions &eo) {
 MathStructure sets[2];
 if(finiteDomain(left,sets[0],eo)!=DomainState::Finite || finiteDomain(right,sets[1],eo)!=DomainState::Finite)return false;
 bool pending=false;
 for(unsigned side=0;side<2;++side) {
  const MathStructure &source=sets[side],&target=sets[1-side];
  for(size_t k=0;k<source.size();++k) {
   if(CALCULATOR->aborted())return false;
   bool found=false,unknown=false;
   for(size_t j=0;j<target.size();++j) {
    SetEquality match=setEquality(source[k],target[j]);
    if(match==SetEquality::Equal) {found=true;break;}
    if(match==SetEquality::Unknown)unknown=true;
   }
   if(!found && !unknown) {equal=false;return true;}
   if(!found)pending=true;
  }
 }
 equal=true;return !pending;
}
bool quantumScalarExpression(const MathStructure &value) {return scalarExpression(value);}
bool quantumReplacementShapeInput(const MathStructure &value,MathStructure &term,const EvaluationOptions &eo) {
 if(!value.isFunction() || value.function()->referenceName()!="qreplace" || value.size()!=3 ||
    (!hasRegisterSum(value[0]) && !hasTensorSeries(value[0])))return false;
 // Products can retain the original replacement wrapper after evaluating a
 // temporary operand. Apply the indexed replacement operation to a copy only;
 // its ordered history stays intact and the resulting body is not evaluated.
 MathStructure arguments;arguments.clearVector();
 for(size_t k=0;k<value.size();++k)arguments.addChild(value[k]);
 return value.function()->calculate(term,arguments,eo)==1;
}
bool quantumSetSumShapeInput(const MathStructure &value,MathStructure &term,const EvaluationOptions &eo) {
 if(!value.isFunction() || value.function()->referenceName()!="qsumset" || value.size()!=3)return false;
 if((!value[2].isSymbolic() && !value[2].isVariable()) || (value[2].isVariable() && value[2].variable()->isKnown()))return false;
 MathStructure members;
 if(finiteDomain(value[1],members,eo)!=DomainState::Finite || members.size()==0)return false;
 term=value[0];unsigned dimension=completeSetBasisDimension(members);
 if(dimension) {MathStructure size{Number(dimension)};inferSumBasis(term,value[2],&size);}
 return true;
}
void registerQuantumIndexed(Calculator &calculator) {
 calculator.addFunction(new QuantumIndexedFunction("qindexedlabel",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedcolumn",3));
 calculator.addFunction(new QuantumIndexedFunction("qdescendingcolumn",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedmatrix",5));
 calculator.addFunction(new QuantumIndexedFunction("qindexedcoefficient",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedket",1));
 calculator.addFunction(new QuantumIndexedFunction("qfamilymembers",4));
 calculator.addFunction(new QuantumIndexedFunction("qregisterfamily",4));
 calculator.addFunction(new QuantumIndexedFunction("qregisterword",4));
 calculator.addFunction(new QuantumIndexedFunction("qregistersum",7));
 calculator.addFunction(new QuantumIndexedFunction("qregisterelement",2));
 calculator.addFunction(new QuantumIndexedFunction("qtensorseries",5));
 calculator.addFunction(new QuantumIndexedFunction("qboundtensorseries",6));
 calculator.addFunction(new QuantumIndexedFunction("qscalarproductsum",4));
 calculator.addFunction(new QuantumIndexedFunction("qreplace",3));
 calculator.addFunction(new QuantumIndexedFunction("qstatecall",2));
 calculator.addFunction(new QuantumIndexedFunction("qstatecalls",2));
 calculator.addFunction(new QuantumIndexedFunction("qsum",4));
 calculator.addFunction(new QuantumIndexedFunction("qbars",1));
 calculator.addFunction(new QuantumIndexedFunction("qmember",2));
 calculator.addFunction(new QuantumIndexedFunction("qbitstrings",1));
 calculator.addFunction(new QuantumIndexedFunction("qbitlabel",2));
 calculator.addFunction(new QuantumIndexedFunction("qpreimage",2));
 calculator.addFunction(new QuantumIndexedFunction("qfunctiontype",3));
 calculator.addFunction(new QuantumIndexedFunction("qfunctionrange",1));
 calculator.addFunction(new QuantumIndexedFunction("qwordpower",2));
 calculator.addFunction(new QuantumIndexedFunction("qtuple",1));
 calculator.addFunction(new QuantumIndexedFunction("qset",1));
 calculator.addFunction(new QuantumIndexedFunction("qdomainvector",1));
 calculator.addFunction(new QuantumIndexedFunction("qdomainresult",2));
 calculator.addFunction(new QuantumIndexedFunction("qcartesian",2));
 calculator.addFunction(new QuantumIndexedFunction("qcartesianpower",2));
 calculator.addFunction(new QuantumIndexedFunction("qsetimage",3));
 calculator.addFunction(new QuantumIndexedFunction("qsetfilter",3));
 for(const char *name:{"qsetunion","qsetintersect","qsetdiff"})calculator.addFunction(new QuantumIndexedFunction(name,2));
 for(const auto &entry:{std::pair<const char *,int>("qphasefunction",3),{"qsequence",3},{"qsumset",3},{"qindexrange",2},{"qoraclefunction",4},{"qtensorproduct",4},{"qblocksum",4}})calculator.addFunction(new QuantumIndexedFunction(entry.first,entry.second));
}
void defineQuantumStateFamily(Calculator &calculator,const std::string &name,const MathStructure &body,const MathStructure &parameter) {
 defineQuantumStateFamily(calculator,name,body,std::vector<MathStructure>{parameter});
}

void defineQuantumStateFamily(Calculator &calculator,const std::string &name,const MathStructure &body,const std::vector<MathStructure> &parameters) {
 if(parameters.empty() || parameters.size()>16)throw std::invalid_argument("State families require 1 to 16 parameters.");
 for(size_t k=0;k<parameters.size();++k) {
  if(!parameters[k].isSymbolic() && (!parameters[k].isVariable() || parameters[k].variable()->isKnown()))throw std::invalid_argument("State-family parameters must be unknown symbols.");
  for(size_t j=0;j<k;++j)if(parameters[k].equals(parameters[j]))throw std::invalid_argument("State-family parameters must be distinct.");
 }
 calculator.addFunction(new QuantumStateFamilyFunction(name,body,parameters));
}

// Apply declarations before evaluating the body; assumptions alone disappear
// when a family parameter is replaced by an ordinary unknown argument.
void declareQuantumComplexParameter(Calculator &calculator,MathStructure &body,const MathStructure &parameter) {
 if(!parameter.isSymbolic() && (!parameter.isVariable() || parameter.variable()->isKnown()))throw std::invalid_argument("Complex parameters must be unknown symbols.");
 auto function=calculator.getFunction("complexparam");
 if(!function)throw std::logic_error("Complex parameter support is not registered.");
 MathStructure replacement;replacement.set(function,&parameter,NULL);
 replaceQuantumIndex(body,parameter,replacement,true);
}

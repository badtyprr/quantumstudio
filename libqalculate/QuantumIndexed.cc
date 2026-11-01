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
QuantumBitLabelState validateQuantumBitLabel(MathStructure &index,MathStructure &width,const EvaluationOptions &eo) {
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 index.eval(exact);width.eval(exact);
 bool symbolicIndex=!index.isNumber() && index.representsScalar() && index.containsUnknowns();
 bool symbolicWidth=!width.isNumber() && width.representsScalar() && width.containsUnknowns();
 if((!symbolicWidth && (!width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10)) ||
    (!symbolicIndex && (!index.isNumber() || !index.number().isInteger() || index.number()<0)) ||
    (!symbolicIndex && !symbolicWidth && index.number()>=Number(1<<width.number().intValue()))) {
  CALCULATOR->error(true,"Binary-string labels require integer width 0 to 10 and a nonnegative integer value fitting that width.",NULL);
  return QuantumBitLabelState::Invalid;
 }
 return symbolicIndex || symbolicWidth ? QuantumBitLabelState::Symbolic : QuantumBitLabelState::Concrete;
}
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
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
 return name=="qset" || name=="qbitstrings" || name=="qindexrange" || name=="qcartesian" || name=="qcartesianpower" || name=="qsetimage" || name=="qsetfilter" || name=="qsetunion" || name=="qsetintersect" || name=="qsetdiff";
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
DomainState finiteDomain(const MathStructure &raw,MathStructure &members,const EvaluationOptions &eo) {
 members=raw;members.eval(eo);
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
bool registerBitIndex(const MathStructure &label,const std::string &prefix,long &index) {
 if(!label.isSymbolic() || label.symbol().compare(0,prefix.size(),prefix)!=0)return false;
 std::string suffix=label.symbol().substr(prefix.size());
 if(suffix.empty() || suffix.size()>7)return false;
 index=0;for(char c:suffix) {if(c<'0' || c>'9')return false;index=index*10+c-'0';}
 return index<=1000000 && suffix==std::to_string(index);
}
bool bindRegisterBit(MathStructure &value,const MathStructure &label,const MathStructure &bit) {
 bool changed=false;
 if(value.isFunction() && value.function()->referenceName()=="qregisterfamily" && value.size()==4 && value[0].isSymbolic()) {
  long index;
  if(registerBitIndex(label,value[0].symbol(),index) && value[3].isVector() && value[3].size()%2==0) {
   // Do not claim an unrelated label when concrete bounds already exclude it.
   if(value[1].isNumber() && value[2].isNumber() &&
      (Number(index)>value[1].number() || Number(index)<value[2].number()))return false;
   for(size_t k=0;k<value[3].size();k+=2)if(value[3][k].isNumber() && value[3][k].number()==Number(index)) {
    // This label was already substituted. Later replacements act only on
    // free occurrences in its stored value, not on this metadata key.
    return false;
   }
   if(value[3].size()>=256) {CALCULATOR->error(true,"A register family supports at most 128 supplied bit values.",NULL);return false;}
   value[3].addChild(MathStructure(Number(index)));value[3].addChild(bit);value.childrenUpdated();return true;
  }
 }
 for(size_t k=0;k<value.size();++k)changed=bindRegisterBit(value[k],label,bit) || changed;
 if(changed)value.childrenUpdated();return changed;
}
// These operations bind an index in their first argument only.
int quantumBinderPosition(const MathStructure &value) {
 int bound=-1;
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
// Substitute a free index without capturing a nested finite-product/sum index.
void replaceQuantumIndex(MathStructure &value,const MathStructure &index,const MathStructure &replacement,bool preserveComplexDomain=false) {
 if(preserveComplexDomain && value.isFunction() && value.function()->referenceName()=="complexparam")return;
 if(value.equals(index)) {value=replacement;return;}
 int declaration=quantumBinderPosition(value);
 if(declaration>=0 && !value[declaration].equals(index) &&
    (value[declaration].isSymbolic() || value[declaration].isVariable()) &&
    replacement.contains(value[declaration]) && value[0].contains(index)) {
  // A free name in a symbolic replacement must not become a nested index.
  // Rename only its bound body; range endpoints and initial states are free.
  unsigned serial=0;MathStructure fresh;
  do {fresh=MathStructure("__qbound_index_"+std::to_string(serial++),true);}
  while(value.contains(fresh) || replacement.contains(fresh) || index.equals(fresh));
  MathStructure old=value[declaration];
  replaceQuantumIndex(value[0],old,fresh);value[declaration]=fresh;
 }
 int bound=quantumIndexBinder(value,index);
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  replaceQuantumIndex(value[k],index,replacement,preserveComplexDomain);
 }
 value.childrenUpdated();
}
// The complete range 0..d-1 supplies a basis for bare kets/bras of its index.
// Explicit basis dimensions and nested declarations retain their own meaning.
void inferSumBasis(MathStructure &value,const MathStructure &index,const MathStructure &dimension) {
 if(value.isFunction() && value.size()==1 && value[0].equals(index) &&
    (value.function()->referenceName()=="qketstate" || value.function()->referenceName()=="qnamedket")) {
  auto basis=CALCULATOR->getFunction("qbasis");
  if(basis)value.set(basis,&index,&dimension,NULL);
  return;
 }
 int bound=quantumIndexBinder(value,index);
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  inferSumBasis(value[k],index,dimension);
 }
 value.childrenUpdated();
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
 QuantumIndexedFunction(const char *name,int count):MathFunction(name,count),op(name) {if(op=="qstatecall" || op=="qstatecalls" || op=="qindexedcolumn" || op=="qindexedmatrix" || op=="qindexedcoefficient" || op=="qregisterfamily")setArgumentDefinition(1,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumIndexedFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
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
  if(op=="qregisterfamily") {
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
    if(!bound->isNumber() || !bound->number().isInteger() || bound->number()<0 || bound->number()>1000000) {
     CALCULATOR->error(true,"Register indices require integers from 0 to 1000000.",NULL);return 0;
    }
   }
   for(size_t k=0;k<bindings.size();k+=2) {
    if(!bindings[k].isNumber() || !bindings[k].number().isInteger() || bindings[k].number()<0 || bindings[k].number()>1000000) {CALCULATOR->error(true,"Invalid register bit index.",NULL);return 0;}
    long index=bindings[k].number().intValue();
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
   if(span<0 || span>9) {CALCULATOR->error(true,"A descending register family requires 1 to 10 bits.",NULL);return 0;}
   bool initial=true;
   for(long index=first.number().intValue();index>=last.number().intValue();--index) {
    MathStructure bit(prefix+std::to_string(index),true),dimension(2);
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
  if(op=="qindexedcolumn" || op=="qindexedmatrix") {
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
    element(out,row,col).set(prefix+std::to_string(row)+(matrix ? ","+std::to_string(col) : ""),true);
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
    inferSumBasis(parameters[0],raw[3],MathStructure(dimension));
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
   if(!width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10) {CALCULATOR->error(true,"Binary-string widths must be integers from 0 to 10.",NULL);return 0;}
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
   MathStructure members=raw[1];
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   members.eval(exact);
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
    MathStructure term=raw[0];replaceQuantumIndex(term,raw[2],member);term.eval(eo);
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
void registerQuantumIndexed(Calculator &calculator) {
 calculator.addFunction(new QuantumIndexedFunction("qindexedlabel",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedcolumn",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedmatrix",5));
 calculator.addFunction(new QuantumIndexedFunction("qindexedcoefficient",3));
 calculator.addFunction(new QuantumIndexedFunction("qindexedket",1));
 calculator.addFunction(new QuantumIndexedFunction("qregisterfamily",4));
 calculator.addFunction(new QuantumIndexedFunction("qreplace",3));
 calculator.addFunction(new QuantumIndexedFunction("qstatecall",2));
 calculator.addFunction(new QuantumIndexedFunction("qstatecalls",2));
 calculator.addFunction(new QuantumIndexedFunction("qsum",4));
 calculator.addFunction(new QuantumIndexedFunction("qbars",1));
 calculator.addFunction(new QuantumIndexedFunction("qmember",2));
 calculator.addFunction(new QuantumIndexedFunction("qbitstrings",1));
 calculator.addFunction(new QuantumIndexedFunction("qbitlabel",2));
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

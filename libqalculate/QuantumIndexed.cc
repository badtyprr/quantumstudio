// GPL-2.0-or-later; see COPYING.
#include "QuantumIndexed.h"
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include <string>
#include <utility>
#include <vector>
#include <stdexcept>
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
// These operations bind an index in their first argument only.
int quantumBinderPosition(const MathStructure &value) {
 int bound=-1;
 if(value.isFunction() && value.size()==4) {
  const std::string &name=value.function()->referenceName();
  if(name=="qtensorproduct" || name=="qblocksum" || name=="qoraclefunction" || name=="qsum" || name=="sum" || name=="product")bound=3;
 }
 if(value.isFunction() && value.size()==3 && (value.function()->referenceName()=="qphasefunction" || value.function()->referenceName()=="qsequence" || value.function()->referenceName()=="qsumset"))bound=2;
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
 QuantumIndexedFunction(const char *name,int count):MathFunction(name,count),op(name) {if(op=="qstatecall" || op=="qstatecalls")setArgumentDefinition(1,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumIndexedFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
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
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure width=raw[op=="qbitlabel" ? 1 : 0];width.eval(exact);
   if(!width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10) {CALCULATOR->error(true,"Binary-string widths must be integers from 0 to 10.",NULL);return 0;}
   int count=1<<width.number().intValue();
   if(op=="qbitlabel") {
    MathStructure index=raw[0];index.eval(exact);
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=count)CALCULATOR->error(true,"Binary-string value is outside its width.",NULL);
    // Preserve a typed label instead of collapsing it to an integer or ket.
    return 0;
   }
   auto label=CALCULATOR->getFunction("qbitlabel");if(!label)return 0;
   out.clearVector();
   for(int k=0;k<count;++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure index(k),entry;entry.set(label,&index,&width,NULL);out.addChild(entry);
   }
   return 1;
  }
  if(op=="qindexrange") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure first=raw[0],last=raw[1];first.eval(exact);last.eval(exact);
   if(!first.isNumber() || !last.isNumber() || !first.number().isInteger() || !last.number().isInteger()) {CALCULATOR->error(true,"Finite index ranges require evaluated integer endpoints.",NULL);return 0;}
   if(CALCULATOR->aborted())return 0;
   out.clearVector();Number span=last.number();span-=first.number();
   if(span.isNegative())return 1;
   if(span>1023) {CALCULATOR->error(true,"Finite index ranges support at most 1024 entries.",NULL);return 0;}
   int count=span.intValue()+1;Number value=first.number();
   for(int k=0;k<count;++k) {
    if(CALCULATOR->aborted())return 0;
    out.addChild(MathStructure(value));value+=1;
   }
   return 1;
  }
  if(op=="qbars") {
   MathStructure source=raw[0];
   for(unsigned depth=0;eo.calculate_variables && depth<128 && source.isVariable() && source.variable()->isKnown();++depth) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=((KnownVariable*)source.variable())->get();
    if(value.equals(source))break;
    source=value;
   }
   bool collection=source.isVector();
   if(source.isFunction()) {
    const std::string &name=source.function()->referenceName();
    collection=name=="qbitstrings" || name=="vector" || name=="union" || name=="intersect" || name=="setdiff" || name=="unique" || name=="select" || name=="qindexrange";
   }
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
   // The generic evaluator collapses a singleton function-result vector.
   // Preserve the collection type of the set operations used by TeX builders.
   bool bitLabel=members.isFunction() && members.function()->referenceName()=="qbitlabel";
   if(!members.isVector() && (members.representsScalar() || bitLabel) && (collection.isVector() || (collection.isFunction() &&
      (collection.function()->referenceName()=="qbitstrings" || collection.function()->referenceName()=="vector" || collection.function()->referenceName()=="union" || collection.function()->referenceName()=="intersect" || collection.function()->referenceName()=="setdiff" || collection.function()->referenceName()=="unique" || collection.function()->referenceName()=="select" || collection.function()->referenceName()=="qindexrange"))))
    members.transform(STRUCT_VECTOR);
   // An unspecified domain is not an invalid concrete collection. Preserve
   // symbolic singleton collections above before deferring an unknown domain.
   if(op=="qsumset" && (members.isSymbolic() || (members.isVariable() && !members.variable()->isKnown())))return 0;
   if(!members.isVector() || members.size()>1024) {CALCULATOR->error(true,"A set sum requires a finite flat vector of at most 1024 scalar indices.",NULL);return 0;}
   if(op=="qmember") {
    auto canonical=[&](MathStructure &value)->bool {
     if(value.isFunction() && value.function()->referenceName()=="qbitlabel") {
      if(value.size()!=2)return false;
      MathStructure index=value[0],width=value[1];index.eval(exact);width.eval(exact);
      if(!index.isNumber() || !index.number().isInteger() || !width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10 || index.number()<0 || index.number()>=Number(1<<width.number().intValue()))return false;
      auto function=value.function();value.set(function,&index,&width,NULL);return true;
     }
     return value.representsScalar();
    };
    MathStructure probe=raw[0];probe.eval(exact);
    if(!canonical(probe)) {CALCULATOR->error(true,"Membership requires a scalar or binary-string label.",NULL);return 0;}
    bool found=false,unknown=false;
    for(size_t k=0;k<members.size();++k) {
     if(CALCULATOR->aborted())return 0;
     MathStructure member=members[k];
     if(!canonical(member)) {CALCULATOR->error(true,"Membership requires a finite flat scalar or binary-string collection.",NULL);return 0;}
     bool probeLabel=probe.isFunction() && probe.function()->referenceName()=="qbitlabel";
     bool memberLabel=member.isFunction() && member.function()->referenceName()=="qbitlabel";
     if(probeLabel && memberLabel) {if(probe[0].equals(member[0]) && probe[1].equals(member[1]))found=true;continue;}
     if(probe.equals(member)) {found=true;continue;}
     if(probeLabel || memberLabel)continue;
     ComparisonResult comparison=probe.compare(member);
     if(comparison==COMPARISON_RESULT_EQUAL)found=true;
     else if(comparison!=COMPARISON_RESULT_LESS && comparison!=COMPARISON_RESULT_GREATER && comparison!=COMPARISON_RESULT_NOT_EQUAL)unknown=true;
    }
    if(!found && unknown) {CALCULATOR->error(true,"Membership could not determine equality of symbolic entries.",NULL);return 0;}
    out=found ? m_one : m_zero;return 1;
   }
   std::vector<MathStructure> seen;
   out=m_zero;
   for(size_t k=0;k<members.size();++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &member=members[k];
    if(!member.representsScalar() && !(member.isFunction() && member.function()->referenceName()=="qbitlabel")) {CALCULATOR->error(true,"Set sum indices must be scalars or binary-string labels.",NULL);return 0;}
    bool duplicate=false;for(const auto &previous:seen)if(member.equals(previous)){duplicate=true;break;}
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
 calculator.addFunction(new QuantumIndexedFunction("qstatecall",2));
 calculator.addFunction(new QuantumIndexedFunction("qstatecalls",2));
 calculator.addFunction(new QuantumIndexedFunction("qsum",4));
 calculator.addFunction(new QuantumIndexedFunction("qbars",1));
 calculator.addFunction(new QuantumIndexedFunction("qmember",2));
 calculator.addFunction(new QuantumIndexedFunction("qbitstrings",1));
 calculator.addFunction(new QuantumIndexedFunction("qbitlabel",2));
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

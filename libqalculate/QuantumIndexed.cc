// GPL-2.0-or-later; see COPYING.
#include "QuantumIndexed.h"
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include <string>
#include <utility>
#include <vector>
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
// Substitute a free index without capturing a nested finite-product/sum index.
void replaceQuantumIndex(MathStructure &value,const MathStructure &index,const MathStructure &replacement) {
 if(value.equals(index)) {value=replacement;return;}
 int bound=-1;
 if(value.isFunction() && value.size()==4) {
  const std::string &name=value.function()->referenceName();
  if((name=="qtensorproduct" || name=="qblocksum" || name=="qoraclefunction" || name=="sum" || name=="product") && value[3].equals(index))bound=3;
 }
 if(value.isFunction() && value.size()==3 && (value.function()->referenceName()=="qphasefunction" || value.function()->referenceName()=="qsequence" || value.function()->referenceName()=="qsumset") && value[2].equals(index))bound=2;
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  replaceQuantumIndex(value[k],index,replacement);
 }
 value.childrenUpdated();
}
class QuantumIndexedFunction: public MathFunction {
 std::string op;
 public:
 QuantumIndexedFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumIndexedFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
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
 calculator.addFunction(new QuantumIndexedFunction("qmember",2));
 calculator.addFunction(new QuantumIndexedFunction("qbitstrings",1));
 calculator.addFunction(new QuantumIndexedFunction("qbitlabel",2));
 for(const auto &entry:{std::pair<const char *,int>("qphasefunction",3),{"qsequence",3},{"qsumset",3},{"qindexrange",2},{"qoraclefunction",4},{"qtensorproduct",4},{"qblocksum",4}})calculator.addFunction(new QuantumIndexedFunction(entry.first,entry.second));
}

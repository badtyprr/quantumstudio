// GPL-2.0-or-later; see COPYING.
#include "QuantumBasisDomain.h"
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include <set>

namespace {
bool function(const MathStructure &value,const char *name,size_t size) {
 return value.isFunction() && value.function()->referenceName()==name && value.size()==size;
}
bool pending(const MathStructure &value) {
 return !value.isNumber() && value.representsScalar() && value.containsUnknowns();
}
bool dimensionValid(MathStructure &dimension,const EvaluationOptions &options) {
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;dimension.eval(exact);
 if(pending(dimension))return true;
 if(dimension.isNumber() && dimension.number().isInteger() && dimension.number()>0)return true;
 CALCULATOR->error(true,"Orthonormal basis dimensions must be positive finite integers.",NULL);return false;
}
bool indexValid(MathStructure &index,const MathStructure &dimension,const EvaluationOptions &options) {
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;index.eval(exact);
 if(pending(index))return true;
 if(index.isNumber() && index.number().isInteger() && index.number()>=0 &&
    (!dimension.isNumber() || index.number()<dimension.number()))return true;
 CALCULATOR->error(true,"An orthonormal basis index must be an integer from zero to dimension minus one.",NULL);return false;
}
class BasisValue: public MathFunction {
 std::string kind;
public:
 BasisValue(const char *name,int count):MathFunction(name,count),kind(name) {
  if(kind=="qorthofamilyket") {setArgumentDefinition(2,new TextArgument());setArgumentDefinition(3,new TextArgument());}
 }
 ExpressionItem *copy() const {return new BasisValue(*this);}
 bool representsScalar(const MathStructure&) const {return kind=="qorthodelta";}
 bool representsNonMatrix(const MathStructure&) const {return kind=="qorthodelta";}
 bool preservesSingletonMatrix() const {return kind!="qorthodelta";}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
  MathStructure args=raw;size_t dim=kind=="qorthofamilyket" ? 3 : kind=="qorthodelta" ? 2 : 0;
  if(!dimensionValid(args[dim],options))return 0;
  if(kind=="qorthoidentity") {
   if(!args[0].isNumber())return 0;
   out.set(CALCULATOR->getFunction("qidentity"),&args[0],NULL);out.eval(options);return 1;
  }
  if(kind=="qorthofamilyket" && (args[1].symbol().empty() || args[2].symbol().empty())) {
   CALCULATOR->error(true,"An indexed orthonormal ket needs a basis and family name.",NULL);return 0;
  }
  if(!indexValid(args[0],args[dim],options))return 0;
  if(kind=="qorthodelta") {
   if(!indexValid(args[1],args[dim],options))return 0;
   // Even equal symbolic indices retain their domain until substitution.
   if(args[0].isNumber() && args[1].isNumber() && args[2].isNumber()) {
    out=args[0].equals(args[1]) ? m_one : m_zero;return 1;
   }
  }
  if(args.equals(raw))return 0;
  out.set(this,static_cast<MathStructure*>(NULL));for(size_t k=0;k<args.size();++k)out.addChild(args[k]);return 1;
 }
};
bool annotate(MathStructure &value,const MathStructure &basis,const MathStructure &family,const MathStructure &dimension,unsigned depth=0,const std::set<std::string> &hidden=std::set<std::string>()) {
 if(CALCULATOR->aborted())return false;
 if(depth>128) {CALCULATOR->error(true,"Orthonormal declaration expression is too deeply nested.",NULL);return false;}
 if(function(value,"qorthofamilyket",4) || function(value,"qorthoket",3))return true;
 if(function(value,"orthofamily",4)) {
  if(value[1].equals(basis) || value[2].equals(family))return true;
  if(!annotate(value[0],basis,family,dimension,depth+1,hidden))return false;
  value.childrenUpdated();return true;
 }
 if(function(value,"orthobasis",3)) {
  if(value[1].equals(basis))return true;
  std::set<std::string> scoped=hidden;
  // The inner finite declaration owns its labels, including labels that
  // resemble an outer indexed family's subscripts.
  std::vector<const MathStructure*> pendingLabels(1,&value[2]);
  while(!pendingLabels.empty()) {
   const MathStructure &label=*pendingLabels.back();pendingLabels.pop_back();
   if(function(label,"qnamedket",1) || function(label,"qketstate",1)) {
    if(label[0].isSymbolic())scoped.insert(label[0].symbol());
    else if(label[0].isVariable())scoped.insert(label[0].variable()->referenceName());
   } else for(size_t k=0;k<label.size();++k)pendingLabels.push_back(&label[k]);
  }
  if(!annotate(value[0],basis,family,dimension,depth+1,scoped))return false;
  value.childrenUpdated();return true;
 }
 MathStructure index;bool matched=false;
 if(function(value,"qstatecall",2) && value[0].equals(family)) {index=value[1];matched=true;}
 if(function(value,"qnamedket",1) || function(value,"qketstate",1)) {
  const std::string label=value[0].isSymbolic() ? value[0].symbol() : value[0].isVariable() ? value[0].variable()->referenceName() : "";
  const std::string prefix=family.symbol()+"_";
  if(!hidden.count(label) && label.compare(0,prefix.size(),prefix)==0 && label.size()>prefix.size()) {
   Variable *existing=CALCULATOR->getActiveVariable(label);
   if(existing && !existing->isBuiltin() && existing->isKnown()) {CALCULATOR->error(true,"An orthonormal declaration cannot override an existing state definition.",NULL);return false;}
   std::string suffix=label.substr(prefix.size());bool digits=true;
   for(char c:suffix)if(c<'0' || c>'9')digits=false;
   if(digits)CALCULATOR->parse(&index,suffix);else index.set(suffix,true);
   matched=true;
  }
 }
 if(function(value,"qindexedket",1) && function(value[0],"qindexedlabel",3) &&
    value[0][0].isSymbolic() && value[0][0].symbol()==family.symbol()+"_" &&
    value[0][2].isSymbolic() && value[0][2].symbol().empty()) {index=value[0][1];matched=true;}
 if(matched) {
  value.set(CALCULATOR->getFunction("qorthofamilyket"),&index,&basis,&family,NULL);value.addChild(dimension);return true;
 }
 for(size_t k=0;k<value.size();++k) {
  Argument *argument=value.isFunction() ? value.function()->getArgumentDefinition(k+1) : NULL;
  if(argument && argument->type()==ARGUMENT_TYPE_TEXT)continue;
  if(!annotate(value[k],basis,family,dimension,depth+1,hidden))return false;
 }
 if(value.size())value.childrenUpdated();return true;
}
class OrthonormalFamily: public MathFunction {
public:
 OrthonormalFamily():MathFunction("orthofamily",4) {setArgumentDefinition(2,new TextArgument());setArgumentDefinition(3,new TextArgument());}
 ExpressionItem *copy() const {return new OrthonormalFamily(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
  MathStructure dimension=raw[3];
  if(raw[1].symbol().empty() || raw[2].symbol().empty()) {CALCULATOR->error(true,"An orthonormal family needs a basis and family name.",NULL);return 0;}
  if(!dimensionValid(dimension,options))return 0;
  if(CALCULATOR->getFunction("__qstate_family_"+raw[2].symbol())) {
   CALCULATOR->error(true,"An orthonormal declaration cannot override an existing state family.",NULL);return 0;
  }
  out=raw[0];if(!annotate(out,raw[1],raw[2],dimension))return 0;
  out.eval(options);return 1;
 }
};
}
bool quantumBasisProduct(const MathStructure &left,const MathStructure &right,MathStructure &result) {
 if(!function(left,"qdag",1) || !function(left[0],"qorthofamilyket",4) || !function(right,"qorthofamilyket",4))return false;
 const MathStructure &ket=left[0];if(!ket[1].equals(right[1]))return false;
 if(!ket[2].equals(right[2]) || !ket[3].equals(right[3])) {
  CALCULATOR->error(true,"Conflicting declarations for the same orthonormal basis.",NULL);return false;
 }
 result.set(CALCULATOR->getFunction("qorthodelta"),&ket[0],&right[0],&ket[3],NULL);return true;
}
bool quantumBasisSum(const MathStructure &body,const MathStructure &first,const MathStructure &last,
                     const MathStructure &index,MathStructure &result,const EvaluationOptions &options) {
 const MathStructure *ket=NULL;
 if(function(body,"qdensity",1))ket=&body[0];
 else if((function(body,"qmul",2) || function(body,"qadjacent",2)) && function(body[1],"qdag",1) && body[0].equals(body[1][0]))ket=&body[0];
 if(!ket || !function(*ket,"qorthofamilyket",4) || !(*ket)[0].equals(index) || !first.isZero())return false;
 if(!(*ket)[1].isSymbolic() || (*ket)[1].symbol().empty() || !(*ket)[2].isSymbolic() || (*ket)[2].symbol().empty()) {
  CALCULATOR->error(true,"An indexed orthonormal ket needs a basis and family name.",NULL);return false;
 }
 if((*ket)[3].contains(index))return false;
 MathStructure dimension=(*ket)[3];if(!dimensionValid(dimension,options))return false;
 MathStructure end=dimension;end-=m_one;EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;end.eval(exact);
 if(!end.equals(last))return false;
 result.set(CALCULATOR->getFunction("qorthoidentity"),&dimension,NULL);result.eval(options);return true;
}
void registerQuantumBasisDomain(Calculator &calculator) {
 calculator.addFunction(new OrthonormalFamily());
 calculator.addFunction(new BasisValue("qorthofamilyket",4));
 calculator.addFunction(new BasisValue("qorthodelta",3));
 calculator.addFunction(new BasisValue("qorthoidentity",1));
}

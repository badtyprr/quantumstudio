// GPL-2.0-or-later; see COPYING.
#include "QuantumAlgebra.h"
#include "QuantumOperatorDomain.h"
#include "QuantumBasisDomain.h"
#include "QuantumIndexed.h"
#include "QuantumBinary.h"
#include "Calculator.h"
#include "Function.h"
#include "BuiltinFunctions.h"
#include "MathStructure-support.h"
#include "Variable.h"
#include <string>
#include <utility>
#include <set>
#include <vector>
#include <cctype>
namespace {
// A ket can share a printed label (for example, phi) with a global
// scalar constant. Local state definitions and global matrices still bind.
Variable *ketVariable(const std::string &label) {
 Variable *v=CALCULATOR->getActiveVariable(label);
 if(!v || v->isBuiltin() || (!v->isLocal() && v->isKnown() && v->representsScalar()))return nullptr;
 return v;
}
bool orthonormalList(const MathStructure &raw,MathStructure &list) {
 list.clearVector();
 if(raw.isMatrix()) {
  if(raw.rows()!=1 && raw.columns()!=1)return false;
  for(size_t r=1;r<=raw.rows();++r)for(size_t c=1;c<=raw.columns();++c)list.addChild(*raw.getElement(r,c));
 } else if(raw.isVector() || (raw.isFunction() &&
            (raw.function()->referenceName()=="vector" || raw.function()->referenceName()=="horzcat" ||
             raw.function()->referenceName()=="vertcat"))) {
  for(size_t i=0;i<raw.size();++i)list.addChild(raw[i]);
 } else return false;
 return true;
}
// Named orthonormal vectors carry their declaration instead of choosing
// computational coordinates. Different bases therefore keep unknown overlaps.
bool orthonormalLabels(const MathStructure &labels) {
 if(!labels.isVector() || labels.isMatrix() || labels.size()==0 || labels.size()>1024)return false;
 std::set<std::string> names;
 for(size_t i=0;i<labels.size();++i)
  if(!labels[i].isSymbolic() || labels[i].symbol().empty() ||
     !names.insert(labels[i].symbol()).second)return false;
 return true;
}
MathStructure storedOrthonormalLabels(const MathStructure &labels) {
 // Keep a constructor in the symbolic AST so clipboard printing emits commas,
 // rather than the library's space-separated display form of a raw vector.
 MathStructure stored(CALCULATOR->getFunction("vector"),static_cast<MathStructure*>(NULL));
 for(size_t i=0;i<labels.size();++i)stored.addChild(labels[i]);
 return stored;
}
bool completeOrthonormalProjectors(const MathStructure &expression,MathStructure &dimension) {
 std::vector<const MathStructure*> pending(1,&expression);
 const MathStructure *basis=NULL;std::set<std::string> seen;
 while(!pending.empty()) {
  if(CALCULATOR->aborted())return false;
  const MathStructure &term=*pending.back();pending.pop_back();
  if(!term.isFunction())return false;
  const std::string &op=term.function()->referenceName();
  if(op=="qadd" && term.size()==2) {pending.push_back(&term[0]);pending.push_back(&term[1]);continue;}
  const MathStructure *ket=NULL;
  if(op=="qdensity" && term.size()==1)ket=&term[0];
  else if((op=="qmul" || op=="qadjacent") && term.size()==2 &&
          term[1].isFunction() && term[1].function()->referenceName()=="qdag" && term[1].size()==1 &&
          term[0].equals(term[1][0]))ket=&term[0];
  if(!ket || !ket->isFunction() || ket->function()->referenceName()!="qorthoket" || ket->size()!=3)return false;
  if(!basis)basis=ket;
  else if(!(*basis)[1].equals((*ket)[1]))return false;
  else if(!(*basis)[2].equals((*ket)[2])) {
   CALCULATOR->error(true,"Conflicting declarations for the same orthonormal basis.",NULL);return false;
  }
  if(!(*ket)[0].isSymbolic() || !seen.insert((*ket)[0].symbol()).second)return false;
 }
 if(!basis)return false;
 MathStructure labels;
 if(!orthonormalList((*basis)[2],labels) || !orthonormalLabels(labels) || seen.size()!=labels.size())return false;
 for(size_t i=0;i<labels.size();++i)if(!seen.count(labels[i].symbol()))return false;
 dimension.set(Number(static_cast<long>(labels.size())));return true;
}
class QuantumOrthonormalKet: public MathFunction {
 public:
 QuantumOrthonormalKet():MathFunction("qorthoket",3) {
  setArgumentDefinition(1,new TextArgument());setArgumentDefinition(2,new TextArgument());
 }
 ExpressionItem *copy() const {return new QuantumOrthonormalKet(*this);}
 bool representsScalar(const MathStructure&) const {return false;}
 bool representsNonMatrix(const MathStructure&) const {return false;}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions&) {
  MathStructure labels;
  bool found=false;
  if(orthonormalList(raw[2],labels) && orthonormalLabels(labels))
   for(size_t i=0;i<labels.size();++i)found=found || raw[0].equals(labels[i]);
  if(raw[1].symbol().empty() || !found) {
   CALCULATOR->error(true,"An orthonormal ket requires a named basis and membership in its distinct finite labels.",NULL);
   return 0;
  }
  MathStructure stored=storedOrthonormalLabels(labels);
  if(!stored.equals(raw[2])) {out.set(this,&raw[0],&raw[1],&stored,NULL);return 1;}
  return 0;
 }
};
bool annotateOrthonormalKets(MathStructure &value,const MathStructure &name,const MathStructure &labels,unsigned depth=0) {
 if(CALCULATOR->aborted())return false;
 if(depth>128) {CALCULATOR->error(true,"Orthonormal declaration expression is too deeply nested.",NULL);return false;}
 if(value.isFunction()) {
  const std::string &op=value.function()->referenceName();
  if(op=="qorthoket" || op=="qorthofamilyket")return true;
  if(op=="orthofamily" && value.size()==4) {
   if(value[1].equals(name))return true;
   MathStructure visible;visible.clearVector();
   const std::string prefix=value[2].isSymbolic() ? value[2].symbol()+"_" : "";
   for(size_t i=0;i<labels.size();++i)
    if(prefix.empty() || labels[i].symbol().compare(0,prefix.size(),prefix)!=0)visible.addChild(labels[i]);
   if(!annotateOrthonormalKets(value[0],name,visible,depth+1))return false;
   value.childrenUpdated();return true;
  }
  if(op=="orthobasis" && value.size()==3) {
   if(value[1].equals(name))return true;
   MathStructure inner,visible;visible.clearVector();
   if(!orthonormalList(value[2],inner))return true;
   for(size_t i=0;i<labels.size();++i) {
    bool shadowed=false;
    for(size_t k=0;k<inner.size();++k)if(inner[k].isFunction() && inner[k].size()==1 && inner[k][0].equals(labels[i]))shadowed=true;
    if(!shadowed)visible.addChild(labels[i]);
   }
   if(!annotateOrthonormalKets(value[0],name,visible,depth+1))return false;
   value.childrenUpdated();return true;
  }
  if((op=="qnamedket" || op=="qketstate") && value.size()==1) {
   std::string label=value[0].isSymbolic() ? value[0].symbol() :
    value[0].isVariable() ? value[0].variable()->referenceName() : "";
   for(size_t i=0;i<labels.size();++i)if(labels[i].symbol()==label) {
    MathStructure text(label,true),stored=storedOrthonormalLabels(labels);
    value.set(CALCULATOR->getFunction("qorthoket"),&text,&name,&stored,NULL);return true;
   }
   return true;
  }
 }
 for(size_t i=0;i<value.size();++i) {
  if(value.isFunction()) {
   Argument *argument=value.function()->getArgumentDefinition(i+1);
   if(argument && argument->type()==ARGUMENT_TYPE_TEXT)continue;
  }
  if(!annotateOrthonormalKets(value[i],name,labels,depth+1))return false;
 }
 if(value.size())value.childrenUpdated();
 return true;
}
class QuantumOrthonormalBasis: public MathFunction {
 public:
 QuantumOrthonormalBasis():MathFunction("orthobasis",3) {setArgumentDefinition(2,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumOrthonormalBasis(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure labels,kets;labels.clearVector();
  if(orthonormalList(raw[2],kets))for(size_t i=0;i<kets.size();++i) {
   const MathStructure &ket=kets[i];
   if(!ket.isFunction() || ket.size()!=1 ||
      (ket.function()->referenceName()!="qnamedket" && ket.function()->referenceName()!="qketstate"))break;
   std::string label=ket[0].isSymbolic() ? ket[0].symbol() :
    ket[0].isVariable() ? ket[0].variable()->referenceName() : "";
   Variable *existing=ketVariable(label);
   bool defined=existing && existing->isKnown();
   size_t split=label.rfind('_');
   while(split!=std::string::npos && split>0) {
    if(split+1<label.size() && CALCULATOR->getFunction("__qstate_family_"+label.substr(0,split)))defined=true;
    split=label.rfind('_',split-1);
   }
   if(defined) {CALCULATOR->error(true,"An orthonormal declaration cannot override an existing state definition.",NULL);return 0;}
   labels.addChild(MathStructure(label,true));
  }
  if(raw[1].symbol().empty() || labels.size()!=kets.size() || !orthonormalLabels(labels)) {
   CALCULATOR->error(true,"orthobasis(expression,name,[|label>,...]) requires distinct named kets.",NULL);return 0;
  }
  out=raw[0];
  if(!annotateOrthonormalKets(out,raw[1],labels))return 0;
  out.eval(eo);return 1;
 }
};
// Reuse the ordinary constructors' argument validation and allocation limits,
// but retain matrix shape at dimension one in quantum expressions.
template<class Constructor> class QuantumMatrixConstructor: public Constructor {
 public:
 explicit QuantumMatrixConstructor(const char *name) {this->setName(name,1);}
 int id() const {return 0;}
 bool preservesSingletonMatrix() const {return true;}
 ExpressionItem *copy() const {return new QuantumMatrixConstructor(*this);}
};
// A matrix domain is retained until both its value and shape are known.
// This keeps substitution checks local instead of changing global assumptions.
class QuantumMatrixParameter: public MathFunction {
 public:
 QuantumMatrixParameter():MathFunction("matrixparam",3) {}
 ExpressionItem *copy() const {return new QuantumMatrixParameter(*this);}
 bool representsScalar(const MathStructure&) const {return false;}
 bool representsNonMatrix(const MathStructure&) const {return false;}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  MathStructure dimensions[2]={raw[1],raw[2]};bool deferred=false;
  for(auto &dimension:dimensions) {
   dimension.eval(exact);
   if(!dimension.isNumber() && !dimension.isVector() && dimension.containsUnknowns()) {deferred=true;continue;}
   if(!dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<=0) {
    CALCULATOR->error(true,"Matrix dimensions must be positive integers.",NULL);return 0;
   }
  }
  MathStructure value=raw[0];value.eval(eo);
  if(value.isUnknown())return 0;
  if(!value.isMatrix()) {CALCULATOR->error(true,"A matrix parameter requires a matrix substitution.",NULL);return 0;}
  for(unsigned axis=0;axis<2;++axis) {
   if(dimensions[axis].isNumber() && dimensions[axis].number()!=Number(static_cast<long>(axis ? value.columns() : value.rows()))) {
    CALCULATOR->error(true,"Matrix substitution does not match its declared dimensions.",NULL);return 0;
   }
  }
  if(deferred)return 0;
  out=value;return 1;
 }
};
// Apply declarations to free scalar symbols, never to text-valued labels.
bool annotateMatrixSymbol(MathStructure &value,const MathStructure &symbol,const MathStructure &declaration,const std::string &declaredName,unsigned depth=0) {
 if(CALCULATOR->aborted())return false;
 if(depth>128) {CALCULATOR->error(true,"Matrix declaration expression is too deeply nested.",NULL);return false;}
 if(value.isUnknown() && value.equals(symbol)) {value=declaration;return true;}
 for(size_t i=0;i<value.size();++i) {
  if(value.isFunction()) {
   Argument *argument=value.function()->getArgumentDefinition(i+1);
   if(argument && argument->type()==ARGUMENT_TYPE_TEXT)continue;
   const std::string &name=value.function()->referenceName();
   // Keep the replacement target a name so the domain validates its new value.
   if(name=="qreplace" && i==1)continue;
   // Explicit domains and single-letter ket labels retain their meaning.
   if((name=="matrixparam" || name=="operatorparam" || name=="qunitaryidentity" || name=="qketstate") && i==0)continue;
   // An inner declaration owns its body, but not its dimension expressions.
   if((name=="matrixassume" || name=="operatorassume" || name=="qgatematrixassume" || name=="qgateoperatorassume") && value.size()==4 && i==0 && value[1].isSymbolic() && value[1].symbol()==declaredName)continue;
  }
  if(!annotateMatrixSymbol(value[i],symbol,declaration,declaredName,depth+1))return false;
 }
 if(value.size())value.childrenUpdated();
 return true;
}
class QuantumMatrixAssumption: public MathFunction {
 bool operatorProperty,gateName;
 public:
 explicit QuantumMatrixAssumption(bool property=false,bool gate=false):MathFunction(std::string(gate ? "qgate" : "")+(property ? "operatorassume" : "matrixassume"),4),operatorProperty(property),gateName(gate) {
  setArgumentDefinition(2,new TextArgument());
  if(property)setArgumentDefinition(4,new TextArgument());
 }
 ExpressionItem *copy() const {return new QuantumMatrixAssumption(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  const std::string name=raw[1].symbol();
  bool valid=!name.empty() && name.size()<=128 && !(name[0]>='0' && name[0]<='9');
  for(unsigned char c:name)if(c<128 && !std::isalnum(c) && c!='_')valid=false;
  if(!valid) {CALCULATOR->error(true,"A matrix declaration requires a single symbol name.",NULL);return 0;}
  MathStructure symbol=gateName ? MathStructure(name,true) : CALCULATOR->calculate("quantum: "+name,eo);
  if(!symbol.isUnknown()) {CALCULATOR->error(true,"Matrix names cannot override gates, constants, or existing values.",NULL);return 0;}
  // Parsing must preserve the declared name: for example M1 simplifies to M.
  if((symbol.isSymbolic() && symbol.symbol()!=name) || (symbol.isVariable() && symbol.variable()->referenceName()!=name)) {
   CALCULATOR->error(true,"Matrix names must parse as the same symbol. Use an underscore before an index (for example M_1).",NULL);return 0;
  }
  MathStructure declaration;declaration.set(CALCULATOR->getFunction(operatorProperty ? "operatorparam" : "matrixparam"),&symbol,&raw[2],&raw[3],NULL);
  declaration.eval(eo);out=raw[0];
  if(!annotateMatrixSymbol(out,symbol,declaration,name))return 0;
  out.eval(eo);return 1;
 }
};
// An expression-level domain survives printing and a fresh calculator request.
// Unlike changing the default assumptions, it does not change real angles.
class QuantumComplexParameter: public MathFunction {
public:
 QuantumComplexParameter():MathFunction("complexparam",1) {}
 ExpressionItem *copy() const {return new QuantumComplexParameter(*this);}
 // General complex numbers include real values; representsComplex would
 // incorrectly assert a nonzero imaginary part.
 bool representsNumber(const MathStructure&,bool=false) const {return true;}
 int calculate(MathStructure &out,const MathStructure &args,const EvaluationOptions &eo) {
  MathStructure value=args[0];value.eval(eo);
  if(value.isUnknown()) {out=value;return -1;}
  if(!value.containsUnknowns() && value.representsNumber() &&
     !(value.isNumber() && (value.number().isUndefined() || value.number().isInfinite(false)))) {
   out=value;return 1;
  }
  CALCULATOR->error(true,"complexparam requires a single unknown symbol or a finite numeric substitution.",NULL);
  return 0;
 }
};
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
// Transposing a 1-by-1 matrix is the identity; the generic helper flattens it.
void transposeQuantumMatrix(MathStructure &a) {
 if(a.rows()!=1 || a.columns()!=1) a.transposeMatrix();
}
MathStructure conjugateScalar(const MathStructure &a, const EvaluationOptions &eo) {
 if(CALCULATOR->aborted()) return a;
 MathStructure out=a;
 // Positive real bases have a real logarithm, so conjugating their powers
 // only conjugates the exponent. Do not apply this across a branch cut for
 // negative or unknown-sign bases. This includes exp(z), stored as e^z.
 if(a.isPower() && a.size()==2 && a[0].representsPositive()) {
  out[1]=conjugateScalar(a[1],eo);out.childrenUpdated();out.eval(eo);
 } else if(a.isAddition() || a.isMultiplication()) {
  for(size_t k=0;k<a.size();++k)out[k]=conjugateScalar(a[k],eo);
  out.childrenUpdated();out.eval(eo);
 } else {
  out.set(CALCULATOR->getFunction("conj"),&a,NULL);out.eval(eo);
 }
 return out;
}
MathStructure dagger(const MathStructure &a, const EvaluationOptions &eo) {
 MathStructure out=a;
 if(out.isMatrix()) {
  transposeQuantumMatrix(out);
  for(size_t r=0;r<out.rows();++r) for(size_t c=0;c<out.columns();++c) {
   element(out,r,c)=conjugateScalar(element(out,r,c),eo);
  }
 } else out=conjugateScalar(a,eo);
 return out;
}
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo, bool scalarResult=true) {
 bool unitMatrix=!scalarResult && (
  (a.isMatrix() && b.isMatrix() && a.rows()==1 && b.columns()==1 && a.columns()==b.rows()) ||
  (a.isMatrix() && a.rows()==1 && a.columns()==1 && b.representsScalar()) ||
  (b.isMatrix() && b.rows()==1 && b.columns()==1 && a.representsScalar()));
 a*=b; a.eval(eo);
 // Generic multiplication reduces a 1-by-1 product to a scalar. Restore the
 // declared matrix shape for callers such as density, while norms stay scalar.
 if(unitMatrix && !a.isVector() && a.representsScalar()) {
  MathStructure scalar=a;a.clearMatrix();a.resizeMatrix(1,1,m_zero);element(a,0,0)=scalar;
 }
 if(scalarResult && a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
bool indexedUppercaseFactor(const MathStructure &value) {
 if(!value.isSymbolic())return false;
 const std::string &label=value.symbol();
 if(label.compare(0,3,"Π_")==0 && label.size()>3)return label.find_first_not_of("0123456789",3)==std::string::npos;
 return label.size()>2 && label[0]>='A' && label[0]<='Z' && label[1]=='_' &&
        label.find_first_not_of("0123456789",2)==std::string::npos;
}
bool unresolvedMatrixOperand(const MathStructure &value,unsigned depth=0) {
 // On a deep expression, defer instead of guessing a scalar domain.
 if(depth>128)return true;
 if(value.isUnknown())return true;
 if(value.isFunction())return !value.representsScalar();
 if(value.isPower() && value.size()==2)return unresolvedMatrixOperand(value[0],depth+1);
 if(value.isAddition() || value.isMultiplication())
  for(size_t i=0;i<value.size();++i)if(unresolvedMatrixOperand(value[i],depth+1))return true;
 return false;
}
// Infer only shapes justified by explicit declarations or concrete matrices.
// Different unknown dimensions are not assumed unequal.
bool adjacentStateShapes(const MathStructure &ar,const MathStructure &ac,const MathStructure &br,const MathStructure &bc) {
 return (ac.isOne() && bc.isOne()) || (ar.isOne() && br.isOne());
}
// Shape metadata must not expand a large dimension just to describe a deferred
// matrix. Normalize small powers and symbolic algebra, retaining large powers.
bool normalizeDimension(MathStructure &value,const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>64)return false;
 bool bounded=true;
 for(size_t k=0;k<value.size();++k)
  bounded=normalizeDimension(value[k],eo,depth+1) && bounded;
 if(!bounded)return false;
 if(value.isPower() && value.size()==2 && value[1].isNumber()) {
  Number exponent=value[1].number();exponent.abs();
  if(exponent>4096)return false;
  if(value[0].isNumber() && value[0].number().isInteger()) {
   Number bits(value[0].number().integerLength());bits.multiply(exponent);
   if(bits>4096)return false;
  }
 }
 value.childrenUpdated();
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 value.eval(exact);return true;
}
bool matrixShape(const MathStructure &value,MathStructure &rows,MathStructure &columns,const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>64)return false;
 if(value.isMatrix()) {rows.set(Number(static_cast<long>(value.rows())));columns.set(Number(static_cast<long>(value.columns())));return true;}
 if(value.isVector() && value.size()>0) {
  for(size_t i=0;i<value.size();++i)if(!value[i].representsScalar())return false;
  rows=m_one;columns.set(Number(static_cast<long>(value.size())));return true;
 }
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 if(name=="qreplace" && value.size()==3) {
  MathStructure term;
  return quantumReplacementShapeInput(value,term,eo) && matrixShape(term,rows,columns,eo,depth+1);
 }
 if(name=="matrix" || name=="qmatrix") {
  // Deferred tensors retain their original arguments, which may include a
  // concrete constructor. Reuse its validation before trusting its shape.
  MathStructure concrete=value;concrete.eval(eo);
  if(!concrete.isMatrix())return false;
  rows.set(Number(static_cast<long>(concrete.rows())));
  columns.set(Number(static_cast<long>(concrete.columns())));return true;
 }
 if(name=="qbasis" && value.size()==2) {rows=value[1];columns=m_one;return true;}
 if((name=="qfourier" || name=="qft") && value.size()==1) {
  MathStructure size=value[0];normalizeDimension(size,eo);
  if(size.isNumber()) {
   if(!size.number().isInteger() || size.number()<(name=="qft" ? 0 : 1))return false;
  } else if(!size.representsScalar() || !size.containsUnknowns())return false;
  rows=name=="qft" ? MathStructure(2) : size;
  if(name=="qft")rows.raise(size);
  normalizeDimension(rows,eo);columns=rows;return true;
 }
 if(name=="qregisterfamily" && value.size()==4) {
  MathStructure width=value[1];width-=value[2];width+=m_one;
  normalizeDimension(width,eo);
  if(width.isNumber() && (!width.number().isInteger() || width.number()<0))return false;
  if(!width.isNumber() && (!width.representsScalar() || !width.containsUnknowns()))return false;
  rows=MathStructure(2);rows.raise(width);columns=m_one;
  normalizeDimension(rows,eo);return true;
 }
 if(name=="qketstate" && value.size()==1 && value[0].isFunction() &&
    value[0].function()->referenceName()=="qbitlabel" && value[0].size()==2) {
  MathStructure index=value[0][0],width=value[0][1];
  if(validateQuantumBitLabel(index,width,eo)==QuantumBitLabelState::Invalid)return false;
  rows=MathStructure(2);rows.raise(width);columns=m_one;
  normalizeDimension(rows,eo);return true;
 }
 if(name=="qorthofamilyket" && value.size()==4) {rows=value[3];columns=m_one;return true;}
 if(name=="qorthoidentity" && value.size()==1) {rows=value[0];columns=rows;return true;}
 if(name=="qorthoket" && value.size()==3) {
  MathStructure labels;
  if(orthonormalList(value[2],labels) && orthonormalLabels(labels)) {rows.set(Number(static_cast<long>(labels.size())));columns=m_one;return true;}
  return false;
 }
 if(name=="qfourierdomain" && value.size()==3) {rows=value[2];columns=m_one;return true;}
 if(name=="matrixparam" && value.size()==3) {
  rows=value[1];columns=value[2];EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  normalizeDimension(rows,exact);normalizeDimension(columns,exact);return true;
 }
 if(quantumOperatorDimension(value,rows,eo)) {columns=rows;return true;}
 if((name=="qdag" || name=="qtranspose") && value.size()==1)
  return matrixShape(value[0],columns,rows,eo,depth+1);
 if(name=="qsumset" && value.size()==3) {
  MathStructure term;
  if(!quantumSetSumShapeInput(value,term,eo) || !matrixShape(term,rows,columns,eo,depth+1))return false;
  // A single summand only determines the result's shape when its dimensions
  // are independent of the bound value. Do not guess a heterogeneous sum.
  return !rows.contains(value[2]) && !columns.contains(value[2]);
 }
 if(name=="qregistersum" && value.size()==7) {
  MathStructure term,dependent;
  if(!quantumRegisterSumShapeInput(value,term,dependent,eo) || !matrixShape(term,rows,columns,eo,depth+1))return false;
  for(size_t k=0;k<dependent.size();++k)if(rows.contains(dependent[k]) || columns.contains(dependent[k]))return false;
  normalizeDimension(rows,eo);normalizeDimension(columns,eo);return true;
 }
 if(name=="qtensorseries" || name=="qboundtensorseries") {
  MathStructure factor,count;
  if(!quantumTensorSeriesShapeInput(value,factor,count,eo))return false;
  if(count.isZero()) {rows=m_one;columns=m_one;return true;}
  if(!matrixShape(factor,rows,columns,eo,depth+1) || rows.contains(value[3]) || columns.contains(value[3]))return false;
  if(!rows.isOne())rows.raise(count);if(!columns.isOne())columns.raise(count);
  normalizeDimension(rows,eo);normalizeDimension(columns,eo);return true;
 }
 if(name=="qtensorpow" && value.size()==2) {
  MathStructure count=value[1];EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  count.eval(exact);
  bool unknown=!count.isNumber() && count.representsScalar() && count.containsUnknowns();
  if(!unknown && (!count.isNumber() || !count.number().isInteger() || count.number()<0))return false;
  if(!matrixShape(value[0],rows,columns,eo,depth+1))return false;
  if(!rows.isOne())rows.raise(count);if(!columns.isOne())columns.raise(count);
  normalizeDimension(rows,exact);normalizeDimension(columns,exact);return true;
 }
 if(value.size()!=2)return false;
 MathStructure ar,ac,br,bc;
 bool left=matrixShape(value[0],ar,ac,eo,depth+1),right=matrixShape(value[1],br,bc,eo,depth+1);
 if(left && right && (name=="qtensor" || (name=="qadjacent" && adjacentStateShapes(ar,ac,br,bc)))) {
  rows=ar;rows*=br;columns=ac;columns*=bc;
  EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  normalizeDimension(rows,exact);normalizeDimension(columns,exact);return true;
 }
 if((name=="qadd" || name=="qsub") && left && right && ar.equals(br) && ac.equals(bc)) {rows=ar;columns=ac;return true;}
 if(name=="qmul" || name=="qadjacent") {
  if(left && right && ac.equals(br)) {
   // Row-column contraction has scalar semantics in quantum multiplication.
   if(ar.isOne() && bc.isOne())return false;
   rows=ar;columns=bc;return true;
  }
  if(left && quantumScalarExpression(value[1])) {rows=ar;columns=ac;return true;}
  if(right && quantumScalarExpression(value[0])) {rows=br;columns=bc;return true;}
 }
 return false;
}
bool containsBasisIndex(const MathStructure &dimension,const MathStructure &index,unsigned depth=0) {
 if(depth>64 || CALCULATOR->aborted())return true;
 if(dimension.equals(index))return true;
 auto name=[](const MathStructure &value) {
  return value.isSymbolic() ? value.symbol() :
   value.isVariable() && !value.variable()->isKnown() ? value.variable()->referenceName() : std::string();
 };
 const std::string bound=name(index);
 if(!bound.empty() && name(dimension)==bound)return true;
 for(size_t k=0;k<dimension.size();++k)if(containsBasisIndex(dimension[k],index,depth+1))return true;
 return false;
}
bool resolveBasisDimension(MathStructure &value,const MathStructure &dimension,unsigned depth=0) {
 if(depth>64 || CALCULATOR->aborted())return false;
 bool changed=false;
 if(value.isFunction()) {
  const std::string &name=value.function()->referenceName();
  if(name=="qcomputationalket" && value.size()==1) {
   MathStructure index=value[0];value.set(CALCULATOR->getFunction("qbasis"),&index,&dimension,NULL);return true;
  }
  if((name=="qadd" || name=="qsub") && value.size()==2) {
   for(size_t k=0;k<2;++k)changed=resolveBasisDimension(value[k],dimension,depth+1) || changed;
  } else if((name=="qmul" || name=="qadjacent") && value.size()==2) {
   if(quantumScalarExpression(value[0]))changed=resolveBasisDimension(value[1],dimension,depth+1);
   else if(quantumScalarExpression(value[1]))changed=resolveBasisDimension(value[0],dimension,depth+1);
  } else if((name=="qsum" && value.size()==4) || (name=="qsumset" && value.size()==3)) {
   // An ambient dimension cannot capture the summation's bound index.
   if(!containsBasisIndex(dimension,value[value.size()-1]))changed=resolveBasisDimension(value[0],dimension,depth+1);
  }
 } else if(value.isAddition()) {
  for(size_t k=0;k<value.size();++k)changed=resolveBasisDimension(value[k],dimension,depth+1) || changed;
 } else if(value.isMultiplication()) {
  size_t factor=value.size();
  for(size_t k=0;k<value.size();++k)if(!quantumScalarExpression(value[k])) {
   if(factor!=value.size())return false;factor=k;
  }
  if(factor<value.size())changed=resolveBasisDimension(value[factor],dimension,depth+1);
 }
 if(changed)value.childrenUpdated();return changed;
}
bool unequalKnownDimensions(const MathStructure &a,const MathStructure &b) {
 if(a.isNumber() && b.isNumber())return a.number()!=b.number();
 // Normalization may turn 2^(n+1) into 2*2^n. Compare the complete scalar
 // expressions as well as their power syntax, requiring a definite nonzero
 // difference so overlapping intervals and unresolved relations stay pending.
 MathStructure difference=a;difference-=b;
 normalizeDimension(difference,default_evaluation_options);
 if(difference.representsNonZero())return true;
 if(a.isPower() && b.isPower() && a.size()==2 && b.size()==2 &&
    a[0].equals(b[0]) && a[0].isNumber() && a[0].number()>1) {
  MathStructure difference=a[1];difference-=b[1];
  normalizeDimension(difference,default_evaluation_options);
  if(difference.isNumber() && difference.number().isReal() && difference.number().isNonZero())return true;
 }
 // A huge retained power can still contradict a small explicit dimension.
 for(unsigned side=0;side<2;++side) {
  const MathStructure &number=side ? b : a,&power=side ? a : b;
  if(number.isNumber() && number.number().isInteger() && number.number()>0 &&
     power.isPower() && power.size()==2 && power[0].isNumber() &&
     power[0].number().isInteger() && power[0].number()>=2 &&
     power[1].isNumber() && power[1].number().isInteger() &&
     power[1].number()>=Number(number.number().integerLength()))return true;
 }
 return false;
}
// A named ket can have an unknown dimension while its orientation is known.
bool stateActionOperand(const MathStructure &value,const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>128)return false;
 MathStructure rows,columns;
 if(matrixShape(value,rows,columns,eo))return columns.isOne();
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 if(name=="qnamedket" || name=="qketstate" || name=="qstatecall" || name=="qstatecalls")return true;
 if(value.size()!=2)return false;
 if(name=="qtensor" || name=="qadd" || name=="qsub")
  return stateActionOperand(value[0],eo,depth+1) && stateActionOperand(value[1],eo,depth+1);
 if(name=="qmul" || name=="qadjacent")
  return stateActionOperand(value[1],eo,depth+1) ||
         (value[1].representsScalar() && stateActionOperand(value[0],eo,depth+1));
 return false;
}
// Recover the unique reduced u/v with v < N and |phase - u/v| < 1/(2N²).
int recoverPhaseFraction(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
 MathStructure phase=raw[0],bound=raw[1];phase.eval(exact);bound.eval(exact);
 if(!bound.isInteger() || bound.isApproximate() || bound.number()<2) {
  if(bound.containsUnknowns() && bound.representsScalar())return 0;
  CALCULATOR->error(true,"Phase recovery requires an exact integer bound of at least two.",NULL);return 0;
 }
 if(phase.containsUnknowns() && phase.representsScalar())return 0;
 if(phase.isApproximate() || !phase.representsReal()) {
  CALCULATOR->error(true,"Phase recovery requires an exact real phase between zero and one.",NULL);return 0;
 }
 MathStructure positive=phase,belowOne=phase;
 positive.transform(COMPARISON_GREATER,m_zero);positive.eval(exact);
 belowOne.transform(COMPARISON_LESS,m_one);belowOne.eval(exact);
 if(positive.isZero() || belowOne.isZero()) {
  CALCULATOR->error(true,"Phase recovery requires a phase strictly between zero and one.",NULL);return 0;
 }
 if(!positive.isOne() || !belowOne.isOne())return 0;

 const Number &n=bound.number();
 Number tolerance=Number(1)/(n*n*2);
 Number rationalPhase;
 if(phase.isNumber() && phase.number().isRational())rationalPhase=phase.number();
 else {
  // Floor to a rational within 1/(4N³) of the exact phase. A qualifying
  // u/v is then within 1/(2v²) of that rational (v <= N-1), hence is one
  // of its continued-fraction convergents. Test acceptance on the original.
  Number scale=n*n*n*4;
  MathStructure scaled=phase;scaled*=MathStructure(scale);
  MathStructure lower(CALCULATOR->getFunctionById(FUNCTION_ID_FLOOR),&scaled,NULL);
  lower.eval(exact);
  if(!lower.isInteger() || lower.isApproximate())return 0;
  rationalPhase=lower.number()/scale;
 }
 Number dividend=rationalPhase.numerator(),divisor=rationalPhase.denominator();
 Number previousU(0),u(1),previousV(1),v(0);
 MathStructure entries;entries.clearVector();
 while(!divisor.isZero()) {
  if(CALCULATOR->aborted())return 0;
  Number coefficient;
  if(!dividend.irem(divisor,coefficient))return 0;
  Number nextV=coefficient*v+previousV;
  if(nextV>=n)break;
  Number nextU=coefficient*u+previousU;
  Number candidate=nextU/nextV;
  MathStructure difference=phase;difference-=MathStructure(candidate);
  MathStructure accepted(CALCULATOR->getFunctionById(FUNCTION_ID_ABS),&difference,NULL);
  accepted.transform(COMPARISON_LESS,MathStructure(tolerance));accepted.eval(exact);
  if(accepted.isOne()) {entries.addChild(MathStructure(candidate));break;}
  if(!accepted.isZero())return 0;
  previousU=u;u=nextU;previousV=v;v=nextV;
  Number remainder=dividend;dividend=divisor;divisor=remainder;
 }
 out.set(CALCULATOR->getFunction("qset"),&entries,NULL);return 1;
}
class QuantumAlgebraFunction: public MathFunction {
 std::string op;
 public:
 QuantumAlgebraFunction(const std::string &name,int n):MathFunction(name,n),op(name) {
  if(op=="qnamedket" || op=="qfrequency" || op=="qphysicalunit")setArgumentDefinition(1,new TextArgument());
  if(op=="qphysicalunit")setArgumentDefinition(2,new TextArgument());
 }
 ExpressionItem *copy() const {return new QuantumAlgebraFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 bool representsScalar(const MathStructure &args) const {
  return op=="qtrace" || op=="qbitlength" || op=="qfloorlog2" || op=="qmodpower" || op=="qmodpowerequal" || MathFunction::representsScalar(args);
 }
 bool representsNonMatrix(const MathStructure &args) const {
  return op=="qtrace" || op=="qbitlength" || op=="qfloorlog2" || op=="qmodpower" || op=="qmodpowerequal" || MathFunction::representsNonMatrix(args);
 }
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(op=="qoperatorunequal") {
   MathStructure left=raw[0],right=raw[1];left.eval(eo);right.eval(eo);
   if(!left.isMatrix() || !right.isMatrix())return 0;
   MathStructure unequal(5);
   out.set(CALCULATOR->getFunction("qcompare"),&left,&right,&unequal,NULL);out.eval(eo);return 1;
  }
  if(op=="qkrylovstates") {
   MathStructure h=raw[0],state=raw[1],step=raw[2],count=raw[3];
   h.eval(eo);state.eval(eo);step.eval(eo);count.eval(eo);
   if(!count.isNumber())return 0;
   if(!count.isInteger() || count.number()<1 || count.number()>1024) {
    CALCULATOR->error(true,"A Krylov family requires 1 to 1024 states.",NULL);return 0;
   }
   if(!h.isMatrix() || !state.isMatrix() || !step.representsReal())return 0;
   if(h.rows()!=h.columns() || state.columns()!=1 || h.rows()!=state.rows()) {
    CALCULATOR->error(true,"The Krylov Hamiltonian and initial ket require compatible dimensions.",NULL);return 0;
   }
   MathStructure evolution(CALCULATOR->getFunction("qevolution"),&h,&step,NULL);
   evolution.eval(eo);if(!evolution.isMatrix())return 0;
   const int size=count.number().intValue();
   out.clearVector();out.addChild(state);
   for(int j=1;j<size;++j) {
    if(CALCULATOR->aborted())return 0;
    state=multiply(evolution,state,eo,false);out.addChild(state);
   }
   return 1;
  }
  if(op=="qpropagator") {
   MathStructure h=raw[0],time=raw[1];h.eval(eo);time.eval(eo);
   if(!h.isMatrix() || !time.representsReal()) {
    if(h.equals(raw[0]) && time.equals(raw[1]))return 0;
    out.set(this,&h,&time,NULL);return 1;
   }
   out.set(CALCULATOR->getFunction("qevolution"),&h,&time,NULL);out.eval(eo);return 1;
  }
  if(op=="qspinladder") {
   MathStructure args=raw;for(size_t k=0;k<3;++k)args[k].eval(eo);
   for(size_t k=0;k<3;++k)if(!args[k].isInteger() || args[k].isApproximate())return 0;
   if(args[0].number()<1 || args[0].number()>9 || args[1].number()<0 ||
      args[1].number()>=args[0].number() || (!args[2].isZero() && !args[2].isOne())) {
    CALCULATOR->error(true,"A spin ladder requires 1 to 9 wires, a wire in range, and a binary transition selector.",NULL);return 0;
   }
   const unsigned n=args[0].number().intValue(),site=args[1].number().intValue();
   const unsigned dimension=1u<<n,bit=1u<<(n-1-site);
   const bool create=args[2].isOne();
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(unsigned column=0;column<dimension;++column)
    if(bool(column&bit)!=create)element(out,column^bit,column)=m_one;
   return 1;
  }
  if(op=="qjwimage") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure width=raw[0],site=raw[1],create=raw[2];
   width.eval(exact);site.eval(exact);create.eval(exact);
   if(!width.isNumber() || !site.isNumber() || !create.isNumber())return 0;
   if(!create.isZero() && !create.isOne()) {
    CALCULATOR->error(true,"The Jordan-Wigner ladder selector must be zero or one.",NULL);return 0;
   }
   MathStructure jw(CALCULATOR->getFunction(create.isOne() ? "qfcreate" : "qfdestroy"),&width,&site,NULL);
   jw.eval(exact);
   if(!jw.isMatrix())return 0;
   // This displayed convention uses a negative Z on every preceding wire.
   if(site.number().isOdd())jw.negate();
   out=jw;return 1;
  }
  if(op=="qhadamardpower") {
   MathStructure width=raw[0];width.eval(eo);
   if(!width.isNumber())return 0;
   MathStructure gate;gate.clearMatrix();gate.resizeMatrix(2,2,m_one);
   MathStructure scale(2);scale.raise(Number(-1,2));scale.eval(eo);
   gate.multiply(scale);gate.eval(eo);element(gate,1,1).negate();
   out.set(CALCULATOR->getFunction("qtensorpow"),&gate,&width,NULL);out.eval(eo);return 1;
  }
  if(op=="qbinarypowersum" || op=="qprojectorproduct") {
   MathStructure operators=raw[0];operators.eval(eo);
   if(!operators.isVector() || !operators.size())return 0;
   bool single=operators.isMatrix() && operators.rows() && operators.columns() && operators.getElement(1,1)->isNumber();
   const MathStructure &first=single ? operators : operators[0];
   if(!first.isMatrix() || !first.rows() || first.rows()!=first.columns())return 0;
   size_t size=first.rows();
   if(op=="qprojectorproduct") {
    MathStructure dimension=raw[1];dimension.eval(eo);
    if(!dimension.isInteger() || dimension.number()!=size)return 0;
   }
   MathStructure identity;identity.clearMatrix();identity.resizeMatrix(size,size,m_zero);
   for(size_t j=1;j<=size;++j)*identity.getElement(j,j)=m_one;
   MathStructure product=identity;
   // Distribute in order. No commutation between distinct factors is needed.
   for(size_t k=0;k<(single ? 1 : operators.size());++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &factor=single ? operators : operators[k];
    if(!factor.isMatrix() || factor.rows()!=size || factor.columns()!=size)return 0;
    MathStructure term(CALCULATOR->getFunction("qadd"),&identity,&factor,NULL);
    term.eval(eo);
    if(op=="qprojectorproduct") {term/=MathStructure(2);term.eval(eo);}
    MathStructure previous=product;
    product.set(CALCULATOR->getFunction("qmul"),&previous,&term,NULL);product.eval(eo);
   }
   out=product;return 1;
  }
  if(op=="qfixedby") {
   MathStructure operators=raw[0],state=raw[1];operators.eval(eo);state.eval(eo);
   if(!operators.isVector() || !state.isMatrix() || state.columns()!=1 || state.containsUnknowns())return 0;
   bool single=operators.isMatrix() && operators.rows() && operators.columns() && operators.getElement(1,1)->isNumber();
   for(size_t k=0;k<(single ? 1 : operators.size());++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &gate=single ? operators : operators[k];
    if(!gate.isMatrix() || gate.containsUnknowns())return 0;
    if(gate.rows()!=state.rows() || gate.columns()!=state.rows()) {out=0;return 1;}
    MathStructure image(CALCULATOR->getFunction("qmul"),&gate,&state,NULL);
    image.eval(eo);
    if(!image.isMatrix())return 0;
    if(!image.equals(state)) {out=0;return 1;}
   }
   out=1;return 1;
  }
  if(op=="qorderedpowers") {
   MathStructure factors=raw[0],powers=raw[1];factors.eval(eo);powers.eval(eo);
   bool single=factors.isMatrix() && factors.rows() && factors.columns() && factors.getElement(1,1)->isNumber();
   size_t count=single ? 1 : factors.size();
   if(!factors.isVector() || !count)return 0;
   bool shared=powers.isInteger();
   if(!shared && (!powers.isVector() || powers.size()!=count))return 0;
   MathStructure accumulated;
   for(size_t k=0;k<count;++k) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &factor=single ? factors : factors[k],&power=shared ? powers : powers[k];
    if(!factor.isMatrix() || !power.isInteger())return 0;
    MathStructure term(CALCULATOR->getFunction("qpower"),&factor,&power,NULL);
    term.eval(eo);
    if(!k)accumulated=term;
    else {MathStructure left=accumulated;accumulated.set(CALCULATOR->getFunction("qmul"),&left,&term,NULL);accumulated.eval(eo);}
   }
   out=accumulated;return 1;
  }
  if(op=="qsignedequal") {
   MathStructure left=raw[0],right=raw[1];left.eval(eo);right.eval(eo);
   if(!left.isMatrix() || !right.isMatrix() || left.containsUnknowns() || right.containsUnknowns())return 0;
   if(left.equals(right)) {out=1;return 1;}
   right.negate();right.eval(eo);out=left.equals(right) ? 1 : 0;return 1;
  }
  if(op=="qallmembers") {
   MathStructure entries=raw[0];entries.eval(eo);
   // Indexed entries collapse to a single scalar when the family has length one.
   if(!entries.isVector() && !entries.isNumber())return 0;
   size_t count=entries.isVector() ? entries.size() : 1;
   bool pending=false;
   for(size_t j=0;j<count;++j) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &entry=entries.isVector() ? entries[j] : entries;
    MathStructure member(CALCULATOR->getFunction("qmember"),&entry,&raw[1],NULL);
    member.eval(eo);
    if(member.isZero()) {out=0;return 1;}
    if(!member.isOne())pending=true;
   }
   if(pending)return 0;
   out=1;return 1;
  }
  if(op=="qstrictorder") {
   MathStructure entries=raw[0],direction=raw[1];entries.eval(eo);direction.eval(eo);
   if(!entries.isVector() || (!direction.isZero() && !direction.isOne()))return 0;
   MathStructure relation(1);
   for(size_t j=1;j<entries.size();++j) {
    MathStructure pair=entries[j-1];
    pair.transform(direction.isOne() ? COMPARISON_GREATER : COMPARISON_LESS,entries[j]);
    relation.transform(STRUCT_LOGICAL_AND,pair);
   }
   out=relation;return 1;
  }
  if(op=="qspinnumber") {
   MathStructure value=raw[0];value.eval(eo);
   if(value.isUnknown() || value.isSymbolic())return 0;
   if(value.isNumber() && value.number().isReal() && !value.number().isNegative()) {
    Number twice=value.number();
    if(twice.multiply(2) && twice.isInteger()) {out=value;return 1;}
   }
   CALCULATOR->error(true,"A total-spin quantum number must be a nonnegative integer or half-integer.",NULL);return 0;
  }
  if(op=="qchebyshev") {
   MathStructure degree=raw[0],argument=raw[1];degree.eval(eo);argument.eval(eo);
   if(!degree.isNumber() || !argument.isNumber())return 0;
   if(!degree.number().isInteger() || degree.number().isNegative() || degree.number()>Number(4096) ||
      argument.number().includesInfinity()) {
    CALCULATOR->error(true,"Chebyshev evaluation needs a degree from 0 to 4096 and a finite argument.",NULL);return 0;
   }
   Number previous(1),current=argument.number();
   int n=degree.number().intValue();
   for(int i=1;i<n;++i) {
    if(CALCULATOR->aborted())return 0;
    Number next=current;
    if(!next.multiply(argument.number()) || !next.multiply(2) || !next.subtract(previous))return 0;
    previous=current;current=next;
   }
   out.set(n ? current : previous);return 1;
  }
  if(op=="qdistancegreater") {
   MathStructure left=raw[0],right=raw[1],threshold=raw[2];
   left.eval(eo);right.eval(eo);threshold.eval(eo);
   if(!left.isNumber() || !right.isNumber() || !threshold.isNumber())return 0;
   left.subtract(right);left.eval(eo);
   MathStructure distance(CALCULATOR->getFunction("abs"),&left,NULL);distance.eval(eo);
   distance.transform(COMPARISON_GREATER,threshold);distance.eval(eo);out=distance;return 1;
  }
  if(op=="qpolynomialat") {
   MathStructure coefficients=raw[0],argument=raw[1];
   coefficients.eval(eo);argument.eval(eo);
   if(coefficients.isSymbolic() || coefficients.isUnknown())return 0;
   if(!coefficients.isVector() || coefficients.isMatrix() || coefficients.size()==0) {
    CALCULATOR->error(true,"A polynomial filter needs a coefficient vector, constant term first.",NULL);return 0;
   }
   for(size_t i=0;i<coefficients.size();++i) {
    if(!coefficients[i].isNumber() || coefficients[i].number().includesInfinity()) {
     CALCULATOR->error(true,"Polynomial coefficients must be finite numbers.",NULL);return 0;
    }
   }
   if(argument.containsUnknowns() || argument.isSymbolic() || argument.isFunction())return 0;
   bool matrix=argument.isMatrix();
   if(matrix ? argument.rows()!=argument.columns() : !argument.isNumber()) {
    CALCULATOR->error(true,"A polynomial filter needs a scalar or square matrix.",NULL);return 0;
   }
   const bool oneByOne=matrix && argument.rows()==1;
   if(oneByOne) {
    MathStructure scalar=*argument.getElement(1,1);
    argument=scalar;matrix=false;
   }
   if(argument.containsInfinity()) {
    CALCULATOR->error(true,"Polynomial arguments must be finite.",NULL);return 0;
   }
   if(matrix)out.setToIdentityMatrix(argument.rows());
   else out=1;
   out.multiply(coefficients.last());out.eval(eo);
   for(size_t i=coefficients.size()-1;i>0;--i) {
    if(CALCULATOR->aborted())return 0;
    out.multiply(argument);out.eval(eo);
    if(matrix) {
     if(!out.isMatrix() || out.rows()!=argument.rows() || out.columns()!=argument.columns())return 0;
     for(size_t j=1;j<=argument.rows();++j)out.getElement(j,j)->add(coefficients[i-1]);
    } else out.add(coefficients[i-1]);
    out.eval(eo);
   }
   if(oneByOne) {
    MathStructure scalar=out;
    out.clearMatrix();out.resizeMatrix(1,1,scalar);
   }
   return 1;
  }
  if(op=="qrealvectormember") {
   MathStructure value=raw[0],dimension=raw[1];value.eval(eo);dimension.eval(eo);
   if(!dimension.isNumber())return 0;
   if(!dimension.number().isInteger() || dimension.number().isNegative()) {
    CALCULATOR->error(true,"A real vector space needs a nonnegative integer dimension.",NULL);return 0;
   }
   if(value.isFunction() || value.isSymbolic() || value.isUnknown())return 0;
   if(!value.isVector() || (value.isMatrix() && value.rows()!=1 && value.columns()!=1)) {out=0;return 1;}
   size_t count=value.isMatrix() ? value.rows()*value.columns() : value.size();
   if(dimension.number()!=Number((long int)count)) {out=0;return 1;}
   for(size_t k=0;k<count;++k) {
    const auto &part=value.isMatrix() ? *value.getElement(value.rows()==1 ? 1 : k+1,value.rows()==1 ? k+1 : 1) : value[k];
    if(!part.isNumber())return 0;
    if(!part.number().isReal() || part.number().includesInfinity()) {out=0;return 1;}
   }
   out=1;return 1;
  }
  if(op=="qvectordot") {
   MathStructure vectors[2]={raw[0],raw[1]};
   for(auto &v:vectors) {
    v.eval(eo);
    if(v.isFunction() || v.isSymbolic() || v.isUnknown())return 0;
    if(!v.isVector() || (v.isMatrix() && v.rows()!=1 && v.columns()!=1)) {
     CALCULATOR->error(true,"A vector dot product needs two rows or columns.",NULL);return 0;
    }
    if(v.isMatrix()) {
     MathStructure flat;flat.clearVector();
     for(size_t j=0;j<v.rows()*v.columns();++j)
      flat.addChild(*v.getElement(v.rows()==1 ? 1 : j+1,v.rows()==1 ? j+1 : 1));
     v=flat;
    }
   }
   if(vectors[0].size()!=vectors[1].size()) {
    CALCULATOR->error(true,"A vector dot product needs equal lengths.",NULL);return 0;
   }
   out.set(CALCULATOR->getFunction("dot"),&vectors[0],&vectors[1],NULL);out.eval(eo);return 1;
  }
  if(op=="qvectorref") {
   MathStructure value=raw[0];value.eval(eo);
   if(value.isSymbolic() || value.isUnknown() || (value.isFunction() && value.function()->referenceName()=="qindexedlabel"))return 0;
   if(!value.isVector() || (value.isMatrix() && value.rows()!=1 && value.columns()!=1)) {
    CALCULATOR->error(true,"A vector parameter requires a row or column vector.",NULL);return 0;
   }
   size_t count=value.isMatrix() ? value.rows()*value.columns() : value.size();
   for(size_t k=0;k<count;++k) {
    const MathStructure &part=value.isMatrix() ? *value.getElement(value.rows()==1 ? 1 : k+1,value.rows()==1 ? k+1 : 1) : value[k];
    if(!part.representsScalar() || part.isUndefined() || (part.isNumber() && part.number().isInfinite(false))) {
     CALCULATOR->error(true,"Vector parameters must contain finite scalar entries.",NULL);return 0;
    }
   }
   out=value;return 1;
  }
  if(op=="qwireoperatorlike") {
   MathStructure gate=raw[0],wire=raw[1],reference=raw[2];
   gate.eval(eo);wire.eval(eo);reference.eval(eo);
   if(gate.isMatrix() && !reference.isMatrix() && !gate.equals(raw[0])) {
    out.set(this,&gate,&wire,&raw[2],NULL);return 1;
   }
   if(!gate.isMatrix() || !wire.isNumber() || !reference.isMatrix())return 0;
   size_t n=reference.rows(),width=0;
   for(size_t size=n;size>1;size>>=1)++width;
   if(!n || n!=reference.columns() || (n&(n-1)) || gate.rows()!=2 || gate.columns()!=2 ||
      !wire.number().isInteger() || wire.number().isNegative() || wire.number()>=Number((long int)width)) {
    CALCULATOR->error(true,"A gate embedding needs a qubit register, a two-by-two gate and an in-range wire.",NULL);return 0;
   }
   size_t flip=size_t(1)<<wire.number().intValue();
   out.clearMatrix();out.resizeMatrix(n,n,m_zero);
   for(size_t c=0;c<n;++c) {
    if(CALCULATOR->aborted())return 0;
    size_t bit=(c & flip) ? 1 : 0;
    *out.getElement((c & ~flip)+1,c+1)=*gate.getElement(1,bit+1);
    *out.getElement((c | flip)+1,c+1)=*gate.getElement(2,bit+1);
   }
   return 1;
  }
  if(op=="qwireapply") {
   MathStructure gate=raw[0],target=raw[1],control=raw[2],state=raw[3];
   gate.eval(eo);target.eval(eo);control.eval(eo);state.eval(eo);
   if(!gate.isMatrix() || !state.isMatrix() || !target.isNumber() || !control.isNumber())return 0;
   size_t dimension=state.rows(),width=0;
   for(size_t n=dimension;n>1;n>>=1)++width;
   if(!dimension || (dimension & (dimension-1)) || state.columns()!=1 || gate.rows()!=2 || gate.columns()!=2 ||
      !target.number().isInteger() || target.number().isNegative() || target.number()>=Number((long int)width) ||
      !control.number().isInteger() || control.number()<Number(-1) || control.number()>=Number((long int)width) || control==target) {
    CALCULATOR->error(true,"Indexed gates require a two-by-two gate, a qubit ket and distinct in-range wires.",NULL);return 0;
   }
   size_t flip=size_t(1)<<target.number().intValue();
   size_t enable=control.number().isNegative() ? 0 : size_t(1)<<control.number().intValue();
   out=state;
   for(size_t low=0;low<dimension;++low) {
    if((low & flip) || (enable && !(low & enable)))continue;
    if(CALCULATOR->aborted())return 0;
    for(size_t bit=0;bit<2;++bit) {
     MathStructure value=*gate.getElement(bit+1,1),other=*gate.getElement(bit+1,2);
     value.multiply(*state.getElement(low+1,1));other.multiply(*state.getElement((low|flip)+1,1));
     value.add(other);value.eval(eo);
     *out.getElement((bit ? low|flip : low)+1,1)=value;
    }
   }
   return 1;
  }
  if(op=="qzeroimage") {
   MathStructure opMatrix=raw[0];opMatrix.eval(eo);
   if(!opMatrix.isMatrix()) {
    if(opMatrix.isFunction() || opMatrix.isSymbolic() || opMatrix.isUnknown())return 0;
    CALCULATOR->error(true,"An all-zero input requires a square qubit operator.",NULL);return 0;
   }
   size_t n=opMatrix.rows();
   if(n==0 || n!=opMatrix.columns() || (n & (n-1))) {
    CALCULATOR->error(true,"An all-zero input requires a square operator of power-of-two dimension.",NULL);return 0;
   }
   out.clearMatrix();out.resizeMatrix(n,1,m_zero);
   for(size_t r=0;r<n;++r)*out.getElement(r+1,1)=*opMatrix.getElement(r+1,1);
   return 1;
  }
  if(op=="qoperatorref") {
   MathStructure value=raw[0];value.eval(eo);
   if(!value.isMatrix()) {
    if(value.equals(raw[0]))return 0;
    out.set(this,&value,NULL);return 1;
   }
   out=value;return 1;
  }
  if(op=="qkrausapply") {
   MathStructure operators=raw[0];operators.eval(eo);
   MathStructure density=raw[1];density.eval(eo);
   if(!operators.isVector() || !density.isMatrix())return 0;
   out.set(CALCULATOR->getFunction("qchannel"),&density,&operators,NULL);return 1;
  }
  if(op=="qstateaction") {
   MathStructure states=raw;
   for(unsigned k=0;k<2;++k) {
    states[k].eval(eo);
    if(!stateActionOperand(states[k],eo)) {
     CALCULATOR->error(true,"A state mapping requires an input ket and an output ket.",NULL);return 0;
    }
   }
   if(states.equals(raw))return 0;
   out.set(this,&states[0],&states[1],NULL);return 1;
  }
  if(op=="qcheckaction") {
   MathStructure gate=raw[0],action=raw[1],rows,columns;
   gate.eval(eo);action.eval(eo);
   if(!action.isFunction() || action.function()->referenceName()!="qstateaction" ||
      !quantumMatrixShape(gate,rows,columns,eo)) {
    CALCULATOR->error(true,"checkaction requires a matrix operator and a ket mapping.",NULL);return 0;
   }
   MathStructure applied(CALCULATOR->getFunction("qmul"),&gate,&action[0],NULL),equality(4,1);
   out.set(CALCULATOR->getFunction("qcompare"),&applied,&action[1],&equality,NULL);return 1;
  }
  if(op=="qfloorlog2") {
   MathStructure value=raw[0];value.eval(eo);
   if(!value.isNumber() && value.representsScalar() && value.containsUnknowns())return 0;
   if(value.isNumber() && value.number().isRational() && !value.number().isApproximate() && value.number().isPositive()) {
    // Align the leading binary digits. One exact comparison distinguishes
    // the two possible exponents, including just below a power of two.
    Number numerator=value.number().numerator(),denominator=value.number().denominator();
    int shift=numerator.integerLength()-denominator.integerLength();
    if(shift>=0) {if(!denominator.shiftLeft(shift))return 0;}
    else if(!numerator.shiftLeft(-shift))return 0;
    out=shift-(numerator<denominator ? 1 : 0);return 1;
   }
   MathStructure two(2),logarithm(CALCULATOR->getFunctionById(FUNCTION_ID_LOGN),&value,&two,NULL);
   out.set(CALCULATOR->getFunctionById(FUNCTION_ID_FLOOR),&logarithm,NULL);return 1;
  }
  if(op=="qbitlength") {
   MathStructure value=raw[0];value.eval(eo);
   if(!value.isNumber() && value.representsScalar() && value.containsUnknowns())return 0;
   if(!value.isInteger() || value.number().isNegative()) {
    CALCULATOR->error(true,"Binary length requires a nonnegative integer.",NULL);return 0;
   }
   out=value.number().integerLength();return 1;
  }
  if(op=="qrecoverphase")return recoverPhaseFraction(out,raw,eo);
  if(op=="qintegergcd" || op=="qmodpower" || op=="qmodpowerequal") {
   MathStructure args=raw;
   bool pending=false;
   for(size_t k=0;k<args.size();++k) {
    args[k].eval(eo);
    if(args[k].isInteger() && !args[k].isApproximate() && (k!=2 || args[k].number().isPositive()))continue;
    if(!args[k].isNumber() && args[k].containsUnknowns() && args[k].representsScalar()) {pending=true;continue;}
    CALCULATOR->error(true,op=="qintegergcd" ? "Integer GCD requires two exact integers." : "Modular powers require exact integers and a positive modulus.",NULL);return 0;
   }
   if(pending)return 0;
   if(op!="qintegergcd") {
    if(args[1].number().isNegative()) {
     Number divisor=args[0].number();
     if(!divisor.gcd(args[2].number()) || !divisor.isOne()) {
      CALCULATOR->error(true,"A negative modular exponent requires an invertible base.",NULL);return 0;
     }
    }
    out.set(CALCULATOR->getFunctionById(FUNCTION_ID_POWER_MOD),&args[0],&args[1],&args[2],NULL);
    if(op=="qmodpowerequal") {
     out.eval(eo);
     Number rhs=args[3].number();
     if(!out.isInteger() || !rhs.mod(args[2].number()))return 0;
     out=out.number()==rhs ? 1 : 0;
    }
    return 1;
   }
   // Polynomial GCD would assume two unbound integer labels are coprime.
   Number result=args[0].number();
   if(!result.gcd(args[1].number()))return 0;
   out=result;return 1;
  }
  if(op=="qresidue") {
   MathStructure modulus=raw[1];modulus.eval(eo);
   if(modulus.isZero()) {CALCULATOR->error(true,"A modulus must be nonzero.",NULL);return 0;}
   const MathStructure &value=raw[0];
   const bool power=value.isPower() || (value.isFunction() && value.function()->referenceName()=="qpower" && value.size()==2);
   if(power) {
    // Bind each operand independently. In particular, substituting the
    // exponent before the modulus must never materialize the full power.
    MathStructure base=value[0],exponent=value[1];
    base.eval(eo);exponent.eval(eo);
    if(base.isInteger() && exponent.isInteger() && exponent.number().isNonNegative() &&
       modulus.isInteger() && modulus.number().isPositive()) {
     out.set(CALCULATOR->getFunctionById(FUNCTION_ID_POWER_MOD),&base,&exponent,&modulus,NULL);return 1;
    }
    if(base.containsUnknowns() || exponent.containsUnknowns() || modulus.containsUnknowns())return 0;
   }
   out.set(CALCULATOR->getFunctionById(FUNCTION_ID_MOD),&value,&modulus,NULL);return 1;
  }
  if(op=="qmatrixdimensions") {
   MathStructure dimensions=raw;
   for(size_t axis=0;axis<2;++axis) {
    dimensions[axis].eval(eo);
    const MathStructure &count=dimensions[axis];
    if(count.containsUnknowns() && count.representsScalar())continue;
    if(!count.isNumber() || !count.number().isInteger() || count.number()<1) {
     CALCULATOR->error(true,"Matrix dimensions must be positive integers.",NULL);return 0;
    }
   }
   if(dimensions.equals(raw))return 0;
   out.set(this,&dimensions[0],&dimensions[1],NULL);return 1;
  }
  if(op=="qimplicitidentity" || op=="qidentitylike") {
   MathStructure rows(2),columns;
   if(op=="qidentitylike" && !matrixShape(raw[0],rows,columns,eo)) {
    MathStructure product=raw[0];product.eval(eo);
    if(!matrixShape(product,rows,columns,eo)) {
     if(product.containsUnknowns() || !product.isNumber())return 0;
     // A row-column contraction is represented by a scalar.
     out=m_one;return 1;
    }
   }
   out.set(CALCULATOR->getFunction("qidentity"),&rows,NULL);out.eval(eo);return 1;
  }
  if(op=="qcomputationalket") {
   MathStructure index=raw[0];index.eval(eo);
   if(isQuantumBitLabel(index)) {
    out.set(CALCULATOR->getFunction("qketstate"),&index,NULL);return 1;
   }
   bool pending=index.containsUnknowns() && (index.representsScalar() ||
    (index.isFunction() && (index.function()->referenceName()=="qoplus" || index.function()->referenceName()=="qbitxor")));
   if(!pending && (!index.isNumber() || !index.number().isInteger() || index.number()<0)) {
    CALCULATOR->error(true,"A computational basis index must be a nonnegative integer.",NULL);return 0;
   }
   if(index.equals(raw[0]))return 0;
   out.set(this,&index,NULL);return 1;
  }
  if(op=="qtensorchain") {
   // Only notation in one unparenthesized product emits this form. Explicit
   // qtensor calls keep their strict two-matrix contract.
   const MathStructure &factors=raw[1];
   if(!factors.isVector() || factors.size()<2 || factors.size()>2048) {
    CALCULATOR->error(true,"A tensor factor chain requires 2 to 2048 adjacent factors.",NULL);return 0;
   }
   MathStructure right=factors[0];right.eval(eo);size_t next=1;
   while(right.representsScalar()) {
    // An unassigned scalar name may later be replaced by an operator. Keep
    // the original grouping decision available until its type is settled.
    if(right.containsUnknowns()) {
     if(next==1 && !right.equals(factors[0])) {
      MathStructure resolved=factors;resolved[0]=right;resolved.childrenUpdated();
      out.set(this,&raw[0],&resolved,NULL);return 1;
     }
     return 0;
    }
    if(next==factors.size())break;
    if(CALCULATOR->aborted())return 0;
    MathStructure scaled;
    scaled.set(CALCULATOR->getFunction("qadjacent"),&right,&factors[next],NULL);
    scaled.eval(eo);right=scaled;++next;
   }
   out.set(CALCULATOR->getFunction("qtensor"),&raw[0],&right,NULL);
   while(next<factors.size()) {
    if(CALCULATOR->aborted())return 0;
    MathStructure previous=out;
    out.set(CALCULATOR->getFunction("qadjacent"),&previous,&factors[next],NULL);++next;
   }
   out.eval(eo);return 1;
  }
  if(op=="qfourierdomain") {
   EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
   MathStructure index=raw[1],dimension=raw[2];index.eval(exact);dimension.eval(exact);
   bool unknownIndex=!index.isNumber() && index.representsScalar() && index.containsUnknowns();
   bool unknownDimension=!dimension.isNumber() && dimension.representsScalar() && dimension.containsUnknowns();
   if((!unknownIndex && (!index.isNumber() || !index.number().isInteger() || index.number()<0)) ||
      (!unknownDimension && (!dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<1)) ||
      (!unknownIndex && !unknownDimension && index.number()>=dimension.number())) {
    CALCULATOR->error(true,"Fourier basis expansion requires a positive integer dimension and a zero-based index in range.",NULL);return 0;
   }
   // Keep the guard and actual sum together until substitution validates both
   // parameters. Periodic exponentials alone cannot enforce basis membership.
   if(unknownIndex || unknownDimension)return 0;
   if(dimension.number()>64) {
    MathStructure rows,columns;
    if(matrixShape(raw[0],rows,columns,exact) &&
       (unequalKnownDimensions(rows,dimension) || unequalKnownDimensions(columns,m_one)))
     CALCULATOR->error(true,"A Fourier basis expansion must produce a column with the declared dimension.",NULL);
    return 0;
   }
   out=raw[0];out.eval(eo);
   if(!out.isMatrix() || out.columns()!=1 || out.rows()!=size_t(dimension.number().intValue())) {
    CALCULATOR->error(true,"A Fourier basis expansion must produce a column with the declared dimension.",NULL);return 0;
   }
   return 1;
  }
  if((op=="qmul" || op=="qadjacent") && raw.size()==2 && raw[1].isFunction() && raw[1].size()==2 && raw[1].function()->referenceName()=="qbasis") {
   const MathStructure *gate=&raw[0];bool inverse=false;
   if(gate->isFunction() && gate->size()==1 && gate->function()->referenceName()=="qdag") {inverse=true;gate=&(*gate)[0];}
   else if(gate->isFunction() && gate->size()==2 && gate->function()->referenceName()=="qpower") {
    EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
    MathStructure power=(*gate)[1];power.eval(exact);
    if(power.isNumber() && power.number()==-1) {inverse=true;gate=&(*gate)[0];}
   }
   if(gate->isFunction() && gate->size()==1 && gate->function()->referenceName()=="qfourier" && (*gate)[0].equals(raw[1][1]) &&
      (raw[1][0].containsUnknowns() || raw[1][1].containsUnknowns())) {
    const MathStructure &index=raw[1][0],&dimension=raw[1][1];
    unsigned serial=0;MathStructure bound;
    do {bound=MathStructure("qboundindex_fourier_"+std::to_string(serial++),true);}while(raw.contains(bound));
    MathStructure exponent=CALCULATOR->calculate("2*pi*i",eo);exponent*=index;exponent*=bound;exponent/=dimension;if(inverse)exponent.negate();
    MathStructure phase,ket,term,upper=dimension,sum,normalization=dimension,expanded;
    phase.set(CALCULATOR->getFunction("qexp"),&exponent,NULL);
    ket.set(CALCULATOR->getFunction("qbasis"),&bound,&dimension,NULL);
    term.set(CALCULATOR->getFunction("qmul"),&phase,&ket,NULL);
    upper-=m_one;sum.set(CALCULATOR->getFunction("qsum"),&term,&m_zero,&upper,&bound,NULL);
    normalization.raise(Number(-1,2));expanded.set(CALCULATOR->getFunction("qmul"),&normalization,&sum,NULL);
    out.set(CALCULATOR->getFunction("qfourierdomain"),&expanded,&index,&dimension,NULL);out.eval(eo);return 1;
   }
  }
  if(op=="qphysicalunit") {
   Unit *unit=CALCULATOR->getActiveUnit(raw[0].symbol());
   const std::string &name=raw[1].symbol();
   Prefix *prefix=name.empty() ? NULL : CALCULATOR->getPrefix(name);
   if(!unit || (!name.empty() && !prefix)) {
    CALCULATOR->error(true,"Unknown physical unit or prefix.",NULL);return 0;
   }
   out.set(unit,prefix);return 1;
  }
  if(op=="qfrequency") {
   const std::string name=raw[0].symbol();
   Unit *hertz=CALCULATOR->getActiveUnit("Hz");
   if(name.size()<2 || name.compare(name.size()-2,2,"Hz")!=0 || !hertz) {
    CALCULATOR->error(true,"Expected a loaded hertz unit with an optional SI prefix.",NULL);return 0;
   }
   Prefix *prefix=name.size()==2 ? NULL : CALCULATOR->getPrefix(name.substr(0,name.size()-2));
   if(name.size()!=2 && !prefix) {
    CALCULATOR->error(true,"Unknown frequency unit prefix.",NULL);return 0;
   }
   out.set(hertz,prefix);return 1;
  }
  if((op=="qdag" || op=="qconj" || op=="qdensity" || op=="qnorm" || op=="qnormalize") && !CALCULATOR->getFunction("conj")) {
   CALCULATOR->error(true,"Load global function definitions before quantum conjugation.",NULL);return 0;
  }
  if(op=="qasin" || op=="qacos" || op=="qatan" || op=="qsin" || op=="qcos" || op=="qtan") {
   EvaluationOptions radians=eo;radians.parse_options.angle_unit=ANGLE_UNIT_RADIANS;
   EvaluationOptions exact=radians;exact.approximation=APPROXIMATION_EXACT;
   MathFunction *function=CALCULATOR->getFunction(op.substr(1));
   if(!function)return 0;
   // Preserve exact special angles before approximating, especially at the
   // integer discontinuities used by Grover iteration-count floor formulas.
   MathStructure argument=raw[0];argument.eval(exact);
   // Direct trigonometric AST calls bypass AngleArgument parsing; attach the
   // radian unit explicitly so exact evaluation sees an angle in every mode.
   if((op=="qsin" || op=="qcos" || op=="qtan") && !contains_angle_unit(argument,radians.parse_options))
    argument.multiply(CALCULATOR->getRadUnit());
   out.set(function,&argument,NULL);out.eval(exact);
   if(out.containsFunction(function) && eo.approximation!=APPROXIMATION_EXACT)out.eval(radians);
   // Direct functions retain the explicit radian unit in their symbolic argument.
   // Inverse functions need the wrapper to retain dimensionless radian output.
   if(op.size()==5 && out.containsFunction(function))return 0;
   return 1;
  }
  if(op=="qnamedket") {
   out.set(CALCULATOR->getFunction("qketstate"), &raw[0], NULL);out.eval(eo);return 1;
  }
  MathStructure args=raw;
  // Text ket labels retain their full name; resolve explicitly registered
  // variables without routing the label through the ordinary expression parser.
  if(op=="qketstate" && args[0].isSymbolic()) {
   Variable *state=ketVariable(args[0].symbol());
   if(state)args[0].set(state);
   else {
    // A declared family gives a simple subscript its parameter meaning.
    // Explicit named states take precedence; undeclared labels stay opaque.
    const std::string label=args[0].symbol();
    size_t split=label.rfind('_');
    while(split!=std::string::npos && split>0) {
     if(split+1<label.size() && CALCULATOR->getFunction("__qstate_family_"+label.substr(0,split))) {
      MathStructure argument=CALCULATOR->calculate("quantum: "+label.substr(split+1),eo),name;
      name.set(label.substr(0,split),true);
      out.set(CALCULATOR->getFunction("qstatecall"),&name,&argument,NULL);out.eval(eo);return 1;
     }
     split=label.rfind('_',split-1);
    }
   }
  }
  size_t evaluatedArguments=0;
  if(op=="qsub" || op=="qadd")for(size_t k=0;k<2;++k) {
   if(!args[k].isFunction() || args[k].function()->referenceName()!="qimplicitidentity")continue;
   MathStructure other=args[1-k],rows,columns;
   other.eval(eo);
   if(matrixShape(other,rows,columns,eo))args[k].set(CALCULATOR->getFunction("qidentity"),&rows,NULL);
   else if(unresolvedMatrixOperand(other))return 0;
  }
  if((op=="qmul" || op=="qadjacent") && args.size()==2) {
   args[0].eval(eo);MathStructure rows,columns;
   evaluatedArguments=1;
   // Juxtaposed columns mean a tensor product, not operator application.
   if(matrixShape(args[0],rows,columns,eo) && (op=="qmul" || !columns.isOne()) &&
      resolveBasisDimension(args[1],columns)) {
    out.set(this,&args[0],&args[1],NULL);out.eval(eo);return 1;
   }
  }
  for(size_t j=evaluatedArguments;j<args.size();++j)args[j].eval(eo);
  // Retain evaluated basis declarations even when the surrounding operation
  // must remain symbolic (for example, an overlap between distinct bases).
  auto sum=CALCULATOR->getFunction("qsum");
  if(!args.equals(raw) && ((sum && raw.containsFunction(sum)>0 && !args.containsFunction(sum)) ||
     args.containsFunction(CALCULATOR->getFunction("qorthoket"))>0 ||
     args.containsFunction(CALCULATOR->getFunction("qorthofamilyket"))>0)) {
   out=MathStructure(this,static_cast<MathStructure*>(NULL));
   for(size_t j=0;j<args.size();++j)out.addChild(args[j]);
   return 1;
  }
  if(op=="qtensor" || op=="qadjacent" || op=="qtensorpow" || op=="qdag" || op=="qtranspose")for(size_t j=0;j<((op=="qtensor" || op=="qadjacent") ? 2U : 1U);++j) {
   if(!args[j].isVector() || args[j].isMatrix())continue;
   bool flat=true;for(size_t k=0;k<args[j].size();++k)if(args[j][k].isVector())flat=false;
   if(flat && args[j].size()>0 && args[j].size()<=1024) {
    MathStructure row;row.clearMatrix();row.resizeMatrix(1,args[j].size(),m_zero);
    for(size_t k=0;k<args[j].size();++k)element(row,0,k)=args[j][k];
    args[j]=row;
   }
  }
  if(op=="qketstate" && args[0].isFunction() && args[0].function()->referenceName()=="qset" && args[0].size()==1 && args[0][0].isVector()) {
   MathStructure entries=args[0][0];args[0]=entries;
  }
  const MathStructure &a=args[0];
  if(op=="qadjacent" && a.isFunction() && a.function()->referenceName()=="qset" && isQuantumBitLabel(args[1]))
   return applyQuantumBinaryGraph(out,a,args[1],eo);
  if((op=="qadd" || op=="qmul" || op=="qadjacent" || op=="qdensity") &&
     args.containsFunction(CALCULATOR->getFunction("qorthoket"))>0) {
   MathStructure expression(this,static_cast<MathStructure*>(NULL)),dimension;
   for(size_t j=0;j<args.size();++j)expression.addChild(args[j]);
   if(completeOrthonormalProjectors(expression,dimension)) {
    out.set(CALCULATOR->getFunction("qidentity"),&dimension,NULL);out.eval(eo);return 1;
   }
  }
  if(op=="qdensity" && a.isFunction() && a.function()->referenceName()=="qorthoket") {
   MathStructure bra;bra.set(CALCULATOR->getFunction("qdag"),&a,NULL);
   out.set(CALCULATOR->getFunction("qmul"),&a,&bra,NULL);out.eval(eo);return 1;
  }
  // Reject provably incompatible symbolic shapes before numerical expansion.
  if(op=="qadd" || op=="qsub" || op=="qmul" || op=="qadjacent" || op=="qtrace") {
   MathStructure ar,ac,br,bc;
   if(matrixShape(a,ar,ac,eo)) {
    bool mismatch=op=="qtrace" && unequalKnownDimensions(ar,ac);
    if(op!="qtrace" && matrixShape(args[1],br,bc,eo)) {
     if(op=="qmul" || op=="qadjacent")
      mismatch=!(op=="qadjacent" && adjacentStateShapes(ar,ac,br,bc)) && unequalKnownDimensions(ac,br);
     else mismatch=unequalKnownDimensions(ar,br) || unequalKnownDimensions(ac,bc);
    }
    if(mismatch) {CALCULATOR->error(true,"Quantum operation has incompatible declared matrix dimensions.",NULL);return 0;}
   }
  }
  if(op=="qadd" || op=="qsub") {
   const MathStructure &b=args[1];
   if(a.isVector() && b.isVector()) {
    size_t ar=a.isMatrix() ? a.rows() : 1,ac=a.isMatrix() ? a.columns() : a.size();
    size_t br=b.isMatrix() ? b.rows() : 1,bc=b.isMatrix() ? b.columns() : b.size();
    if(ar!=br || ac!=bc) {CALCULATOR->error(true,"Quantum addition and subtraction require matching matrix dimensions.",NULL);return 0;}
   } else if(a.isVector() || b.isVector()) {
    const MathStructure &scalar=a.isVector() ? b : a;
    if(!scalar.representsScalar())return 0;
    if(!scalar.isZero()) {CALCULATOR->error(true,"Quantum addition cannot broadcast a scalar over a matrix; use an explicit identity or matrix.",NULL);return 0;}
   } else if(!a.representsScalar() || !b.representsScalar()) {
    // Retain non-scalar expressions until dimensions are available. Ordinary
    // symbolic scalars still use the library's algebraic simplification.
    return 0;
   }
   out=a;if(op=="qsub")out-=b;else out+=b;out.eval(eo);return 1;
  }
  if(op=="qketstate") {
   if(a.isUnknown())return 0;
   if(a.isVector() && !a.isMatrix() && a.size()>0 && a.size()<=1024) {
    std::set<int> indices;Number registerWidth(-1);bool deferred=false;
    for(size_t k=0;k<a.size();++k) {
     if(CALCULATOR->aborted())return 0;
     const MathStructure &label=a[k];
     if(!label.isFunction() || label.function()->referenceName()!="qbitlabel" || label.size()!=2) {CALCULATOR->error(true,"A set ket requires binary-string labels of one width.",NULL);return 0;}
     MathStructure index=label[0],width=label[1];
     QuantumBitLabelState state=validateQuantumBitLabel(index,width,eo);
     if(state==QuantumBitLabelState::Invalid)return 0;
     if(width.isNumber()) {
      if(registerWidth>=0 && registerWidth!=width.number()) {CALCULATOR->error(true,"A set ket requires binary-string labels of one width.",NULL);return 0;}
      registerWidth=width.number();
     }
     if(state==QuantumBitLabelState::Symbolic || width.number()>10)deferred=true;
     else indices.insert(index.number().intValue());
    }
    if(deferred)return 0;
    MathStructure amplitude(static_cast<int>(indices.size()));amplitude.raise(Number(-1,2));amplitude.eval(eo);
    out.clearMatrix();out.resizeMatrix(1<<registerWidth.intValue(),1,m_zero);
    for(int index:indices)element(out,index,0)=amplitude;
    return 1;
   }
   if(a.isFunction() && a.function()->referenceName()=="qbitlabel" && a.size()==2) {
    MathStructure index=a[0],width=a[1];
    if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Concrete)return 0;
    if(width.number()>10)return 0;
    int dimension=1<<width.number().intValue();out.clearMatrix();out.resizeMatrix(dimension,1,m_zero);
    element(out,index.number().intValue(),0)=m_one;return 1;
   }
   if(!a.isMatrix() || a.columns()!=1 || a.rows()==0 || a.rows()>1024) {
    CALCULATOR->error(true,"A named ket must evaluate to a column vector with at most 1024 rows. For an integer basis index, specify the dimension, for example |k>_4.",NULL);return 0;
   }
   out=a;return 1;
  }
  if(op=="qindexxor" || op=="qoplus") {
   if(isQuantumBitLabel(a) && isQuantumBitLabel(args[1])) {
    out.set(CALCULATOR->getFunction("qbitxor"),&a,&args[1],NULL);
    return 1;
   }
   // A computed index may contain matrix expressions such as trace(A oplus B).
   if(a.isMatrix() && args[1].isMatrix()) {
    out.set(CALCULATOR->getFunction("qdirectsum"), &a, &args[1], NULL);out.eval(eo);
    return out.isMatrix() ? 1 : 0;
   }
   // A free operand can later be bound to an integer, a word or a matrix.
   // Keep the operator until the binding determines which operation applies.
   auto pending=[](const MathStructure &v) {
    return v.isSymbolic() || v.isUnknown() || (v.containsUnknowns() && (v.representsScalar() ||
     (v.isFunction() && (v.function()->referenceName()=="qnamedapplication" || v.function()->referenceName()=="qgraphapply" || v.function()->referenceName()=="qoplus"))));
   };
   if(pending(a) || pending(args[1])) {
    for(size_t j=0;j<2;++j) {
     const MathStructure &v=args[j];
     if(pending(v) || v.isMatrix() || isQuantumBitLabel(v) ||
        (v.isNumber() && v.number().isInteger() && !v.number().isNegative()))continue;
     CALCULATOR->error(true,"Scalar XOR requires nonnegative integer operands.",NULL);return 0;
    }
    return 0;
   }
   for(size_t j=0;j<2;++j)if(!args[j].isNumber() || !args[j].number().isInteger() || args[j].number()<0) {
    CALCULATOR->error(true,"Scalar XOR requires nonnegative integer operands.",NULL);return 0;
   }
   Number value=a.number();if(!value.bitXor(args[1].number()))return 0;
   out.set(value);return 1;
  }
  if(op=="qbasis") {
   const MathStructure &dimension=args[1];
   bool symbolicIndex=!a.isNumber() && a.representsScalar() && a.containsUnknowns();
   bool symbolicDimension=!dimension.isNumber() && dimension.representsScalar() && dimension.containsUnknowns();
   if((!symbolicIndex && (!a.isNumber() || !a.number().isInteger() || a.number()<0)) ||
      (!symbolicDimension && (!dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<1)) ||
      (!symbolicIndex && !symbolicDimension && a.number()>=dimension.number())) {
    CALCULATOR->error(true,"basis(index,dimension) requires a positive integer dimension and a zero-based index in range.",NULL); return 0;
   }
   if(symbolicIndex || symbolicDimension || dimension.number()>1024) {
    // Retain validated scalar normalization while keeping the basis wrapper
    // and its domain checks for later substitutions.
    if(!args.equals(raw)) {out.set(this,&a,&dimension,NULL);return 1;}
    return 0;
   }
   out.clearMatrix(); out.resizeMatrix(dimension.number().intValue(),1,m_zero); element(out,a.number().intValue(),0)=m_one; return 1;
  }
  // Each of these operations is an involution, including on unresolved states.
  if((op=="qdag" || op=="qconj" || op=="qtranspose") && raw[0].isFunction() && raw[0].size()==1) {
   const std::string &inner=raw[0].function()->referenceName();
   if(inner=="qdag" || inner=="qconj" || inner=="qtranspose") {
    // Transpose and conjugation commute, and each is an involution.
    // Keep the operand so later substitution still validates its domain.
    out=raw[0][0];
    if(inner!=op) {
     const char *composed=op!="qdag" && inner!="qdag" ? "qdag" :
       op!="qconj" && inner!="qconj" ? "qconj" : "qtranspose";
     MathStructure operand=out;out.set(CALCULATOR->getFunction(composed),&operand,NULL);
    }
    out.eval(eo);return 1;
   }
  }
  if(op=="qdag" && quantumOperatorAdjoint(a,out))return 1;
  // An unbound capital letter can denote an operator. Retain its adjoint
  // across Copy until substitution supplies its entries and dimensions.
  if(op=="qdag" && a.isSymbolic() && a.symbol().size()==1 && a.symbol()[0]>='A' && a.symbol()[0]<='Z')return 0;
  if((op=="qdag" || op=="qconj" || op=="qtranspose") && !a.isVector() && !a.representsScalar())return 0;
  if(op=="qdag") { out=dagger(a,eo); return 1; }
  if(op=="qconj") { out=dagger(a,eo); if(a.isMatrix()) transposeQuantumMatrix(out); return 1; }
  if(op=="qtranspose") { out=a; if(a.isMatrix()) transposeQuantumMatrix(out); else if(a.isVector()) { CALCULATOR->error(true,"Transpose requires a matrix or scalar.",NULL); return 0; } return 1; }
  if(op=="qadjacent" && a.isMatrix() && args[1].isMatrix() &&
     ((a.columns()==1 && args[1].columns()==1) || (a.rows()==1 && args[1].rows()==1))) {
   // Juxtaposed state vectors form a tensor product, including grouped sums.
   // Reuse the tensor operation's allocation and cancellation checks.
   out.set(CALCULATOR->getFunction("qtensor"), &a, &args[1], NULL);out.eval(eo);
   return out.isMatrix() || out.isVector() ? 1 : 0;
  }
  if(op=="qmul" || op=="qadjacent") {
   const MathStructure &b=args[1];
   if(quantumOperatorProduct(a,b,out)) {out.eval(eo);return 1;}
   if(quantumBasisProduct(a,b,out)) {out.eval(eo);return 1;}
   if(a.isFunction() && a.function()->referenceName()=="qdag" && a.size()==1 &&
      a[0].isFunction() && a[0].function()->referenceName()=="qorthoket" &&
      b.isFunction() && b.function()->referenceName()=="qorthoket") {
    const MathStructure &left=a[0];
    if(left[1].equals(b[1])) {
     if(!left[2].equals(b[2])) {CALCULATOR->error(true,"Conflicting declarations for the same orthonormal basis.",NULL);return 0;}
     out=left[0].equals(b[0]) ? m_one : m_zero;return 1;
    }
   }
   // An indexed operator can later receive a matrix value. Reordering it
   // with an unknown factor here would change the result after substitution.
   if((indexedUppercaseFactor(a) && !b.isNumber()) || (indexedUppercaseFactor(b) && !a.isNumber())) {
    if(!args.equals(raw)){out.set(this,&a,&b,NULL);return 1;}
    return 0;
   }
   // Retain operand order until symbolic operators and states have dimensions.
   if((!a.isVector() && !a.representsScalar()) || (!args[1].isVector() && !args[1].representsScalar()))return 0;
   if(a.isMatrix() && args[1].isMatrix() && a.columns()!=args[1].rows()) { CALCULATOR->error(true,"Quantum matrix dimensions do not match.",NULL); return 0; }
   // Scaling a matrix retains its shape; a row-column product is a scalar.
   bool scaling=(a.isMatrix() && args[1].representsScalar()) || (args[1].isMatrix() && a.representsScalar());
   out=multiply(a,args[1],eo,!scaling); return 1;
  }
  // A trace is scalar, but its operand may still be an unresolved operator.
  // Keep the wrapper so a later substitution is checked for square shape.
  // Returning without a replacement retains the original ordered quantum AST,
  // including during clipboard serialization and subsequent substitutions.
  if(op=="qtrace" && !a.isVector() && unresolvedMatrixOperand(a)) {
   MathStructure rows,columns;
   if(a.isFunction() && a.size()==2 && matrixShape(a,rows,columns,eo) && rows.equals(columns)) {
    const std::string &operation=a.function()->referenceName();
    if(operation=="qadd" || operation=="qsub") {
     MathStructure left,right;left.set(this,&a[0],NULL);right.set(this,&a[1],NULL);
     out=left;if(operation=="qadd")out+=right;else out-=right;out.eval(eo);return 1;
    }
    if(operation=="qmul" || operation=="qadjacent") {
     const int scalar=a[0].representsScalar() ? 0 : a[1].representsScalar() ? 1 : -1;
     if(scalar>=0) {
      MathStructure traced;traced.set(this,&a[1-scalar],NULL);
      out=a[scalar];out*=traced;out.eval(eo);return 1;
     }
    }
   }
   return 0;
  }
  if(op=="qtensor" &&
     ((!a.isVector() && unresolvedMatrixOperand(a)) ||
      (!args[1].isVector() && unresolvedMatrixOperand(args[1])))) {
   // Indexed register bits retain their basis constraints until substitution.
   // A symbolic factor must not hide a concrete invalid scalar factor.
   for(size_t j=0;j<2;++j)if(!args[j].isMatrix() && !unresolvedMatrixOperand(args[j])) {
    CALCULATOR->error(true,"Quantum operation requires two matrices.",NULL);return 0;
   }
   return 0;
  }
  if(op=="qtensorpow") {
   // Preserve both operands until substitution can validate the repeat count
   // and the matrix domain, including when the eventual count is zero.
   bool unknownCount=!args[1].isNumber() && args[1].representsScalar() && args[1].containsUnknowns();
   if(!unknownCount && (!args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0)) {
    CALCULATOR->error(true,"Tensor power requires a nonnegative integer exponent.",NULL);return 0;
   }
   // The expansion limit is not a limit on valid register widths. Keep wide
   // powers intact before converting the count or allocating any matrices.
   bool deferredCount=unknownCount || args[1].number()>10;
   if(a.isMatrix() && a.rows() && a.columns() && !deferredCount) {
    size_t rows=1,columns=1;
    for(int k=0;k<args[1].number().intValue();++k) {
     if(a.rows()>1024/rows || a.columns()>1024/columns) {deferredCount=true;break;}
     rows*=a.rows();columns*=a.columns();
    }
   }
   if((!a.isMatrix() && unresolvedMatrixOperand(a)) || (a.isMatrix() && deferredCount)) {
    // Retain evaluated constructors so copying and re-entry display the same
    // matrix, while the tensor-power wrapper keeps its deferred constraints.
    if(!args.equals(raw)) {
     out=MathStructure(this,static_cast<MathStructure*>(NULL));
     for(size_t j=0;j<args.size();++j)out.addChild(args[j]);
     return 1;
    }
    return 0;
   }
  }
  if((op=="qnorm" || op=="qnormalize") && !a.isVector() && a.containsUnknowns()) {
   if(a.isUnknown() || a.isSymbolic())return 0;
   MathStructure rows,columns;
   if(matrixShape(a,rows,columns,eo)) {
    if(unequalKnownDimensions(columns,m_one))CALCULATOR->error(true,"norm and normalize require a column ket.",NULL);
    return 0;
   }
   // A weighted sum of kets may have no known dimension until its domain
   // is bound. Keep the operation so the resulting column is checked then.
   if(a.isFunction() && unresolvedMatrixOperand(a)) {
    const std::string &name=a.function()->referenceName();
    if(name=="qsumset" || name=="qsum" || name=="qadjacent" || name=="qmul" ||
       name=="qadd" || name=="qsub" || name=="qketstate" || name=="qstatecall")return 0;
   }
  }
  if(op=="qnorm" && a.isZero()) {out.clear();return 1;}
  if(!a.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires a matrix (kets are column matrices).",NULL); return 0; }
  if(op=="qtensorpow") {
   int count=args[1].number().intValue(); out.setToIdentityMatrix(1);
   for(int k=0;k<count;++k) {
    MathStructure previous=out; out.set(CALCULATOR->getFunction("qtensor"), &previous, &a, NULL); out.eval(eo);
    // A tensor product of bras simplifies to a flat row vector.
    if(!out.isMatrix() && !out.isVector()) return 0;
   } return 1;
  }
  if(op=="qnorm" || op=="qnormalize") {
   if(a.columns()!=1) { CALCULATOR->error(true,"norm and normalize require a column ket.",NULL); return 0; }
   MathStructure norm=multiply(dagger(a,eo),a,eo);
   if(norm.isZero() && op=="qnormalize") { CALCULATOR->error(true,"Cannot normalize the zero ket.",NULL); return 0; }
   norm.raise(Number(1,2)); norm.eval(eo);
   out= op=="qnorm" ? norm : a; if(op=="qnormalize") out/=norm; return 1;
  }
  if(op=="qdensity") {
   if(a.columns()!=1 || a.rows()>1024) { CALCULATOR->error(true,"density requires a column ket with at most 1024 entries.",NULL); return 0; }
   out=multiply(a,dagger(a,eo),eo,false); return 1;
  }
  if(op=="qtrace") {
   if(a.rows()!=a.columns()) { CALCULATOR->error(true,"Trace requires a square matrix.",NULL); return 0; }
   out.clear(); for(size_t r=0;r<a.rows();++r) out+=element(a,r,r); return 1;
  }
  if(op=="qcontrol" || op=="qcontrolpattern") {
   const MathStructure &count=args[1], &state=args[2];
   if(!count.isNumber() || !count.number().isInteger() || count.number()<1 || count.number()>8) {
    CALCULATOR->error(true,"Controlled gates require an integer control count from 1 to 8.",NULL); return 0;
   }
   size_t blocks=size_t(1)<<count.number().intValue(), n=a.rows();
   if(op=="qcontrolpattern" && args[3]!=count) {
    CALCULATOR->error(true,"The control pattern length must equal the number of controls.",NULL);return 0;
   }
   if(n!=a.columns() || n<2 || (n & (n-1)) || n>512/blocks) {
    CALCULATOR->error(true,"Controlled gates require a square qubit operator and at most 512 total dimensions.",NULL); return 0;
   }
   if(!state.isNumber() || !state.number().isInteger() || state.number()<0 || state.number()>=Number(blocks)) {
    CALCULATOR->error(true,"Control state must be an integer from 0 to 2^controls-1; the leftmost control is the most significant bit.",NULL); return 0;
   }
   size_t offset=n*state.number().intValue();
   out.setToIdentityMatrix(n*blocks);
   for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,offset+r,offset+c)=element(a,r,c);
   return 1;
  }
  if(op=="qcontrolled") {
   size_t n=a.rows(); if(n!=a.columns() || n>256) { CALCULATOR->error(true,"Controlled gates require a square matrix of dimension at most 256.",NULL); return 0; }
   out.setToIdentityMatrix(n*2); for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,r+n,c+n)=element(a,r,c); return 1;
  }
  const MathStructure &b=args[1]; if(!b.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires two matrices.",NULL); return 0; }
  if(op=="qcomm" || op=="qanticomm") {
   if(a.rows()!=a.columns() || b.rows()!=b.columns() || a.rows()!=b.rows()) { CALCULATOR->error(true,"Commutators require square matrices of the same dimension.",NULL); return 0; }
   out=multiply(a,b,eo); auto reverse=multiply(b,a,eo); if(op=="qcomm") out-=reverse; else out+=reverse; return 1;
  }
  size_t rows=op=="qtensor" ? a.rows()*b.rows() : a.rows()+b.rows();
  size_t cols=op=="qtensor" ? a.columns()*b.columns() : a.columns()+b.columns();
  if(rows>1024 || cols>1024 || rows*cols>1048576) {
   if(op=="qtensor") {
    if(!args.equals(raw)) {out.set(this,&args[0],&args[1],NULL);return 1;}
    return 0;
   }
   CALCULATOR->error(true,"Quantum matrix allocation limit exceeded (1048576 elements).",NULL); return 0;
  }
  out.clearMatrix(); out.resizeMatrix(rows,cols,m_zero);
  for(size_t r=0;r<a.rows();++r) for(size_t c=0;c<a.columns();++c) {
   if(CALCULATOR->aborted()) return 0;
   if(op=="qdirectsum") element(out,r,c)=element(a,r,c);
   else for(size_t j=0;j<b.rows();++j) for(size_t k=0;k<b.columns();++k) { element(out,r*b.rows()+j,c*b.columns()+k)=element(a,r,c); element(out,r*b.rows()+j,c*b.columns()+k)*=element(b,j,k); }
  }
  if(op=="qdirectsum") for(size_t r=0;r<b.rows();++r) for(size_t c=0;c<b.columns();++c) element(out,r+a.rows(),c+a.columns())=element(b,r,c);
  return 1;
 }
};
}
MathStructure quantumAdjoint(const MathStructure &value, const EvaluationOptions &options) {
 return dagger(value,options);
}
bool quantumMatrixShape(const MathStructure &value, MathStructure &rows, MathStructure &columns, const EvaluationOptions &options) {
 return matrixShape(value,rows,columns,options);
}
bool quantumResolveBasisDimension(MathStructure &value,const MathStructure &dimension) {
 return resolveBasisDimension(value,dimension);
}
void registerQuantumAlgebra(Calculator &calculator) {
 registerQuantumOperatorDomain(calculator);
 registerQuantumBasisDomain(calculator);
 calculator.addFunction(new QuantumOrthonormalKet());
 calculator.addFunction(new QuantumOrthonormalBasis());
 calculator.addFunction(new QuantumComplexParameter());
 calculator.addFunction(new QuantumMatrixParameter());
 calculator.addFunction(new QuantumMatrixAssumption());
 calculator.addFunction(new QuantumMatrixAssumption(true));
 calculator.addFunction(new QuantumMatrixAssumption(false,true));
 calculator.addFunction(new QuantumMatrixAssumption(true,true));
 calculator.addFunction(new QuantumMatrixConstructor<MatrixFunction>("qmatrix"));
 calculator.addFunction(new QuantumMatrixConstructor<IdentityMatrixFunction>("qidentity"));
 calculator.addFunction(new QuantumAlgebraFunction("qmatrixdimensions",2));
 calculator.addFunction(new QuantumAlgebraFunction("qimplicitidentity",0));
 calculator.addFunction(new QuantumAlgebraFunction("qidentitylike",1));
 calculator.addFunction(new QuantumAlgebraFunction("qfloorlog2",1));
 calculator.addFunction(new QuantumAlgebraFunction("qbitlength",1));
 calculator.addFunction(new QuantumAlgebraFunction("qrecoverphase",2));
 calculator.addFunction(new QuantumAlgebraFunction("qintegergcd",2));
 calculator.addFunction(new QuantumAlgebraFunction("qmodpower",3));
 calculator.addFunction(new QuantumAlgebraFunction("qmodpowerequal",4));
 calculator.addFunction(new QuantumAlgebraFunction("qresidue",2));
 calculator.addFunction(new QuantumAlgebraFunction("qfrequency",1));
 calculator.addFunction(new QuantumAlgebraFunction("qphysicalunit",2));
 calculator.addFunction(new QuantumAlgebraFunction("qbinarypowersum",1));
 calculator.addFunction(new QuantumAlgebraFunction("qprojectorproduct",2));
 calculator.addFunction(new QuantumAlgebraFunction("qfixedby",2));
 calculator.addFunction(new QuantumAlgebraFunction("qorderedpowers",2));
 calculator.addFunction(new QuantumAlgebraFunction("qsignedequal",2));
 calculator.addFunction(new QuantumAlgebraFunction("qallmembers",2));
 calculator.addFunction(new QuantumAlgebraFunction("qstrictorder",2));
 calculator.addFunction(new QuantumAlgebraFunction("qchebyshev",2));
 calculator.addFunction(new QuantumAlgebraFunction("qspinnumber",1));
 calculator.addFunction(new QuantumAlgebraFunction("qdistancegreater",3));
 calculator.addFunction(new QuantumAlgebraFunction("qpolynomialat",2));
 calculator.addFunction(new QuantumAlgebraFunction("qrealvectormember",2));
 calculator.addFunction(new QuantumAlgebraFunction("qvectordot",2));
 calculator.addFunction(new QuantumAlgebraFunction("qvectorref",1));
 calculator.addFunction(new QuantumAlgebraFunction("qzeroimage",1));
 calculator.addFunction(new QuantumAlgebraFunction("qwireapply",4));
 calculator.addFunction(new QuantumAlgebraFunction("qwireoperatorlike",3));
 calculator.addFunction(new QuantumAlgebraFunction("qoperatorref",1));
 calculator.addFunction(new QuantumAlgebraFunction("qkrausapply",2));
 calculator.addFunction(new QuantumAlgebraFunction("qadd",2));
 calculator.addFunction(new QuantumAlgebraFunction("qsub",2));
 for(const char *name:{"qasin","qacos","qatan","qsin","qcos","qtan"})calculator.addFunction(new QuantumAlgebraFunction(name,1));
 calculator.addFunction(new QuantumAlgebraFunction("qketstate",1));
 calculator.addFunction(new QuantumAlgebraFunction("qnamedket",1));
 calculator.addFunction(new QuantumAlgebraFunction("qcomputationalket",1));
 for(const auto &entry:{std::pair<const char *,int>("qbasis",2),{"qstateaction",2},{"qcheckaction",2},{"qfourierdomain",3},{"qindexxor",2},{"qoplus",2},{"qdag",1},{"qconj",1},{"qtranspose",1},{"qmul",2},{"qadjacent",2},{"qtensorchain",2},{"qtensorpow",2},{"qhadamardpower",1},{"qjwimage",3},{"qspinladder",3},{"qpropagator",2},{"qkrylovstates",4},{"qoperatorunequal",2},{"qnorm",1},{"qnormalize",1},{"qdensity",1},{"qtrace",1},{"qcontrol",3},{"qcontrolpattern",4},{"qcontrolled",1},{"qcomm",2},{"qanticomm",2},{"qtensor",2},{"qdirectsum",2}})
  calculator.addFunction(new QuantumAlgebraFunction(entry.first,entry.second));
}

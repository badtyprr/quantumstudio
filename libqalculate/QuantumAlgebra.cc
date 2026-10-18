// GPL-2.0-or-later; see COPYING.
#include "QuantumAlgebra.h"
#include "Calculator.h"
#include "Function.h"
#include "BuiltinFunctions.h"
#include "Variable.h"
#include <string>
#include <utility>
#include <set>
#include <cctype>
namespace {
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
   // Explicit domains and single-letter ket labels retain their meaning.
   if((name=="matrixparam" || name=="qketstate") && i==0)continue;
   // An inner declaration owns its body, but not its dimension expressions.
   if(name=="matrixassume" && value.size()==4 && i==0 && value[1].isSymbolic() && value[1].symbol()==declaredName)continue;
  }
  if(!annotateMatrixSymbol(value[i],symbol,declaration,declaredName,depth+1))return false;
 }
 if(value.size())value.childrenUpdated();
 return true;
}
class QuantumMatrixAssumption: public MathFunction {
 public:
 QuantumMatrixAssumption():MathFunction("matrixassume",4) {setArgumentDefinition(2,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumMatrixAssumption(*this);}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  const std::string name=raw[1].symbol();
  bool valid=!name.empty() && name.size()<=128 && !(name[0]>='0' && name[0]<='9');
  for(unsigned char c:name)if(c<128 && !std::isalnum(c) && c!='_')valid=false;
  if(!valid) {CALCULATOR->error(true,"A matrix declaration requires a single symbol name.",NULL);return 0;}
  MathStructure symbol=CALCULATOR->calculate("quantum: "+name,eo);
  if(!symbol.isUnknown()) {CALCULATOR->error(true,"Matrix names cannot override gates, constants, or existing values.",NULL);return 0;}
  MathStructure declaration;declaration.set(CALCULATOR->getFunction("matrixparam"),&symbol,&raw[2],&raw[3],NULL);
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
bool matrixShape(const MathStructure &value,MathStructure &rows,MathStructure &columns,const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>64)return false;
 if(value.isMatrix()) {rows.set(Number(static_cast<long>(value.rows())));columns.set(Number(static_cast<long>(value.columns())));return true;}
 if(!value.isFunction())return false;
 const std::string &name=value.function()->referenceName();
 if(name=="matrixparam" && value.size()==3) {
  rows=value[1];columns=value[2];EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
  rows.eval(exact);columns.eval(exact);return true;
 }
 if((name=="qdag" || name=="qtranspose") && value.size()==1)
  return matrixShape(value[0],columns,rows,eo,depth+1);
 if(value.size()!=2)return false;
 MathStructure ar,ac,br,bc;
 bool left=matrixShape(value[0],ar,ac,eo,depth+1),right=matrixShape(value[1],br,bc,eo,depth+1);
 if((name=="qadd" || name=="qsub") && left && right && ar.equals(br) && ac.equals(bc)) {rows=ar;columns=ac;return true;}
 if(name=="qmul" || name=="qadjacent") {
  if(name=="qmul" && left && right && ac.equals(br)) {
   // Row-column contraction has scalar semantics in quantum multiplication.
   if(ar.isOne() && bc.isOne())return false;
   rows=ar;columns=bc;return true;
  }
  if(left && value[1].representsScalar()) {rows=ar;columns=ac;return true;}
  if(right && value[0].representsScalar()) {rows=br;columns=bc;return true;}
 }
 return false;
}
bool unequalKnownDimensions(const MathStructure &a,const MathStructure &b) {
 return a.isNumber() && b.isNumber() && a.number()!=b.number();
}
class QuantumAlgebraFunction: public MathFunction {
 std::string op;
 public:
 QuantumAlgebraFunction(const std::string &name,int n):MathFunction(name,n),op(name) {
  if(op=="qnamedket" || op=="qfrequency")setArgumentDefinition(1,new TextArgument());
 }
 ExpressionItem *copy() const {return new QuantumAlgebraFunction(*this);}
 bool preservesSingletonMatrix() const {return true;}
 bool representsScalar(const MathStructure &args) const {
  return op=="qtrace" || MathFunction::representsScalar(args);
 }
 bool representsNonMatrix(const MathStructure &args) const {
  return op=="qtrace" || MathFunction::representsNonMatrix(args);
 }
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
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
   if(op=="qsin" || op=="qcos" || op=="qtan")argument.multiply(CALCULATOR->getRadUnit());
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
   Variable *state=CALCULATOR->getActiveVariable(args[0].symbol());
   if(state && !state->isBuiltin())args[0].set(state);
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
  for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  if(op=="qtensor" || op=="qadjacent" || op=="qtensorpow" || op=="qdag" || op=="qtranspose")for(size_t j=0;j<((op=="qtensor" || op=="qadjacent") ? 2U : 1U);++j) {
   if(!args[j].isVector() || args[j].isMatrix())continue;
   bool flat=true;for(size_t k=0;k<args[j].size();++k)if(args[j][k].isVector())flat=false;
   if(flat && args[j].size()>0 && args[j].size()<=1024) {
    MathStructure row;row.clearMatrix();row.resizeMatrix(1,args[j].size(),m_zero);
    for(size_t k=0;k<args[j].size();++k)element(row,0,k)=args[j][k];
    args[j]=row;
   }
  }
  const MathStructure &a=args[0];
  // Reject provably incompatible symbolic shapes before numerical expansion.
  if(op=="qadd" || op=="qsub" || op=="qmul" || op=="qtrace") {
   MathStructure ar,ac,br,bc;
   if(matrixShape(a,ar,ac,eo)) {
    bool mismatch=op=="qtrace" && unequalKnownDimensions(ar,ac);
    if(op!="qtrace" && matrixShape(args[1],br,bc,eo))
     mismatch=op=="qmul" ? unequalKnownDimensions(ac,br) : unequalKnownDimensions(ar,br) || unequalKnownDimensions(ac,bc);
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
    std::set<int> indices;int registerWidth=-1;
    for(size_t k=0;k<a.size();++k) {
     if(CALCULATOR->aborted())return 0;
     const MathStructure &label=a[k];
     if(!label.isFunction() || label.function()->referenceName()!="qbitlabel" || label.size()!=2) {CALCULATOR->error(true,"A set ket requires binary-string labels of one width.",NULL);return 0;}
     EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
     MathStructure index=label[0],width=label[1];index.eval(exact);width.eval(exact);
     if(!index.isNumber() || !index.number().isInteger() || !width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10 || index.number()<0 || index.number()>=Number(1<<width.number().intValue())) {CALCULATOR->error(true,"Invalid binary-string basis label.",NULL);return 0;}
     if(registerWidth>=0 && registerWidth!=width.number().intValue()) {CALCULATOR->error(true,"A set ket requires binary-string labels of one width.",NULL);return 0;}
     registerWidth=width.number().intValue();indices.insert(index.number().intValue());
    }
    MathStructure amplitude(static_cast<int>(indices.size()));amplitude.raise(Number(-1,2));amplitude.eval(eo);
    out.clearMatrix();out.resizeMatrix(1<<registerWidth,1,m_zero);
    for(int index:indices)element(out,index,0)=amplitude;
    return 1;
   }
   if(a.isFunction() && a.function()->referenceName()=="qbitlabel" && a.size()==2) {
    MathStructure index=a[0],width=a[1];index.eval(eo);width.eval(eo);
    if(!index.isNumber() || !index.number().isInteger() || !width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10 || index.number()<0 || index.number()>=Number(1<<width.number().intValue())) {CALCULATOR->error(true,"Invalid binary-string basis label.",NULL);return 0;}
    int dimension=1<<width.number().intValue();out.clearMatrix();out.resizeMatrix(dimension,1,m_zero);
    element(out,index.number().intValue(),0)=m_one;return 1;
   }
   if(!a.isMatrix() || a.columns()!=1 || a.rows()==0 || a.rows()>1024) {
    CALCULATOR->error(true,"A named ket must evaluate to a column vector with at most 1024 rows. For an integer basis index, specify the dimension, for example |k>_4.",NULL);return 0;
   }
   out=a;return 1;
  }
  if(op=="qindexxor" || op=="qoplus") {
   // A computed index may contain matrix expressions such as trace(A oplus B).
   if(a.isMatrix() && args[1].isMatrix()) {
    out.set(CALCULATOR->getFunction("qdirectsum"), &a, &args[1], NULL);out.eval(eo);
    return out.isMatrix() ? 1 : 0;
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
      (!symbolicDimension && (!dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<1 || dimension.number()>1024)) ||
      (!symbolicIndex && !symbolicDimension && a.number()>=dimension.number())) {
    CALCULATOR->error(true,"basis(index,dimension) requires an integer dimension from 1 to 1024 and a zero-based index in range.",NULL); return 0;
   }
   if(symbolicIndex || symbolicDimension)return 0;
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
  if(!a.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires a matrix (kets are column matrices).",NULL); return 0; }
  if(op=="qtensorpow") {
   if(!args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0 || args[1].number()>10) { CALCULATOR->error(true,"Tensor power requires an integer exponent from 0 to 10.",NULL); return 0; }
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
  if(rows>1024 || cols>1024 || rows*cols>1048576) { CALCULATOR->error(true,"Quantum matrix allocation limit exceeded (1048576 elements).",NULL); return 0; }
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
void registerQuantumAlgebra(Calculator &calculator) {
 calculator.addFunction(new QuantumComplexParameter());
 calculator.addFunction(new QuantumMatrixParameter());
 calculator.addFunction(new QuantumMatrixAssumption());
 calculator.addFunction(new QuantumMatrixConstructor<MatrixFunction>("qmatrix"));
 calculator.addFunction(new QuantumMatrixConstructor<IdentityMatrixFunction>("qidentity"));
 calculator.addFunction(new QuantumAlgebraFunction("qfrequency",1));
 calculator.addFunction(new QuantumAlgebraFunction("qadd",2));
 calculator.addFunction(new QuantumAlgebraFunction("qsub",2));
 for(const char *name:{"qasin","qacos","qatan","qsin","qcos","qtan"})calculator.addFunction(new QuantumAlgebraFunction(name,1));
 calculator.addFunction(new QuantumAlgebraFunction("qketstate",1));
 calculator.addFunction(new QuantumAlgebraFunction("qnamedket",1));
 for(const auto &entry:{std::pair<const char *,int>("qbasis",2),{"qindexxor",2},{"qoplus",2},{"qdag",1},{"qconj",1},{"qtranspose",1},{"qmul",2},{"qadjacent",2},{"qtensorpow",2},{"qnorm",1},{"qnormalize",1},{"qdensity",1},{"qtrace",1},{"qcontrol",3},{"qcontrolpattern",4},{"qcontrolled",1},{"qcomm",2},{"qanticomm",2},{"qtensor",2},{"qdirectsum",2}})
  calculator.addFunction(new QuantumAlgebraFunction(entry.first,entry.second));
}

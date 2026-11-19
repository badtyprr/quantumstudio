// GPL-2.0-or-later; see COPYING.
#include "QuantumOrder.h"
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
#include "QuantumBinary.h"
#include "QuantumIndexed.h"
namespace {
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
bool symbolicGram(const MathStructure &value,const EvaluationOptions &eo) {
 if(!value.isFunction() || value.size()!=2)return false;
 const std::string &name=value.function()->referenceName();
 if(name!="qmul" && name!="qadjacent")return false;
 for(unsigned i=0;i<2;++i) {
  const MathStructure &adjoint=value[i],&factor=value[1-i];
  if(!adjoint.isFunction() || adjoint.function()->referenceName()!="qdag" || adjoint.size()!=1 || !adjoint[0].equals(factor))continue;
  MathStructure rows,columns;
  if(quantumMatrixShape(factor,rows,columns,eo))return true;
 }
 return false;
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
class QuantumOrderFunction: public MathFunction {
 public:
 QuantumOrderFunction():MathFunction("qcompare",3) {}
 ExpressionItem *copy() const {return new QuantumOrderFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;args[2].eval(eo);
  args[0].eval(eo);
  bool equality=args[2].isNumber() && args[2].number()==4;
  MathStructure rows,columns;
  if(equality && quantumMatrixShape(args[0],rows,columns,eo) && columns.isOne())
   quantumResolveBasisDimension(args[1],rows);
  args[1].eval(eo);
  if(equality && quantumMatrixShape(args[1],rows,columns,eo) && columns.isOne() &&
     quantumResolveBasisDimension(args[0],rows))args[0].eval(eo);
  {
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>5) {
    CALCULATOR->error(true,"Invalid quantum comparison kind.",NULL);return 0;
   }
   static const ComparisonType kinds[]={COMPARISON_LESS,COMPARISON_GREATER,COMPARISON_EQUALS_LESS,COMPARISON_EQUALS_GREATER,COMPARISON_EQUALS,COMPARISON_NOT_EQUALS};
   int kind=args[2].number().intValue();
   bool equal=false;
   if(kind>=4 && compareBitLabels(args[0],args[1],equal,eo)) {out=(kind==4)==equal ? 1 : 0;return 1;}
   if(args[1].isZero() && symbolicGram(args[0],eo) && (kind==0 || kind==3)) {out=kind==3 ? 1 : 0;return 1;}
   if(args[0].isZero() && symbolicGram(args[1],eo) && (kind==1 || kind==2)) {out=kind==2 ? 1 : 0;return 1;}
   if(args[2].number()<4 && (args[0].containsType(STRUCT_VECTOR,true)>0 || args[1].containsType(STRUCT_VECTOR,true)>0))
    return quantumMatrixOrder(out,raw[0],raw[1],args[2].number().intValue(),eo) ? 1 : 0;
   out=args[0];out.transform(kinds[args[2].number().intValue()],args[1]);out.eval(eo);return 1;
  }
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
  for(size_t k=0;k<operands.size();++k) {
   if(CALCULATOR->aborted())return 0;
   operands[k].eval(eo);MathStructure rows,columns;
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
 calculator.addFunction(new QuantumEquivalence());
 calculator.addFunction(new QuantumOrderFunction());
 calculator.addFunction(new QuantumEqualityChain());
}

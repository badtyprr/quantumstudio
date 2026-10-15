// GPL-2.0-or-later; see COPYING.
#include "QuantumOrder.h"
#include "Calculator.h"
#include "Function.h"
namespace {
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
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  {
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>5) {
    CALCULATOR->error(true,"Invalid quantum comparison kind.",NULL);return 0;
   }
   static const ComparisonType kinds[]={COMPARISON_LESS,COMPARISON_GREATER,COMPARISON_EQUALS_LESS,COMPARISON_EQUALS_GREATER,COMPARISON_EQUALS,COMPARISON_NOT_EQUALS};
   if(args[2].number()<4 && (args[0].containsType(STRUCT_VECTOR,true)>0 || args[1].containsType(STRUCT_VECTOR,true)>0))
    return quantumMatrixOrder(out,raw[0],raw[1],args[2].number().intValue(),eo) ? 1 : 0;
   out=args[0];out.transform(kinds[args[2].number().intValue()],args[1]);out.eval(eo);return 1;
  }
 }
};
}
void registerQuantumOrder(Calculator &calculator) {calculator.addFunction(new QuantumOrderFunction());}

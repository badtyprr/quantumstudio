// GPL-2.0-or-later; see COPYING.
#include "QuantumBinary.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
bool binaryMatrix(const MathStructure &a,std::vector<std::vector<unsigned char>> &matrix) {
 size_t rows=a.isMatrix() ? a.rows() : 1, columns=a.isMatrix() ? a.columns() : a.isVector() ? a.size() : 1;
 if(rows==0 || columns==0 || rows>128 || columns>128) {CALCULATOR->error(true,"GF(2) operations require a nonempty matrix with at most 128 rows and columns.",NULL);return false;}
 matrix.assign(rows,std::vector<unsigned char>(columns));
 for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c) {
  const MathStructure &value=a.isMatrix() ? element(a,r,c) : a.isVector() ? a[c] : a;
  if(!value.isNumber() || (!value.number().isZero() && !value.number().isOne())) {CALCULATOR->error(true,"GF(2) matrix entries must be 0 or 1.",NULL);return false;}
  matrix[r][c]=value.number().isOne() ? 1 : 0;
 }
 return true;
}
class QuantumBinaryFunction: public MathFunction {
 std::string op;
 public:
 QuantumBinaryFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumBinaryFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qgf2mul") {
   std::vector<std::vector<unsigned char>> left,right;
   if(!binaryMatrix(a,left) || !binaryMatrix(args[1],right))return 0;
   if(left[0].size()!=right.size()) {CALCULATOR->error(true,"GF(2) matrix multiplication requires matching inner dimensions.",NULL);return 0;}
   out.clearMatrix();out.resizeMatrix(left.size(),right[0].size(),m_zero);
   for(size_t r=0;r<left.size();++r) {
    if(CALCULATOR->aborted())return 0;
    for(size_t c=0;c<right[0].size();++c) {
     unsigned char parity=0;for(size_t k=0;k<right.size();++k)parity^=left[r][k]&right[k][c];
     if(parity)element(out,r,c)=m_one;
    }
   }
   return 1;
  }
  if(op=="qgf2rref" || op=="qgf2rank" || op=="qgf2nullspace" || op=="qgf2inverse" || op=="qlineargate") {
   std::vector<std::vector<unsigned char>> reduced;
   if(!binaryMatrix(a,reduced))return 0;
   size_t rows=reduced.size(),columns=reduced[0].size();
   bool inverse=op=="qgf2inverse",linear=op=="qlineargate";
   if((inverse || linear) && rows!=columns) {CALCULATOR->error(true,"GF(2) inversion and linear gates require square matrices.",NULL);return 0;}
   if(linear && columns>9) {CALCULATOR->error(true,"Linear gates support 1 to 9 qubits.",NULL);return 0;}
   std::vector<std::vector<unsigned char>> original;if(linear)original=reduced;
   size_t width=inverse ? 2*columns : columns;
   if(inverse)for(size_t r=0;r<rows;++r) {reduced[r].resize(width,0);reduced[r][columns+r]=1;}
   std::vector<size_t> pivots;
   for(size_t c=0;c<columns && pivots.size()<rows;++c) {
    if(CALCULATOR->aborted())return 0;
    size_t rank=pivots.size(),selected=rank;
    while(selected<rows && !reduced[selected][c])++selected;
    if(selected==rows)continue;
    std::swap(reduced[rank],reduced[selected]);
    for(size_t r=0;r<rows;++r)if(r!=rank && reduced[r][c])for(size_t k=c;k<width;++k)reduced[r][k]^=reduced[rank][k];
    pivots.push_back(c);
   }
   if(linear) {
    if(pivots.size()!=columns) {CALCULATOR->error(true,"A linear quantum gate requires an invertible binary map.",NULL);return 0;}
    size_t dimension=size_t(1)<<columns;
    out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
    for(size_t x=0;x<dimension;++x) {
     if(CALCULATOR->aborted())return 0;
     size_t y=0;
     for(size_t r=0;r<rows;++r) {
      unsigned char parity=0;for(size_t c=0;c<columns;++c)parity^=original[r][c]&((x>>(columns-1-c))&1);
      y=(y<<1)|parity;
     }
     element(out,y,x)=m_one;
    }
    return 1;
   }
   if(inverse) {
    if(pivots.size()!=columns) {CALCULATOR->error(true,"The matrix is singular over GF(2).",NULL);return 0;}
    out.clearMatrix();out.resizeMatrix(rows,columns,m_zero);
    for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c)if(reduced[r][columns+c])element(out,r,c)=m_one;
    return 1;
   }
   if(op=="qgf2rank") {out=MathStructure((int)pivots.size());return 1;}
   if(op=="qgf2rref") {
    out.clearMatrix();out.resizeMatrix(rows,columns,m_zero);
    for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c)if(reduced[r][c])element(out,r,c)=m_one;
    return 1;
   }
   size_t nullity=columns-pivots.size();
   // No basis vectors means the kernel contains only zero. Qalculate has no
   // zero-column matrix representation, so expose an empty vector in this case.
   if(!nullity) {out.clearVector();return 1;}
   out.clearMatrix();out.resizeMatrix(columns,nullity,m_zero);
   size_t pivotIndex=0,basisColumn=0;
   for(size_t free=0;free<columns;++free) {
    if(pivotIndex<pivots.size() && pivots[pivotIndex]==free) {++pivotIndex;continue;}
    element(out,free,basisColumn)=m_one;
    for(size_t r=0;r<pivots.size();++r)if(reduced[r][free])element(out,pivots[r],basisColumn)=m_one;
    ++basisColumn;
   }
   return 1;
  }
  if(op=="qbits") {
   const MathStructure &width=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number().isNegative() || !width.isNumber() || !width.number().isInteger() || width.number()<1 || width.number()>1024) {CALCULATOR->error(true,"bits(value,width) requires a nonnegative integer and a width from 1 to 1024.",NULL);return 0;}
   Number limit(1);limit.shiftLeft(width.number());
   if(a.number()>=limit) {CALCULATOR->error(true,"The integer does not fit in the requested binary width.",NULL);return 0;}
   out.clearVector();
   for(int k=width.number().intValue();k>0;--k)out.addChild(a.number().bitGet(k) ? m_one : m_zero);
   return 1;
  }
  if(op=="qbitdot" || op=="qbitxor" || op=="qbitvalue") {
   std::vector<MathStructure> bits[2];
   bool labels[2]={false,false};
   for(size_t j=0;j<(op=="qbitvalue" ? 1U : 2U);++j) {
    const MathStructure &value=args[j];
    labels[j]=value.isFunction() && value.function()->referenceName()=="qbitlabel";
    if(labels[j]) {
     if(value.size()!=2) {CALCULATOR->error(true,"Invalid binary-string label.",NULL);return 0;}
     MathStructure index=value[0],width=value[1];
     EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;index.eval(exact);width.eval(exact);
     if(!index.isNumber() || !index.number().isInteger() || !width.isNumber() || !width.number().isInteger() || width.number()<0 || width.number()>10 || index.number()<0 || index.number()>=Number(1<<width.number().intValue())) {CALCULATOR->error(true,"Invalid binary-string label.",NULL);return 0;}
     for(int k=width.number().intValue()-1;k>=0;--k)bits[j].push_back((index.number().intValue()>>k)&1 ? m_one : m_zero);
    } else if(value.isMatrix()) {
     if(value.rows()!=1 && value.columns()!=1) {CALCULATOR->error(true,"Binary bit operations require vectors, not multi-row matrices.",NULL);return 0;}
     if(value.rows()*value.columns()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t r=0;r<value.rows();++r)for(size_t c=0;c<value.columns();++c)bits[j].push_back(*value.getElement(r+1,c+1));
    } else if(value.isVector()) {
     if(value.size()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t k=0;k<value.size();++k)bits[j].push_back(value[k]);
    } else bits[j].push_back(value);
    if(bits[j].empty() && !labels[j]) {CALCULATOR->error(true,"Binary bit operations require nonempty bit vectors.",NULL);return 0;}
    for(const auto &bit:bits[j])if(!bit.isNumber() || (!bit.number().isZero() && !bit.number().isOne())) {CALCULATOR->error(true,"Binary bit operations require each entry to be 0 or 1.",NULL);return 0;}
   }
   if(op=="qbitvalue") {
    Number value(0);
    for(const auto &bit:bits[0]) {value.multiply(2);if(bit.number().isOne())value.add(1);}
    out=MathStructure(value);return 1;
   }
   if(bits[0].size()!=bits[1].size()) {CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;}
   if(op=="qbitxor") {
    if(labels[0] && labels[1]) {
     int value=0;
     for(size_t k=0;k<bits[0].size();++k)value=2*value+(bits[0][k].number().isOne()!=bits[1][k].number().isOne());
     MathStructure index(value),width(static_cast<int>(bits[0].size()));
     out.set(args[0].function(),&index,&width,NULL);return 1;
    }
    out.clearVector();
    for(size_t k=0;k<bits[0].size();++k)out.addChild(bits[0][k].number().isOne()!=bits[1][k].number().isOne() ? m_one : m_zero);
    return 1;
   }
   bool parity=false;
   for(size_t k=0;k<bits[0].size();++k)if(bits[0][k].number().isOne() && bits[1][k].number().isOne())parity=!parity;
   out=parity ? m_one : m_zero;return 1;
  }
  return 0;
 }
};
}
void registerQuantumBinary(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qgf2mul",2),{"qgf2rref",1},{"qgf2rank",1},{"qgf2inverse",1},{"qgf2nullspace",1},{"qlineargate",1},{"qbits",2},{"qbitdot",2},{"qbitxor",2},{"qbitvalue",1}})calculator.addFunction(new QuantumBinaryFunction(entry.first,entry.second));
}

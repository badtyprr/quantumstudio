// GPL-2.0-or-later; see COPYING.
#include "QuantumBinary.h"
#include "QuantumIndexed.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
bool encodedBits(const MathStructure &value) {
 return value.isFunction() && (value.function()->referenceName()=="qbitlabel" || value.function()->referenceName()=="qbits");
}
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
  if(op=="qcenterdot") {
   bool binary=encodedBits(args[0]) && encodedBits(args[1]);
   out.set(CALCULATOR->getFunction(binary ? "qbitdot" : "qmul"),&args[0],&args[1],NULL);
   return 1;
  }
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
   MathStructure index=a,width=args[1];
   QuantumBitLabelState state=validateQuantumBitLabel(index,width,eo);
   if(state==QuantumBitLabelState::Invalid)return 0;
   // Width validity does not depend on the vector expansion budget. Keep the
   // constructor so later substitutions can expand and still validate it.
   if(state==QuantumBitLabelState::Symbolic || width.number()>1024) {
    if(!index.equals(raw[0]) || !width.equals(raw[1])) {out.set(this,&index,&width,NULL);return 1;}
    return 0;
   }
   out.clearVector();
   for(int k=width.number().intValue();k>0;--k)out.addChild(index.number().bitGet(k) ? m_one : m_zero);
   return 1;
  }
  if(op=="qbitdot" || op=="qbitxor" || op=="qbitvalue") {
   unsigned operands=op=="qbitvalue" ? 1U : 2U;
   bool allLabels=true;
   for(unsigned j=0;j<operands;++j)
    allLabels=allLabels && encodedBits(args[j]);
   if(allLabels) {
    MathStructure indices[2],widths[2];bool pending=false;
    for(unsigned j=0;j<operands;++j) {
     if(args[j].size()!=2) {CALCULATOR->error(true,"Invalid binary-string label.",NULL);return 0;}
     indices[j]=args[j][0];widths[j]=args[j][1];
     QuantumBitLabelState state=validateQuantumBitLabel(indices[j],widths[j],eo);
     if(state==QuantumBitLabelState::Invalid)return 0;
     pending=pending || state==QuantumBitLabelState::Symbolic;
    }
    if(operands==2 && widths[0].isNumber() && widths[1].isNumber() && widths[0].number()!=widths[1].number()) {
     CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;
    }
    if(pending)return 0;
    if(op=="qbitvalue") {out=indices[0];return 1;}
    Number value=indices[0].number();
    if(op=="qbitxor") {
     if(!value.bitXor(indices[1].number()))return 0;
     MathStructure index(value);out.set(args[0].function(),&index,&widths[0],NULL);return 1;
    }
    if(!value.bitAnd(indices[1].number()))return 0;
    bool parity=false;
    for(int bit=1;bit<=value.integerLength();++bit) {
     if(CALCULATOR->aborted())return 0;
     if(value.bitGet(bit))parity=!parity;
    }
    out=parity ? m_one : m_zero;return 1;
   }
   bool symbolicLabel=false;
   Number knownWidths[2]={Number(-1),Number(-1)};
   std::vector<MathStructure> bits[2];
   bool labels[2]={false,false};
   for(size_t j=0;j<(op=="qbitvalue" ? 1U : 2U);++j) {
    const MathStructure &value=args[j];
    labels[j]=encodedBits(value);
    if(labels[j]) {
     if(value.size()!=2) {CALCULATOR->error(true,"Invalid binary-string label.",NULL);return 0;}
     MathStructure index=value[0],width=value[1];
     QuantumBitLabelState state=validateQuantumBitLabel(index,width,eo);
     if(state==QuantumBitLabelState::Invalid)return 0;
     if(width.isNumber())knownWidths[j]=width.number();
     if(state==QuantumBitLabelState::Symbolic || width.number()>1024) {symbolicLabel=true;continue;}
     for(int k=width.number().intValue();k>0;--k)bits[j].push_back(index.number().bitGet(k) ? m_one : m_zero);
    } else if(value.isMatrix()) {
     if(value.rows()!=1 && value.columns()!=1) {CALCULATOR->error(true,"Binary bit operations require vectors, not multi-row matrices.",NULL);return 0;}
     if(value.rows()*value.columns()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t r=0;r<value.rows();++r)for(size_t c=0;c<value.columns();++c)bits[j].push_back(*value.getElement(r+1,c+1));
    } else if(value.isVector()) {
     if(value.size()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t k=0;k<value.size();++k)bits[j].push_back(value[k]);
    } else bits[j].push_back(value);
    for(const auto &bit:bits[j])if(!bit.isNumber() || (!bit.number().isZero() && !bit.number().isOne())) {CALCULATOR->error(true,"Binary bit operations require each entry to be 0 or 1.",NULL);return 0;}
    knownWidths[j]=static_cast<int>(bits[j].size());
   }
   if(op!="qbitvalue" && knownWidths[0]>=0 && knownWidths[1]>=0 && knownWidths[0]!=knownWidths[1]) {CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;}
   // Retain both operands so later substitutions still check their domains.
   if(symbolicLabel)return 0;
   if(op=="qbitvalue") {
    Number value(0);
    for(const auto &bit:bits[0]) {value.multiply(2);if(bit.number().isOne())value.add(1);}
    out=MathStructure(value);return 1;
   }
   if(bits[0].size()!=bits[1].size()) {CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;}
   if(op=="qbitxor") {
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
 for(const auto &entry:{std::pair<const char *,int>("qgf2mul",2),{"qgf2rref",1},{"qgf2rank",1},{"qgf2inverse",1},{"qgf2nullspace",1},{"qlineargate",1},{"qbits",2},{"qbitdot",2},{"qcenterdot",2},{"qbitxor",2},{"qbitvalue",1}})calculator.addFunction(new QuantumBinaryFunction(entry.first,entry.second));
}

// GPL-2.0-or-later; see COPYING.
#include "QuantumBinary.h"
#include <map>
#include "QuantumIndexed.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
bool isQuantumBitLabel(const MathStructure &value) {
 return value.isFunction() && (value.function()->referenceName()=="qbitlabel" || value.function()->referenceName()=="qbits");
}
static bool binaryGraphPair(const MathStructure &pair) {
 return pair.isFunction() && pair.function()->referenceName()=="qtuple" && pair.size()==1 &&
        pair[0].isVector() && pair[0].size()==2 && isQuantumBitLabel(pair[0][0]) && pair[0][0].size()==2;
}
bool pendingQuantumGraphLookup(const MathStructure &graph,const MathStructure &input,const EvaluationOptions &eo) {
 if(!graph.isFunction() || graph.function()->referenceName()!="qset" || graph.size()!=1 || !graph[0].isVector())return false;
 if(!input.isUnknown()) {
  if(!isQuantumBitLabel(input) || input.size()!=2)return false;
  MathStructure index=input[0],width=input[1];
  if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Symbolic)return false;
 }
 for(size_t i=0;i<graph[0].size();++i) {
  const auto &pair=graph[0][i];
  if(!binaryGraphPair(pair))return false;
  const auto &key=pair[0][0];
  MathStructure index=key[0],width=key[1];
  if(validateQuantumBitLabel(index,width,eo)==QuantumBitLabelState::Invalid)return false;
 }
 return true;
}
// Apply the finite relation at one input. Both the width and the bits
// identify the input, so an entry for 01 cannot answer a query for 1.
int applyQuantumBinaryGraph(MathStructure &out,const MathStructure &graph,const MathStructure &input,const EvaluationOptions &eo) {
 if(input.size()!=2 || graph.size()!=1 || !graph[0].isVector())return 0;
 MathStructure index=input[0],width=input[1];
 if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Concrete)return 0;
 const MathStructure *answer=nullptr;
 for(size_t i=0;i<graph[0].size();++i) {
  const MathStructure &pair=graph[0][i];
  if(!binaryGraphPair(pair)) {
   CALCULATOR->error(true,"A binary function graph requires pairs with bit-string inputs.",NULL);return 0;
  }
  const MathStructure &key=pair[0][0];
  MathStructure keyIndex=key[0],keyWidth=key[1];
  if(validateQuantumBitLabel(keyIndex,keyWidth,eo)!=QuantumBitLabelState::Concrete)return 0;
  if(!index.equals(keyIndex) || !width.equals(keyWidth))continue;
  if(answer && !answer->equals(pair[0][1])) {
   CALCULATOR->error(true,"The function graph has conflicting outputs for this input.",NULL);return 0;
  }
  answer=&pair[0][1];
 }
 if(!answer) {CALCULATOR->error(true,"The function graph has no output for this bit string.",NULL);return 0;}
 out=*answer;return 1;
}
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
 QuantumBinaryFunction(const char *name,int count):MathFunction(name,count),op(name) {if(op=="qcomparisonliteral")setArgumentDefinition(2,new TextArgument());}
 ExpressionItem *copy() const {return new QuantumBinaryFunction(*this);}
 bool representsScalar(const MathStructure &value) const {
  return op=="qcontrolbit" || MathFunction::representsScalar(value);
 }
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qcontrolbit") {
   if(a.isUnknown() || (a.containsUnknowns() && (a.representsScalar() ||
      (a.isFunction() && a.function()->referenceName()=="qgraphapply"))))return 0;
   if(isQuantumBitLabel(a) && a.size()==2) {
    MathStructure value=a[0],width=a[1];
    const auto state=validateQuantumBitLabel(value,width,eo);
    if(state==QuantumBitLabelState::Invalid)return 0;
    if(width.isNumber() && !width.isOne()) {CALCULATOR->error(true,"A qubit control requires a one-bit word.",NULL);return 0;}
    if(state!=QuantumBitLabelState::Concrete)return 0;
    out=value;return 1;
   }
   if(a.isNumber() && !a.isApproximate() && (a.isZero() || a.isOne())) {out=a;return 1;}
   CALCULATOR->error(true,"A qubit control requires zero, one or a one-bit word.",NULL);return 0;
  }
  if(op=="qallbitdot") {
   MathStructure width=args[1],zero(0);
   if(validateQuantumBitLabel(zero,width,eo)==QuantumBitLabelState::Invalid)return 0;
   const MathStructure &target=args[2];
   if(target.isApproximate() || (!target.isZero() && !target.isOne())) {
    CALCULATOR->error(true,"A universal binary dot comparison requires a target bit.",NULL);return 0;
   }
   MathStructure word=a;
   if(a.isVector()) {
    word.set(CALCULATOR->getFunction("qbitword"),&a,NULL);word.eval(eo);
    if(!isQuantumBitLabel(word))return 0;
   }
   MathStructure index=word;
   if(isQuantumBitLabel(word)) {
    index=word[0];MathStructure labelWidth=word[1];
    if(validateQuantumBitLabel(index,labelWidth,eo)==QuantumBitLabelState::Invalid)return 0;
    if(labelWidth.isNumber() && width.isNumber() && !labelWidth.equals(width)) {
     CALCULATOR->error(true,"The word and the quantified binary strings must have the same width.",NULL);return 0;
    }
    if(!labelWidth.isNumber() || !width.isNumber()) {
     validateQuantumBitLabel(index,width,eo);return 0;
    }
   }
   if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Concrete)return 0;
   // The zero input gives parity zero. Every nonzero word has a set bit
   // whose corresponding unit vector gives parity one.
   out=index.isZero() && target.isZero() ? 1 : 0;return 1;
  }
  if(op=="qbinarytail") {
   if(!a.isSymbolic() || !args[1].isInteger() || !args[1].number().isPositive())
    CALCULATOR->error(true,"A binary tail requires a digit family and a positive starting index.",NULL);
   return 0;
  }
  if(op=="qbinaryfraction") {
   if(!a.isVector() || a.isMatrix() || !a.size() || a.size()>1024 ||
      !args[1].isInteger() || args[1].number()<0 || args[1].number()>Number(a.size())) {
    CALCULATOR->error(true,"A binary fraction requires a word of up to 1024 bits and a radix position within it.",NULL);return 0;
   }
   MathStructure word(CALCULATOR->getFunction("qbitword"),&a,NULL);word.eval(eo);
   const MathStructure &tail=args[2];
   if(tail.isUndefined() || tail.isVector() || tail.containsType(STRUCT_UNIT,true,true,true) || (tail.isNumber() && (!tail.number().isReal() || tail.number()<0 || tail.number()>1))) {
    CALCULATOR->error(true,"The remaining binary fraction must be between zero and one.",NULL);return 0;
   }
   if(!isQuantumBitLabel(word) || !tail.representsReal())return 0;
   MathStructure lower=tail,upper=tail;
   lower.transform(COMPARISON_EQUALS_GREATER,m_zero);upper.transform(COMPARISON_EQUALS_LESS,m_one);
   lower.eval(eo);upper.eval(eo);
   if(lower.isZero() || upper.isZero()) {CALCULATOR->error(true,"The remaining binary fraction must be between zero and one.",NULL);return 0;}
   if(!lower.isOne() || !upper.isOne())return 0;
   out=word[0];out+=tail;MathStructure scale(2);scale.raise(args[1]);out/=scale;return 1;
  }
  if(op=="qcomparisonzero") {
   if(isQuantumBitLabel(a)) {
    MathStructure index(0),width=args[1];
    if(validateQuantumBitLabel(index,width,eo)==QuantumBitLabelState::Invalid)return 0;
    out.set(CALCULATOR->getFunction("qbitlabel"),&index,&width,NULL);return 1;
   }
   if(!a.isVector() && a.containsUnknowns())return 0;
   out=m_zero;out.raise(args[1]);return 1;
  }
  if(op=="qcomparisonliteral") {
   if(!raw[1].isSymbolic())return 0;
   const std::string &digits=raw[1].symbol();
   if(digits.size()<2 || digits.size()>1024 || digits.front()!='0' || digits.find_first_not_of("01")!=std::string::npos) {
    CALCULATOR->error(true,"Expected a zero-padded binary digit string.",NULL);return 0;
   }
   if(a.isUnknown() || a.isSymbolic())return 0;
   const bool word=isQuantumBitLabel(a);
   if(!word && !a.isNumber())return 0;
   ParseOptions options;options.base=word ? 2 : 10;
   MathStructure number(Number(digits,options));
   if(word) {
    MathStructure width(static_cast<int>(digits.size()));
    out.set(CALCULATOR->getFunction("qbitlabel"),&number,&width,NULL);
   } else out=number;
   return 1;
  }
  if(op=="qinversefunction") {
   if(a.isUnknown())return 0;
   if(!a.isFunction() || a.function()->referenceName()!="qset") {
    if(a.containsUnknowns() && !a.isVector())return 0;
    out=a;out.raise(-1);return 1;
   }
   if(a.size()!=1 || !a[0].isVector())return 0;
   // Reversing a finite function is valid only if both directions are
   // single-valued. The width is part of each binary word's identity.
   using Word=std::pair<Number,Number>;
   std::map<Word,Word> maps[2];
   MathStructure reversed=a;
   for(size_t i=0;i<a[0].size();++i) {
    if(CALCULATOR->aborted())return 0;
    const MathStructure &pair=a[0][i];
    if(!pair.isFunction() || pair.function()->referenceName()!="qtuple" ||
       pair.size()!=1 || !pair[0].isVector() || pair[0].size()!=2) {
     CALCULATOR->error(true,"An inverse function requires a graph of ordered pairs.",NULL);return 0;
    }
    Word keys[2];
    for(unsigned j=0;j<2;++j) {
     const MathStructure &entry=pair[0][j];
     if(!isQuantumBitLabel(entry) || entry.size()!=2) {
      if(!entry.containsUnknowns())CALCULATOR->error(true,"An inverse binary function requires bit-string inputs and outputs.",NULL);
      return 0;
     }
     MathStructure index=entry[0],width=entry[1];
     if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Concrete)return 0;
     keys[j]=Word(width.number(),index.number());
    }
    for(unsigned j=0;j<2;++j) {
     auto inserted=maps[j].emplace(keys[j],keys[1-j]);
     if(!inserted.second && inserted.first->second!=keys[1-j]) {
      CALCULATOR->error(true,"An inverse function requires a one-to-one function graph.",NULL);return 0;
     }
    }
    reversed[0][i][0][0]=pair[0][1];reversed[0][i][0][1]=pair[0][0];
   }
   out=reversed;return 1;
  }
  if(op=="qnamedapplication") {
   if(a.isUnknown() || (a.isFunction() && a.function()->referenceName()=="qinversefunction"))return 0;
   bool graph=a.isFunction() && a.function()->referenceName()=="qset";
   out.set(CALCULATOR->getFunction(graph ? "qgraphapply" : "qmul"),&a,&args[1],NULL);return 1;
  }
  if(op=="qgraphapply") {
   if(!isQuantumBitLabel(args[1])) {
    if(!args[1].containsUnknowns())CALCULATOR->error(true,"A binary function graph requires a bit-string input.",NULL);
    return 0;
   }
   if(!a.isFunction() || a.function()->referenceName()!="qset")return 0;
   return applyQuantumBinaryGraph(out,a,args[1],eo);
  }
  if(op=="qcenterdot") {
   bool binary=isQuantumBitLabel(args[0]) && isQuantumBitLabel(args[1]);
   auto possibleWord=[](const MathStructure &v) {
    if(isQuantumBitLabel(v) || v.isUnknown() || v.isSymbolic())return true;
    if(!v.isFunction())return false;
    const auto &name=v.function()->referenceName();
    return name=="qoplus" || name=="qbitxor" || name=="qgraphapply" || name=="qregisterword";
   };
   if(!binary && possibleWord(args[0]) && possibleWord(args[1]))return 0;
   out.set(CALCULATOR->getFunction(binary ? "qbitdot" : "qmul"),&args[0],&args[1],NULL);
   return 1;
  }
  if(op=="qgf2mul") {
   std::vector<std::vector<unsigned char>> left,right;
   // A named matrix or vector can be supplied after a formula is copied.
   // Validate each concrete operand even while the other is still unknown.
   bool pendingLeft=a.isUnknown() || a.isSymbolic();
   bool pendingRight=args[1].isUnknown() || args[1].isSymbolic();
   if((!pendingLeft && !binaryMatrix(a,left)) || (!pendingRight && !binaryMatrix(args[1],right)))return 0;
   if(pendingLeft || pendingRight)return 0;
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
  if(op=="qbitdot" || op=="qbitxor" || op=="qbitvalue" || op=="qbitword") {
   unsigned operands=(op=="qbitvalue" || op=="qbitword") ? 1U : 2U;
   if(op=="qbitword" && (!a.isVector() || a.isMatrix())) {
    CALCULATOR->error(true,"A binary word requires a flat vector of bits.",NULL);return 0;
   }
   bool allLabels=true;
   for(unsigned j=0;j<operands;++j)
    allLabels=allLabels && isQuantumBitLabel(args[j]);
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
   for(size_t j=0;j<operands;++j) {
    const MathStructure &value=args[j];
    if(value.isFunction() && value.function()->referenceName()=="qbitword") {symbolicLabel=true;continue;}
    labels[j]=isQuantumBitLabel(value);
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
    for(const auto &bit:bits[j]) {
     if(op=="qbitword" && (bit.isUnknown() || bit.isSymbolic() ||
        (bit.isFunction() && bit.function()->referenceName()=="qcontrolbit" && bit.containsUnknowns()))) {symbolicLabel=true;continue;}
     if(!bit.isNumber() || (!bit.number().isZero() && !bit.number().isOne())) {CALCULATOR->error(true,"Binary bit operations require each entry to be 0 or 1.",NULL);return 0;}
    }
    knownWidths[j]=static_cast<int>(bits[j].size());
   }
   if(operands==2 && knownWidths[0]>=0 && knownWidths[1]>=0 && knownWidths[0]!=knownWidths[1]) {CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;}
   // Retain both operands so later substitutions still check their domains.
   if(symbolicLabel)return 0;
   if(operands==1) {
    Number value(0);
    for(const auto &bit:bits[0]) {value.multiply(2);if(bit.number().isOne())value.add(1);}
    if(op=="qbitword") {
     MathStructure index(value),width(knownWidths[0]);
     out.set(CALCULATOR->getFunction("qbitlabel"),&index,&width,NULL);return 1;
    }
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
 calculator.addFunction(new QuantumBinaryFunction("qallbitdot",3));
 calculator.addFunction(new QuantumBinaryFunction("qbinarytail",2));
 calculator.addFunction(new QuantumBinaryFunction("qbinaryfraction",3));
 calculator.addFunction(new QuantumBinaryFunction("qbitword",1));
 calculator.addFunction(new QuantumBinaryFunction("qcontrolbit",1));
 for(const auto &entry:{std::pair<const char *,int>("qgf2mul",2),{"qgf2rref",1},{"qgf2rank",1},{"qgf2inverse",1},{"qgf2nullspace",1},{"qlineargate",1},{"qbits",2},{"qbitdot",2},{"qcenterdot",2},{"qcomparisonliteral",2},{"qcomparisonzero",2},{"qnamedapplication",2},{"qinversefunction",1},{"qgraphapply",2},{"qbitxor",2},{"qbitvalue",1}})calculator.addFunction(new QuantumBinaryFunction(entry.first,entry.second));
}

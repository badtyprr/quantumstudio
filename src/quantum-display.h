// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_DISPLAY_H
#define QUANTUM_DISPLAY_H
#include "MathStructure.h"
#include "QuantumNotation.h"
#include "Function.h"
#include "Variable.h"
#include <set>
#include <string>
#include <vector>
#include <utility>
#include <cctype>

// Presentation only. Never feed this text back into evaluation in place of the
// canonical clipboard expression. Unknown forms retain the library's printer.
namespace QuantumDisplay {
enum Kind { Other, Ket, Bra, BraProduct };
struct Fragment {
 std::string text,label;int precedence;Kind kind;
 Fragment(std::string value,int level=100,Kind shape=Other,std::string name=""):
  text(value),label(name),precedence(level),kind(shape) {}
};
class Printer {
 const PrintOptions &options;
 unsigned nodes=0, collected=0;
 bool lostBinding=false;
 std::set<std::string> names;
 std::vector<std::pair<MathStructure,std::string>> bindings;
 std::vector<std::pair<std::string,std::string>> familyBindings;
 std::string familyName(const std::string &name,bool metadata=false) const {
  for(auto i=familyBindings.rbegin();i!=familyBindings.rend();++i) {
   if(metadata) {if(name==i->first)return i->second;continue;}
   if(name.compare(0,i->first.size(),i->first)!=0)continue;
   std::string suffix=name.substr(i->first.size());
   if(!suffix.empty() && !(suffix.size()>1 && suffix.front()=='0') && suffix.find_first_not_of("0123456789")==std::string::npos)return i->second+suffix;
  }
  return name;
 }
 bool containsFamilyBinding(const MathStructure &value,unsigned depth=0) const {
  if(depth>128)return true;
  if(value.isSymbolic() && familyName(value.symbol())!=value.symbol())return true;
  if(value.isFunction()) {
   const std::string &name=value.function()->referenceName();
   if((name=="qregisterfamily" || name=="qindexedlabel" || name=="qscalarproductsum") && value.size()>0 && value[0].isSymbolic() && familyName(value[0].symbol(),true)!=value[0].symbol())return true;
   if(name=="qscalarproductsum" && value.size()>1 && value[1].isSymbolic() && familyName(value[1].symbol(),true)!=value[1].symbol())return true;
  }
  for(size_t k=0;k<value.size();++k)if(containsFamilyBinding(value[k],depth+1))return true;
  return false;
 }
 std::string historyText(const MathStructure &history,unsigned depth) {
  if(!history.size())return "";
  std::string text=" [body substitutions, in order: ";
  for(size_t k=0;k<history.size();k+=2) {
   if(k)text+="; then ";
   text+=render(history[k],depth+1).text+" ← "+render(history[k+1],depth+1).text;
  }
  return text+"]";
 }
 bool collect(const MathStructure &value,unsigned depth=0) {
  if(depth>128 || ++collected>2048)return false;
  if(value.isSymbolic() || value.isVariable()) {
   const std::string name=value.isSymbolic() ? value.symbol() : value.variable()->referenceName();names.insert(name);
   // A fixed subscript remains free even inside a generated indexed label.
   // Reserve its components so choosing a displayed binder cannot capture it.
   size_t start=0;
   for(size_t end=0;end<=name.size();++end)if(end==name.size() || name[end]=='_') {
    if(end>start)names.insert(name.substr(start,end-start));
    start=end+1;
   }
  }
  for(size_t i=0;i<value.size();++i)if(!collect(value[i],depth+1))return false;
  return true;
 }
 std::string fresh() {
  for(const char *name:{"k","j","l","n","t"})if(names.insert(name).second)return name;
  for(unsigned i=1;;++i){std::string name="k"+std::to_string(i);if(names.insert(name).second)return name;}
 }
 static std::string grouped(const Fragment &value,int precedence) {
  return value.precedence<precedence ? "("+value.text+")" : value.text;
 }
 static bool safeLabel(const std::string &value) {
  if(value.empty())return false;
  for(unsigned char c:value)if(c<128 && !std::isalnum(c) && c!='_' && c!=' ')return false;
  for(const char *special:{"⟨","⟩","↑","↓","±","−","∑"})if(value.find(special)!=std::string::npos)return false;
  return true;
 }
 Fragment fallback(const MathStructure &value) {
  for(const auto &binding:bindings)if(value.contains(binding.first))lostBinding=true;
  if(!familyBindings.empty() && containsFamilyBinding(value))lostBinding=true;
  int precedence=value.isComparison() ? 5 : value.isAddition() ? 20 : value.isMultiplication() || value.isInverse() || value.isDivision() ? 40 : value.isNegate() ? 70 : value.isPower() ? 80 : 100;
  if(value.isNumber() && value.number().isNegative())precedence=70;
  if(value.isNumber() && value.number().isComplex())precedence=20;
  return Fragment(value.print(options),precedence);
 }
 Fragment render(const MathStructure &value,unsigned depth) {
  if(depth>128 || ++nodes>2048)return fallback(value);
  // A space between columns also denotes multiplication in quantum input.
  // Use explicit separators so a displayed matrix keeps its shape on paste.
  if(value.isMatrix() && value.columns()>1) {
   std::string text="[";
   for(size_t row=1;row<=value.rows();++row) {
    if(row>1)text+="; ";
    for(size_t col=1;col<=value.columns();++col) {
     if(col>1)text+=", ";
     text+=render(*value.getElement(row,col),depth+1).text;
    }
   }
   return Fragment(text+"]");
  }
  if(value.isVector() && !value.isMatrix() && value.size()>0) {
   bool labels=true;
   for(size_t i=0;i<value.size();++i)labels=labels && value[i].isFunction() && (value[i].function()->referenceName()=="qbitlabel" || value[i].function()->referenceName()=="qtuple");
   if(labels) {
    std::string text="{";
    for(size_t i=0;i<value.size();++i) {if(i)text+=", ";text+=render(value[i],depth+1).text;}
    return Fragment(text+"}");
   }
  }
  for(auto i=bindings.rbegin();i!=bindings.rend();++i)if(value.equals(i->first))return Fragment(i->second);
  if(value.isSymbolic() && familyName(value.symbol())!=value.symbol())return Fragment(familyName(value.symbol()));
  if(value.isVariable() && !value.variable()->isKnown())return Fragment(value.variable()->referenceName());
  // Bare c denotes the speed of light on re-entry.
  if(value.isSymbolic() && value.symbol()=="c")return Fragment("'c'");
  if(value.isSymbolic() && value.symbol().size()==1 && std::isalpha(static_cast<unsigned char>(value.symbol()[0])) && value.symbol()!="i" && value.symbol()!="e")return Fragment(value.symbol());
  if(value.isLogicalAnd() || value.isLogicalOr()) {
   const int level=value.isLogicalAnd() ? 3 : 2;
   std::string text;
   for(size_t k=0;k<value.size();++k) {
    if(k)text+=value.isLogicalAnd() ? " and " : " or ";
    text+=grouped(render(value[k],depth+1),level);
   }
   return Fragment(text,level);
  }
  // Evaluation can turn scalar quantum operations into ordinary arithmetic.
  // Recurse through that arithmetic without changing its order or clipboard AST.
  if(value.isAddition() || value.isMultiplication() || value.isPower() || value.isComparison() || value.isNegate() || value.isInverse() || value.isDivision()) {
   std::vector<Fragment> children;bool changed=false;
   for(size_t i=0;i<value.size();++i) {
    children.push_back(render(value[i],depth+1));
    changed=changed || children.back().text!=value[i].print(options);
   }
   if(!changed)return fallback(value);
   if(value.isNegate() && children.size()==1)return Fragment("−"+grouped(children[0],70),70);
   if(value.isDivision() && children.size()==2)return Fragment(grouped(children[0],40)+" / "+grouped(children[1],41),40);
   if(value.isInverse() && children.size()==1)return Fragment("1 / "+grouped(children[0],41),40);
   if(value.isAddition() || value.isMultiplication()) {
    int level=value.isAddition() ? 20 : 40;std::string text;
    for(size_t i=0;i<children.size();++i) {
     const auto &child=children[i];
     if(i && value.isAddition() && value[i].isNegate() && child.text.compare(0,3,"−")==0) {
      text+=" − "+child.text.substr(3);
     } else {
      if(i)text+=value.isAddition() ? " + " : " · ";
      text+=grouped(child,level);
     }
    }
    return Fragment(text,level);
   }
   if(value.isPower() && children.size()==2)
    return Fragment(grouped(children[0],81)+"^"+grouped(children[1],81),80);
   if(value.isComparison() && children.size()==2) {
    const char *op=nullptr;
    switch(value.comparisonType()) {
     case COMPARISON_EQUALS:op=" = ";break;
     case COMPARISON_NOT_EQUALS:op=" ≠ ";break;
     case COMPARISON_LESS:op=" < ";break;
     case COMPARISON_GREATER:op=" > ";break;
     case COMPARISON_EQUALS_LESS:op=" ≤ ";break;
     case COMPARISON_EQUALS_GREATER:op=" ≥ ";break;
    }
    if(op)return Fragment(grouped(children[0],6)+op+grouped(children[1],6),5);
   }
  }
  if(!value.isFunction())return fallback(value);
  const std::string name=value.function()->referenceName();
  // Ordinary Copy can retain a matrix constructor inside a deferred product.
  // Display the same literal grid without evaluating any of its entries.
  if((name=="matrix" || name=="qmatrix") && value.size()==3 && value[0].isNumber() && value[1].isNumber() &&
     value[0].number().isInteger() && value[1].number().isInteger() &&
     value[0].number()>0 && value[0].number()<=2048 && value[1].number()>0 && value[1].number()<=2048 &&
     (value[2].isVector() || (value[2].isFunction() &&
      (value[2].function()->referenceName()=="horzcat" || value[2].function()->referenceName()=="vector")))) {
   size_t rows=value[0].number().intValue(),columns=value[1].number().intValue();
   bool flat=true;
   for(size_t i=0;i<value[2].size();++i) {
    const MathStructure &entry=value[2][i];
    if(entry.isVector() || (entry.isFunction() &&
       (entry.function()->referenceName()=="horzcat" || entry.function()->referenceName()=="vector")))flat=false;
   }
   if(flat && rows<=2048/columns && value[2].size()==rows*columns) {
    MathStructure literal;literal.clearMatrix();literal.resizeMatrix(rows,columns,MathStructure(0));
    std::string text="[";bool changed=columns>1;
    for(size_t row=0;row<rows;++row) {
     if(row)text+="; ";
     for(size_t column=0;column<columns;++column) {
      const MathStructure &entry=value[2][row*columns+column];
      literal.setElement(entry,row+1,column+1);
      Fragment rendered=render(entry,depth+1);changed=changed || rendered.text!=entry.print(options);
      if(column)text+=", ";text+=rendered.text;
     }
    }
    return changed ? Fragment(text+"]") : fallback(literal);
   }
  }
  if(name=="qfloorlog2" && value.size()==1)return Fragment("floor(log2("+render(value[0],depth+1).text+"))");
  if(name=="qbitlength" && value.size()==1)return Fragment("bitlength("+render(value[0],depth+1).text+")");
  if((name=="qresidues" || name=="qunitsmod") && value.size()==1)
   return Fragment(std::string(name=="qresidues" ? "residues(" : "invertible_residues(")+render(value[0],depth+1).text+")");
  if(name=="qrecoverphase" && value.size()==2)
   return Fragment("recoverphase("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qintegergcd" && value.size()==2)
   return Fragment("integergcd("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qresidue" && value.size()==2)
   return Fragment(grouped(render(value[0],depth+1),40)+" pmod ("+render(value[1],depth+1).text+")",40);
  if(name=="qcostparam" && value.size()==1 && value[0].isSymbolic())return Fragment(value[0].symbol());
  if(name=="qinversefunction" && value.size()==1 && value[0].isSymbolic())
   return Fragment(value[0].symbol()+"^(-1)",80);
  if(name=="qnamedapplication" && value.size()==2 && value[0].isFunction() &&
     value[0].function()->referenceName()=="qinversefunction" && value[0].size()==1 && value[0][0].isSymbolic())
   return Fragment(render(value[0],depth+1).text+"("+render(value[1],depth+1).text+")");
  if(name=="qnamedapplication" && value.size()==2 && value[0].isSymbolic()) {
   const std::string &head=value[0].symbol();
   const std::string arg=render(value[1],depth+1).text;
   if((head=="f" || head=="g" || head=="h") && arg.size()==1 && std::isalpha((unsigned char)arg[0]))
    return Fragment(head+"("+arg+")");
  }
  if(name=="qprobabilitycall" && value.size()==2)
   return Fragment("p("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qbigorder" && value.size()==1)return Fragment("O("+render(value[0],depth+1).text+")");
  if(name=="qcostcall" && value.size()==2 && value[0].isSymbolic()) {
   const std::string &function=value[0].symbol();
   std::vector<std::string> arguments;
   if(value[1].isVector()) {
    for(size_t i=0;i<value[1].size();++i)arguments.push_back(render(value[1][i],depth+1).text);
   } else arguments.push_back(render(value[1],depth+1).text);
   std::string text=function+"(";
   for(size_t i=0;i<arguments.size();++i) {if(i)text+=", ";text+=arguments[i];}
   text+=")";
   return Fragment(function=="size" || quantumSizeApplication(function,arguments) ? text : "cost("+text+")");
  }
  if(name=="qindexedketset" && value.size()==4 && value[0].isSymbolic() && safeLabel(value[0].symbol()) &&
     value[3].isVector() && value[3].size()%2==0) {
   const std::string &prefix=value[0].symbol();
   Fragment upper=render(value[2],depth+1);
   std::string index=upper.precedence<100 ? "{"+upper.text+"}" : upper.text;
   std::string text="\\{|"+prefix+render(value[1],depth+1).text+"⟩,\\ldots,|"+prefix+index+"⟩\\}";
   for(size_t k=0;k<value[3].size();k+=2)
    text="replace("+text+","+prefix+render(value[3][k],depth+1).text+","+render(value[3][k+1],depth+1).text+")";
   return Fragment(text);
  }
  if(name=="qunitcircle" && !value.size())return Fragment("\\mathbb{T}");
  if(name=="qcomplexplane" && !value.size())return Fragment("\\mathbb{C}");
  if(name=="qset" && value.size()==1) {
   // Formatting collapses a singleton vector; the enclosing descriptor keeps
   // its collection meaning even in this presentation-only tree.
   auto displayMember=[&](const MathStructure &member) {
    if(member.isFunction() && member.function()->referenceName()=="qoutcome" && member.size()==1 &&
       member[0].isSymbolic() && member[0].symbol().find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")==std::string::npos)
     return "\\text{"+member[0].symbol()+"}";
    return render(member,depth+1).text;
   };
   if(!value[0].isVector())return Fragment("\\{"+displayMember(value[0])+"\\}");
   std::string text="\\{";
   for(size_t k=0;k<value[0].size();++k) {if(k)text+=", ";text+=displayMember(value[0][k]);}
   return Fragment(text+"\\}");
  }
  if(name=="qstateaction" && value.size()==2)
   return Fragment(render(value[0],depth+1).text+" ↦ "+render(value[1],depth+1).text,2);
  if(name=="qdecimalmatch" && value.size()==4 && value[1].isNumber() &&
     value[2].isInteger() && value[3].isInteger()) {
   const Number &target=value[1].number();
   std::string text;bool valid=!target.isApproximate();
   for(unsigned k=0;k<2 && valid;++k) {
    Number part=k ? target.imaginaryPart() : target.realPart();
    const Number &places=value[k+2].number();
    if(k && places==-1 && part.isZero())break;
    if(places<0 || places>100) {valid=false;break;}
    Number scaled(10);scaled.raise(places);scaled.multiply(part);
    if(!scaled.isInteger()) {valid=false;break;}
    if(k) {text+=part.isNegative() ? " - " : " + ";part.abs();}
    PrintOptions decimal=options;decimal.base=10;decimal.min_exp=EXP_NONE;
    decimal.number_fraction_format=FRACTION_DECIMAL;
    decimal.use_min_decimals=decimal.use_max_decimals=true;
    decimal.min_decimals=decimal.max_decimals=places.intValue();
    text+=part.print(decimal);if(k)text+=" i";
   }
   if(valid)return Fragment(grouped(render(value[0],depth+1),6)+" ≈ "+text,5);
  }
  if(name=="qcompare" && value.size()==3 && value[2].isNumber() && value[2].number().isInteger() && value[2].number()>=0 && value[2].number()<=5) {
   const char *operators[]={" < "," > "," ≤ "," ≥ "," = "," ≠ "};
   auto side=[&](unsigned index) {
    const MathStructure &term=value[index];
    if(term.isFunction() && term.size()==2) {
     const auto &op=term.function()->referenceName();
     if(op=="qcomparisonzero" && term[0].equals(value[1-index]))return "0^"+grouped(render(term[1],depth+1),81);
     if(op=="qcomparisonliteral" && term[0].equals(value[1-index]) && term[1].isSymbolic())return term[1].symbol();
     if(op=="qnamedapplication" && term[0].isSymbolic() && safeLabel(term[0].symbol()))
      return term[0].symbol()+"("+render(term[1],depth+1).text+")";
    }
    return grouped(render(term,depth+1),6);
   };
   return Fragment(side(0)+operators[value[2].number().intValue()]+side(1),5);
  }
  if(((name=="qindexedcolumn" || name=="qonebasedcolumn" || name=="qdescendingcolumn") && value.size()==3) || ((name=="qindexedmatrix" || name=="qsamplebitmatrix") && value.size()==5)) {
   const bool samples=name=="qsamplebitmatrix";
   const bool matrix=samples || name=="qindexedmatrix";
   std::string prefix=value[0].isSymbolic() ? value[0].symbol() : "";
   bool safe=prefix.size()>1 && prefix.back()==(samples ? '^' : '_');
   for(size_t i=0;i+1<prefix.size();++i)if((unsigned char)prefix[i]<128 && !std::isalpha((unsigned char)prefix[i]))safe=false;
   std::string endpoints[2];int minima[2]={0,0};
   // Keep a bounded, re-enterable surface form. Complex endpoints or large
   // explicit prefixes retain the library's canonical presentation.
   for(int axis=0;axis<(matrix ? 2 : 1);++axis) {
    const MathStructure &minimum=value[(matrix ? 3 : 2)+axis];
    if(!minimum.isNumber() || !minimum.number().isInteger() || minimum.number()<0 || minimum.number()>(matrix ? 4 : 16))safe=false;
    else minima[axis]=minimum.number().intValue();
    endpoints[axis]=render(value[1+axis],depth+1).text;
    if(endpoints[axis].empty())safe=false;
    for(unsigned char c:endpoints[axis])if(c<128 && !std::isalnum(c) && !std::isspace(c) && c!='+' && c!='-' && c!='*' && c!='/')safe=false;
   }
   if(safe && samples && minima[0]>=1 && minima[1]==0) {
    auto row=[&](const std::string &sample) {
     std::string label=prefix+"("+sample+")_";
     return label+"("+endpoints[1]+"), ⋯, "+label+"0";
    };
    std::string text="[";
    for(int index=1;index<=minima[0];++index)text+=row(std::to_string(index))+"; ";
    return Fragment(text+"⋮, ⋱, ⋮; "+row(endpoints[0])+"]");
   }
   if(safe && !matrix) {
    std::string text="[";
    if(name=="qdescendingcolumn") {
     text+=prefix+"("+endpoints[0]+"); ⋮";
     for(int row=minima[0];row>=0;--row)text+="; "+prefix+std::to_string(row);
     return Fragment(text+"]");
    }
    for(int row=name=="qonebasedcolumn" ? 1 : 0;row<=minima[0];++row)text+=prefix+std::to_string(row)+"; ";
    return Fragment(text+"⋮; "+prefix+"("+endpoints[0]+")]");
   }
   if(safe && !samples) {
    std::string text="[";int height=minima[0]+3,width=minima[1]+3;
    for(int row=0;row<height;++row) {
     if(row)text+=";\n ";
     for(int col=0;col<width;++col) {
      if(col)text+=", ";
      if(row==height-2)text+=col==width-2 ? "⋱" : "⋮";
      else if(col==width-2)text+="⋯";
      else text+=prefix+"("+(row==height-1 ? endpoints[0] : std::to_string(row))+","+(col==width-1 ? endpoints[1] : std::to_string(col))+")";
     }
    }
    return Fragment(text+"]");
   }
  }
  if(name=="qindexedcoefficient" && value.size()==3 && value[0].isSymbolic()) {
   std::string prefix=value[0].symbol();bool safe=prefix.size()>1 && prefix.back()=='_' && ((unsigned char)prefix[0]>=128 || std::isalpha((unsigned char)prefix[0]));
   for(size_t i=0;i+1<prefix.size();++i)if((unsigned char)prefix[i]<128 && !std::isalnum((unsigned char)prefix[i]) && prefix[i]!='_')safe=false;
   if(safe) {
    auto index=[&](const MathStructure &v){return render(v,depth+1).text;};
    return Fragment(prefix+"("+index(value[1])+","+index(value[2])+")");
   }
  }
  if(name=="qindexedlabel" && value.size()==3) {
   auto part=[&](const MathStructure &v){return v.isSymbolic() ? v.symbol() : render(v,depth+1).text;};
   Fragment index=render(value[1],depth+1);
   return Fragment(familyName(part(value[0]),true)+grouped(index,100)+part(value[2]));
  }
  if(name=="qorthoket" && value.size()==3 && value[0].isSymbolic() && value[1].isSymbolic())
   return Fragment("|"+value[0].symbol()+"⟩ (basis "+value[1].symbol()+")");
  if(name=="qorthofamilyket" && value.size()==4 && value[1].isSymbolic() && value[2].isSymbolic())
   return Fragment("|"+value[2].symbol()+"("+render(value[0],depth+1).text+")⟩ (basis "+value[1].symbol()+", dimension "+render(value[3],depth+1).text+")");
  if(name=="qorthoidentity" && value.size()==1)
   return Fragment("I_("+render(value[0],depth+1).text+") (positive integer dimension)");
  if(name=="qorthodelta" && value.size()==3) {
   std::string a=render(value[0],depth+1).text,b=render(value[1],depth+1).text,n=render(value[2],depth+1).text;
   return Fragment((value[0].equals(value[1]) ? "1" : "δ_("+a+", "+b+")")+" (integer indices 0 ≤ "+a+", "+b+" < "+n+")");
  }
  if(name=="qbitlabel" && value.size()==2)
   return Fragment("bitstring("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qbits" && value.size()==2)
   return Fragment("bits("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if((name=="qspectralsum" && value.size()==2) || (name=="qspectralaction" && value.size()==3)) {
   const auto &a=value[0],&b=value[1];
   auto family=[](const MathStructure &v) {
    return v.isFunction() && v.function()->referenceName()=="qindexedentries" && v.size()==4 &&
     v[0].isSymbolic() && v[0].symbol().size()>1 && v[0].symbol().back()=='_' && v[3].size()==0;
   };
   if(family(a) && family(b) && a[1].equals(b[1]) && a[2].equals(b[2])) {
    std::string index="k",probe;
    if(value.size()==3) {
     const auto &ket=value[2];
     if(!ket.isFunction() || ket.size()!=1 || !ket[0].isSymbolic() || !safeLabel(ket[0].symbol()) ||
        (ket.function()->referenceName()!="qnamedket" && ket.function()->referenceName()!="qketstate"))return fallback(value);
     probe=ket[0].symbol();
     if(probe.size()>=2 && probe.substr(probe.size()-2)=="_k")index="l";
     probe+="\\rangle";
    }
    std::string state=b[0].symbol()+index;
    return Fragment("\\sum_{"+index+"="+render(a[1],depth+1).text+"}^{"+render(a[2],depth+1).text+"} "+
                    a[0].symbol()+index+" \\vert "+state+"\\rangle\\langle "+state+"\\vert"+(probe.empty() ? "" : " "+probe),20);
   }
  }
  if(name=="qindexedlist" && value.size()==4 && value[0].isSymbolic() && value[1].isInteger() &&
     safeLabel(value[0].symbol()) && value[3].size()%2==0 &&
     (value[3].isVector() || (value[3].isFunction() && value[3].function()->referenceName()=="vector"))) {
   std::string last=render(value[2],depth+1).text;
   if(last.size()==1 && std::isalpha((unsigned char)last[0])) {
    const std::string &prefix=value[0].symbol();
    std::string text="("+prefix+render(value[1],depth+1).text+", …, "+prefix+last+")";
    for(size_t k=0;k<value[3].size();k+=2)
     text="replace("+text+","+prefix+render(value[3][k],depth+1).text+","+render(value[3][k+1],depth+1).text+")";
    return Fragment(text);
   }
  }
  if(((name=="qhalfopen" && value.size()==3) ||
      (name=="qrealinterval" && value.size()==4 && (value[3].isOne() || value[3].isZero()))) &&
     (value[2].isOne() || value[2].isZero())) {
   bool left=value[2].isOne(),right=value.size()==4 ? value[3].isOne() : !left;
   return Fragment(std::string(left ? "[" : "(")+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+(right ? "]" : ")"));
  }
  if(name=="qmember" && value.size()==2 && value[1].isFunction() &&
     value[1].function()->referenceName()=="qindexrange" && value[1].size()==2)
   return Fragment(render(value[0],depth+1).text+" ∈ indexrange("+render(value[1][0],depth+1).text+", "+render(value[1][1],depth+1).text+")",10);
  if(name=="qmember" && value.size()==2)
   return Fragment(render(value[0],depth+1).text+" ∈ "+render(value[1],depth+1).text,10);
  if(name=="qmatrixdimensions" && value.size()==2)
   return Fragment(render(value[0],depth+1).text+" × "+render(value[1],depth+1).text);
  if(name=="qbinarytail" && value.size()==2)
   return Fragment("binarytail("+value[0].print(options)+","+render(value[1],depth+1).text+")");
  if(name=="qbinaryfraction" && value.size()==3 && value[0].isVector()) {
   std::string digits="vector(";
   for(size_t k=0;k<value[0].size();++k) {
    if(k)digits+=", ";
    digits+=render(value[0][k],depth+1).text;
   }
   return Fragment("binaryfraction("+digits+"), "+render(value[1],depth+1).text+", "+render(value[2],depth+1).text+")");
  }
  if(name=="qbasiskets" && value.size()==1)return Fragment("basislist("+render(value[0],depth+1).text+")");
  if(name=="qbasisketset" && value.size()==1)return Fragment("basisset("+render(value[0],depth+1).text+")");
  if(name=="qtuple" && value.size()==1 && value[0].isVector()) {
   std::string text="(";
   for(size_t k=0;k<value[0].size();++k) {if(k)text+=", ";text+=render(value[0][k],depth+1).text;}
   if(value[0].size()==1)text+=",";
   return Fragment(text+")");
  }
  if(name=="qcartesian" && value.size()==2)
   return Fragment("("+render(value[0],depth+1).text+") × ("+render(value[1],depth+1).text+")");
  if(name=="qwordpower" && value.size()==2)
   return Fragment("wordpower("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qcartesianpower" && value.size()==2)
   return Fragment("("+render(value[0],depth+1).text+")^("+render(value[1],depth+1).text+") (Cartesian power; nonnegative integer count)");
  if(name=="qbitstrings" && value.size()==1)
   return Fragment("{0,1}^("+render(value[0],depth+1).text+") (nonnegative integer width)");
  if(name=="qindexedfamily" && value.size()==2 && value[0].isSymbolic() && value[1].isInteger()) {
   Number next=value[1].number();next+=1;
   PrintOptions decimal;decimal.use_unicode_signs=false;decimal.min_exp=EXP_NONE;
   const std::string &prefix=value[0].symbol();
   return Fragment("{"+prefix+value[1].number().print(decimal)+", "+prefix+next.print(decimal)+", …}");
  }
  if(name=="qindexrange" && value.size()==2 && depth)
   return Fragment("indexrange("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qindexrange" && value.size()==2)
   return Fragment("{"+render(value[0],depth+1).text+", …, "+render(value[1],depth+1).text+"} (integer endpoints)");
  if((name=="qsetimage" || name=="qsetfilter") && value.size()==3) {
   Fragment domain=render(value[1],depth+1);std::string index=fresh();
   bindings.push_back({value[2],index});Fragment body=render(value[0],depth+1);bindings.pop_back();
   return Fragment(name=="qsetimage" ? "\\{"+body.text+" : "+index+" ∈ "+domain.text+"\\}" : "\\{"+index+" ∈ "+domain.text+" : "+body.text+"\\}");
  }
  if(name=="qsumset" && value.size()==3) {
   Fragment domain=render(value[1],depth+1);std::string index=fresh();
   bindings.push_back({value[2],index});Fragment body=render(value[0],depth+1);bindings.pop_back();
   return Fragment("∑_{"+index+" ∈ "+domain.text+"} ("+body.text+")",10);
  }
  if(name=="qscalarproductsum" && value.size()==4 && value[0].isSymbolic() && value[1].isSymbolic() && value[3].isVector() && value[3].size()%3==0) {
   bool valid=true;
   for(size_t k=0;k<value[3].size();k+=3)if(!value[3][k].isNumber() || !value[3][k].number().isInteger() || value[3][k].number()<0 || value[3][k].number()>1)valid=false;
   if(valid) {
    std::string index=fresh(),width=render(value[2],depth+1).text;
    std::string left=familyName(value[0].symbol(),true),right=familyName(value[1].symbol(),true);
    std::string term=left+index+" · "+right+index;
    if(value[3].size()) {
     term+=" [component assignments: ";
     for(size_t k=0;k<value[3].size();k+=3) {
      if(k)term+=", ";
      term+=(value[3][k].number().isZero() ? left : right)+render(value[3][k+1],depth+1).text+" = "+render(value[3][k+2],depth+1).text;
     }
     term+="]";
    }
    return Fragment("∑_{"+index+"=0}^{("+width+")−1} ("+term+") (nonnegative integer width)",10);
   }
  }
  if((name=="qtensorseries" && value.size()==5) || (name=="qboundtensorseries" && value.size()==6 && value[5].isVector() && value[5].size()%2==0)) {
   std::string first=render(value[1],depth+1).text,last=render(value[2],depth+1).text,step=render(value[4],depth+1).text;
   std::string history=value.size()==6 ? historyText(value[5],depth+1) : "";
   std::string index=fresh();bindings.push_back({value[3],index});
   Fragment body=render(value[0],depth+1);bindings.pop_back();
   return Fragment("⊗_{"+index+"="+first+" to "+last+"; step "+step+"} ("+body.text+history+")",30);
  }
  if(name=="qregistersum" && value.size()==7 && value[4].isSymbolic() && value[6].isVector() && value[6].size()%2==0) {
   std::string domain=render(value[1],depth+1).text,first=render(value[2],depth+1).text,last=render(value[3],depth+1).text,width=render(value[5],depth+1).text;
   std::string history=historyText(value[6],depth+1),prefix=fresh()+"_";
   familyBindings.push_back({value[4].symbol(),prefix});
   Fragment body=render(value[0],depth+1);familyBindings.pop_back();
   return Fragment("∑_{"+prefix+"("+first+") ⋯ "+prefix+"("+last+") ∈ ("+domain+")^("+width+")} ("+body.text+history+") (width = first − last + 1; nonnegative integer width)",10);
  }
  if(name=="qbars" && value.size()==1)
   return Fragment("|"+render(value[0],depth+1).text+"|");
  if(name=="qgeometricsum" && value.size()==2)
   return Fragment("geosum("+render(value[0],depth+1).text+", "+render(value[1],depth+1).text+")");
  if(name=="qbitword" && value.size()==1) {
   const auto &bits=value[0];
   std::string text="bitword([";
   if(bits.isVector() || (bits.isFunction() && (bits.function()->referenceName()=="horzcat" ||
      bits.function()->referenceName()=="vector"))) {
    for(size_t k=0;k<bits.size();++k) {
     if(k)text+=", ";
     text+=render(bits[k],depth+1).text;
    }
   } else text+=render(bits,depth+1).text;
   return Fragment(text+"])");
  }
  if((name=="qbitvalue" && value.size()==1) || ((name=="qbitxor" || name=="qbitdot") && value.size()==2)) {
   std::string text=name.substr(1)+"(";
   for(size_t i=0;i<value.size();++i) {if(i)text+=", ";text+=render(value[i],depth+1).text;}
   return Fragment(text+")");
  }
  if(name=="qketstate" && value.size()==1 && value[0].isFunction() &&
     value[0].function()->referenceName()=="qbitlabel" && value[0].size()==2)
   return Fragment("|"+render(value[0][0],depth+1).text+"⟩_{2^("+render(value[0][1],depth+1).text+")}");
  if(name=="qketstate" && value.size()==1 && value[0].isVector() && !value[0].isMatrix()) {
   bool labels=value[0].size()>0;std::string text="uniform({";
   for(size_t i=0;i<value[0].size();++i) {
    const MathStructure &label=value[0][i];
    labels=labels && label.isFunction() && label.function()->referenceName()=="qbitlabel";
    if(i)text+=", ";text+=render(label,depth+1).text;
   }
   if(labels)return Fragment(text+"})");
  }
  if((name=="qketstate" || name=="qnamedket" || name=="qindexedket") && value.size()==1) {
   std::string label=value[0].isSymbolic() ? familyName(value[0].symbol()) : render(value[0],depth+1).text;
   // Bound labels must use the same fresh name as their displayed sum index.
   // Unbound single-letter named kets still retain the canonical fallback.
   bool bound=false;
   for(auto i=bindings.rbegin();i!=bindings.rend();++i)if(value[0].equals(i->first)) {
    label=i->second;bound=true;break;
   }
   bool literalCollision=!bound && ((value[0].isSymbolic() && label.size()==1) || label.find_first_not_of("0123456789 ")==std::string::npos);
   if(!literalCollision && safeLabel(label))return Fragment("|"+label+"⟩",100,Ket,label);
  }
  if(name=="qregisterfamily" && value.size()==4 && value[0].isSymbolic() && value[3].isVector() && value[3].size()%2==0) {
   const std::string prefix=familyName(value[0].symbol(),true);
   std::string label=prefix+grouped(render(value[1],depth+1),100)+" ⋯ "+prefix+grouped(render(value[2],depth+1),100);
   std::string text="|"+label+"⟩";
   if(!value[3].size())return Fragment(text,100,Ket,label);
   // Keep assignments and explicit-bit existence constraints outside the ket.
   // Mark the result as an annotated expression so bra composition cannot
   // discard these conditions by using only the label.
   text+="  (";
   for(size_t k=0;k<value[3].size();k+=2) {
    if(k)text+=", ";
    std::string bit=prefix+render(value[3][k],depth+1).text;
    text+=bit;
    if(value[3][k+1].isSymbolic() && familyName(value[3][k+1].symbol())==bit)text+=" present";
    else text+=" = "+render(value[3][k+1],depth+1).text;
   }
   return Fragment(text+")",10);
  }
  if(name=="qpower" && value.size()==2)return Fragment(grouped(render(value[0],depth+1),81)+"^"+grouped(render(value[1],depth+1),81),80);
  if(name=="qsqrt" && value.size()==1)return Fragment("√("+render(value[0],depth+1).text+")");
  if(name=="qequalchain" && value.size()==1 && value[0].isVector() && value[0].size()>=3 && value[0].size()<=128) {
   std::string text;
   for(size_t k=0;k<value[0].size();++k) {
    if(k)text+=" = ";text+=grouped(render(value[0][k],depth+1),11);
   }
   return Fragment(text,10);
  }
  if(name=="qcomputationalket" && value.size()==1 && value[0].isFunction() &&
     value[0].function()->referenceName()=="qoplus" && value[0].size()==2) {
   const MathStructure &op=value[0];
   auto word=[&](const MathStructure &v) {
    if(v.isFunction() && v.function()->referenceName()=="qnamedapplication" && v.size()==2 && v[0].isSymbolic())
     return v[0].symbol()+"("+render(v[1],depth+1).text+")";
    return render(v,depth+1).text;
   };
   return Fragment("|"+word(op[0])+" ⊕ "+word(op[1])+"⟩");
  }
  if(name=="qcomputationalket" && value.size()==1)
   return Fragment("|"+render(value[0],depth+1).text+"⟩ (dimension unresolved)");
  if(name=="qtensorchain" && value.size()==2 && value[1].isVector() && value[1].size()>=2 && value[1].size()<=2048) {
   std::string text=grouped(render(value[0],depth+1),31)+" ⊗ ";
   for(size_t k=0;k<value[1].size();++k) {
    if(k)text+=" ";text+=grouped(render(value[1][k],depth+1),61);
   }
   return Fragment(text,30);
  }
  if(name=="qtensorpow" && value.size()==2 && value[1].isSymbolic() && safeLabel(value[1].symbol())) {
   std::string base=render(value[0],depth+1).text;
   if(base=="[1; 0]" || base=="[0; 1]")
    return Fragment(std::string(base=="[1; 0]" ? "|0^" : "|1^")+value[1].symbol()+"⟩");
  }
  if(name=="qtensorpow" && value.size()==2)return Fragment(grouped(render(value[0],depth+1),81)+"^{⊗ "+render(value[1],depth+1).text+"}",80);
  // Keep the basis dimension explicit; treating this as an ordinary named ket
  // would let bra/ket composition accidentally omit that dimension.
  if(name=="qbasis" && value.size()==2)
   return Fragment("|"+render(value[0],depth+1).text+"⟩_{"+render(value[1],depth+1).text+"}");
  if((name=="qsin" || name=="qcos" || name=="qtan" || name=="qasin" || name=="qacos" || name=="qatan" || name=="qexp") && value.size()==1)
   return Fragment(name.substr(1)+"("+render(value[0],depth+1).text+")");
  if(name=="qfourierdomain" && value.size()==3) {
   Fragment body=render(value[0],depth+1),index=render(value[1],depth+1),dimension=render(value[2],depth+1);
   return Fragment(body.text+"  (0 ≤ "+index.text+" < "+dimension.text+"; "+index.text+", "+dimension.text+" ∈ ℤ)",10);
  }
  if(name=="qunitaryidentity" && value.size()==2) {
   std::string dimension=render(value[1],depth+1).text;
   return Fragment("I_{"+dimension+"}  ("+render(value[0],depth+1).text+" unitary; dimension "+dimension+")",10);
  }
  if(name=="qfourier" && value.size()==1)return Fragment("QFT_"+grouped(render(value[0],depth+1),100));
  if(name=="qtrace" && value.size()==1)return Fragment("Tr("+render(value[0],depth+1).text+")");
  if(name=="qsum" && value.size()==4) {
   Fragment first=render(value[1],depth+1),last=render(value[2],depth+1);
   std::string index=fresh();bindings.push_back({value[3],index});
   Fragment body=render(value[0],depth+1);bindings.pop_back();
   return Fragment("∑_{"+index+"="+first.text+"}^{"+last.text+"} ("+body.text+")",10);
  }
  if(name=="qdag" && value.size()==1) {
   Fragment child=render(value[0],depth+1);
   if(child.kind==Ket)return Fragment("⟨"+child.label+"|",100,Bra,child.label);
   if(child.kind==Bra)return Fragment("|"+child.label+"⟩",100,Ket,child.label);
   return Fragment(grouped(child,100)+"†",90);
  }
  if((name=="qadd" || name=="qsub" || name=="qmul" || name=="qadjacent" || name=="qtensor") && value.size()==2) {
   Fragment left=render(value[0],depth+1),right=render(value[1],depth+1);
   if(name=="qadd" || name=="qsub")return Fragment(grouped(left,20)+(name=="qadd" ? " + " : " − ")+grouped(right,name=="qsub" ? 21 : 20),20);
   if(name=="qtensor")return Fragment(grouped(left,31)+" ⊗ "+grouped(right,31),30);
   if(left.kind==Bra && right.kind==Ket)return Fragment("⟨"+left.label+"|"+right.label+"⟩");
   if(left.kind==BraProduct && right.kind==Ket)return Fragment(left.text+" "+right.text);
   if(left.kind==Bra)return Fragment(left.text+" "+grouped(right,41),40,BraProduct);
   // Juxtaposition with a row or column can become a tensor product once
   // the left operand is bound. Keep that decision for the evaluator.
   if(name=="qadjacent") {
    const auto &operand=value[1];
    bool vectorMatrix=operand.isMatrix() && (operand.columns()==1 || operand.rows()==1);
    if(operand.isFunction() && operand.function()->referenceName()=="matrix" && operand.size()==3)
     vectorMatrix=operand[0].isOne() || operand[1].isOne();
    // A computed state beside another ket must remain a separate factor.
    // Without grouping, consecutive Dirac kets can bind before the operator.
    std::string rightType=operand.isFunction() ? operand.function()->referenceName() : "";
    bool ketOperand=rightType=="qketstate" || rightType=="qnamedket" || rightType=="qindexedket" || rightType=="qbasis";
    if(vectorMatrix || (ketOperand && (right.kind!=Ket || left.precedence==40)))
     return Fragment("("+left.text+") ("+right.text+")",40);
   }
   return Fragment(grouped(left,40)+(right.kind==Ket ? " " : " · ")+grouped(right,40),40);
  }
  return fallback(value);
 }
 public:
 explicit Printer(const PrintOptions &print):options(print) {}
 std::string print(const MathStructure &value) {
  if(value.isNumber() || (value.isMatrix() && value.columns()<=1))return value.print(options);
  if(!collect(value))return value.print(options);
  std::string text=render(value,0).text;
  return !lostBinding && text.size()<=131072 ? text : value.print(options);
 }
};
inline std::string print(const MathStructure &value,const PrintOptions &options) {return Printer(options).print(value);}
}
#endif

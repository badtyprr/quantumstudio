// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_DISPLAY_H
#define QUANTUM_DISPLAY_H
#include "MathStructure.h"
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
 bool collect(const MathStructure &value,unsigned depth=0) {
  if(depth>128 || ++collected>2048)return false;
  if(value.isSymbolic()) {
   const std::string name=value.symbol();names.insert(name);
   // A fixed subscript remains free even inside a generated indexed label.
   // Reserve its components so choosing a displayed binder cannot capture it.
   size_t start=0;
   for(size_t end=0;end<=name.size();++end)if(end==name.size() || name[end]=='_') {
    if(end>start)names.insert(name.substr(start,end-start));
    start=end+1;
   }
  }
  if(value.isVariable())names.insert(value.variable()->referenceName());
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
  int precedence=value.isComparison() ? 5 : value.isAddition() ? 20 : value.isMultiplication() || value.isInverse() || value.isDivision() ? 40 : value.isNegate() ? 70 : value.isPower() ? 80 : 100;
  if(value.isNumber() && value.number().isNegative())precedence=70;
  if(value.isNumber() && value.number().isComplex())precedence=20;
  return Fragment(value.print(options),precedence);
 }
 Fragment render(const MathStructure &value,unsigned depth) {
  if(depth>128 || ++nodes>2048)return fallback(value);
  for(auto i=bindings.rbegin();i!=bindings.rend();++i)if(value.equals(i->first))return Fragment(i->second);
  if(value.isVariable() && !value.variable()->isKnown())return Fragment(value.variable()->referenceName());
  if(value.isSymbolic() && value.symbol().size()==1 && std::isalpha(static_cast<unsigned char>(value.symbol()[0])) && value.symbol()!="i" && value.symbol()!="e")return Fragment(value.symbol());
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
  if((name=="qindexedcolumn" && value.size()==3) || (name=="qindexedmatrix" && value.size()==5)) {
   const bool matrix=name=="qindexedmatrix";
   std::string prefix=value[0].isSymbolic() ? value[0].symbol() : "";
   bool safe=prefix.size()>1 && prefix.back()=='_';
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
   if(safe && !matrix) {
    std::string text="[";
    for(int row=0;row<=minima[0];++row)text+=prefix+std::to_string(row)+"; ";
    return Fragment(text+"⋮; "+prefix+"("+endpoints[0]+")]");
   }
   if(safe) {
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
   return Fragment(part(value[0])+grouped(index,100)+part(value[2]));
  }
  if((name=="qketstate" || name=="qnamedket" || name=="qindexedket") && value.size()==1) {
   std::string label=value[0].isSymbolic() ? value[0].symbol() : render(value[0],depth+1).text;
   // Bound labels must use the same fresh name as their displayed sum index.
   // Unbound single-letter named kets still retain the canonical fallback.
   bool bound=false;
   for(auto i=bindings.rbegin();i!=bindings.rend();++i)if(value[0].equals(i->first)) {
    label=i->second;bound=true;break;
   }
   bool literalCollision=!bound && ((value[0].isSymbolic() && label.size()==1) || label.find_first_not_of("0123456789 ")==std::string::npos);
   if(!literalCollision && safeLabel(label))return Fragment("|"+label+"⟩",100,Ket,label);
  }
  if(name=="qpower" && value.size()==2)return Fragment(grouped(render(value[0],depth+1),81)+"^"+grouped(render(value[1],depth+1),81),80);
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
   return Fragment(grouped(left,40)+(right.kind==Ket ? " " : " · ")+grouped(right,40),40);
  }
  return fallback(value);
 }
 public:
 explicit Printer(const PrintOptions &print):options(print) {}
 std::string print(const MathStructure &value) {
  if(value.isMatrix() || value.isNumber())return value.print(options);
  if(!collect(value))return value.print(options);
  std::string text=render(value,0).text;
  return !lostBinding && text.size()<=131072 ? text : value.print(options);
 }
};
inline std::string print(const MathStructure &value,const PrintOptions &options) {return Printer(options).print(value);}
}
#endif

// GPL-2.0-or-later; see COPYING.
#include "QuantumTeX.h"
#include <cctype>
#include <map>
#include <stdexcept>
#include <vector>

namespace {
bool asciiLetter(unsigned char c) {return (c>='A' && c<='Z') || (c>='a' && c<='z');}
std::string trim(const std::string &s) {
 size_t first=s.find_first_not_of(" \t\r\n"),last=s.find_last_not_of(" \t\r\n");
 return first==std::string::npos ? "" : s.substr(first,last-first+1);
}
class TeXReader {
 const std::string &input;
 size_t pos=0;
 unsigned depth=0;
 bool setBound=false;
 void space() { while(pos<input.size() && std::isspace((unsigned char)input[pos])) ++pos; }
 std::string error(const std::string &message) const { return message+" at byte "+std::to_string(pos+1); }
 std::string group() {
  space();
  if(pos==input.size() || input[pos]!='{') throw std::runtime_error(error("Expected a braced TeX argument"));
  ++pos;
  return read('}');
 }
 std::string argument() {
  space();
  if(pos==input.size()) throw std::runtime_error(error("Missing TeX argument"));
  if(input[pos]=='{') return group();
  if(input[pos]=='\\') {
   if(++depth>128) throw std::runtime_error(error("TeX nesting exceeds 128"));
   int norms=0; auto value=command(false,norms); --depth;
   if(norms || value.empty()) throw std::runtime_error(error("Expected a complete TeX argument"));
   return value;
  }
  unsigned char c=input[pos];
  if(c<128) {
   if(!std::isalnum(c)) throw std::runtime_error(error("Put a compound TeX argument in braces"));
   return input.substr(pos++,1);
  }
  size_t start=pos++;
  while(pos<input.size() && ((unsigned char)input[pos] & 0xc0)==0x80) ++pos;
  return input.substr(start,pos-start);
 }
 // Raw groups are used only for command names and environment names, which
 // cannot contain TeX structure. Unlike expression groups, no evaluation occurs.
 std::string nameGroup() {
  space(); if(pos==input.size() || input[pos++]!='{') throw std::runtime_error(error("Expected {name}"));
  size_t start=pos;
  while(pos<input.size() && input[pos]!='}') {
   if(!std::isalnum((unsigned char)input[pos]) && input[pos]!='*') throw std::runtime_error(error("Invalid TeX name"));
   ++pos;
  }
  if(pos==input.size()) throw std::runtime_error(error("Unclosed TeX name"));
  std::string result=input.substr(start,pos-start); ++pos; return result;
 }
 std::string closeNorm(bool required=false) {
  space();
  // TeX permits either order of super- and subscripts. Preserve the power's
  // scope over the norm rather than the matrix or its Schatten order.
  std::string power;
  if(pos<input.size() && input[pos]=='^') {++pos;power=argument();if(power.empty())throw std::runtime_error(error("Empty norm power"));space();}
  std::string order;bool indexed=false;
  if(input.compare(pos,3,"₁")==0 || input.compare(pos,3,"₂")==0) {indexed=true;order=input.compare(pos,3,"₁")==0 ? "1" : "2";pos+=3;}
  else if(pos<input.size() && input[pos]=='_') {indexed=true;++pos;order=argument();}
  size_t first=order.find_first_not_of(" \t\r\n"),last=order.find_last_not_of(" \t\r\n");
  if(first!=std::string::npos)order=order.substr(first,last-first+1);
  else if(indexed)throw std::runtime_error(error("Empty norm order"));
  if(order=="F")order="2";
  if(required && order.empty())throw std::runtime_error(error("Matrix norms require an explicit norm convention"));
  return (order.empty() ? ")" : ","+order+")")+(power.empty() ? "" : "^("+power+")");
 }
 std::string command(bool matrix, int &norms, bool cases=false) {
  ++pos;
  if(pos==input.size()) throw std::runtime_error(error("Incomplete TeX command"));
  if(!asciiLetter((unsigned char)input[pos])) {
   char c=input[pos++];
   if(setBound && c=='{')return "vector(";
   if(setBound && c=='}')return ")";
   if(c=='\\' && matrix) {
    space();
    if(pos<input.size() && input[pos]=='[') {
     // Row spacing is presentation-only. Accept a literal TeX dimension, never
     // translate its contents into the matrix's mathematical expression.
     ++pos;space();
     if(pos<input.size() && (input[pos]=='+' || input[pos]=='-'))++pos;
     bool digit=false,dot=false;
     while(pos<input.size()) {
      char d=input[pos];
      if(d>='0' && d<='9')digit=true;
      else if(d=='.' && !dot)dot=true;
      else break;
      ++pos;
     }
     if(!digit)throw std::runtime_error(error("Matrix row spacing requires a literal numeric dimension"));
     space();size_t unitStart=pos;
     while(pos<input.size() && asciiLetter((unsigned char)input[pos]))++pos;
     std::string unit=input.substr(unitStart,pos-unitStart);
     if(unit!="pt" && unit!="pc" && unit!="in" && unit!="bp" && unit!="cm" && unit!="mm" &&
        unit!="dd" && unit!="cc" && unit!="sp" && unit!="em" && unit!="ex" && unit!="mu")
      throw std::runtime_error(error("Unsupported matrix row spacing unit"));
     space();if(pos==input.size() || input[pos]!=']')throw std::runtime_error(error("Invalid matrix row spacing"));
     ++pos;
    }
    return ";";
   }
   if(c==',' || c==';' || c==':' || c=='!' || c==' ') return " ";
   if(c=='|') { if(norms) { --norms; return closeNorm(); } ++norms; return "norm("; }
   throw std::runtime_error(error("Unsupported TeX control symbol"));
  }
  size_t start=pos; while(pos<input.size() && asciiLetter((unsigned char)input[pos])) ++pos;
  std::string name=input.substr(start,pos-start);
  if(name=="left" || name=="right" || name=="big" || name=="Big" || name=="bigl" || name=="bigr" || name=="Bigl" || name=="Bigr" || name=="bigg" || name=="Bigg" || name=="biggl" || name=="biggr" || name=="Biggl" || name=="Biggr") {
   space(); if(pos<input.size() && input[pos]=='.') ++pos; return "";
  }
  if(name=="in" && setBound)return "∈";
  if(name=="frac" || name=="dfrac" || name=="tfrac") { auto a=argument(), b=argument(); return "(("+a+")/("+b+"))"; }
  if(name=="tilde" || name=="widetilde") {
   std::string value=trim(argument());
   if(value.empty() || std::isdigit((unsigned char)value[0]))throw std::runtime_error(error("A tilde requires a symbol name"));
   for(unsigned char c:value)if(c<128 && !std::isalnum(c) && c!='_')throw std::runtime_error(error("A tilde requires a symbol name, not a compound expression"));
   // Estimates and transformed variables must remain distinct from the original.
   return " "+value+"_tilde ";
  }
  if(name=="hat" || name=="widehat") {
   auto value=argument();size_t first=value.find_first_not_of(" \t\r\n"), last=value.find_last_not_of(" \t\r\n");
   if(first==std::string::npos)throw std::runtime_error(error("An operator hat requires an operand"));
   value=value.substr(first,last-first+1);bool identifier=true;
   for(unsigned char c:value)if(c<128 && !std::isalnum(c) && c!='_')identifier=false;
   // Keep names intact for subsequent subscripts and function calls. Compound
   // operands must retain their scope under a following power or dagger.
   return identifier ? " "+value+" " : "("+value+")";
  }
  if(name=="sqrt") {
   space(); std::string index;
   if(pos<input.size() && input[pos]=='[') { ++pos; index=read(']'); }
   auto a=argument(); return index.empty() ? "sqrt("+a+")" : "(("+a+")^(1/("+index+")))";
  }
  if(name=="sum" || name=="prod" || name=="bigotimes" || name=="bigoplus") {
   space(); if(input.compare(pos,7,"\\limits")==0) pos+=7;
   std::string lower, upper;
   for(int k=0;k<2;++k) {
    space(); if(pos==input.size() || (input[pos]!='_' && input[pos]!='^')) throw std::runtime_error(error("A finite sum/product requires lower and upper bounds"));
    char bound=input[pos++]; bool priorSetBound=setBound;setBound=bound=='_';
    std::string value=argument();setBound=priorSetBound;
    if(bound=='_') { if(!lower.empty()) throw std::runtime_error(error("Duplicate lower bound")); lower=value; }
    else { if(!upper.empty()) throw std::runtime_error(error("Duplicate upper bound")); upper=value; }
    if(lower.find("∈")!=std::string::npos)break;
   }
   size_t membership=lower.find("∈");
   bool setSum=membership!=std::string::npos;
   if(setSum && (name!="sum" || !upper.empty()))throw std::runtime_error(error("Set-indexed sums have no upper bound"));
   size_t equal=setSum ? membership : lower.find('=');
   if(equal==std::string::npos) throw std::runtime_error(error("Use an index assignment such as k=0 in the lower bound"));
   std::string variable=lower.substr(0,equal), startValue=lower.substr(equal+(setSum ? std::string("∈").size() : 1));
   if(setSum && trim(startValue).empty())throw std::runtime_error(error("A set sum requires a finite index collection"));
   size_t first=variable.find_first_not_of(" \t\r\n"), last=variable.find_last_not_of(" \t\r\n");
   if(first==std::string::npos) throw std::runtime_error(error("Missing summation index"));
   variable=variable.substr(first,last-first+1);
   if(variable[0]>='0' && variable[0]<='9') throw std::runtime_error(error("A summation index cannot begin with a digit"));
   for(unsigned char c:variable) if(c<128 && !asciiLetter(c) && c!='_' && !(c>='0' && c<='9' && variable.find('_')!=std::string::npos)) throw std::runtime_error(error("Invalid summation index"));
   space();
   if(pos==input.size())throw std::runtime_error(error("Missing finite sum/product body"));
   if(input[pos]!='{') {
    // The expression parser determines the multiplicative body's extent.
    if(setSum)return "qtexsumset("+startValue+","+variable+") ";
    return "qtex"+name+"("+startValue+","+upper+","+variable+") ";
   }
   auto body=group();
   if(setSum)return "sumset("+body+","+startValue+","+variable+")";
   return (name=="sum" ? "sum(" : name=="prod" ? "product(" : name=="bigoplus" ? "blocksum(" : "tensorproduct(")+body+","+startValue+","+upper+","+variable+")";
  }
  bool expectation=name=="expectationvalue" || name=="expval" || name=="ev";
  bool matrixElement=name=="matrixelement" || name=="matrixel" || name=="mel";
  bool dirac=name=="ket" || name=="Ket" || name=="bra" || name=="Bra" || name=="braket" || name=="Braket" || name=="innerproduct" || name=="ip" || name=="ketbra" || name=="outerproduct" || name=="dyad" || name=="op";
  if(expectation || matrixElement || dirac) {
   space();unsigned stars=0;while(pos<input.size() && input[pos]=='*') {++pos;++stars;}
   if(stars>(expectation || matrixElement ? 2U : 1U))throw std::runtime_error(error("Too many Dirac sizing stars"));
  }
  if(expectation) {
   auto observable=group();space();
   if(pos==input.size() || input[pos]!='{')throw std::runtime_error(error("An expectation value requires an explicit state label: use expval{A}{state}"));
   auto state=group();return "(<"+state+"|("+observable+")|"+state+">)";
  }
  if(matrixElement) {
   auto left=group(),observable=group(),right=group();
   return "(<"+left+"|("+observable+")|"+right+">)";
  }
  if(name=="ket" || name=="Ket") return "|"+argument()+">";
  if(name=="bra" || name=="Bra") return "<"+argument()+"|";
  if(name=="braket" || name=="Braket" || name=="innerproduct" || name=="ip") {
   auto a=group(); space();
   if(pos<input.size() && input[pos]=='{') return "<"+a+"|"+group()+">";
   if(a.find('|')==std::string::npos)return "<"+a+"|"+a+">";
   return "<"+a+">";
  }
  if(name=="ketbra" || name=="outerproduct" || name=="dyad" || name=="op") {
   auto a=group(); space(); auto b=pos<input.size() && input[pos]=='{' ? group() : a;
   return "(|"+a+"><"+b+"|)";
  }
  if(name=="norm") {auto body=group();return "norm("+body+closeNorm();}
  if(name=="abs") return "abs("+group()+")";
  if(name=="comm" || name=="commutator" || name=="anticommutator") {
   auto a=group(), b=group(); return (name=="anticommutator" ? "anticomm(" : "comm(")+a+","+b+")";
  }
  if(name=="operatorname" || name=="mathrm" || name=="mathsf" || name=="mathbf" || name=="mathbb" || name=="mathcal") {
   auto a=nameGroup();
   if((name=="mathbb" || name=="mathbf") && a=="1") a="I";
   return " "+a+" ";
  }
  if(name=="text" && cases) {
   std::string text=trim(group());
   if(text=="otherwise")return text;
   if(text!="if" && (text.size()<3 || text.compare(0,2,"if")!=0 || !std::isspace((unsigned char)text[2])))throw std::runtime_error(error("Cases text must introduce if or otherwise"));
   text=trim(text.substr(2));
   if(text.size()>=2 && text.front()=='$' && text.back()=='$')text=text.substr(1,text.size()-2);
   return text;
  }
  if(name=="begin") {
   auto env=nameGroup();
   if(env=="cases")return read(0,true,env);
   if(env!="matrix" && env!="pmatrix" && env!="bmatrix" && env!="Bmatrix" && env!="vmatrix" && env!="Vmatrix") throw std::runtime_error(error("Unsupported TeX environment: "+env));
   auto body=read(0,true,env); std::string m="["+body+"]";
   if(env=="vmatrix") return "det("+m+")";
   if(env=="Vmatrix") return "norm("+m+closeNorm(true);
   return m;
  }
  if(name=="lVert") { ++norms; return "norm("; }
  if(name=="rVert") { if(norms==0) throw std::runtime_error(error("Unmatched norm delimiter")); --norms; return closeNorm(); }
  if(name=="Vert") { if(norms) { --norms; return closeNorm(); } ++norms; return "norm("; }
  static const std::map<std::string,std::string> aliases={
   {"langle","<"},{"rangle",">"},{"vert","|"},{"lvert","|"},{"rvert","|"},
   {"otimes","@"},{"oplus","#"},{"dagger","~"},{"cdot","*"},{"times","*"},
   {"top","`"},{"ast","*"},{"bmod","%"},{"mod","%"},
   {"le","<="},{"leq","<="},{"ge",">="},{"geq",">="},{"ne","!="},{"neq","!="},
   {"preceq","<="},{"succeq",">="},{"preccurlyeq","<="},{"succcurlyeq",">="},{"prec","<"},{"succ",">"},
   {"land"," and "},{"wedge"," and "},{"lor"," or "},{"vee"," or "},{"lnot"," not "},{"neg"," not "},{"veebar"," xor "},
   {"uparrow","↑"},{"downarrow","↓"},
   {"infty","infinity"},{"pi","pi"},{"alpha","α"},{"beta","β"},{"gamma","γ"},{"delta","δ"},{"theta","θ"},
   {"phi","φ"},{"Phi","Φ"},{"varphi","φ"},{"psi","ψ"},{"Psi","Ψ"},{"rho","ρ"},{"sigma","σ"},
   {"lambda","λ"},{"omega","ω"},{"epsilon","ε"},{"varepsilon","ε"},{"chi","χ"},
   {"sin","sin"},{"cos","cos"},{"tan","tan"},{"exp","exp"},{"log","ln"},{"ln","ln"},
   {"det","det"},{"tr","tr"},{"Tr","Tr"},{"quad"," "},{"qquad"," "}
  };
  auto it=aliases.find(name); if(it!=aliases.end()) return it->second;
  throw std::runtime_error(error("Unsupported TeX command: \\"+name));
 }
 std::string read(char close=0, bool matrix=false, const std::string &environment="") {
  if(++depth>128) throw std::runtime_error(error("TeX nesting exceeds 128"));
  std::string result; int norms=0; bool closed=false;
  std::vector<std::pair<std::string,std::string>> branches;
  std::string caseValue;bool caseColumn=false;
  auto finishCase=[&]() {
   if(!caseColumn || trim(caseValue).empty() || trim(result).empty())throw std::runtime_error(error("Each case requires a value and condition separated by &"));
   if(branches.size()>=64)throw std::runtime_error(error("Cases are limited to 64 branches"));
   branches.emplace_back(trim(caseValue),trim(result));result.clear();caseValue.clear();caseColumn=false;
  };
  while(pos<input.size()) {
   if(close && input[pos]==close) { ++pos; closed=true; break; }
   if(matrix && input.compare(pos,4,"\\end")==0 && (pos+4==input.size() || !asciiLetter((unsigned char)input[pos+4]))) {
    pos+=4; if(nameGroup()!=environment) throw std::runtime_error(error("Mismatched matrix environment")); closed=true; break;
   }
   // Quoted labels are literal data; do not reinterpret operator subscripts.
   if(input[pos]=='"' || input[pos]=='\'') {
    char quote=input[pos++];result+=quote;bool ended=false;
    while(pos<input.size()) {char c=input[pos++];result+=c;if(c==quote){ended=true;break;}}
    if(!ended)throw std::runtime_error(error("Unclosed quoted label"));
   }
   else if(input[pos]=='\\') {
    std::string part=command(matrix,norms,environment=="cases");
    if(environment=="cases" && part==";")finishCase();else result+=part;
   }
   else if(input[pos]=='(' || input[pos]=='[') {
    char open=input[pos++], end=open=='(' ? ')' : ']';
    result+=open; result+=read(end); result+=end;
   }
   else if(input[pos]==')' || input[pos]==']') throw std::runtime_error(error("Unmatched closing delimiter"));
   else if(input[pos]=='_') {
    while(!result.empty() && std::isspace((unsigned char)result.back()))result.pop_back();
    bool spin=!result.empty() && result.back()=='J' && (result.size()==1 ||
     ((unsigned char)result[result.size()-2]<128 && !std::isalnum((unsigned char)result[result.size()-2]) && result[result.size()-2]!='_'));
    bool bell=false;
    for(const std::string &name:{std::string("Φ"),std::string("φ"),std::string("ϕ"),std::string("Ψ"),std::string("ψ"),std::string("Phi"),std::string("phi"),std::string("Psi"),std::string("psi")})
     if(result.size()>=name.size() && result.compare(result.size()-name.size(),name.size(),name)==0)bell=true;
    bool fourier=result.size()>=3 && result.substr(result.size()-3)=="QFT" &&
     (result.size()==3 || (!std::isalnum((unsigned char)result[result.size()-4]) && result[result.size()-4]!='_' && (unsigned char)result[result.size()-4]<128));
    ++pos; space(); std::string index;bool grouped=false;
    if(pos<input.size() && input[pos]=='{') {grouped=true;index=group();}
    else if(pos<input.size() && input[pos]=='(') {grouped=true;++pos;index=read(')');}
    else if(fourier && pos<input.size() && std::isdigit((unsigned char)input[pos])) {
     while(pos<input.size() && std::isdigit((unsigned char)input[pos]))index+=input[pos++];
    }
    else if(pos<input.size() && std::isalnum((unsigned char)input[pos])) index+=input[pos++];
    else if((spin || bell) && pos<input.size() && (input[pos]=='+' || input[pos]=='-')) index+=input[pos++];
    else throw std::runtime_error(error("Expected a subscript"));
    bool trace=result.size()>=2 && (result.substr(result.size()-2)=="Tr" || result.substr(result.size()-2)=="tr") &&
     (result.size()==2 || !std::isalnum((unsigned char)result[result.size()-3]));
    if(fourier) {result.resize(result.size()-3);result+="qfourier("+index+")";}
    else if(trace) {
     space(); std::string body;
     if(pos<input.size() && input[pos]=='{') body=group();
     else if(pos<input.size() && input[pos]=='(') { ++pos; body=read(')'); }
     else throw std::runtime_error(error("A subscripted trace requires a parenthesized or braced operand"));
     result.resize(result.size()-2); result+="ptrace("+body+",vector("+index+"))";
    } else if(spin) {
     size_t first=index.find_first_not_of(" \t\r\n"), last=index.find_last_not_of(" \t\r\n");
     if(first!=std::string::npos)index=index.substr(first,last-first+1);
     if(index=="+")result+="plus";
     else if(index=="-")result+="minus";
     else result+="_"+index;
    } else if(grouped && !result.empty() && (result.back()=='>' || result.back()=='|'))result+="_("+index+")";
    else result+="_"+index;
   }
   else if(input[pos]=='{') {
    auto value=group();
    // TeX ignores spaces around operator-valued superscripts.
    size_t first=value.find_first_not_of(" \t\r\n"), last=value.find_last_not_of(" \t\r\n");
    if(first!=std::string::npos)value=value.substr(first,last-first+1);
    while(!result.empty() && std::isspace((unsigned char)result.back()))result.pop_back();
    // TeX power groups preserve postfix dagger and the tensor-power operator.
    if(!result.empty() && result.back()=='^' && value=="~") { result.pop_back(); result+="~"; }
    else if(!result.empty() && result.back()=='^' && (value=="T" || value=="`")) { result.pop_back(); result+="`"; }
    else if(!result.empty() && result.back()=='^' && value=="*") { result.pop_back(); result+="?"; }
    else if(!result.empty() && result.back()=='^' && value.compare(0,2,"T_")==0) result+="%("+value.substr(2)+")";
    else if(!result.empty() && result.back()=='^' && !value.empty() && value[0]=='@') result+="@("+value.substr(1)+")";
    else result+="("+value+")";
   }
   else if(input[pos]=='}') throw std::runtime_error(error("Unexpected closing brace"));
   else if(input[pos]=='&') { if(!matrix) throw std::runtime_error(error("Alignment separator outside a matrix")); ++pos;
    if(environment=="cases") {
     if(caseColumn)throw std::runtime_error(error("Each case has exactly two columns"));
     caseValue=result;result.clear();caseColumn=true;
    } else result+=",";
   }
   else if(input.compare(pos,3,"‖")==0 || input.compare(pos,3,"∥")==0) { pos+=3; if(norms) { --norms; result+=closeNorm(); } else { ++norms; result+="norm("; } }
   else result+=input[pos++];
   if(result.size()>131072) throw std::runtime_error(error("Expanded TeX expression exceeds the size limit"));
  }
  if((close || matrix) && !closed) throw std::runtime_error(error("Unclosed TeX group or environment"));
  if(norms) throw std::runtime_error(error("Unclosed norm delimiter"));
  if(environment=="cases") {
   if(caseColumn || !trim(result).empty())finishCase();
   if(branches.empty())throw std::runtime_error(error("A cases environment cannot be empty"));
   result="undefined";
   for(size_t j=branches.size();j>0;--j) {
    const auto &branch=branches[j-1];
    if(branch.second=="otherwise") {
     if(j!=branches.size())throw std::runtime_error(error("Otherwise must be the final case"));
     result=branch.first;
    } else result="if("+branch.second+","+branch.first+","+result+")";
    if(result.size()>131072)throw std::runtime_error(error("Expanded TeX expression exceeds the size limit"));
   }
   result="("+result+")";
  }
  --depth; return result;
 }
 public:
 explicit TeXReader(const std::string &s):input(s) {}
 std::string run() { return read(); }
};
}
std::string quantumTeX(const std::string &input) {
 // Strip only a complete paired math wrapper. A dollar inside an expression
 // remains an error in the quantum grammar.
 size_t first=input.find_first_not_of(" \t\r\n"), last=input.find_last_not_of(" \t\r\n");
 if(first==std::string::npos) return "";
 std::string s=input.substr(first,last-first+1);
 if(s.size()>=4 && s.substr(0,2)=="$$" && s.substr(s.size()-2)=="$$") s=s.substr(2,s.size()-4);
 else if(s.size()>=2 && s.front()=='$' && s.back()=='$') s=s.substr(1,s.size()-2);
 else if(s.size()>=4 && ((s.substr(0,2)=="\\(" && s.substr(s.size()-2)=="\\)") || (s.substr(0,2)=="\\[" && s.substr(s.size()-2)=="\\]"))) s=s.substr(2,s.size()-4);
 // Unicode large operators use the same explicit bounds and operand grammar
 // as their TeX spellings. Preserve quoted labels verbatim.
 static const auto largeOperators=std::map<std::string,std::string>{{"∑","\\sum "},{"∏","\\prod "},{"⨂","\\bigotimes "},{"⨁","\\bigoplus "}};
 std::string normalized;char quote=0;
 for(size_t k=0;k<s.size();) {
  if(s[k]=='"' || s[k]=='\'') {if(quote==s[k])quote=0;else if(!quote)quote=s[k];normalized+=s[k++];continue;}
  if(!quote && s.compare(k,3,"QFT")==0 &&
     (k==0 || (!std::isalnum((unsigned char)s[k-1]) && s[k-1]!='_' && (unsigned char)s[k-1]<128))) {
   size_t end=k+3;std::string digits;
   const std::string subscripts[]={"₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"};
   while(end<s.size()) {
    bool found=false;
    for(unsigned d=0;d<10;++d)if(s.compare(end,subscripts[d].size(),subscripts[d])==0) {
     digits+=char('0'+d);end+=subscripts[d].size();found=true;break;
    }
    if(!found)break;
   }
   if(!digits.empty()) {normalized+="QFT_{"+digits+"}";k=end;continue;}
  }
  bool matched=false;
  if(!quote)for(const auto &alias:largeOperators) {
   if(s.compare(k,alias.first.size(),alias.first)==0) {normalized+=alias.second;k+=alias.first.size();matched=true;break;}
  }
  if(!matched)normalized+=s[k++];
 }
 return TeXReader(normalized).run();
}

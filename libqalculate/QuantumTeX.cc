// GPL-2.0-or-later; see COPYING.
#include "QuantumTeX.h"
#include <algorithm>
#include <cctype>
#include <map>
#include <regex>
#include <set>
#include <stdexcept>
#include <vector>

namespace {
bool asciiSpace(unsigned char c) {return c==' ' || (c>='\t' && c<='\r');}
bool asciiLetter(unsigned char c) {return (c>='A' && c<='Z') || (c>='a' && c<='z');}
// In binary-word mode, adjacent digits and named bits occupy consecutive
// positions, most significant first. Leave explicit calculator calls intact.
std::string orderedBitWord(const std::string &text) {
 std::string digits;
 for(unsigned char c:text)if(!asciiSpace(c))digits+=c;
 if(!digits.empty() && digits.find_first_not_of("01")==std::string::npos)
  return "bitstring(\""+digits+"\")";
 std::string result="qbitword(vector(";size_t count=0;
 for(size_t i=0;i<text.size();) {
  unsigned char c=text[i];
  if(asciiSpace(c)) {++i;continue;}
  size_t first=i++;
  if(asciiLetter(c)) {
   if(i<text.size() && text[i]=='_') {
    size_t index=++i;
    while(i<text.size() && std::isdigit((unsigned char)text[i]))++i;
    if(i==index)return text;
   }
  } else if(!std::isdigit(c))return text;
  if(count==1024)throw std::runtime_error("A binary word supports at most 1024 bits.");
  if(count++)result+=",";
  result+=text.substr(first,i-first);
 }
 return count ? result+"))" : text;
}
std::string trim(const std::string &s) {
 size_t first=s.find_first_not_of(" \t\r\n"),last=s.find_last_not_of(" \t\r\n");
 return first==std::string::npos ? "" : s.substr(first,last-first+1);
}
// Binary-fraction mode supplies the radix for an open sequence of named bits.
std::string openBinaryFraction(const std::string &source) {
 std::string text=trim(source);
 size_t end=text.size();
 for(const std::string dots:{"\\cdots","\\ldots","…","..."}) {
  if(end>=dots.size() && text.compare(end-dots.size(),dots.size(),dots)==0) {end-=dots.size();break;}
 }
 if(end==text.size())return "";
 size_t equals=text.rfind('=',end),at=equals==std::string::npos ? 0 : equals+1;
 auto space=[&](){while(at<end && asciiSpace((unsigned char)text[at]))++at;};
 space();
 if(text.compare(at,2,"0.")==0)++at;
 std::string prefix,entries;int count=0,point=-1;
 while(at<end) {
  if(text[at]=='.' && point<0) {point=count;++at;space();continue;}
  if(!asciiLetter(text[at]) || at+1>=end || text[at+1]!='_')return "";
  std::string family=text.substr(at,2);at+=2;
  if(prefix.empty())prefix=family;
  if(prefix!=family)return "";
  bool grouped=at<end && text[at]=='{';if(grouped)++at;
  size_t begin=at;
  while(at<end && std::isdigit((unsigned char)text[at]))++at;
  std::string index=text.substr(begin,at-begin);
  if(index!=std::to_string(count+1) || (grouped && (at==end || text[at++]!='}')))return "";
  if(++count>1024)throw std::runtime_error("A binary word supports at most 1024 bits.");
  if(count>1)entries+=",";
  entries+=family+index;space();
 }
 if(count<2 || point<0 || point==count)return "";
 return text.substr(0,equals==std::string::npos ? 0 : equals+1)+"qbinaryfraction(vector("+entries+"),"+
        std::to_string(count-point)+",qbinarytail(\""+prefix+"\","+std::to_string(count+1)+"))";
}
// Display mathematics may end with a sentence period or comma. Preserve decimals,
// quoted labels, ellipses and dots following incomplete operators.
// Full-line comments occur in pasted display derivations. Keep inline
// remainder operators and escaped percentage signs in their original form.
std::string withoutTeXCommentLines(const std::string &s) {
 std::string result;
 for(size_t begin=0;begin<s.size();) {
  size_t end=s.find_first_of("\r\n",begin);
  if(end==std::string::npos)end=s.size();
  size_t first=begin;
  while(first<end && (s[first]==' ' || s[first]=='\t'))++first;
  if(first==end || s[first]!='%')result.append(s,begin,end-begin);
  if(end==s.size())break;
  result+=s[end];begin=end+1;
 }
 return result;
}
std::string booleanGraph(const std::string &outputs) {
 const int width=outputs.size()==2 ? 1 : 2;
 std::string result="qset(vector(";
 for(size_t index=0;index<outputs.size();++index) {
  if(index)result+=",";
  result+="qtuple(vector(qbitlabel("+std::to_string(index)+","+std::to_string(width)+"),"+outputs[index]+"))";
 }
 return result+"))";
}
std::string quantifiedPaulis(const std::string &clause) {
 // Match the quantifier as well as the algebra: removing a sign or changing
 // an index can change whether the statement is universally true.
 static const std::regex pair(R"re(([A-Z])_([a-z])\1_([a-z])=\1_\3\1_\2\\text\{\(forall\$\2,\3\\in\\\{1,\\ldots,([a-z])\\\}\$\)\})re");
 static const std::regex independent(R"re(([A-Z])_([a-z])\\notin\\langle\1_1,\\ldots,\1_\{\2-1\},\1_\{\2\+1\},\\ldots,\1_([a-z])\\rangle\\text\{\(forall\$\2\\in\\\{1,\\ldots,\3\\\}\$\)\})re");
 static const std::regex someAnti(R"re(([A-Z])_([a-z])([A-Z])=-\3\1_\2\\text\{foratleastone\}\2\\in\\\{1,\\ldots,([a-z])\\\})re");
 static const std::regex allCommute(R"re(([A-Z])([A-Z])_([a-z])=\2_\3\1\\text\{forevery\}\3\\in\\\{1,\\ldots,([a-z])\\\})re");
 static const std::regex signedMember(R"re(([A-Z])(=|\\neq)\\pm([A-Z])\\text\{(forsome|for)\}\3\\in\\langle([A-Z])_1,\\ldots,\5_([a-z])\\rangle)re");
 std::smatch m;
 auto family=[](const std::string &name,const std::string &bound) {return "qindexedentries(\""+name+"_\",1,"+bound+",vector())";};
 if(std::regex_match(clause,m,pair))return "qpairwisecommute("+family(m[1],m[4])+")";
 if(std::regex_match(clause,m,independent))return "qindependentpaulis("+family(m[1],m[3])+")";
 if(std::regex_match(clause,m,someAnti))return "qsomeanticommute("+family(m[1],m[4])+",\""+m[3].str()+"\")";
 if(std::regex_match(clause,m,allCommute))return "!(qsomeanticommute("+family(m[2],m[4])+",\""+m[1].str()+"\"))";
 if(std::regex_match(clause,m,signedMember)) {
  std::string member="qsignedpaulimember("+family(m[5],m[6])+",\""+m[1].str()+"\")";
  if(m[2]=="=" && m[4]=="forsome")return member;
  if(m[2]=="\\neq" && m[4]=="for")return "!("+member+")";
 }
 return "";
}
// In a standalone register declaration, sans-serif capital letters name
// systems. Preserve their names even when the same letters are Pauli gates.
std::string systemNames(const std::string &input) {
 if(input.find("\\mathsf")==std::string::npos)return "";
 if(input.find("\\ldots")!=std::string::npos || input.find("\\cdots")!=std::string::npos) {
  static const std::regex descending(R"(\s*\(\s*\\mathsf\{([A-Za-z])\}_([1-9])\s*,\s*\\mathsf\{\1\}_([0-9])\s*,\s*\\(?:ldots|cdots)\s*,\s*\\mathsf\{\1\}_0\s*\)\s*)");
  std::smatch match;
  if(std::regex_match(input,match,descending) && match[2].str()[0]==match[3].str()[0]+1)
   return "qreverseindexedlist(\""+match[1].str()+"_\",0,"+match[2].str()+",vector())";
 }
 // A subscript inside the typeface group names a wire; it is not a power,
 // gate application, or subscript on an already evaluated expression.
 if(input.find("_{")!=std::string::npos) {
  std::string wires=trim(input);
  if(wires.size()>1 && wires.front()=='(' && wires.back()==')')wires=trim(wires.substr(1,wires.size()-2));
  const std::string wire=R"(\\mathsf\{([A-Za-z])_\{([0-9]+|[A-Za-z](?:-1)?)\}\})";
  static const std::regex one(wire),range(wire+R"(\s*,\s*\\(?:ldots|cdots)\s*,\s*)"+wire);
  std::smatch match;
  if(std::regex_match(wires,match,one))
   return "qindexedlabel(\""+match[1].str()+"_\","+match[2].str()+",\"\")";
  if(std::regex_match(wires,match,range) && match[1].str()==match[3].str()) {
   const bool descending=match[4].str()=="0";
   if(descending || match[2].str()=="0") {
    const std::string op=descending ? "qreverseindexedlist" : "qindexedlist";
    return op+"(\""+match[1].str()+"_\",0,"+match[descending ? 2 : 4].str()+",vector())";
   }
  }
 }
 size_t at=0;
 auto space=[&]() {while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;};
 space();bool tuple=at<input.size() && input[at]=='(';
 if(tuple)++at;
 std::string result=tuple ? "tuple(" : "";
 do {
  space();
  if(input.compare(at,7,"\\mathsf")!=0)return "";
  at+=7;space();if(at==input.size() || input[at++]!='{')return "";
  space();if(at==input.size() || input[at]<'A' || input[at]>'Z')return "";
  std::string label(1,input[at++]);
  space();if(at==input.size() || input[at++]!='}')return "";
  result+="\""+label+"\"";space();
  if(!tuple || at==input.size() || input[at]!=',')break;
  ++at;result+=",";
 } while(true);
 if(tuple) {
  if(at==input.size() || input[at++]!=')' || result.find(',')==std::string::npos)return "";
  result+=")";space();
 }
 return at==input.size() ? result : "";
}
// Aligned rows can put separate equations on either side of an ampersand.
// A relation inside a function argument or a quoted name does not split a row.
bool completeAlignedEquation(const std::string &cell) {
 int nesting=0;char quote=0;
 for(size_t i=0;i<cell.size();++i) {
  char c=cell[i];
  if(quote) {if(c==quote)quote=0;continue;}
  if(c=='"' || c=='\'')quote=c;
  else if(c=='(' || c=='[')++nesting;
  else if(c==')' || c==']')--nesting;
  else if(!nesting && c=='=' && i && i+1<cell.size()) {
   const size_t lhs=cell.find_last_not_of(" \t\r\n<>=!",i-1);
   return lhs!=std::string::npos && cell.find_first_not_of(" \t\r\n=",i+1)!=std::string::npos;
  }
 }
 return false;
}
std::string withoutDisplayPunctuation(std::string value) {
 size_t mark=value.find_last_not_of(" \t\r\n");
 // Display spacing may follow the sentence comma inside a math span.
 while(mark!=std::string::npos && mark>1 && value[mark-1]=='\\' &&
       (value[mark]==';' || value[mark]==',' || value[mark]=='!'))
  mark=value.find_last_not_of(" \t\r\n",mark-2);
 if(mark==std::string::npos || mark==0 || (value[mark]!='.' && value[mark]!=','))return value;
 if(value[mark]=='.' && std::isdigit((unsigned char)value[mark-1])) {
  // An unbraced TeX superscript consumes one token. The following period
  // belongs to the sentence, while a number such as 1. keeps its decimal.
  size_t previous=mark>=2 ? value.find_last_not_of(" \t\r\n",mark-2) : std::string::npos;
  size_t digits=mark;
  while(digits && std::isdigit((unsigned char)value[digits-1]))--digits;
  bool hasRadix=digits && value[digits-1]=='.' && (digits==1 || value[digits-2]!='.');
  if(!hasRadix && (previous==std::string::npos || value[previous]!='^'))return value;
 }
 size_t before=value.find_last_not_of(" \t\r\n",mark-1);
 if(before==std::string::npos)return value;
 unsigned char end=value[before];
 if(end<128 && !std::isalnum(end) && end!=')' && end!=']' && end!='}' && end!='>' && end!='|' && end!='\'' && end!='"')return value;
 char quote=0;
 for(size_t k=0;k<mark;++k)if(value[k]=='\'' || value[k]=='"') {
  if(quote==value[k])quote=0;else if(!quote)quote=value[k];
 }
 if(!quote)value.erase(mark,1);
 return value;
}
// Fixed-width binary words in a complete function table retain leading zeros.
// Single-bit results are Boolean scalars; longer results are register labels.
std::string binaryFunctionGraph(const std::vector<std::string> &rows) {
 const size_t count=rows.size();
 if(count<4 || (count & (count-1)))return "";
 size_t width=0;
 for(size_t n=count;n>1;n/=2)++width;
 std::vector<std::string> outputs(count);
 size_t outputWidth=0;
 std::string function;
 for(const auto &row:rows) {
  size_t open=row.find('('),close=row.find(')'),equal=row.find('=');
  if(open==std::string::npos || close==std::string::npos || equal==std::string::npos ||
     open>=close || close>=equal || !trim(row.substr(close+1,equal-close-1)).empty())return "";
  std::string name=trim(row.substr(0,open)),bits=trim(row.substr(open+1,close-open-1)),value=trim(row.substr(equal+1));
  if(name=="e" || name=="i")return ""; // These are built-in scalar constants.
  if(name.size()!=1 || name[0]<'a' || name[0]>'z' || (!function.empty() && function!=name) ||
     bits.size()!=width || bits.find_first_not_of("01")!=std::string::npos || value.empty() || value.find_first_not_of("01")!=std::string::npos ||
     (outputWidth && value.size()!=outputWidth))return "";
  function=name;
  size_t index=0;
  for(char bit:bits)index=2*index+(bit-'0');
  if(!outputs[index].empty())return "";
  outputWidth=value.size();
  outputs[index]=outputWidth==1 ? value : "bitstring("+value+"_2,"+std::to_string(outputWidth)+")";
 }
 std::string graph="qset(vector(";
 for(size_t i=0;i<count;++i) {
  if(i)graph+=",";
  graph+="tuple(bitstring("+std::to_string(i)+","+std::to_string(width)+"),"+outputs[i]+")";
 }
 return graph+"))";
}
// A shared Hadamard acting on each indexed bit is a tensor power acting on
// the whole register. Recognize the complete contextual pattern before an
// isolated indexed ket becomes a named state. General tensor ellipses remain
// unsupported; the existing register owns bit, width and substitution checks.
std::string hadamardRegisterTensor(const std::string &input,size_t start,size_t &end) {
 size_t at=start;
 auto space=[&]() {while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;};
 auto token=[&](const std::string &text) {
  space();if(input.compare(at,text.size(),text)!=0)return false;
  const size_t next=at+text.size();
  if(text[0]=='\\' && next<input.size() && asciiLetter((unsigned char)input[next]))return false;
  at=next;return true;
 };
 auto factor=[&](std::string &family,std::string &index) {
  const bool sized=token("\\bigl");
  if(!token("(") || !token("H") || !token("\\vert"))return false;
  space();size_t begin=at;while(at<input.size() && asciiLetter((unsigned char)input[at]))++at;
  if(at==begin || at-begin>127)return false;
  family=input.substr(begin,at-begin);if(!token("_"))return false;
  space();if(at==input.size())return false;
  if(input[at]=='{') {
   ++at;while(at<input.size() && input[at]!='}') {
    if(!asciiSpace((unsigned char)input[at]))index+=input[at];
    if(index.size()>32)return false;++at;
   }
   if(at==input.size())return false;++at;
  } else if(input[at]>='0' && input[at]<='9')index+=input[at++];
  else return false;
  if(!token("\\rangle"))return false;
  if(sized && !token("\\bigr"))return false;
  return token(")");
 };
 std::string first,last,upper,lower;
 if(!factor(first,upper) || !token("\\otimes") || !token("\\cdots") || !token("\\otimes") || !factor(last,lower))return "";
 if(first!=last || lower!="0")return "";
 space();if(at<input.size() && input[at]!=')' && input[at]!='}' && input[at]!=',')return "";
 std::string width;
 if(upper.size()==3 && asciiLetter((unsigned char)upper[0]) && upper.substr(1)=="-1")width=upper.substr(0,1);
 else {
  // Concrete upper endpoints 0..9 denote one through ten indexed qubits.
  if(upper.size()!=1 || upper[0]<'0' || upper[0]>'9')return "";
  width=std::to_string(upper[0]-'0'+1);
 }
 end=at;
 return "(tensorpow(H,"+width+")*|"+first+"_("+upper+") ... "+first+"_0>)";
}
struct TensorSeriesPattern {
 std::string body,first,last,index,direction;
 size_t end=0;
};
// Compare corresponding endpoint factors, varying only scalar subscripts.
// Operators, coefficients, domains and fixed subscripts must agree. Keep the
// original first factor text for the ordinary TeX and lexical-binder parsers.
bool tensorSeriesPattern(const std::string &input,size_t start,TensorSeriesPattern &pattern) {
 size_t at=start;
 auto space=[&]() {while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;};
 auto token=[&](const std::string &text) {
  space();if(input.compare(at,text.size(),text)!=0)return false;
  size_t next=at+text.size();
  if(text[0]=='\\' && next<input.size() && asciiLetter((unsigned char)input[next]))return false;
  at=next;return true;
 };
 auto factor=[&](std::string &body) {
  space();
  for(const auto *size:{"\\left","\\bigl","\\Bigl","\\biggl","\\Biggl"})if(token(size))break;
  if(!token("("))return false;
  size_t begin=at;unsigned depth=1;char quote=0;
  while(at<input.size()) {
   char c=input[at++];
   if(c=='\'' || c=='"') {if(!quote)quote=c;else if(quote==c)quote=0;}
   if(quote)continue;
   if(c=='(')++depth;
   if(c==')' && --depth==0) {
    body=input.substr(begin,at-begin-1);
    for(const auto *size:{"\\right","\\bigr","\\Bigr","\\biggr","\\Biggr"}) {
     size_t end=body.find_last_not_of(" \t\r\n");
     std::string suffix=size;
     if(end!=std::string::npos && end+1>=suffix.size() && body.compare(end+1-suffix.size(),suffix.size(),suffix)==0) {
      body.resize(end+1-suffix.size());break;
     }
    }
    return true;
   }
  }
  return false;
 };
 std::string left,right;
 if(!factor(left) || !token("\\otimes") || !token("\\cdots") || !token("\\otimes") || !factor(right))return false;
 struct Subscript {size_t begin,end;std::string index;};
 auto subscripts=[](const std::string &text) {
  std::vector<Subscript> found;char quote=0;
  for(size_t k=0;k<text.size();++k) {
   if(text[k]=='\'' || text[k]=='"') {if(!quote)quote=text[k];else if(quote==text[k])quote=0;}
   if(quote || text[k]!='_')continue;
   size_t begin=k+1;while(begin<text.size() && asciiSpace((unsigned char)text[begin]))++begin;
   if(begin==text.size())continue;
   size_t end=begin;std::string index;
   if(text[begin]=='{') {
    unsigned depth=1;end=begin+1;
    while(end<text.size() && depth) {if(text[end]=='{')++depth;if(text[end]=='}')--depth;++end;}
    if(depth)continue;index=text.substr(begin+1,end-begin-2);
   } else {end=begin+1;index=text.substr(begin,1);}
   std::string compact;bool scalar=true;
   for(unsigned char c:index) {
    if(asciiSpace(c))continue;
    if(!std::isalnum(c) && c!='+' && c!='-' && c!='*' && c!='/' && c!='(' && c!=')')scalar=false;
    compact+=char(c);
   }
   if(scalar && !compact.empty()) {found.push_back({k,end,compact});k=end-1;}
  }
  return found;
 };
 auto canonical=[](const std::string &text) {
  std::string out;
  for(size_t k=0;k<text.size();++k) {
   if(asciiSpace((unsigned char)text[k]))continue;
   out+=text[k];
   if(text[k]=='\'' || text[k]=='"') {
    const char quote=text[k];
    while(k+1<text.size()) {out+=text[++k];if(text[k]==quote)break;}
   } else if(text[k]=='\\') {
    while(k+1<text.size() && asciiLetter((unsigned char)text[k+1]))out+=text[++k];
    out+='\x1f';
   } else if(std::isalnum((unsigned char)text[k]) || (unsigned char)text[k]>=128 || text[k]=='_') {
    while(k+1<text.size() && (std::isalnum((unsigned char)text[k+1]) || (unsigned char)text[k+1]>=128 || text[k+1]=='_'))out+=text[++k];
    out+='\x1f';
   }
  }
  return out;
 };
 auto a=subscripts(left),b=subscripts(right);
 if(a.empty() || a.size()!=b.size())return false;
 size_t previousA=0,previousB=0;std::vector<size_t> varying;
 for(size_t k=0;k<a.size();++k) {
  if(canonical(left.substr(previousA,a[k].begin-previousA))!=canonical(right.substr(previousB,b[k].begin-previousB)))return false;
  previousA=a[k].end;previousB=b[k].end;
  if(a[k].index==b[k].index)continue;
  if(varying.empty()) {pattern.first=a[k].index;pattern.last=b[k].index;}
  else if(pattern.first!=a[k].index || pattern.last!=b[k].index)return false;
  varying.push_back(k);
 }
 if(varying.empty() || canonical(left.substr(previousA))!=canonical(right.substr(previousB)))return false;
 auto decimal=[](const std::string &s) {return !s.empty() && s.find_first_not_of("0123456789")==std::string::npos;};
 if(decimal(pattern.first) && decimal(pattern.last)) {
  auto normalized=[](const std::string &s) {size_t first=s.find_first_not_of('0');return first==std::string::npos ? std::string("0") : s.substr(first);};
  std::string first=normalized(pattern.first),last=normalized(pattern.last);
  pattern.direction=(first.size()>last.size() || (first.size()==last.size() && first>last)) ? "-1" : "1";
 } else if(pattern.last=="0")pattern.direction="-1";
 else if(pattern.first=="0")pattern.direction="1";
 else return false; // Two unspecified endpoints do not establish direction.
 pattern.index="qseriesindex";
 while(input.find(pattern.index)!=std::string::npos)pattern.index+="q";
 pattern.body=left;
 for(auto k=varying.rbegin();k!=varying.rend();++k)
  pattern.body.replace(a[*k].begin,a[*k].end-a[*k].begin,"_{"+pattern.index+"}");
 pattern.end=at;return true;
}
// Recognize a complete scalar argument before ordinary subscript handling
// flattens its grouped upper endpoint. No general ellipsis token is enabled.
std::string indexedProduct(const std::string &input,size_t start,size_t &end) {
 size_t at=start;
 auto space=[&]() {while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;};
 auto token=[&](const std::string &text) {space();if(input.compare(at,text.size(),text)!=0)return false;at+=text.size();return true;};
 auto factor=[&](std::string &family,std::string &index) {
  space();size_t begin=at;while(at<input.size() && asciiLetter((unsigned char)input[at]))++at;
  if(at==begin || at-begin>127)return false;
  family=input.substr(begin,at-begin);if(!token("_"))return false;
  space();if(at==input.size())return false;
  if(input[at]=='{') {
   ++at;while(at<input.size() && input[at]!='}') {
    if(!asciiSpace((unsigned char)input[at]))index+=input[at];
    if(index.size()>32)return false;++at;
   }
   if(at==input.size())return false;++at;
  } else if(std::isalnum((unsigned char)input[at]))index+=input[at++];
  else return false;
  return !index.empty();
 };
 std::string first,second,lastFirst,lastSecond,upperA,upperB,lowerA,lowerB;
 if(!factor(first,upperA))return "";
 // Read a descending family of maps in application order: the map
 // with the lowest index acts first on the input column.
 size_t afterFirst=at;
 token("\\,");
 if(token("\\cdots")) {
  token("\\,");
  if(!factor(lastFirst,lowerA) || first!=lastFirst || lowerA!="1" ||
     first.size()!=1 || first[0]<'A' || first[0]>'Z')return "";
  if(!(upperA.size()==1 && asciiLetter(upperA[0])) &&
     (upperA[0]=='0' || upperA.find_first_not_of("0123456789")!=std::string::npos))return "";
  space();
  if(at<input.size() && input[at]=='.' && input.find_first_not_of(" \t\r\n",at+1)==std::string::npos)++at;
  if(at<input.size() && std::string(",)}=").find(input[at])==std::string::npos && !asciiSpace((unsigned char)input[at]))return "";
  end=at;
  return "qcomposemaps(qindexedentries(\""+first+"_\",1,"+upperA+",vector()))";
 }
 at=afterFirst;
 if(!factor(second,upperB) || !token("+") || !token("\\cdots") || !token("+") ||
    !factor(lastFirst,lowerA) || !factor(lastSecond,lowerB))return "";
 if(first!=lastFirst || second!=lastSecond || upperA!=upperB || lowerA!="0" || lowerB!="0")return "";
 space();if(at<input.size() && input[at]!=')' && input[at]!='}' && input[at]!=',')return "";
 std::string width;
 if(upperA.size()==3 && asciiLetter((unsigned char)upperA[0]) && upperA.substr(1)=="-1")width="\""+upperA.substr(0,1)+"\"";
 else {
  if(upperA.empty() || (upperA.size()>1 && upperA[0]=='0') || upperA.find_first_not_of("0123456789")!=std::string::npos)return "";
  // Decimal increment avoids converting an arbitrary-precision endpoint to a
  // machine integer merely to preserve the symbolic scalar-product width.
  width=upperA;size_t digit=width.size();
  while(digit && width[digit-1]=='9')width[--digit]='0';
  if(digit)++width[digit-1];else width.insert(width.begin(),'1');
 }
 end=at;return "qscalarproductsum(\""+first+"_\",\""+second+"_\","+width+",vector())";
}
// Infer only a contiguous, zero-based column family. Keep the raw subscript
// groups: flattening alpha_{n-1} first would confuse it with alpha_n - 1.
std::string indexedColumn(const std::string &raw, bool tex) {
 const std::string marker=tex ? "\\vdots" : "⋮", separator=tex ? "\\\\" : ";";
 std::vector<std::string> rows;
 size_t start=0;unsigned nesting=0;char quote=0;bool found=false;
 for(size_t i=0;i<raw.size();++i) {
  char c=raw[i];
  if(quote) {if(c==quote)quote=0;continue;}
  if(c=='\'' || c=='"') {quote=c;continue;}
  if(c=='(' || c=='[' || c=='{') {++nesting;continue;}
  if(c==')' || c==']' || c=='}') {if(nesting)--nesting;continue;}
  if(nesting)continue;
  if(raw.compare(i,marker.size(),marker)==0)found=true;
  if(raw.compare(i,separator.size(),separator)==0) {
   rows.push_back(trim(raw.substr(start,i-start)));i+=separator.size()-1;start=i+1;
  }
 }
 if(!found)return "";
 rows.push_back(trim(raw.substr(start)));
 // read() has already validated each optional TeX row-spacing dimension.
 // Remove that presentation suffix before checking the coefficient pattern.
 if(tex)for(size_t row=1;row<rows.size();++row)if(!rows[row].empty() && rows[row][0]=='[') {
  size_t close=rows[row].find(']');
  if(close!=std::string::npos)rows[row]=trim(rows[row].substr(close+1));
 }
 auto invalid=[]() {throw std::runtime_error("An indexed column requires consecutive entries starting at 0 or 1, a vertical ellipsis, and an endpoint in the same family; group compound subscripts");};
 if(rows.size()<3 || rows.size()>1027 || (rows[1]!=marker && rows[rows.size()-2]!=marker))invalid();
 if(rows[rows.size()-2]==marker && std::count(rows.begin(),rows.end(),"0")==int(rows.size()-1))
  return "qtexzerocolumn("+std::to_string(rows.size()-2)+")";
 const std::string dot=tex ? "\\cdot" : "·";
 if(rows.front().find(dot)!=std::string::npos) {
  auto malformed=[](){throw std::runtime_error("A sample dot-product column requires consecutive one-based samples and a common right operand");};
  if(rows[rows.size()-2]!=marker)malformed();
  std::string family,probe,last;
  for(size_t r=0;r<rows.size();++r) {
   if(r==rows.size()-2)continue;
   const std::string &entry=rows[r];size_t at=entry.find(dot);
   if(at==std::string::npos)malformed();
   std::string label=trim(entry.substr(0,at)),right=trim(entry.substr(at+dot.size()));
   if(label.size()<3 || label[0]<'a' || label[0]>'z' || label[1]!='^' || right.size()!=1 || !asciiLetter(right[0]))malformed();
   if(family.empty()) {family=label.substr(0,1);probe=right;}
   if(label[0]!=family[0] || probe!=right)malformed();
   std::string index=trim(label.substr(2));
   if(index.size()>=2 && ((index.front()=='{' && index.back()=='}') || (index.front()=='(' && index.back()==')')))index=trim(index.substr(1,index.size()-2));
   if(index.empty() || index.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-*/ ")!=std::string::npos)malformed();
   if(r+1<rows.size() && index!=std::to_string(r+1))malformed();
   last=index;
  }
  return "qsampledotcolumn(\""+family+"^\",("+last+"),"+probe+",vector(),"+std::to_string(rows.size()-2)+")";
 }
 std::string family;
 std::vector<std::string> indices;
 for(size_t row=0;row<rows.size();++row) {
  if(rows[row]==marker)continue;
  const std::string &entry=rows[row];size_t sub=entry.find('_');
  if(sub==std::string::npos || sub==0)invalid();
  std::string name=trim(entry.substr(0,sub)), index=trim(entry.substr(sub+1));
  if(name.empty())invalid();
  size_t first=tex && name[0]=='\\' ? 1 : 0;
  if(first==name.size())invalid();
  for(size_t i=first;i<name.size();++i)if((unsigned char)name[i]<128 && !asciiLetter(name[i]))invalid();
  if(family.empty())family=name;else if(family!=name)invalid();
  bool grouped=index.size()>=2 && ((index.front()=='{' && index.back()=='}') || (index.front()=='(' && index.back()==')'));
  if(grouped)index=trim(index.substr(1,index.size()-2));
  if(index.empty())invalid();
  // Endpoint arithmetic deliberately excludes separators, calls, and nested
  // subscripts: those require a more explicit indexed construction.
  for(unsigned char c:index)if(c<128 && !std::isalnum(c) && !asciiSpace(c) && ( !grouped || (c!='+' && c!='-' && c!='*' && c!='/')))invalid();
  indices.push_back(index);
 }
 if(indices.size()+1!=rows.size())invalid();
 bool descending=rows[1]==marker && indices.back()=="0" && !(rows[rows.size()-2]==marker && indices.front()=="0");
 if(descending)std::reverse(indices.begin(),indices.end());
 else if(rows[rows.size()-2]!=marker)invalid();
 const unsigned first=indices.front()=="1" && !descending ? 1 : 0;
 for(size_t i=0;i+1<indices.size();++i)if(indices[i]!=std::to_string(first+i))invalid();
 const char *operation=descending ? "qdescendingcolumn" : first ? "qonebasedcolumn" : "qindexedcolumn";
 return std::string(operation)+"(\""+quantumTeX(family)+"_\",("+indices.back()+"),"+std::to_string(first+rows.size()-3)+")";
}
// Split only at the current matrix level; commas in grouped paired indices
// and delimiters in quoted labels must not create extra cells.
std::vector<std::string> indexedParts(const std::string &raw,const std::string &separator) {
 std::vector<std::string> parts;size_t start=0;unsigned nesting=0;char quote=0;
 for(size_t i=0;i<raw.size();++i) {
  char c=raw[i];if(quote){if(c==quote)quote=0;continue;}
  if(c=='\'' || c=='"'){quote=c;continue;}
  if(c=='(' || c=='[' || c=='{'){++nesting;continue;}
  if(c==')' || c==']' || c=='}'){if(nesting)--nesting;continue;}
  if(!nesting && raw.compare(i,separator.size(),separator)==0) {
   parts.push_back(trim(raw.substr(start,i-start)));i+=separator.size()-1;start=i+1;
  }
 }
 parts.push_back(trim(raw.substr(start)));return parts;
}
std::string conjugateCoefficientRow(const std::string &raw) {
 if(raw.find("\\cdots")==std::string::npos || raw.find("\\overline{")==std::string::npos)return "";
 std::string column;
 for(const auto &cell:indexedParts(raw,"&")) {
  if(!column.empty())column+="\\\\";
  if(cell=="\\cdots")column+="\\vdots";
  else if(cell.compare(0,10,"\\overline{")==0 && cell.back()=='}')
   column+=cell.substr(10,cell.size()-11);
  else return "";
 }
 std::string values=indexedColumn(column,true);
 return values.empty() ? "" : "qdag(qcomplexcolumn("+values+"))";
}
std::string sampleArray(const std::vector<std::vector<std::string>> &cells,const std::string &horizontal,
                        const std::string &vertical,const std::string &diagonal,bool definitions) {
  const size_t height=cells.size(),width=cells[0].size();
  auto invalidSample=[](){throw std::runtime_error("A sample matrix requires consecutive one-based rows and matching bit columns ending at zero");};
  auto index=[](std::string text) {
   text=trim(text);
   if(text.size()>=2 && ((text.front()=='{' && text.back()=='}') || (text.front()=='(' && text.back()==')')))text=trim(text.substr(1,text.size()-2));
   return text;
  };
  std::string name,lastSample,highBit;
  if(width!=3)invalidSample();
  for(size_t r=0;r<height;++r) {
   if(cells[r].size()!=width)invalidSample();
   if(r==height-2) {
    if(cells[r][0]!=vertical || cells[r][1]!=diagonal || cells[r][2]!=vertical)invalidSample();
    continue;
   }
   if(cells[r][1]!=horizontal)invalidSample();
   std::string row;
   for(size_t c:{size_t(0),size_t(2)}) {
    const std::string &cell=cells[r][c];
    size_t sub=cell.find('_');
    if(cell.size()<5 || cell[0]<'a' || cell[0]>'z' || cell[1]!='^' || sub==std::string::npos || sub<3)invalidSample();
    if(name.empty())name=cell.substr(0,1);
    if(name[0]!=cell[0])invalidSample();
    std::string sample=index(cell.substr(2,sub-2)),bit=index(cell.substr(sub+1));
    auto scalarIndex=[](const std::string &s) {
     return !s.empty() && s.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-*/ ")==std::string::npos;
    };
    if(!scalarIndex(sample) || !scalarIndex(bit) || (!row.empty() && row!=sample))invalidSample();
    row=sample;
    if(c==0) {if(highBit.empty())highBit=bit;else if(highBit!=bit)invalidSample();}
    else if(bit!="0")invalidSample();
   }
   if(r<height-2 && row!=std::to_string(r+1))invalidSample();
   if(r==height-1)lastSample=row;
  }
  std::string args="(\""+name+"^\",("+lastSample+"),("+highBit+"),";
  return definitions ? "qsamplewordrows"+args+"vector(),"+std::to_string(height-2)+")" :
                       "qsamplebitmatrix"+args+std::to_string(height-2)+",0)";
}
std::string sampleWordDefinitions(const std::vector<std::string> &lines) {
 if(lines.size()<3 || lines[lines.size()-2]!="⋮" || lines[0].find("⋯")==std::string::npos)return "";
 std::vector<std::vector<std::string>> cells;
 for(const auto &line:lines) {
  if(line=="⋮") {cells.push_back({"⋮","⋱","⋮"});continue;}
  auto sides=indexedParts(line,"=");
  if(sides.size()!=2 || sides[0].size()<3 || sides[0][1]!='^')return "";
  auto bits=indexedParts(sides[1],"⋯");
  if(bits.size()!=2 || bits[0].compare(0,sides[0].size()+1,sides[0]+"_")!=0 ||
     bits[1].compare(0,sides[0].size()+1,sides[0]+"_")!=0)return "";
  cells.push_back({bits[0],"⋯",bits[1]});
 }
 return sampleArray(cells,"⋯","⋮","⋱",true);
}
std::string indexedLabelRange(const std::string &first,const std::string &last,const std::string &operation);
std::string indexedMatrix(const std::string &raw,bool tex) {
 const std::string horizontal=tex ? "\\cdots" : "⋯",vertical=tex ? "\\vdots" : "⋮",diagonal=tex ? "\\ddots" : "⋱";
 auto rows=indexedParts(raw,tex ? "\\\\" : ";");
 std::vector<std::vector<std::string>> cells;bool found=false;
 for(size_t r=0;r<rows.size();++r) {
  if(tex && r && !rows[r].empty() && rows[r][0]=='[') {
   size_t end=rows[r].find(']');if(end!=std::string::npos)rows[r]=trim(rows[r].substr(end+1));
  }
  cells.push_back(indexedParts(rows[r],tex ? "&" : ","));
  for(const auto &cell:cells.back())if(cell==diagonal)found=true;
 }
 if(!found)return "";
 auto invalid=[](){throw std::runtime_error("An indexed matrix requires contiguous zero-based paired indices and consistent horizontal, vertical and diagonal ellipses");};
 const size_t height=cells.size(),width=cells[0].size();
 if(height<3 || width<3 || height>1026 || width>1026)invalid();
 // All later block columns are either explicitly zero or independently unspecified.
 const std::string &fill=cells.front()[1];
 if(height==width && (fill=="0" || (tex && fill=="\\fbox{?}"))) {
  size_t sub=cells.front()[0].find('_');
  if(sub!=std::string::npos) {
   std::string prefix=cells.front()[0].substr(0,sub+1);
   for(size_t r=0;r<height;++r) {
    if(cells[r].size()!=width)invalid();
    for(size_t c=0;c<width;++c) {
     if(r==height-1 && c==0)continue;
     std::string expected=r==height-2 ? (c==width-2 ? diagonal : vertical) :
                          c==width-2 ? horizontal : c==0 ? prefix+std::to_string(r) : fill;
     if(cells[r][c]!=expected)invalid();
    }
   }
   if(cells.back()[0].compare(0,prefix.size(),prefix)!=0)invalid();
   std::string name=quantumTeX(prefix.substr(0,sub))+"_";
   std::string family=indexedLabelRange(name+"0",name+cells.back()[0].substr(prefix.size()),"qindexedentries(");
   if(family.empty())invalid();
   return std::string(fill=="0" ? "qblockcolumn(" : "qopenblockcolumn(")+family+","+std::to_string(height-2)+")";
  }
 }
 // A superscript names the one-based sample row. Subscripts label the
 // bits of that sample in descending order, with zero at the right.
 if(cells[0][0].find('^')!=std::string::npos) {
  return sampleArray(cells,horizontal,vertical,diagonal,false);
 }
 std::string family,lastRow,lastColumn;
 for(size_t r=0;r<height;++r) {
  if(cells[r].size()!=width)invalid();
  for(size_t c=0;c<width;++c) {
   const std::string &cell=cells[r][c];
   if(r==height-2 || c==width-2) {
    if(cell!=(r==height-2 ? (c==width-2 ? diagonal : vertical) : horizontal))invalid();
    continue;
   }
   size_t sub=cell.find('_');if(sub==std::string::npos || !sub)invalid();
   std::string name=trim(cell.substr(0,sub)),indices=trim(cell.substr(sub+1));
   if(name.empty() || indices.size()<3 || !((indices.front()=='{' && indices.back()=='}') || (indices.front()=='(' && indices.back()==')')))invalid();
   size_t first=tex && name[0]=='\\' ? 1 : 0;if(first==name.size())invalid();
   for(size_t i=first;i<name.size();++i)if((unsigned char)name[i]<128 && !asciiLetter(name[i]))invalid();
   if(family.empty())family=name;else if(family!=name)invalid();
   auto pair=indexedParts(indices.substr(1,indices.size()-2),",");if(pair.size()!=2)invalid();
   for(auto &index:pair) {
    std::string compact;
    for(unsigned char ch:index) {
     if(asciiSpace(ch)) {compact+=ch;continue;}
     if(ch<128 && !std::isalnum(ch) && ch!='+' && ch!='-' && ch!='*' && ch!='/')invalid();
     compact+=ch;
    }
    if(compact.empty())invalid();index=compact;
   }
   if(r<height-2) {if(pair[0]!=std::to_string(r))invalid();}
   else {if(lastRow.empty())lastRow=pair[0];else if(lastRow!=pair[0])invalid();}
   if(c<width-2) {if(pair[1]!=std::to_string(c))invalid();}
   else {if(lastColumn.empty())lastColumn=pair[1];else if(lastColumn!=pair[1])invalid();}
  }
 }
 return "qindexedmatrix(\""+quantumTeX(family)+"_\",("+lastRow+"),("+lastColumn+"),"+std::to_string(height-3)+","+std::to_string(width-3)+")";
}
bool registerSumDeclaration(const std::string &variable,const std::string &domain,
                            std::string &prefix,std::string &first,std::string &last,
                            std::string &alphabet,std::string &width) {
 size_t dots=variable.find("...");
 if(dots==std::string::npos || variable.find("...",dots+3)!=std::string::npos)return false;
 auto endpoint=[&](std::string text,std::string &index) {
  text=trim(text);size_t mark=text.find('_');
  if(mark==std::string::npos || !mark)return false;
  std::string name=text.substr(0,mark+1);
  for(size_t k=0;k<mark;++k)if(!asciiLetter((unsigned char)name[k]))return false;
  if(!prefix.empty() && prefix!=name)return false;prefix=name;
  index=trim(text.substr(mark+1));
  if(index.size()>1 && ((index.front()=='{' && index.back()=='}') || (index.front()=='(' && index.back()==')')))
   index=trim(index.substr(1,index.size()-2));
  return !index.empty();
 };
 if(!endpoint(variable.substr(0,dots),first) || !endpoint(variable.substr(dots+3),last))return false;
 // Require a single Cartesian-power spelling. Ungrouped additions outside
 // the power must not silently become part of its alphabet or exponent.
 std::string text=trim(domain);size_t power=std::string::npos;unsigned depth=0;
 for(size_t k=0;k<text.size();++k) {
  if(text[k]=='(' || text[k]=='[' || text[k]=='{')++depth;
  else if(text[k]==')' || text[k]==']' || text[k]=='}') {if(!depth)return false;--depth;}
  else if(text[k]=='^' && !depth) {if(power!=std::string::npos)return false;power=k;}
 }
 if(depth || power==std::string::npos)return false;
 auto atom=[](const std::string &s) {
  if(s.empty())return false;
  unsigned depth=0;
  for(size_t k=0;k<s.size();++k) {
   unsigned char c=s[k];
   if(c=='(' || c=='[' || c=='{')++depth;
   else if(c==')' || c==']' || c=='}') {if(!depth)return false;--depth;if(!depth && k+1!=s.size())return false;}
   else if(!depth && c<128 && !std::isalnum(c) && c!='_' && c!='.')return false;
  }
  return depth==0;
 };
 alphabet=trim(text.substr(0,power));width=trim(text.substr(power+1));
 return atom(alphabet) && atom(width);
}
void nextDecimalIndex(std::string &index) {
 size_t pos=index.find_last_not_of('9');
 if(pos==std::string::npos)index="1"+std::string(index.size(),'0');
 else {++index[pos];std::fill(index.begin()+pos+1,index.end(),'0');}
}
// Open-ended families need a common label and consecutive integer subscripts.
// Keep only the first index; a trailing comma after the ellipsis is typography.
// A standalone list with two or more consecutive printed indices is ordered.
std::string explicitIntegerList(const std::string &expression) {
 if(expression.find("...")==std::string::npos)return "";
 std::vector<std::string> entries;
 size_t at=0;
 while(at<expression.size()) {
  size_t comma=expression.find(',',at);
  entries.push_back(trim(expression.substr(at,comma==std::string::npos ? comma : comma-at)));
  if(comma==std::string::npos)break;
  at=comma+1;
 }
 if(entries.size()<4 || entries[entries.size()-2]!="...")return "";
 for(size_t k=0;k<entries.size();++k) {
  if(k==entries.size()-2)continue;
  const auto &entry=entries[k];
  if(entry.empty() || entry.find_first_not_of("0123456789")!=std::string::npos || (entry.size()>1 && entry[0]=='0'))return "";
 }
 std::string value=entries.front();
 for(size_t k=1;k+2<entries.size();++k) {
  nextDecimalIndex(value);
  if(value!=entries[k])throw std::runtime_error("An integer list requires consecutive prefix values");
 }
 const auto &last=entries.back();
 if(value.size()>last.size() || (value.size()==last.size() && value>last))throw std::runtime_error("Integer list endpoint precedes its prefix");
 return "qindexsequence("+entries.front()+","+last+")";
}
std::string openIndexedFamily(const std::vector<std::string> &entries) {
 size_t end=entries.size();
 if(end && entries[end-1].empty())--end;
 if(end<3 || (entries[end-1]!="..." && entries[end-1]!="…"))return "";
 const std::string &first=entries.front();
 size_t split=first.rfind('_');
 if(split==std::string::npos || split==0 || !std::all_of(first.begin(),first.begin()+split,asciiLetter))return "";
 std::string prefix=first.substr(0,split+1),start=first.substr(split+1),index=start;
 if(start.empty() || start.find_first_not_of("0123456789")!=std::string::npos || (start.size()>1 && start[0]=='0'))return "";
 for(size_t k=0;k+1<end;++k) {
  if(entries[k]!=prefix+index)return "";
  nextDecimalIndex(index);
 }
 return "qindexedfamily(\""+prefix+"\","+start+")";
}
std::string indexedLabelRange(const std::string &first,const std::string &last,const std::string &operation) {
 size_t split=first.rfind('_');
 if(split==std::string::npos || split==0)return "";
 std::string prefix=first.substr(0,split+1);
 if(last.compare(0,prefix.size(),prefix)!=0)return "";
 for(size_t k=0;k<split;++k)if((unsigned char)prefix[k]<128 && !asciiLetter(prefix[k]))return "";
 std::string from=first.substr(split+1),to=last.substr(split+1);
 auto integer=[](const std::string &s){return !s.empty() && s.find_first_not_of("0123456789")==std::string::npos && (s.size()==1 || s.front()!='0');};
 // Grouped offsets belong to the index. Ungrouped arithmetic does not.
 auto endpoint=[&](std::string &value) {
  if(value.size()<3 || value.front()!='{' || value.back()!='}')
   return integer(value) || (value.size()==1 && asciiLetter(value.front()));
  std::string bound=trim(value.substr(1,value.size()-2));
  if(bound.empty() || !asciiLetter(bound.front()))return false;
  std::string offset=trim(bound.substr(1));
  if(offset.empty() || (offset.front()!='+' && offset.front()!='-'))return false;
  std::string magnitude=trim(offset.substr(1));
  if(!integer(magnitude))return false;
  value=bound.substr(0,1)+offset.front()+magnitude;return true;
 };
 if(!endpoint(from) || !endpoint(to))return "";
 return operation+"\""+prefix+"\","+from+","+to+",vector())";
}
// A finite family of kets uses the same prefix at both endpoints.
std::string indexedKets(const std::vector<std::string> &entries,bool ordered) {
 auto label=[](const std::string &entry) {
  return entry.size()>2 && entry.front()=='|' && entry.back()=='>' ? trim(entry.substr(1,entry.size()-2)) : std::string();
 };
 if(entries.size()==4 && entries[2]=="...") {
  std::string first=label(entries[0]),second=label(entries[1]);
  size_t split=first.rfind('_');
  if(split==std::string::npos)return "";
  std::string index=first.substr(split+1);
  if(index.empty() || index.find_first_not_of("0123456789")!=std::string::npos)return "";
  nextDecimalIndex(index);
  if(second!=first.substr(0,split+1)+index)return "";
  return indexedKets({entries[0],entries[2],entries[3]},ordered);
 }
 if(entries.size()!=3 || entries[1]!="...")return "";
 std::string first=label(entries.front()),last=label(entries.back());
 const std::string basis=ordered ? "qbasiskets(" : "qbasisketset(";
 if(first.size()>1 && first.find_first_not_of("0")==std::string::npos &&
    last.size()==first.size() && last.find_first_not_of("1")==std::string::npos)
  return basis+"2^"+std::to_string(first.size())+")";
 if(first=="0" && last.size()>1 && last.find_first_not_of("01")==std::string::npos)
  throw std::runtime_error("Binary ket list endpoints must specify matching register widths.");
 if(first=="0") {
  if(!last.empty() && last.find_first_not_of("0123456789")==std::string::npos && (last.size()==1 || last[0]!='0'))
   return basis+"("+last+")+1)";
  if(!last.empty() && asciiLetter(last[0])) {
   std::string offset=trim(last.substr(1));
   if(!offset.empty() && offset[0]=='-' && trim(offset.substr(1))=="1")return basis+last.substr(0,1)+")";
  }
 }
 return indexedLabelRange(first,last,ordered ? "qindexedketlist(" : "qindexedketset(");
}
std::string orderedKetList(const std::string &text) {
 return text.find("...")==std::string::npos ? "" : indexedKets(indexedParts(text,","),true);
}
class TeXReader {
 const std::string &input;
 size_t pos=0;
 unsigned depth=0;
 std::string rootAlignment;
 std::vector<std::string> rootLines;
 bool setBound=false;
 bool stateLabel=false;
 std::string stateArgument() {bool previous=stateLabel;stateLabel=true;auto value=argument();stateLabel=previous;return value;}
 std::string stateGroup() {bool previous=stateLabel;stateLabel=true;auto value=group();stateLabel=previous;return value;}
 unsigned setDepth=0;
 // The state is supplied by the surrounding lesson. Keep its distribution
 // as a free name until the caller supplies the probabilities.
 std::string eventProbability() {
  size_t at=pos;
  auto space=[&]() {while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;};
  auto take=[&](const std::string &token) {
   space();if(input.compare(at,token.size(),token)!=0)return false;
   at+=token.size();return true;
  };
  std::string closingSize;
  static const std::pair<const char *,const char *> sizes[]={{"\\left","\\right"},{"\\bigl","\\bigr"},{"\\Bigl","\\Bigr"},{"\\biggl","\\biggr"},{"\\Biggl","\\Biggr"}};
  for(const auto &size:sizes) {
   if(take(size.first)) {closingSize=size.second;break;}
  }
  if(!take("("))return "";
  std::string distribution;
  bool prose=take("\\text");
  if(prose) {
   if(!take("{") || !take("outcome") || at==input.size() || !asciiSpace((unsigned char)input[at]) ||
      !take("is") || at==input.size() || !asciiSpace((unsigned char)input[at]))return "";
   distribution="measurement probabilities";
  } else {
   if(!take("\\mathsf") || !take("{"))return "";
   space();size_t begin=at;
   while(at<input.size() && asciiLetter(input[at]))++at;
   if(at==begin)return "";
   distribution=input.substr(begin,at-begin);
   if(!take("}") || !take("="))return "";
  }
  bool inlineMath=prose && take("$");
  space();size_t first=at;
  std::string outcome;
  if(inlineMath && at<input.size() && asciiLetter(input[at])) {
   outcome="\""+input.substr(at++,1)+"\"";
  } else {
   while(at<input.size() && std::isdigit((unsigned char)input[at]))++at;
   if(at==first || (at>first+1 && input[first]=='0'))return "";
   outcome=input.substr(first,at-first);
  }
  if(inlineMath && !take("$"))return "";
  if((prose && !take("}")) || (!closingSize.empty() && !take(closingSize)) || !take(")"))return "";
  pos=at;return "qeventprob(\""+distribution+"\","+outcome+")";
 }
 bool beforeMembership() const {
  size_t next=input.find_first_not_of(" \t\r\n",pos);
  if(next==std::string::npos)return false;
  for(const std::string op:{"\\in","\\notin","∈","∉"}) {
   if(input.compare(next,op.size(),op)!=0)continue;
   size_t end=next+op.size();
   if(op[0]!='\\' || end==input.size() || !asciiLetter(input[end]))return true;
  }
  return false;
 }
 bool wholeSetEntry(const std::string *preceding) const {
  if(!setDepth || depth!=setDepth || !preceding)return false;
  const size_t last=preceding->find_last_not_of(" \t\r\n");
  if(last!=std::string::npos && (*preceding)[last]!=',')return false;
  const size_t next=input.find_first_not_of(" \t\r\n",pos);
  return next!=std::string::npos && (input[next]==',' || input[next]=='}' || input.compare(next,2,"\\}")==0);
 }
 unsigned matrixDepth=0,alignmentDepth=0;
 void space() { while(pos<input.size() && asciiSpace((unsigned char)input[pos])) ++pos; }
 // Check the displayed initial powers and the final base before consuming
 // an ellipsis. Keep the endpoint expression available for substitution.
 std::string geometricSum() {
  size_t at=pos;
  auto token=[&](const std::string &s) {
   while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;
   if(input.compare(at,s.size(),s)!=0)return false;
   at+=s.size();return true;
  };
  if(!token("1") || !token("+"))return "";
  while(at<input.size() && asciiSpace((unsigned char)input[at]))++at;
  size_t first=at;
  if(at<input.size() && input[at]=='\\') {
   ++at;size_t name=at;while(at<input.size() && asciiLetter(input[at]))++at;
   if(name==at)return "";
  } else if(at<input.size() && asciiLetter(input[at]))++at;
  else if(at<input.size() && std::isdigit((unsigned char)input[at]))
   while(at<input.size() && std::isdigit((unsigned char)input[at]))++at;
  else return "";
  const std::string base=input.substr(first,at-first);
  if(!token("+") || !token(base) || !token("^") || !(token("2") || token("{2}")) ||
     !token("+") || !(token("\\cdots") || token("\\ldots") || token("\\dots") || token("⋯") || token("…")) ||
     !token("+") || !token(base) || !token("^"))return "";
  size_t start=pos;pos=at;
  std::string exponent=argument();
  space();
  if(pos<input.size() && std::string("=,;)}]").find(input[pos])==std::string::npos) {pos=start;return "";}
  return "qgeometricsum("+TeXReader(base).run(nullptr)+",("+exponent+")+1)";
 }
 std::string error(const std::string &message) const { return message+" at byte "+std::to_string(pos+1); }
 // Spacing takes a literal dimension. Its contents never become expression tokens.
 void spacingDimension(char close) {
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
  if(!digit)throw std::runtime_error(error("TeX spacing requires a literal numeric dimension"));
  space();size_t unitStart=pos;
  while(pos<input.size() && asciiLetter((unsigned char)input[pos]))++pos;
  std::string unit=input.substr(unitStart,pos-unitStart);
  if(unit!="pt" && unit!="pc" && unit!="in" && unit!="bp" && unit!="cm" && unit!="mm" &&
     unit!="dd" && unit!="cc" && unit!="sp" && unit!="em" && unit!="ex" && unit!="mu")
   throw std::runtime_error(error("Unsupported TeX spacing unit"));
  space();if(pos==input.size() || input[pos]!=close)throw std::runtime_error(error("Invalid TeX spacing"));
  ++pos;
 }
 // Match only the text label that introduces a parenthesized modulus.
 bool takeModulusLabel(bool congruence) {
  size_t start=pos;
  space();
  size_t length=0;
  if(congruence && input.compare(pos,7,"\\textrm")==0)length=7;
  else if(congruence && input.compare(pos,7,"\\mathrm")==0)length=7;
  else if(input.compare(pos,5,"\\text")==0)length=5;
  if(length) {
   pos+=length;space();
   if(pos<input.size() && input[pos]=='{') {
    ++pos;space();
    if(input.compare(pos,3,"mod")==0) {
     pos+=3;space();
     if(pos<input.size() && input[pos]=='}') {++pos;return true;}
    }
   }
  }
  pos=start;return false;
 }
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
 std::string nameGroup(bool columnSpec=false) {
  space(); if(pos==input.size() || input[pos++]!='{') throw std::runtime_error(error("Expected {name}"));
  size_t start=pos;
  while(pos<input.size() && input[pos]!='}') {
   if(!std::isalnum((unsigned char)input[pos]) && input[pos]!='*' && !(columnSpec && input[pos]=='|')) throw std::runtime_error(error("Invalid TeX name"));
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
 std::string setLiteral(bool escaped) {
  const unsigned outerSet=setDepth;
  setDepth=depth+1;
  std::string contents=read(escaped ? 0 : '}',false,"",escaped);
  setDepth=outerSet;
  size_t membership=std::string::npos,separator=std::string::npos,startEntry=0;int nesting=0;char quote=0;
  std::vector<std::string> entries;
  for(size_t j=0;j<contents.size();++j) {
   char token=contents[j];if(quote){if(token==quote)quote=0;continue;}
   if(token=='"' || token=='\''){quote=token;continue;}
   if(token=='(' || token=='[')++nesting;else if(token==')' || token==']')--nesting;
   else if(!nesting && token==',') {entries.push_back(trim(contents.substr(startEntry,j-startEntry)));startEntry=j+1;}
   else if(!nesting && (separator==std::string::npos || membership==std::string::npos) && contents.compare(j,3,"∈")==0) {
    if(membership!=std::string::npos)throw std::runtime_error(error("A set builder requires one index membership"));membership=j;
   } else if(!nesting && token==':') {
    if(separator!=std::string::npos)throw std::runtime_error(error("A set builder requires one predicate separator"));separator=j;
   }
  }
  if(membership==std::string::npos && separator==std::string::npos) {
   entries.push_back(trim(contents.substr(startEntry)));
   bool ellipsis=false;for(const auto &entry:entries)if(entry=="...")ellipsis=true;
   std::string alphabet="vector("+contents+")";
   if(ellipsis) {
    alphabet=openIndexedFamily(entries);
    if(alphabet.empty())alphabet=indexedKets(entries,false);
    if(alphabet.empty() && entries.size()==3 && entries[1]=="...")alphabet=indexedLabelRange(entries.front(),entries.back(),"qindexedset(");
    if(alphabet.empty()) {
     if(entries.size()<3 || entries[entries.size()-2]!="..." || entries.front().empty() || entries.back().empty() ||
        entries.front()=="..." || entries.back()=="...")throw std::runtime_error(error("Expected endpoints for an ascending integer range"));
     if(entries.size()>3) {
      std::string index=entries.front();
      if(index.find_first_not_of("0123456789")!=std::string::npos || (index.size()>1 && index.front()=='0'))
       throw std::runtime_error(error("An explicit range prefix must contain consecutive nonnegative integers"));
      for(size_t i=1;i+2<entries.size();++i) {
       nextDecimalIndex(index);
       if(entries[i]!=index)throw std::runtime_error(error("An explicit range prefix must contain consecutive integers"));
      }
      const std::string &end=entries.back();
      if(end.find_first_not_of("0123456789")==std::string::npos &&
         (end.size()<index.size() || (end.size()==index.size() && end<index)))
       throw std::runtime_error(error("Range endpoint precedes its explicit prefix"));
     }
     alphabet="qindexrange("+entries.front()+","+entries.back()+")";
    }
   } else if(entries.size()==2 && entries[0].size()>3 && entries[0].compare(entries[0].size()-3,3,"...")==0) {
    std::string range=indexedLabelRange(trim(entries[0].substr(0,entries[0].size()-3)),entries[1],"qindexedset(");
    if(!range.empty()) {alphabet=range;ellipsis=true;}
   }
   size_t afterSet=pos;space();
   if(pos<input.size() && input[pos]=='^') {
    bool zero=false,one=false,binary=true;
    for(const auto &entry:entries) {if(entry=="0")zero=true;else if(entry=="1")one=true;else binary=false;}
    ++pos;std::string count=argument();
    if(binary && zero && one)return "qbitstrings("+count+")";
    return "qcartesianpower("+alphabet+","+count+")";
   }
   pos=afterSet;
   if(ellipsis)return alphabet;
   return "qset(vector("+contents+"))";
  }
  if(membership!=std::string::npos && separator!=std::string::npos && separator<membership) {
   std::string body=trim(contents.substr(0,separator)),index=trim(contents.substr(separator+1,membership-separator-1)),collection=trim(contents.substr(membership+3));
   if(body.empty() || index.empty() || collection.empty() || std::isdigit((unsigned char)index[0]))throw std::runtime_error(error("An indexed image requires an expression, index and domain"));
   for(unsigned char ch:index)if(ch<128 && !std::isalnum(ch) && ch!='_')throw std::runtime_error(error("An indexed image requires a symbol index"));
   auto domains=indexedParts(collection,",");
   if(domains.size()==2) {
    size_t second=domains[1].find("∈");
    if(second!=std::string::npos) {
     std::string other=trim(domains[1].substr(0,second)),product=body;
     product.erase(std::remove_if(product.begin(),product.end(),asciiSpace),product.end());
     auto values=[](std::string set) {
      set=trim(set);const std::string prefix="qset(vector(";
      if(set.size()<=prefix.size()+2 || set.compare(0,prefix.size(),prefix)!=0 || set.substr(set.size()-2)!="))")
       return std::vector<std::string>{};
      return indexedParts(set.substr(prefix.size(),set.size()-prefix.size()-2),",");
     };
     auto left=values(domains[0]),right=values(domains[1].substr(second+3));
     if(product==index+other && !other.empty() && !left.empty() && !right.empty() && left.size()<=1024/right.size()) {
      bool paulis=std::any_of(right.begin(),right.end(),[](const std::string &e){return trim(e)=="X";}) &&
                  std::all_of(right.begin(),right.end(),[](const std::string &e){std::string p=trim(e);return p=="qimplicitidentity()" || p=="X" || p=="Y" || p=="Z";});
      std::string terms;
      for(const auto &x:left)for(const auto &y:right) {
       if(!terms.empty())terms+=",";
       terms+="("+x+")*("+((paulis && trim(y)=="qimplicitidentity()") ? "I" : y)+")";
      }
      return "qset(vector("+terms+"))";
     }
    }
   }
   return "qsetimage("+body+","+collection+","+index+")";
  }
  if(membership==std::string::npos || separator==std::string::npos)throw std::runtime_error(error("Use an index, finite collection and predicate in a set builder"));
  std::string index=trim(contents.substr(0,membership)),collection=trim(contents.substr(membership+3,separator-membership-3)),predicate=trim(contents.substr(separator+1));
  if(index.empty() || std::isdigit((unsigned char)index[0]) || collection.empty() || predicate.empty())throw std::runtime_error(error("A set builder requires an index, collection and predicate"));
  for(unsigned char ch:index)if(ch<128 && !std::isalnum(ch) && ch!='_')throw std::runtime_error(error("A set builder requires a symbol index"));
  return "qsetfilter("+predicate+","+collection+","+index+")";
 }
 // A horizontal rule separates column labels from reported numeric data.
 std::string numericTable(bool allowWrapper=true) {
  std::string alignment=nameGroup(true);
  alignment.erase(std::remove(alignment.begin(),alignment.end(),'|'),alignment.end());
  if(alignment.empty() || alignment.find_first_not_of("lcr")!=std::string::npos)
   throw std::runtime_error(error("A numeric table requires l, c or r for each column"));
  const std::string endMarker="\\end{array}";
  space();
  if(allowWrapper && alignment.size()==1 && input.compare(pos,13,"\\begin{array}")==0) {
   pos+=13;std::string nested=numericTable(false);space();
   while(input.compare(pos,2,"\\\\")==0){pos+=2;space();}
   if(input.compare(pos,endMarker.size(),endMarker)!=0)throw std::runtime_error(error("Expected the end of the single-cell table"));
   pos+=endMarker.size();return nested;
  }
  const size_t end=input.find(endMarker,pos);
  if(end==std::string::npos)throw std::runtime_error(error("Unclosed numeric table"));
  if(input[pos]=='&' && input.find("\\otimes",pos)<end) {
   std::string cells;unsigned count=0;
   bool matched=true;
   static const std::regex tensorWord(R"(\s*(?:[IXYZ]|\\mathbb\{I\})(?:\s*\\otimes\s*(?:[IXYZ]|\\mathbb\{I\}))*\s*)");
   for(auto row:indexedParts(input.substr(pos,end-pos),"\\\\")) {
    row=trim(row);if(row.compare(0,6,"\\hline")==0)row=trim(row.substr(6));
    if(row.empty())continue;
    auto columns=indexedParts(row,"&");if(columns.size()!=alignment.size()) {matched=false;break;}
    for(size_t j=0;j<columns.size();++j) {
     std::string entry=trim(columns[j]);
     if(!count && !j && entry.empty())entry="qoutcome(\"syndrome\")";
     else if(!count || !j) {
      if(!std::regex_match(entry,tensorWord)) {matched=false;break;}
      size_t at=0;while((at=entry.find("\\mathbb{I}",at))!=std::string::npos)entry.replace(at,10," I ");
      entry=quantumTeX(entry);
     } else if(entry!="+1" && entry!="1" && entry!="-1") {matched=false;break;}
     if(!cells.empty())cells+=",";
     cells+=entry;
    }
    if(!matched)break;
    ++count;
   }
   if(matched && count>1) {
    pos=end+endMarker.size();
    return "matrix("+std::to_string(count)+","+std::to_string(alignment.size())+",vector("+cells+"))";
   }
  }
  // Each row of a stabilizer generator table is an ordered tensor word.
  // Preserve it in the compact Pauli representation used by rank and distance.
  if(alignment.size()>=2 && alignment.size()<=25) {
   std::string generators;size_t width=0;
   bool matched=true;
   for(auto row:indexedParts(input.substr(pos,end-pos),"\\\\")) {
    row=trim(row);
    if(row.empty())continue;
    if(row.front()=='[') {
     static const std::regex spacing(R"(^\[\s*-?[0-9]+(?:\.[0-9]+)?\s*(?:mm|cm|pt|em|ex)\s*\])");
     std::smatch match;if(!std::regex_search(row,match,spacing)) {matched=false;break;}
     row=trim(row.substr(match.length()));
     if(row.empty())continue;
    }
    auto entries=indexedParts(row,"&");
    if(!width)width=entries.size();
    if(entries.size()!=width || width<2 || width>25) {matched=false;break;}
    unsigned x=0,z=0,phase=0;
    for(auto gate:entries) {
     gate=trim(gate);
     if(gate=="\\mathbb{I}")gate="I";
     if(gate.size()!=1 || gate.find_first_not_of("IXYZ")!=std::string::npos) {matched=false;break;}
     x=2*x+(gate=="X" || gate=="Y");
     z=2*z+(gate=="Z" || gate=="Y");
     if(gate=="Y")phase=(phase+3)%4;
    }
    if(!matched)break;
    if(!generators.empty())generators+=",";
    generators+="qcompactpauli("+std::to_string(entries.size())+","+std::to_string(x)+","+std::to_string(z)+","+std::to_string(phase)+")";
   }
   if(matched && !generators.empty()) {pos=end+endMarker.size();return "vector("+generators+")";}
  }
  if(alignment.size()==3) {
   auto lines=indexedParts(input.substr(pos,end-pos),"\\\\");
   auto heading=indexedParts(lines.front(),"&");
   if(heading==std::vector<std::string>{"(x,y)","\\text{win}","\\text{lose}"}) {
    if(lines.size()!=5)throw std::runtime_error(error("A two-bit game table needs four input pairs"));
    std::string entries="\"(x,y)\",\"win\",\"lose\"";bool seen[4]={};
    static const std::regex pair(R"(\(\s*([01])\s*,\s*([01])\s*\))");
    for(size_t row=1;row<lines.size();++row) {
     std::string line=lines[row];
     if(!line.empty() && line.front()=='[') {
      size_t saved=pos;pos=input.find(line,pos);size_t at=pos;spacingDimension(']');
      line=trim(line.substr(pos-at));pos=saved;
     }
     if(line.compare(0,6,"\\hline")==0)line=trim(line.substr(6));
     static const std::regex strut(R"(^\\rule\{0(?:mm|pt)\}\{[0-9]+(?:mm|pt)\})");
     line=std::regex_replace(line,strut,"");
     auto cells=indexedParts(line,"&");std::smatch match;
     if(cells.size()!=3 || !std::regex_match(cells[0],match,pair))throw std::runtime_error(error("Invalid game table input"));
     int index=2*(match[1].str()[0]-'0')+match[2].str()[0]-'0';
     if(seen[index])throw std::runtime_error(error("Repeated game table input"));seen[index]=true;
     entries+=",qtuple(vector("+match[1].str()+","+match[2].str()+"))";
     for(size_t col=1;col<=2;++col) {
      if(cells[col]=="a = b")entries+=",qcompare(a,b,4)";
      else if(cells[col]=="a \\neq b")entries+=",qcompare(a,b,5)";
      else throw std::runtime_error(error("Expected a relation between the game outputs"));
     }
    }
    pos=end+endMarker.size();return "matrix(5,3,vector("+entries+"))";
   }
  }
  if(alignment.size()==2) {
   auto lines=indexedParts(input.substr(pos,end-pos),"\\\\");
   auto heading=indexedParts(lines.front(),"&");
   if(heading.size()==2 && (heading[0]=="a" || heading[0]=="ab") &&
      (heading[1]=="\\neg a" || heading[1]=="a \\wedge b" || heading[1]=="a \\vee b" || heading[1]=="a \\oplus b")) {
    if(lines.back().empty())lines.pop_back();
    size_t width=heading[0].size(),count=size_t(1)<<width;
    if(lines.size()!=count+1 || (width==1)!=(heading[1]=="\\neg a"))throw std::runtime_error(error("Truth table dimensions do not match its inputs"));
    std::string outputs(count,'?');
    for(size_t row=1;row<lines.size();++row) {
     std::string line=lines[row];
     if(row==1 && line.compare(0,6,"\\hline")==0)line=trim(line.substr(6));
     auto cells=indexedParts(line,"&");
     if(cells.size()!=2 || cells[0].size()!=width || cells[0].find_first_not_of("01")!=std::string::npos ||
        (cells[1]!="0" && cells[1]!="1"))throw std::runtime_error(error("Invalid binary truth table row"));
     size_t index=0;for(char bit:cells[0])index=index*2+(bit-'0');
     if(outputs[index]!='?')throw std::runtime_error(error("Truth table contains a repeated input"));
     outputs[index]=cells[1][0];
    }
    pos=end+endMarker.size();return booleanGraph(outputs);
   }
  }
  const size_t firstCell=input.find_first_not_of(" \t\r\n",pos);
  if(firstCell<end && input.compare(firstCell,5,"\\rule")==0) {
   auto rows=indexedParts(input.substr(pos,end-pos),"\\\\");
   if(rows.size()!=3 || alignment.size()!=7)throw std::runtime_error(error("Expected a seven-column basis completion diagram"));
   if(!rows[2].empty() && rows[2][0]=='[') {
    auto close=rows[2].find(']');
    if(close!=std::string::npos) {
     size_t saved=pos;pos=input.find(rows[2],pos);spacingDimension(']');pos=saved;
     rows[2]=trim(rows[2].substr(close+1));
    }
   }
   const auto top=indexedParts(rows[0],"&"),labels=indexedParts(rows[1],"&"),bottom=indexedParts(rows[2],"&");
   if(top.size()!=7 || labels.size()!=7 || top!=bottom)throw std::runtime_error(error("Mismatched column guides in basis diagram"));
   static const std::regex rule(R"(\\rule\{[0-9]+(\.[0-9]+)?pt\}\{[0-9]+(\.[0-9]+)?pt\})");
   static const std::regex ket(R"(\\vert\s*(\\?[a-zA-Z]+)_(\{[a-zA-Z0-9+]+\}|[a-zA-Z0-9])\s*\\rangle)");
   std::string family;std::vector<std::string> indices;
   for(size_t k=0;k<labels.size();++k) {
    if(k==2 || k==5) {
     if(!top[k].empty() || labels[k]!="\\cdots")throw std::runtime_error(error("Expected a horizontal ellipsis between ket columns"));
    } else {
     std::smatch match;
     if(!std::regex_match(top[k],rule) || !std::regex_match(labels[k],match,ket))
      throw std::runtime_error(error("Expected an indexed ket between column guides"));
     if(family.empty())family=match[1].str();
     if(family!=match[1].str())throw std::runtime_error(error("Ket columns must share a family"));
     std::string index=match[2].str();if(index.front()=='{')index=index.substr(1,index.size()-2);
     indices.push_back(index);
    }
   }
   if(indices[0]!="1" || indices[1]!="2" || indices[2].size()!=1 || !asciiLetter(indices[2][0]) ||
      indices[3]!=indices[2]+"+1" || indices[4].size()!=1 || !asciiLetter(indices[4][0]))
    throw std::runtime_error(error("Expected consecutive ket ranges for a basis completion"));
   pos=end+endMarker.size();
   return "qbasiscolumns(qindexedentries(\""+quantumTeX(family)+"_\",1,"+indices[4]+",vector()),"+indices[2]+")";
  }
  // Unlabelled codeword arrays present words of a common width in row order.
  // Keep a Hadamard-basis state as a complete cell even when it is a vector.
  {
   static const std::regex gap(R"(^\[\s*-?[0-9]+(?:\.[0-9]+)?\s*(?:mm|cm|pt|em|ex)\s*\])");
   static const std::regex hadamard(R"(\\vert\s*\{([+-]+)\}\s*\\rangle\s*(?:\\quad)?)");
   std::string table;
   size_t width=0;
   bool valid=true,states=false;
   for(auto row:indexedParts(input.substr(pos,end-pos),"\\\\")) {
    row=trim(std::regex_replace(trim(row),gap,""));
    if(row.empty())continue;
    const auto cells=indexedParts(row,"&");
    if(cells.size()!=alignment.size()) {valid=false;break;}
    std::string entries;
    for(const auto &cell:cells) {
     std::string word=trim(cell),entry;
     std::smatch match;
     bool state=std::regex_match(word,match,hadamard);
     if(state)word=match[1].str();
     else if(word.find_first_not_of("01")!=std::string::npos) {valid=false;break;}
     if(word.size()<2 || word.size()> (state ? 10u : 30u)) {valid=false;break;}
     if(!width) {width=word.size();states=state;}
     if(width!=word.size() || states!=state) {valid=false;break;}
     if(state) {
      for(char sign:word) {
       std::string factor=std::string("|")+sign+">";
       entry=entry.empty() ? factor : "qtensor("+entry+","+factor+")";
      }
     } else {
      unsigned mask=0;
      for(char bit:word)mask=mask*2+(bit-'0');
      entry="qbitlabel("+std::to_string(mask)+","+std::to_string(width)+")";
     }
     if(!entries.empty())entries+=",";
     entries+=entry;
    }
    if(!valid)break;
    if(!table.empty())table+=",";
    table+=states ? "vector("+entries+")" : "qtuple(vector("+entries+"))";
   }
   if(valid && !table.empty()) {pos=end+endMarker.size();return states ? "vector("+table+")" : "qtuple(vector("+table+"))";}
  }
  std::string values;
  size_t rows=0;
  while(pos<end) {
   size_t rowEnd=input.find("\\\\",pos);
   if(rowEnd==std::string::npos || rowEnd>end)rowEnd=end;
   std::string row=trim(input.substr(pos,rowEnd-pos));
   pos=rowEnd==end ? end : rowEnd+2;
   if(row.empty() && pos==end)break;
   if(rows==1) {
    if(row.compare(0,6,"\\hline")!=0)throw std::runtime_error(error("A numeric table requires a horizontal rule below the labels"));
    row=trim(row.substr(6));
   }
   size_t column=0,start=0;
   while(true) {
    size_t separator=row.find('&',start);
    std::string cell=trim(row.substr(start,separator==std::string::npos ? std::string::npos : separator-start));
    if(!rows) {
     if(cell.compare(0,6,"\\text{")==0 && cell.back()=='}')cell=trim(cell.substr(6,cell.size()-7));
     if(cell.empty() || cell.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_ (),-")!=std::string::npos)
      throw std::runtime_error(error("Unsupported column label in numeric table"));
     cell="\""+cell+"\"";
    } else {
     size_t digit=!cell.empty() && (cell[0]=='+' || cell[0]=='-') ? 1 : 0;
     const size_t point=cell.find('.',digit);
     if(cell.find_first_of("0123456789",digit)==std::string::npos || cell.find_first_not_of("0123456789.",digit)!=std::string::npos ||
        (point!=std::string::npos && cell.find('.',point+1)!=std::string::npos))
      throw std::runtime_error(error("Numeric table entries must be integers or decimals"));
    }
    if(!values.empty())values+=",";
    values+=cell;++column;
    if(separator==std::string::npos)break;
    start=separator+1;
   }
   if(column!=alignment.size())throw std::runtime_error(error("Numeric table row width differs from its column declaration"));
   ++rows;
  }
  if(rows<2)throw std::runtime_error(error("A numeric table requires column labels and data"));
  pos=end+endMarker.size();
  return "matrix("+std::to_string(rows)+","+std::to_string(alignment.size())+",vector("+values+"))";
 }
 std::string command(bool matrix, int &norms, bool cases=false,bool registerLabel=false,std::string *preceding=nullptr) {
  ++pos;
  if(pos==input.size()) throw std::runtime_error(error("Incomplete TeX command"));
  if(!asciiLetter((unsigned char)input[pos])) {
   char c=input[pos++];
   if(c=='{')return setLiteral(true);
   if(c=='}')throw std::runtime_error(error("Unmatched set delimiter"));
   if(c=='\\' && matrix) {
    space();
    if(pos<input.size() && input[pos]=='[') {
     spacingDimension(']');
    }
    return ";";
   }
   if(c=='\\' && !matrix && alignmentDepth) {
    space();
    if(pos<input.size() && input[pos]=='[')spacingDimension(']');
    space();
    if(pos<input.size() && input[pos]=='&') {++pos;return " ";}
    throw std::runtime_error(error("Expected an alignment tab on a grouped continuation"));
   }
   if(c==',' || c==';' || c==':' || c=='!' || c==' ') return " ";
   if(c=='%')return " qtexpercent ";
   if(c=='|') { if(norms) { --norms; return closeNorm(); } ++norms; return "norm("; }
   throw std::runtime_error(error("Unsupported TeX control symbol"));
  }
  size_t start=pos; while(pos<input.size() && asciiLetter((unsigned char)input[pos])) ++pos;
  std::string name=input.substr(start,pos-start);
  if(name=="equiv")return " qtexcongruent ";
  if(name=="pmod") {
   std::string modulus=trim(group());
   if(modulus.empty())throw std::runtime_error(error("Expected a modulus"));
   return " qtexmodulus ("+modulus+")";
  }
  if(name=="hspace") {
   space();
   if(pos==input.size() || input[pos]!='{')throw std::runtime_error(error("Expected a braced spacing dimension"));
   spacingDimension('}');return " ";
  }
  if(name=="log") {
   size_t afterName=pos;space();
   if(pos<input.size() && input[pos]=='_') {
    ++pos;std::string base=trim(argument());space();
    if(input.compare(pos,5,"\\left")==0) {pos+=5;space();}
    std::string operand;
    if(pos<input.size() && input[pos]=='(') {++pos;operand=read(')');}
    else if(pos<input.size() && (std::isdigit((unsigned char)input[pos]) ||
            (input[pos]=='.' && pos+1<input.size() && std::isdigit((unsigned char)input[pos+1])))) {
     size_t start=pos;while(pos<input.size() && std::isdigit((unsigned char)input[pos]))++pos;
     if(pos+1<input.size() && input[pos]=='.' && std::isdigit((unsigned char)input[pos+1])) {
      ++pos;while(pos<input.size() && std::isdigit((unsigned char)input[pos]))++pos;
     }
     operand=input.substr(start,pos-start);
    } else operand=argument();
    if(base.empty() || trim(operand).empty())throw std::runtime_error(error("A logarithm needs a base and an operand"));
    return base=="2" ? "log2("+operand+")" : "log("+operand+","+base+")";
   }
   pos=afterName;
  }
  if(name=="sin" || name=="cos" || name=="tan") {
   size_t afterName=pos;
   space();
   if(pos<input.size() && input[pos]=='^') {
    ++pos;std::string power=trim(argument());
    if(power.empty())throw std::runtime_error(error("Empty trigonometric power"));
    space();
    if(pos<input.size() && input[pos]=='\\') {
     size_t end=pos+1;while(end<input.size() && asciiLetter((unsigned char)input[end]))++end;
     std::string size=input.substr(pos+1,end-pos-1);
     if(size=="left" || size=="big" || size=="Big" || size=="bigl" || size=="Bigl" || size=="bigg" || size=="Bigg" || size=="biggl" || size=="Biggl") {pos=end;space();}
    }
    std::string operand;
    if(pos<input.size() && input[pos]=='(') {++pos;operand=read(')');}
    else if(pos<input.size() && input[pos]=='{')operand=group();
    else throw std::runtime_error(error("A powered trigonometric function requires a parenthesized or braced argument"));
    if(trim(operand).empty())throw std::runtime_error(error("Empty trigonometric argument"));
    std::string compactPower;for(unsigned char c:power)if(!asciiSpace(c))compactPower+=c;
    if(compactPower=="-1")return "a"+name+"("+operand+")";
    return "("+name+"("+operand+"))^("+power+")";
   }
   pos=afterName;
  }
  if(name=="left" || name=="right" || name=="big" || name=="Big" || name=="bigl" || name=="bigr" || name=="Bigl" || name=="Bigr" || name=="bigg" || name=="Bigg" || name=="biggl" || name=="biggr" || name=="Biggl" || name=="Biggr") {
   // Explicitly paired sized bars can enclose a bra-ket with its own
   // separator. A sized ket alone instead ends in a right angle bracket.
   if(name=="bigl" || name=="Bigl" || name=="biggl" || name=="Biggl" || name=="left") {
    space();
    std::string right=name=="left" ? "right" : name.substr(0,name.size()-1)+"r";
    size_t end=input.find("\\"+right,pos);
    std::string close;
    if(end!=std::string::npos) {
     size_t bar=end+1+right.size();
     if(input.compare(bar,5,"\\vert")==0)close=right+"\\vert";
     else if(bar<input.size() && input[bar]=='|')close=right+"|";
    }
    if(input.compare(pos,5,"\\vert")==0 && end!=std::string::npos &&
       !close.empty() &&
       input.find("\\"+name,pos+5)>end && input.find("\\langle",pos+5)<end &&
       input.find("\\rangle",pos+5)<end) {
     pos+=5;
     return "qbars("+read(0,false,"",false,close)+")";
    }
   }
   space(); if(pos<input.size() && input[pos]=='.') ++pos; return "";
  }
  if(name=="in")return "∈";
  if(name=="notin")return "∉";
  if(name=="lfloor" || name=="lceil") {
   auto body=read(0,false,"",false,name=="lfloor" ? "rfloor" : "rceil");
   if(trim(body).empty())throw std::runtime_error(error("Empty rounding operand"));
   return (name=="lfloor" ? "floor(" : "ceil(")+body+")";
  }
  if(name=="rfloor" || name=="rceil")throw std::runtime_error(error("Unmatched rounding delimiter"));
  if(name=="mid" && setDepth)return ":";
  if((name=="ldots" || name=="dots" || name=="cdots") && pos>name.size()+1) {
   size_t before=input.find_last_not_of(" \t\r\n",pos-name.size()-2);
   size_t after=input.find_first_not_of(" \t\r\n",pos);
   if(before!=std::string::npos && after!=std::string::npos && input[before]==',' && input[after]==',')return "...";
   if(preceding && before!=std::string::npos && after!=std::string::npos &&
      (input[before]=='0' || input[before]=='1') && input[after]==input[before]) {
    size_t open=preceding->find_last_of("|<");
    if(open!=std::string::npos && trim(preceding->substr(open+1))==std::string(1,input[before]))return "...";
   }
  }
  if(name=="cdots") {
   size_t before=input.find_last_not_of(" \t\r\n",pos-name.size()-2),after=input.find_first_not_of(" \t\r\n",pos);
   if(before!=std::string::npos && before>0 && after!=std::string::npos && input[before]=='+' && input[after]=='+') {
    size_t end=input.find_last_not_of(" \t\r\n",before-1);
    if(end!=std::string::npos && (input[end]=='|' ||
       (end>=4 && input.compare(end-4,5,"\\vert")==0) ||
       (end>=5 && input.compare(end-5,6,"\\rvert")==0)))return "...";
   }
  }
  if(setDepth && (name=="ldots" || name=="cdots" || name=="dots"))return "...";
  if((stateLabel || registerLabel || setBound) && (name=="ldots" || name=="cdots" || name=="dots"))return " ... ";
  if(name=="frac" || name=="dfrac" || name=="tfrac") { auto a=argument(), b=argument(); return "(("+a+")/("+b+"))"; }
  if(name=="overline") {
   if(stateLabel)throw std::runtime_error(error("Use conj around the whole ket or bra to conjugate a state"));
   auto value=argument();
   if(trim(value).empty())throw std::runtime_error(error("A conjugation overline requires an operand"));
   return "(conj("+value+"))";
  }
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
    // A bare sum index runs through an unspecified finite collection.
    // Keep that collection symbolic so supplying it later evaluates the sum.
    if(name=="sum" && bound=='_' && upper.empty()) {
     std::string index=trim(lower);
     size_t next=input.find_first_not_of(" \t\r\n",pos);
     if(index.size()==1 && asciiLetter(index.front()) && next!=std::string::npos && input[next]!='^')
      lower=index+" ∈ indexset_"+index;
    }
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
   if(setSum && variable.find("...")!=std::string::npos) {
    std::string prefix,begin,end,alphabet,width;
    if(!registerSumDeclaration(variable,startValue,prefix,begin,end,alphabet,width))
     throw std::runtime_error(error("A register sum requires matching indexed endpoints and an explicit alphabet power"));
    std::string arguments=alphabet+","+width+","+begin+","+end+",\""+prefix+"\"";
    space();if(pos==input.size())throw std::runtime_error(error("Missing register sum body"));
    if(input[pos]!='{')return "qtexregistersum("+arguments+") ";
    return "qtexgroupregistersum("+arguments+","+group()+")";
   }
   if(variable[0]>='0' && variable[0]<='9') throw std::runtime_error(error("A summation index cannot begin with a digit"));
   // A grouped arithmetic subscript is part of the variable's identity,
   // not arithmetic applied to the variable. Keep its expression for the
   // notation parser, which owns lexical binding and expression validation.
   size_t indexed=variable.find("_{");
   std::string identifier=variable;
   if(indexed!=std::string::npos) {
    if(!indexed || variable.back()!='}' || trim(variable.substr(indexed+2,variable.size()-indexed-3)).empty())
     throw std::runtime_error(error("Invalid summation index"));
    identifier=variable.substr(0,indexed);
   }
   for(unsigned char c:identifier) if(c<128 && !asciiLetter(c) && c!='_' && !(c>='0' && c<='9' && identifier.find('_')!=std::string::npos)) throw std::runtime_error(error("Invalid summation index"));
   space();
   if(pos==input.size())throw std::runtime_error(error("Missing finite sum/product body"));
   if(input[pos]!='{') {
    // The expression parser determines the multiplicative body's extent.
    if(setSum)return "qtexsumset("+startValue+","+variable+") ";
    return "qtex"+name+"("+startValue+","+upper+","+variable+") ";
   }
   auto body=group();
   // Bounds precede the body so its lexical index context is known while
   // parsing compact products, including inside nested braced sums.
   if(setSum)return "qtexgroupsumset("+startValue+","+variable+","+body+")";
   return "qtexgroup"+name+"("+startValue+","+upper+","+variable+","+body+")";
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
   auto state=stateGroup();return "(<"+state+"|("+observable+")|"+state+">)";
  }
  if(matrixElement) {
   auto left=stateGroup(),observable=group(),right=stateGroup();
   return "(<"+left+"|("+observable+")|"+right+">)";
  }
  if(name=="ket" || name=="Ket") return "|"+stateArgument()+">";
  if(name=="bra" || name=="Bra") return "<"+stateArgument()+"|";
  if(name=="braket" || name=="Braket" || name=="innerproduct" || name=="ip") {
   auto a=stateGroup(); space();
   if(pos<input.size() && input[pos]=='{') return "<"+a+"|"+stateGroup()+">";
   if(a.find('|')==std::string::npos)return "<"+a+"|"+a+">";
   return "<"+a+">";
  }
  if(name=="ketbra" || name=="outerproduct" || name=="dyad" || name=="op") {
   auto a=stateGroup(); space(); auto b=pos<input.size() && input[pos]=='{' ? stateGroup() : a;
   return "(|"+a+"><"+b+"|)";
  }
  if(name=="norm") {auto body=group();return "norm("+body+closeNorm();}
  if(name=="abs") return "abs("+group()+")";
  if(name=="comm" || name=="commutator" || name=="anticommutator") {
   auto a=group(), b=group(); return (name=="anticommutator" ? "anticomm(" : "comm(")+a+","+b+")";
  }
  if(name=="operatorname" || name=="mathrm" || name=="mathsf" || name=="mathbf" || name=="mathbb" || name=="mathcal") {
   auto a=nameGroup();
   if(name=="mathrm" && a.size()>1 && a.find_first_not_of("abcdefghijklmnopqrstuvwxyz")==std::string::npos &&
      a!="pi" && a!="inf" && a!="infinity" && (wholeSetEntry(preceding) || beforeMembership()))return "qoutcome(\""+a+"\")";
   if(name=="mathbb" && a=="I") {
    if(pos<input.size() && input[pos]=='_')return "I";
    return " qimplicitidentity() ";
   }
   if(name=="mathbb" && a=="Z") {
    space();
    if(pos<input.size() && input[pos]=='_') {
     ++pos;std::string modulus=argument();
     size_t end=pos;space();
     bool units=false;
     if(pos<input.size() && input[pos]=='^') {
      ++pos;space();
      for(const std::string suffix:{"{\\ast}","{*}","\\ast","*"})
       if(input.compare(pos,suffix.size(),suffix)==0) {pos+=suffix.size();units=true;break;}
     }
     if(!units)pos=end;
     return std::string(units ? "qunitsmod(" : "qresidues(")+modulus+")";
    }
   }
   if(name=="mathbb" && a=="T")return " qunitcircle() ";
   if(name=="mathbb" && a=="C")return " qcomplexplane() ";
   if(name=="operatorname" && a=="Pr") {
    std::string event=eventProbability();if(!event.empty())return event;
   }
   if(name=="operatorname" && a=="lg")a="qbitlength";
   if(name=="operatorname" && a=="range")a="qfunctionrange";
   if((name=="mathbb" || name=="mathbf") && a=="1") a="I";
   return " "+a+" ";
  }
  if(name=="fbox") {
   space();
   if(input.compare(pos,3,"{?}")==0) {pos+=3;return "qmissingblock()";}
   throw std::runtime_error(error("Expected a boxed question mark for an unspecified block"));
  }
  if(name=="text") {
   std::string text=trim(group());
   if(!text.empty() && std::all_of(text.begin(),text.end(),asciiLetter)) {
    const std::string prefix=preceding ? trim(*preceding) : "";
    const size_t next=input.find_first_not_of(" \t\r\n",pos);
    if(stateLabel)return text;
    if(!prefix.empty() && next!=std::string::npos) {
     if(prefix.back()=='|' && (input[next]=='>' || input.compare(next,7,"\\rangle")==0))return text;
     if(prefix.back()=='<' && (input[next]=='|' || input.compare(next,5,"\\vert")==0))return text;
    }
    if(wholeSetEntry(preceding) || beforeMembership())return "qoutcome(\""+text+"\")";
   }
   if(text=="and" || text=="or")return " "+text+" ";
   if(!cases)throw std::runtime_error(error("Unsupported text in a mathematical expression"));
   if(text=="otherwise")return text;
   if(text!="if" && (text.size()<3 || text.compare(0,2,"if")!=0 || !asciiSpace((unsigned char)text[2])))throw std::runtime_error(error("Cases text must introduce if or otherwise"));
   text=trim(text.substr(2));
   if(text.size()>=2 && text.front()=='$' && text.back()=='$')text=text.substr(1,text.size()-2);
   return text;
  }
  if(name=="begin") {
   auto env=nameGroup();
   if(env=="array") {
    std::string tables=numericTable();
    bool grouped=false;
    while(true) {
     size_t saved=pos;space();
     bool spaced=false;
     while(input.compare(pos,6,"\\qquad")==0 || input.compare(pos,5,"\\quad")==0) {
      pos+=input.compare(pos,6,"\\qquad")==0 ? 6 : 5;space();spaced=true;
     }
     if(!spaced){pos=saved;break;}
     if(input.compare(pos,13,"\\begin{array}")!=0) {pos=saved;break;}
     pos+=13;
     tables+=","+numericTable();
     grouped=true;
    }
    return grouped ? "vector("+tables+")" : tables;
   }
   if(env=="cases") {
    // On the left of a cases definition, 0.a denotes a single fractional
    // bit. Validate its width when the bit is assigned a concrete value.
    if(preceding) {
     std::string lhs=trim(*preceding);
     if(!lhs.empty() && lhs.back()=='=') {
      lhs=trim(lhs.substr(0,lhs.size()-1));
      if(lhs.size()==3 && lhs.compare(0,2,"0.")==0 && asciiLetter(lhs[2]))
       *preceding="(qbitvalue(qbitlabel("+lhs.substr(2)+",1))/2)=";
     }
    }
    return read(0,true,env);
   }
   if(env=="aligned" || env=="align" || env=="align*" || env=="gathered" || env=="gather" || env=="gather*" || env=="split") {
    space();
    if(pos<input.size() && input[pos]=='[') {
     if(pos+2>=input.size() || input[pos+2]!=']' || (input[pos+1]!='t' && input[pos+1]!='c' && input[pos+1]!='b'))throw std::runtime_error(error("Alignment position must be t, c, or b"));
     pos+=3;
    }
    return read(0,true,env);
   }
   if(env!="matrix" && env!="pmatrix" && env!="bmatrix" && env!="Bmatrix" && env!="vmatrix" && env!="Vmatrix") throw std::runtime_error(error("Unsupported TeX environment: "+env));
   size_t bodyStart=pos;
   size_t bodyEnd=std::string::npos;
   auto body=read(0,true,env,false,"",false,&bodyEnd);
   if(bodyEnd==std::string::npos)bodyEnd=input.rfind("\\end",pos-1);
   std::string raw=input.substr(bodyStart,bodyEnd-bodyStart);
   std::string m=indexedMatrix(raw,true);
   if(m.empty())m=indexedColumn(raw,true);
   if(m.empty())m=conjugateCoefficientRow(raw);
   // Inner products have scalar entries even while the named states are unbound.
   // Preserve the shape instead of asking horizontal concatenation to infer it.
   if(m.empty() && raw.find("\\langle")!=std::string::npos) {
    auto rows=indexedParts(body,";");
    size_t width=0;std::string entries;bool scalar=true;
    for(const auto &row:rows) {
     auto cells=indexedParts(row,",");
     if(!width)width=cells.size();
     if(cells.size()!=width){scalar=false;break;}
     for(const auto &cell:cells) {
      if(cell.empty() || cell.front()!='<' || cell.back()!='>' ||
         cell.find_first_of("<>",1)!=cell.size()-1 || std::count(cell.begin(),cell.end(),'|')!=1){scalar=false;break;}
      if(!entries.empty())entries+=",";
      entries+=cell;
     }
     if(!scalar)break;
    }
    if(scalar)m="matrix("+std::to_string(rows.size())+","+std::to_string(width)+",vector("+entries+"))";
   }
   if(m.empty())m="["+body+"]";
   if(env=="vmatrix") return "det("+m+")";
   if(env=="Vmatrix") return "norm("+m+closeNorm(true);
   return m;
  }
  if(name=="vdots" && matrix)return "⋮";
  // A decimal followed immediately by an ellipsis can specify a recurring
  // digit, as in 5.333... . Do not infer a repetend from mixed digits.
  if((name=="cdots" || name=="ldots") && preceding) {
   size_t end=preceding->find_last_not_of(" \t\r\n");
   if(end!=std::string::npos && std::isdigit((unsigned char)(*preceding)[end])) {
    size_t point=end;
    while(point && (*preceding)[point]==(*preceding)[end])--point;
    if((*preceding)[point]=='.' && end-point>=3) {
     size_t begin=point;
     while(begin && std::isdigit((unsigned char)(*preceding)[begin-1]))--begin;
     if(begin<point && (!begin || (*preceding)[begin-1]!='.')) {
      std::string whole=preceding->substr(begin,point-begin);
      char digit=(*preceding)[end];preceding->erase(begin);
      return "("+whole+"+"+digit+"/9)";
     }
    }
   }
  }
  if(name=="cdots" && matrix)return "⋯";
  if(name=="ddots" && matrix)return "⋱";
  if(name=="lVert") { ++norms; return "norm("; }
  if(name=="rVert") { if(norms==0) throw std::runtime_error(error("Unmatched norm delimiter")); --norms; return closeNorm(); }
  if(name=="Vert") { if(norms) { --norms; return closeNorm(); } ++norms; return "norm("; }
  static const std::map<std::string,std::string> aliases={
   {"langle","<"},{"rangle",">"},{"vert","|"},{"lvert","|"},{"rvert","|"},
   {"cup","∪"},{"cap","∩"},{"setminus","∖"},{"emptyset","vector()"},{"varnothing","vector()"},
   {"otimes","@"},{"oplus","#"},{"dagger","~"},{"cdot"," ⋅ "},{"times","*"},
   {"top","`"},{"ast","*"},{"bmod","%"},{"mod","%"},
   {"le","<="},{"leq","<="},{"ge",">="},{"geq",">="},{"ne","!="},{"neq","!="},
   {"preceq","<="},{"succeq",">="},{"preccurlyeq","<="},{"succcurlyeq",">="},{"prec","<"},{"succ",">"},
   {"mapsto"," ↦ "},{"approx"," ≈ "},{"pm"," ± "},{"rightarrow"," → "},{"to"," → "},{"Leftrightarrow"," iff "},{"iff"," iff "},{"land"," and "},{"wedge"," and "},{"lor"," or "},{"vee"," or "},{"lnot"," not "},{"neg"," not "},{"veebar"," xor "},
   {"uparrow","↑"},{"downarrow","↓"},
   {"infty","infinity"},{"pi","pi"},{"hbar","ℏ"},{"ell","ℓ"},{"alpha","α"},{"beta","β"},{"gamma","γ"},{"delta","δ"},{"theta","θ"},
   {"phi","φ"},{"Phi","Φ"},{"varphi","φ"},{"psi","ψ"},{"Psi","Ψ"},{"rho","ρ"},{"sigma","σ"},
   {"lambda","λ"},{"omega","ω"},{"mu","μ"},{"epsilon","ε"},{"varepsilon","ε"},{"chi","χ"},
   {"zeta","ζ"},{"eta","η"},{"iota","ι"},{"kappa","κ"},{"nu","ν"},{"xi","ξ"},
   {"clubsuit","♣"},{"diamondsuit","♢"},{"heartsuit","♡"},{"spadesuit","♠"},
   {"omicron","ο"},{"tau","τ"},{"upsilon","υ"},{"vartheta","θ"},{"varrho","ρ"},
   {"varkappa","κ"},{"varpi","ϖ"},{"varsigma","ς"},
   {"Gamma","Γ"},{"Delta","Δ"},{"Theta","Θ"},{"Lambda","Λ"},{"Xi","Ξ"},
   {"Pi","Π"},{"Sigma","Σ"},{"Upsilon","Υ"},{"Omega","Ω"},
   {"sin","sin"},{"cos","cos"},{"tan","tan"},{"arcsin","asin"},{"arccos","acos"},{"arctan","atan"},{"exp","exp"},{"log","ln"},{"ln","ln"},
   {"gcd","integergcd"},{"det","det"},{"tr","tr"},{"Tr","Tr"},{"quad"," "},{"qquad"," "}
  };
  auto it=aliases.find(name); if(it!=aliases.end()) return it->second;
  throw std::runtime_error(error("Unsupported TeX command: \\"+name));
 }
 std::string read(char close=0, bool matrix=false, const std::string &environment="", bool setClose=false, const std::string &roundClose="", bool membershipGroup=false, size_t *matrixBodyEnd=nullptr) {
  struct MatrixScope {
   unsigned &depth;bool active;
   MatrixScope(unsigned &depth_,bool active_):depth(depth_),active(active_) {if(active)++depth;}
   ~MatrixScope() {if(active)--depth;}
  } matrixScope(matrixDepth,matrix || close==']');
  if(++depth>128) throw std::runtime_error(error("TeX nesting exceeds 128"));
  std::string result; int norms=0; bool closed=false,congruence=false;
  const bool alignment=environment=="aligned" || environment=="align" || environment=="align*" || environment=="gathered" || environment=="gather" || environment=="gather*" || environment=="split";
  const bool gathered=environment=="gathered" || environment=="gather" || environment=="gather*";
  MatrixScope alignmentScope(alignmentDepth,alignment);
  std::vector<std::string> alignmentCells,expressions;
  std::vector<size_t> preceding;
  unsigned alignmentRows=0;
  auto finishAlignment=[&]() {
   if(++alignmentRows>128)throw std::runtime_error(error("Alignment is limited to 128 rows"));
   alignmentCells.push_back(trim(result));result.clear();
   const bool separate=alignmentCells.size()>1 && std::all_of(alignmentCells.begin(),alignmentCells.end(),completeAlignedEquation);
   const size_t stride=separate ? 1 : 2;
   for(size_t cell=0;cell<alignmentCells.size();cell+=stride) {
    std::string value=alignmentCells[cell];
    bool indented=cell+1<alignmentCells.size() && (value.empty() || (value.size()==1 && value.find_first_of("+-*/@#")!=std::string::npos));
    if(!separate && cell+1<alignmentCells.size())value+=" "+alignmentCells[cell+1];
    value=trim(withoutDisplayPunctuation(value));
    if(value.empty())throw std::runtime_error(error("Empty aligned expression"));
    size_t column=cell/stride;
    if(preceding.size()<=column)preceding.resize(column+1,std::string::npos);
    bool relation=value[0]=='=' || value.compare(0,2,"<=")==0 || value.compare(0,2,">=")==0 || value.compare(0,2,"!=")==0;
    bool operation=value[0]=='+' || value[0]=='-' || value[0]=='*' || value[0]=='/' || value[0]=='@' || value[0]=='#';
    bool positiveContinuation=(environment=="gathered" && value[0]=='+' && preceding[column]!=std::string::npos);
    bool continuation=relation || positiveContinuation || (indented && operation && preceding[column]!=std::string::npos);
    if(continuation) {
     if(preceding[column]==std::string::npos)throw std::runtime_error(error("An aligned continuation requires a preceding expression"));
     expressions[preceding[column]]+=" "+value;
    } else {
     if(expressions.size()>=128)throw std::runtime_error(error("Alignment is limited to 128 independent expressions"));
     preceding[column]=expressions.size();expressions.push_back(value);
    }
   }
   alignmentCells.clear();
  };
  std::vector<std::pair<std::string,std::string>> branches;
  std::string caseValue;bool caseColumn=false;
  auto finishCase=[&]() {
   if(!caseColumn || trim(caseValue).empty() || trim(result).empty())throw std::runtime_error(error("Each case requires a value and condition separated by &"));
   if(branches.size()>=64)throw std::runtime_error(error("Cases are limited to 64 branches"));
   branches.emplace_back(trim(caseValue),trim(withoutDisplayPunctuation(result)));result.clear();caseValue.clear();caseColumn=false;
  };
  while(pos<input.size()) {
   if(!roundClose.empty() && input[pos]=='\\' && input.compare(pos+1,roundClose.size(),roundClose)==0 &&
      (pos+1+roundClose.size()==input.size() || !asciiLetter((unsigned char)input[pos+1+roundClose.size()]))) {
    pos+=roundClose.size()+1;closed=true;break;
   }
   if(setClose && input.compare(pos,2,"\\}")==0) {pos+=2;closed=true;break;}
   if(close && (input[pos]==close || (membershipGroup && (input[pos]==')' || input[pos]==']')))) { ++pos; closed=true; break; }
   if(matrix && input.compare(pos,4,"\\end")==0 && (pos+4==input.size() || !asciiLetter((unsigned char)input[pos+4]))) {
    pos+=4; if(nameGroup()!=environment) throw std::runtime_error(error("Mismatched matrix environment")); closed=true; break;
   }
   if(!matrixDepth && !stateLabel && !setDepth && !setBound) {
    const std::string preceding=trim(result);
    if(input.compare(pos,10,"\\overline{")==0 && input.find("\\cdots",pos)!=std::string::npos) {
     // Both products must use the same two coefficient families and upper index.
     static const std::regex series(R"(\\overline\{(\\?[a-zA-Z]+)_1\}\s*(\\?[a-zA-Z]+)_1\s*\+\s*\\cdots\s*\+\s*\\overline\{\1_([a-zA-Z])\}\s*\2_\3(?![a-zA-Z0-9_]))");
     std::smatch match;
     if(std::regex_search(input.cbegin()+pos,input.cend(),match,series,std::regex_constants::match_continuous)) {
      auto column=[&](size_t family){return "qonebasedcolumn(\""+quantumTeX(match[family].str())+"_\",("+match[3].str()+"),1)";};
      result+="qmul(qdag(qcomplexcolumn("+column(1)+")),"+column(2)+")";pos+=match.length();continue;
     }
    }
    if(input[pos]=='1' && (preceding.empty() || preceding.back()==',' || preceding.back()=='=')) {
     std::string series=geometricSum();
     if(!series.empty()) {result+=series;continue;}
    }
    if(preceding.empty() || preceding.back()==',') {
     size_t end=pos;std::string product=hadamardRegisterTensor(input,pos,end);
     if(product.empty()) {
      TensorSeriesPattern series;
      if(tensorSeriesPattern(input,pos,series)) {
       product="qtexgrouptensorseries("+series.first+","+series.last+","+series.index+","+series.direction+","+
        TeXReader(series.body).run(nullptr)+")";end=series.end;
      }
     }
     if(product.empty())product=indexedProduct(input,pos,end);
     if(!product.empty()) {result+=product;pos=end;continue;}
    }
   }
   // The display uses ordinary braces for the finite domain after a
   // Unicode membership sign. TeX grouping elsewhere keeps its meaning.
   if(input.compare(pos,3,"∈")==0 || input.compare(pos,3,"∉")==0) {
    size_t next=input.find_first_not_of(" \t\r\n",pos+3);
    if(next!=std::string::npos && input[next]=='{') {
     result+=input.substr(pos,next-pos);pos=next+1;result+=setLiteral(false);continue;
    }
   }
   // Quoted labels are literal data; do not reinterpret operator subscripts.
   if(input[pos]=='"' || input[pos]=='\'') {
    char quote=input[pos++];result+=quote;bool ended=false;
    while(pos<input.size()) {char c=input[pos++];result+=c;if(c==quote){ended=true;break;}}
    if(!ended)throw std::runtime_error(error("Unclosed quoted label"));
   }
   else if(input[pos]=='\\') {
    // In a word definition the matching base name disambiguates
    // concatenation of indexed bits from an ellipsis in a scalar product.
    if((input.compare(pos,6,"\\cdots")==0 || input.compare(pos,6,"\\ldots")==0) &&
       (pos+6==input.size() || !asciiLetter((unsigned char)input[pos+6]))) {
     size_t equals=result.find('=');
     if(equals!=std::string::npos) {
      std::string word=trim(result.substr(0,equals)),first=trim(result.substr(equals+1));
      if(!word.empty() && std::all_of(word.begin(),word.end(),asciiLetter) &&
         first.compare(0,word.size()+1,word+"_")==0) {
       first=trim(first.substr(word.size()+1));
       bool grouped=first.size()>2 && first.front()=='{' && first.back()=='}';
       if(grouped)first=first.substr(1,first.size()-2);
       bool valid=!first.empty();
       for(unsigned char c:first)if(!std::isalnum(c) && !(grouped && (asciiSpace(c) || c=='+' || c=='-' || c=='*' || c=='/')))valid=false;
       size_t endpoint=input.find_first_not_of(" \t\r\n",pos+6);
       if(valid && endpoint!=std::string::npos && input.compare(endpoint,word.size()+1,word+"_")==0) {
        pos=endpoint+word.size()+1;
        std::string last=argument();
        result=word+"=qregisterword(\""+word+"_\",("+first+"),("+last+"),vector())";continue;
       }
      }
     }
    }
    // A trailing equation tag labels the display or alignment row.
    if((depth==1 || alignment) && input.compare(pos,4,"\\tag")==0 &&
       (pos+4==input.size() || !asciiLetter((unsigned char)input[pos+4]))) {
     pos+=4;space();if(pos<input.size() && input[pos]=='*') {++pos;space();}
     if(pos==input.size() || input[pos++]!='{')throw std::runtime_error(error("Expected an equation tag"));
     size_t start=pos;
     while(pos<input.size() && input[pos]!='}' && input[pos]!='{' && input[pos]!='\\')++pos;
     if(pos==input.size() || input[pos]!='}' || trim(input.substr(start,pos-start)).empty())
      throw std::runtime_error(error("Expected a nonempty plain equation tag"));
     ++pos;space();
     bool rowEnd=alignment && (input.compare(pos,2,"\\\\")==0 || input.compare(pos,4,"\\end")==0);
     if(trim(result).empty() || (pos!=input.size() && !rowEnd))
      throw std::runtime_error(error("An equation tag must follow the complete expression"));
     result=withoutDisplayPunctuation(result);continue;
    }
    // Delimiter-form kets (\\vert ... \\rangle) do not enter stateGroup.
    // Keep ellipses contextual; the notation parser validates their bounds.
    size_t delimiter=result.find_last_of("|<>");
    bool registerLabel=delimiter!=std::string::npos && result[delimiter]!='>' &&
     result.find('_',delimiter+1)!=std::string::npos;
    size_t commandStart=pos;
    std::string part=command(matrix,norms,environment=="cases",registerLabel,&result);
    if(part==" qtexcongruent ")congruence=true;
    else if(part.compare(0,14," qtexmodulus (")==0) {
     if(!congruence)throw std::runtime_error(error("A congruence modulus must follow a congruence relation"));
     congruence=false;
    }
    // A final TeX row break terminates the last row. Exclude it from both
    // the translated matrix and the raw rows used to infer indexed entries.
    if(matrixBodyEnd && part==";") {
     size_t next=input.find_first_not_of(" \t\r\n",pos);
     if(next!=std::string::npos && input.compare(next,4,"\\end")==0) {
      *matrixBodyEnd=commandStart;continue;
     }
    }
    if(environment=="cases" && part==";")finishCase();
    else if(alignment && part==";")finishAlignment();else result+=part;
   }
   else if(input[pos]=='(' || input[pos]=='[') {
    char open=input[pos++], end=open=='(' ? ')' : ']';
    if(open=='(' && takeModulusLabel(congruence)) {
     auto modulus=trim(read(end));
     if(modulus.empty())throw std::runtime_error(error("Expected a modulus"));
     result=trim(result)+(congruence ? " qtexmodulus (" : " pmod (")+modulus+")";
     congruence=false;continue;
    }
    // Mixed delimiters denote a half-open interval only after membership.
    // The recursive reader still checks grouping inside either endpoint.
    size_t tail=result.find_last_not_of(" \t\r\n");
    bool membership=tail!=std::string::npos && tail>=2 &&
     (result.compare(tail-2,3,"∈")==0 || result.compare(tail-2,3,"∉")==0);
    size_t bodyStart=pos;auto body=read(end,false,"",false,"",membership);
    if(open=='(' && !membership) {
     std::string list=orderedKetList(body);
     if(!list.empty()) {result+="("+list+")";continue;}
    }
    if(membership && input[pos-1]!=end) {
     result+="qhalfopen("+body+","+(open=='[' ? "1)" : "0)");continue;
    }
    if(membership && indexedParts(body,",").size()==2 && indexedParts(body,";").size()==1) {
     result+="qrealinterval("+body+","+(open=='[' ? "1,1)" : "0,0)");continue;
    }
    std::string raw=input.substr(bodyStart,pos-bodyStart-1);
    std::string column=open=='[' ? indexedMatrix(raw,false) : "";
    if(column.empty() && open=='[')column=indexedColumn(raw,false);
    result+=column.empty() ? std::string(1,open)+body+end : column;
   }
   else if(input[pos]==')' || input[pos]==']') throw std::runtime_error(error("Unmatched closing delimiter"));
   else if(input[pos]=='_') {
    if(input.compare(pos,10,"_{\\mathsf{")==0) {
     size_t close=input.find("}}",pos+10);
     size_t ketEnd=result.find_last_not_of(" \t\r\n"),ketStart=result.rfind('|',ketEnd);
     if(close!=std::string::npos && ketEnd!=std::string::npos && result[ketEnd]=='>' && ketStart!=std::string::npos) {
      std::string labels=input.substr(pos+10,close-pos-10);
      if(labels.empty() || labels.size()>32 || labels.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZ")!=std::string::npos)
       throw std::runtime_error(error("Expected uppercase register names on a ket"));
      result.replace(ketStart,std::string::npos,"qregket("+result.substr(ketStart,ketEnd+1-ketStart)+",\""+labels+"\")");
      pos=close+2;continue;
     }
    }
    size_t stateDelimiter=result.find_last_of("|<>");
    bool stateSubscript=stateLabel;
    if(!stateSubscript && stateDelimiter!=std::string::npos && result[stateDelimiter]!='>') {
     std::string prefix=trim(result.substr(stateDelimiter+1));stateSubscript=!prefix.empty();
     for(unsigned char c:prefix)if(c<128 && !std::isalnum(c) && c!='_')stateSubscript=false;
    }
    while(!result.empty() && asciiSpace((unsigned char)result.back()))result.pop_back();
    bool spin=!result.empty() && result.back()=='J' && (result.size()==1 ||
     ((unsigned char)result[result.size()-2]<128 && !std::isalnum((unsigned char)result[result.size()-2]) && result[result.size()-2]!='_'));
    bool bell=false;
    for(const std::string &name:{std::string("Φ"),std::string("φ"),std::string("ϕ"),std::string("Ψ"),std::string("ψ"),std::string("Phi"),std::string("phi"),std::string("Psi"),std::string("psi")})
     if(result.size()>=name.size() && result.compare(result.size()-name.size(),name.size(),name)==0)bell=true;
    bool fourier=result.size()>=3 && result.substr(result.size()-3)=="QFT" &&
     (result.size()==3 || (!std::isalnum((unsigned char)result[result.size()-4]) && result[result.size()-4]!='_' && (unsigned char)result[result.size()-4]<128));
    ++pos; space(); std::string index;bool grouped=false;
    if(input.compare(pos,6,"\\text{")==0 || input.compare(pos,7,"{\\text{")==0) {
     static const std::regex textIndex(R"((?:\\text\{([A-Za-z0-9]+)\}|\{\\text\{([A-Za-z0-9]+)\}\}))");
     std::smatch label;grouped=true;
     if(std::regex_search(input.cbegin()+pos,input.cend(),label,textIndex,std::regex_constants::match_continuous)) {
      index=label[1].str()+label[2].str();pos+=label.length();
     } else index=input[pos]=='{' ? group() : argument();
    }
    else if(pos<input.size() && input[pos]=='{') {grouped=true;index=group();}
    else if(pos<input.size() && input[pos]=='(') {grouped=true;++pos;index=read(')');}
    else if(fourier && pos<input.size() && std::isdigit((unsigned char)input[pos])) {
     while(pos<input.size() && std::isdigit((unsigned char)input[pos]))index+=input[pos++];
    }
    else if(pos<input.size() && std::isalnum((unsigned char)input[pos])) index+=input[pos++];
    else if(pos<input.size() && (input[pos]=='\\' || (unsigned char)input[pos]>=128)) {grouped=true;index=argument();}
    else if((spin || bell) && pos<input.size() && (input[pos]=='+' || input[pos]=='-')) index+=input[pos++];
    else throw std::runtime_error(error("Expected a subscript"));
    if(stateSubscript && grouped && trim(index).empty())throw std::runtime_error(error("A state subscript cannot be empty"));
    bool trace=result.size()>=2 && (result.substr(result.size()-2)=="Tr" || result.substr(result.size()-2)=="tr") &&
     (result.size()==2 || !std::isalnum((unsigned char)result[result.size()-3]));
    if(fourier) {result.resize(result.size()-3);result+="qfourier("+index+")";}
    else if(trace) {
     space(); std::string body;
     if(pos<input.size() && input[pos]=='{') body=group();
     else if(pos<input.size() && input[pos]=='(') { ++pos; body=read(')'); }
     else throw std::runtime_error(error("A subscripted trace requires a parenthesized or braced operand"));
     result.resize(result.size()-2); result+="ptrace("+body+",vector("+index+"))";
    } else if(!stateSubscript && grouped && indexedParts(index,",").size()>1) {
     auto pair=indexedParts(index,",");
     if(pair.size()!=2 || pair[0].empty() || pair[1].empty())throw std::runtime_error(error("A paired coefficient subscript requires two indices"));
     size_t start=result.size();
     while(start && ((unsigned char)result[start-1]>=128 || std::isalnum((unsigned char)result[start-1]) || result[start-1]=='_'))--start;
     while(start<result.size() && std::isdigit((unsigned char)result[start]))++start;
     std::string name=result.substr(start);
     if(name.empty() || ((unsigned char)name[0]<128 && !asciiLetter(name[0])))throw std::runtime_error(error("A paired coefficient subscript requires a name"));
     result.resize(start);result+="qindexedcoefficient(\""+name+"_\",("+pair[0]+"),("+pair[1]+"))";
    } else if(spin) {
     size_t first=index.find_first_not_of(" \t\r\n"), last=index.find_last_not_of(" \t\r\n");
     if(first!=std::string::npos)index=index.substr(first,last-first+1);
     if(index=="+")result+="plus";
     else if(index=="-")result+="minus";
     else result+="_"+index;
    } else if(grouped && !result.empty() && (result.back()=='>' || result.back()=='|'))result+="_("+index+")";
    else {
     index=trim(index);
     bool compound=false;for(unsigned char c:index)if(c<128 && !std::isalnum(c) && c!='_' && !asciiSpace(c))compound=true;
     // Preserve arithmetic subscripts for scalar references and declarations
     // as well as state families. Atomic labels retain their spelling.
     result+=grouped && compound && index!="+" && index!="-" ? "_{"+index+"}" : "_"+index;
    }
   }
   else if(input[pos]=='{') {
    auto value=group();
    // TeX ignores spaces around operator-valued superscripts.
    size_t first=value.find_first_not_of(" \t\r\n"), last=value.find_last_not_of(" \t\r\n");
    if(first!=std::string::npos)value=value.substr(first,last-first+1);
    while(!result.empty() && asciiSpace((unsigned char)result.back()))result.pop_back();
    // The displayed open-ended family uses ordinary braces and an ellipsis.
    if(value.find("…")!=std::string::npos || value.find("...")!=std::string::npos) {
     std::string family=openIndexedFamily(indexedParts(value,","));
     if(!family.empty()) {result+=family;continue;}
    }
    // Braces around an entire Dirac label are typesetting, not arithmetic.
    size_t after=pos;while(after<input.size() && asciiSpace((unsigned char)input[after]))++after;
    bool ketLabel=!result.empty() && result.back()=='|' &&
     (input.compare(after,7,"\\rangle")==0 || input.compare(after,1,">")==0);
    bool braLabel=!result.empty() && result.back()=='<' &&
     (input.compare(after,5,"\\vert")==0 || input.compare(after,6,"\\rvert")==0 || input.compare(after,1,"|")==0);
    // TeX power groups preserve postfix dagger and the tensor-power operator.
    if(ketLabel || braLabel)result+=value;
    else if(!result.empty() && result.back()=='^' && value=="~") { result.pop_back(); result+="~"; }
    else if(!result.empty() && result.back()=='^' && (value=="T" || value=="`")) { result.pop_back(); result+="`"; }
    else if(!result.empty() && result.back()=='^' && value=="*") { result.pop_back(); result+="?"; }
    else if(!result.empty() && result.back()=='^' && value.compare(0,2,"T_")==0) result+="%("+value.substr(2)+")";
    else if(!result.empty() && result.back()=='^' && !value.empty() && value[0]=='@') result+="@("+value.substr(1)+")";
    else result+="("+value+")";
   }
   else if(input[pos]=='}') throw std::runtime_error(error("Unexpected closing brace"));
   else if(input[pos]=='&') { if(!matrix) throw std::runtime_error(error("Alignment separator outside a matrix")); ++pos;
    if(alignment) {
     if(gathered)throw std::runtime_error(error("Gathered expressions do not use alignment columns"));
     if(alignmentCells.size()>=63)throw std::runtime_error(error("Alignment is limited to 32 column pairs"));
     alignmentCells.push_back(trim(result));result.clear();
    } else if(environment=="cases") {
     if(caseColumn)throw std::runtime_error(error("Each case has exactly two columns"));
     caseValue=result;result.clear();caseColumn=true;
    } else result+=",";
   }
   else if(input.compare(pos,3,"‖")==0 || input.compare(pos,3,"∥")==0) { pos+=3; if(norms) { --norms; result+=closeNorm(); } else { ++norms; result+="norm("; } }
   else result+=input[pos++];
   if(result.size()>131072) throw std::runtime_error(error("Expanded TeX expression exceeds the size limit"));
  }
  if((close || matrix || setClose || !roundClose.empty()) && !closed) throw std::runtime_error(error("Unclosed TeX group or environment"));
  if(norms) throw std::runtime_error(error("Unclosed norm delimiter"));
  if(alignment) {
   if(!alignmentCells.empty() || !trim(result).empty())finishAlignment();
   if(expressions.empty())throw std::runtime_error(error("An alignment requires an expression"));
   std::string words=sampleWordDefinitions(expressions);
   if(!words.empty()) {--depth;return words;}
   std::string graph=binaryFunctionGraph(expressions);
   if(!graph.empty()) {--depth;return graph;}
   result=expressions.size()==1 ? "" : "vector(";
   for(size_t i=0;i<expressions.size();++i) {if(i)result+=",";result+="("+expressions[i]+")";}
   if(expressions.size()>1)result+=")";
   if(result.size()>131072)throw std::runtime_error(error("Expanded TeX expression exceeds the size limit"));
   if(depth==2) {rootAlignment=result;rootLines=expressions;}
  }
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
 std::string run(std::vector<std::string> *lines) {
  std::string result=read();
  std::string integers=explicitIntegerList(result);
  if(!integers.empty())return integers;
  std::string list=orderedKetList(result);
  if(!list.empty())return list;
  if(result.find("...")!=std::string::npos && result.find("_{")!=std::string::npos) {
   auto labels=indexedParts(result,",");
   if(labels.size()==3 && labels[1]=="...") {
    list=indexedLabelRange(labels[0],labels[2],"qindexedentries(");
    if(!list.empty())return list;
   }
  }
  if(lines && !rootLines.empty() && trim(result)==rootAlignment)*lines=rootLines;
  return result;
 }
};
}
std::string quantumTeX(const std::string &input) {
 return quantumTeX(input,nullptr);
}
std::string quantumTeX(const std::string &input, std::vector<std::string> *lines) {
 return quantumTeX(input,lines,nullptr);
}
std::string quantumTeX(const std::string &input, std::vector<std::string> *lines, bool *setNotation) {
 if(lines)lines->clear();
 if(setNotation)*setNotation=false;
 // Strip only a complete paired math wrapper. A dollar inside an expression
 // remains an error in the quantum grammar.
 size_t first=input.find_first_not_of(" \t\r\n"), last=input.find_last_not_of(" \t\r\n");
 if(first==std::string::npos) return "";
 // The mode precedes the pasted formula, including any TeX delimiters.
 const bool dimensions=input.compare(first,11,"dimensions:")==0;
 const bool fractionBits=input.compare(first,13,"fractionbits:")==0;
 const bool bitWord=input.compare(first,8,"bitword:")==0;
 const bool spinNumber=input.compare(first,5,"spin:")==0;
 if(dimensions || fractionBits || bitWord || spinNumber) {
  first=input.find_first_not_of(" \t\r\n",first+(dimensions ? 11 : fractionBits ? 13 : spinNumber ? 5 : 8));
  if(first==std::string::npos)return "";
 } else if(input.compare(first,5,"sets:")==0) {
  if(setNotation)*setNotation=true;
  first=input.find_first_not_of(" \t\r\n",first+5);
  if(first==std::string::npos)return "";
 }
 // Session declarations surround the translated expression. Keep the lesson's
 // math delimiters and punctuation available to the ordinary TeX reader.
 const size_t contextStart=first;
 std::vector<std::string> contexts;
 while(input.compare(first,14,"matrixcontext(")==0) {
  size_t end=input.find("):",first+14);
  if(end==std::string::npos || contexts.size()>=32)throw std::runtime_error("Invalid matrix declaration context.");
  contexts.push_back(input.substr(first,end-first));
  first=input.find_first_not_of(" \t\r\n",end+2);
  if(first==std::string::npos)throw std::runtime_error("Expected an expression after the matrix declaration.");
 }
 if(!contexts.empty()) {
  std::string result=quantumTeX(input.substr(0,contextStart)+input.substr(first),lines,setNotation);
  for(auto context=contexts.rbegin();context!=contexts.rend();++context)result=*context+",("+result+"))";
  return result;
 }
 std::string s=input.substr(first,last-first+1);
 // Inline Markdown can leave the radix point immediately outside the
 // math span, as in .$01$. The selected mode supplies it for $01$ alone.
 if(fractionBits && s.compare(0,2,".$")==0)s.erase(0,1);
 bool mathWrapper=true;
 if(s.size()>=4 && s.substr(0,2)=="$$" && s.substr(s.size()-2)=="$$") s=s.substr(2,s.size()-4);
 else if(s.size()>=2 && s.front()=='$' && s.back()=='$') s=s.substr(1,s.size()-2);
 else if(s.size()>=4 && ((s.substr(0,2)=="\\(" && s.substr(s.size()-2)=="\\)") || (s.substr(0,2)=="\\[" && s.substr(s.size()-2)=="\\]"))) s=s.substr(2,s.size()-4);
 else mathWrapper=false;
 if(spinNumber) {
  // Only the bare symbol S changes meaning in a declared scalar spin formula.
  // Keep named operators, quoted labels and other TeX commands independent.
  static const std::regex spinArithmetic(R"(^[0-9S .()+*/^\t\r\n−-]+$)");
  if(!std::regex_match(s,spinArithmetic) || s.find('S')==std::string::npos)
   throw std::runtime_error("Spin notation requires an arithmetic expression in the total-spin quantum number S.");
  for(size_t at=s.find('S');at!=std::string::npos;at=s.find('S',at)) {
   std::string value="qspinnumber(\"S\")";
   if(at && (isdigit((unsigned char)s[at-1]) || s[at-1]==')'))value="*"+value;
   s.replace(at,1,value);at+=value.size();
  }
 }
 if(mathWrapper) {
  if(s.find("\\text{aq[")!=std::string::npos || s.find("\\text{tq[")!=std::string::npos) {
   static const std::regex label(R"(^\s*\\text\{((?:aq|tq)\[(?:0|[1-9][0-9]*)\])\}\s*$)");
   std::smatch match;
   if(std::regex_match(s,match,label))return "\""+match[1].str()+"\"";
   const std::string body=trim(s),begin="\\begin{aligned}",end="\\end{aligned}";
   if(body.size()>=begin.size()+end.size() && body.compare(0,begin.size(),begin)==0 &&
      body.compare(body.size()-end.size(),end.size(),end)==0) {
    // A placement is an injective relation. Preserve both index columns and
    // the published row order, including layouts over non-contiguous sites.
    static const std::regex row(R"(^\s*\\text\{aq\[(0|[1-9][0-9]*)\]\}\s*&?\s*\\rightarrow\s*\\text\{tq\[(0|[1-9][0-9]*)\],?\}\s*$)");
    std::string table=body.substr(begin.size(),body.size()-begin.size()-end.size()),entries;
    std::set<std::string> logical,physical;
    for(size_t at=0;;) {
     size_t next=table.find("\\\\",at);
     std::string part=table.substr(at,next==std::string::npos ? next : next-at);
     if(!std::regex_match(part,match,row))throw std::runtime_error("Expected an abstract-to-physical qubit placement in every row.");
     std::string from=match[1].str(),to=match[2].str();
     if(!logical.insert(from).second || !physical.insert(to).second)
      throw std::runtime_error("A qubit layout must use each abstract and physical qubit at most once.");
     if(!entries.empty())entries+=",";
     entries+=from+","+to;
     if(next==std::string::npos)break;
     at=next+2;
    }
    return "matrix("+std::to_string(logical.size())+",2,vector("+entries+"))";
   }
  }
  static const std::regex hydrogen(R"(^\s*\\text\{H\}_\{?2\}?\s*$)");
  if(std::regex_match(s,hydrogen))return "\"H₂\"";
  static const std::regex percentage(R"(^\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*\\?%\s*$)");
  std::smatch percent;
  if(std::regex_match(s,percent,percentage))return "("+percent[1].str()+"/100)";
  s=withoutTeXCommentLines(s);
  if(s.find("\\text{X}")!=std::string::npos) {
   static const std::regex dataset(R"(\\text\{X\}(?:_\{\\text\{([a-z]+)\}\}|_\\text\{([a-z]+)\}))");
   std::smatch label;
   while(std::regex_search(s,label,dataset)) {
    std::string suffix=label[1].matched ? label[1].str() : label[2].str();
    s.replace(label.position(),label.length(),"\"X_"+suffix+"\"");
   }
  }
  // Some displayed equations end in a nonbreaking space before their
  // sentence punctuation or a check mark that annotates the completed proof.
  static const std::regex annotation(R"(\s*~\s*(?:\\checkmark|[.,])\s*$)");
  s=withoutDisplayPunctuation(std::regex_replace(s,annotation,""));
  static const std::regex bellTextSign(R"((\\(?:Phi|Psi|phi|psi))_\\text\{([+-])\})");
  s=std::regex_replace(s,bellTextSign,"$1^$2");
  static const std::regex bell(R"(^\s*(\\(?:Phi|Psi|phi|psi))\^\{?([+-])\}?\s*$)");
  std::smatch m;
  if(std::regex_match(s,m,bell))return quantumTeX("\\vert"+m[1].str()+"^"+m[2].str()+"\\rangle");
  // An explicitly typeset gate label introduces the displayed definition.
  // Keep the matrix in the author's stated wire order.
  static const std::regex definition(R"(^\s*\\text\{CNOT\}\s*=\s*(?=\\begin\{[bp]matrix\}))");
  s=std::regex_replace(s,definition,"qoperatorref(\"CNOT\") = ");
 }
 if(s.find("\\sum_")!=std::string::npos) {
  // The classical fidelity definition names a function on an ordered
  // pair of distributions. Keep its sum over the common outcome set.
  static const std::regex distributionPair(R"(^\s*F\(\s*([a-z])\s*,\s*([a-z])\s*\)\s*=\s*)");
  std::smatch pair;
  if(std::regex_search(s,pair,distributionPair)) {
   std::string domain="qtuple(vector(\""+pair[1].str()+"\",\""+pair[2].str()+"\"))";
   return "qcompare(qfiniteapply(\"F\","+domain+"),"+quantumTeX(s.substr(pair.length()))+",4)";
  }
 }
 if(s.find("\\sum_")!=std::string::npos) {
  static const std::regex weightedPaulis(R"(^\s*H\s*=\s*(\\sum_\{([a-z])=\d+\}\^[A-Za-z0-9]+\s*\\alpha_\2\s*P_\2)\s*$)");
  std::smatch paulis;
  if(std::regex_match(s,paulis,weightedPaulis))
   return "qcompare(qoperatorref(\"H\"),"+quantumTeX(paulis[1].str())+",4)";
  // A sum of N local contributions with no printed starting index.
  static const std::regex localTerms(R"(^\s*([A-Z])\s*=\s*\\sum_([a-z])\^([A-Z])\s*\{\s*\1_\2\s*\}\s*$)");
  std::smatch m;
  if(std::regex_match(s,m,localTerms)) {
   const std::string name=m[1].str();
   return "qcompare(qoperatorref(\""+name+"\"),qindexedsum(\""+name+"_\",1,"+m[3].str()+",vector()),4)";
  }
 }
 if(s.find("...")!=std::string::npos && s.find("\\rangle")!=std::string::npos) {
  // The digit labels a repeated state and the subscript labels its wire.
  static const std::regex uniformKet(R"(\|([01])_1\s*\.\.\.\s*\1_[a-z]\s*\.\.\.\s*\1_([A-Z])\s*\\rangle)");
  s=std::regex_replace(s,uniformKet,"qtensorpow(|$1>,\"$2\")");
 }
 if(s.find("\\delta")!=std::string::npos && s.find("\\text{for")!=std::string::npos) {
  static const std::regex orbit(R"(^\s*\|\\phi_([a-z])\\rangle\s*=\s*e\^\{-i\s*\\,\s*\\delta\s*t\s*\1\s*H\}\s*\|\\phi_0\\rangle,\s*\\quad\s*\\text\{for\s*\}\s*\1\s*=\s*0,\s*1,\s*\\(?:dots|ldots),\s*([a-z])-1\s*(?:\\quad\s*\\text\{\})?\s*$)");
  std::smatch m;
  if(std::regex_match(s,m,orbit)) {
   std::string count=m[2].str();
   return "qcompare(qindexedketlist(\"φ_\",0,("+count+"-1),vector()),qkrylovstates(\"H\",qketstate(\"φ_0\"),\"δt\","+count+"),4)";
  }
 }
 if(s.find("\\begin{pmatrix}")!=std::string::npos && s.find("\\quad")!=std::string::npos) {
  // A parenthesized dimension after an indexed matrix constrains its
  // definition. It is not a factor multiplying the matrix.
  static const std::regex dimension(R"(^\s*([A-Z])\s*=\s*(\\begin\{pmatrix\}[\s\S]*?\\end\{pmatrix\})\s*\\quad\s*\(([A-Z])\s*=\s*(\d+)\^([a-z])\)\s*$)");
  std::smatch m;
  if(std::regex_match(s,m,dimension) && m[2].str().find(m[1].str()+"_{")!=std::string::npos) {
   std::string entries=quantumTeX(m[2].str());
   return "(qcompare(qoperatorref(\""+m[1].str()+"\"),"+entries+",4) and qcompare(\""+m[3].str()+"\","+m[4].str()+"^"+m[5].str()+",4))";
  }
 }
 // A subscript belongs to the angular frequency. Preserve the imaginary
 // unit and optional Pauli generator as separate factors in a phase.
 if(s.find("\\omega_")!=std::string::npos && s.find("e^{")!=std::string::npos) {
  static const std::regex phase(R"(e\^\{(-?)i([XYZ]?)\\omega_([A-Za-z])\s+([a-z](?:_[0-9])?|\([a-z]-[a-z]_[0-9]\))/(\d+)\})");
  std::smatch m;
  while(std::regex_search(s,m,phase)) {
   std::string angle="(\"ω_"+m[3].str()+"\"*("+quantumTeX(m[4].str())+")/"+m[5].str()+")";
   std::string value=m[2].str().empty() ? "qexp("+m[1].str()+"i*"+angle+")" :
      "qpropagator("+m[2].str()+","+(m[1].str().empty() ? "-" : "")+angle+")";
   s.replace(m.position(),m.length(),value);
  }
 }
 if(s.find("e^{")!=std::string::npos && s.find('H')!=std::string::npos) {
  // A Krylov matrix element has the same Hamiltonian in both time
  // evolutions and in the operator between them. dt is one time step.
  if(s.find("H\\,dt}")!=std::string::npos) {
   static const std::regex step(R"(e\^\{(-?)i(?:\\,)?(\([a-z]-[a-z]\)|[a-z])?(?:\\,)?H\\,dt\})");
   const std::string original=s;
   std::smatch stepMatch;
   while(std::regex_search(s,stepMatch,step)) {
    std::string factor=stepMatch[2].matched ? stepMatch[2].str() : "1";
    std::string time=(stepMatch[1].matched && !stepMatch[1].str().empty() ? "" : "-")+factor+"*\"dt\"";
    s.replace(stepMatch.position(),stepMatch.length(),"qpropagator(\"H\","+time+")");
   }
   if(s!=original) {
    static const std::regex insertion(R"((\)|\|)H(?=qpropagator\())");
    s=std::regex_replace(s,insertion,"$1qoperatorref(\"H\")*");
   }
  }
  static const std::regex dimensioned(R"(e\^\{\s*(?:-|−)\s*i\s*H\s*([a-z])\s*/\s*\\hbar\s*\})");
  s=std::regex_replace(s,dimensioned,"qpropagator(\"H\",($1/ℏ))");
  static const std::regex evolution(R"(e\^\{\s*(?:-|−)\s*i\s*H(?:_([A-Z]))?\s*([a-z])(?:/([a-z0-9]))?\s*\})");
  static const std::regex combined(R"(e\^\{\s*-i\(H_([A-Z])\s*\+\s*H_([A-Z])\)([a-z])\})");
  s=std::regex_replace(s,combined,"qpropagator((\"H_$1\"+\"H_$2\"),$3)");
  std::smatch m;
  while(std::regex_search(s,m,evolution)) {
   std::string name=m[1].matched ? "H_"+m[1].str() : "H";
   std::string time=m[2].str()+(m[3].matched ? "/"+m[3].str() : "");
   s.replace(m.position(),m.length(),"qpropagator(\""+name+"\","+time+")");
  }
  if(s.find("qpropagator(")!=std::string::npos) {
   static const std::regex definition(R"(^\s*U\(([a-z])\)\s*=)");
   s=std::regex_replace(s,definition,"qoperatorref(qindexedlabel(\"U(\",$1,\")\"))=");
   auto distinct=indexedParts(s,"\\neq");
   if(distinct.size()==2)return "qoperatorunequal("+quantumTeX(distinct[0])+","+quantumTeX(distinct[1])+")";
   static const std::regex initialState(R"(\\phi\(([a-z])=0\))");
   s=std::regex_replace(s,initialState,"\\phi(0)");
  }
 }
 if(mathWrapper) {
  static const std::regex dimensionOrder(R"(^\s*([a-z])'\s*([<>])\s*([a-z])\s*$)");
  std::smatch dimensions;
  if(std::regex_match(s,dimensions,dimensionOrder))return "\""+dimensions[1].str()+"_prime\""+dimensions[2].str()+"\""+dimensions[3].str()+"\"";
  if(s.find("\\vec{")!=std::string::npos && s.find("\\mathbb{R}")!=std::string::npos) {
   static const std::regex realSpace(R"(^\s*(.+?)\s*\\in\s*\\mathbb\{R\}\^\{?([a-zA-Z0-9])('?)\}?\s*$)");
   if(std::regex_match(s,dimensions,realSpace)) {
    std::string dimension=dimensions[2].str();
    if(!isdigit((unsigned char)dimension[0]))dimension="\""+dimension+(dimensions[3].str().empty() ? "" : "_prime")+"\"";
    return "qrealvectormember("+quantumTeX("$"+dimensions[1].str()+"$")+","+dimension+")";
   }
  }
  if(s.find("\\begin{array}{c}")!=std::string::npos && s.find('=')!=std::string::npos) {
   static const std::regex equations(R"(^\s*\\left\\\{\s*\\begin\{array\}\{c\}([\s\S]+)\\end\{array\}\s*\\right\\\}\s*$)");
   std::smatch group;
   if(std::regex_match(s,group,equations))
    s="\\begin{gathered}"+group[1].str()+"\\end{gathered}";
  }
  if(s.find_first_of("IXYZ")!=std::string::npos &&
     (s.find('+')!=std::string::npos || s.find('-')!=std::string::npos)) {
   static const std::regex pauliSum(R"(^\s*(?:\\hat\{([A-Z])\}_\{?([0-9]+)\}?\s*:?=\s*)?([+-]?\s*(?:[0-9]+(?:\.[0-9]+)?\s+)?[IXYZ]{2,}(?:\s*[+-]\s*(?:[0-9]+(?:\.[0-9]+)?\s+)?[IXYZ]{2,})+)\s*$)");
   static const std::regex term(R"(([+-]?)\s*(?:([0-9]+(?:\.[0-9]+)?)\s+)?([IXYZ]{2,}))");
   std::smatch expansion;
   if(std::regex_match(s,expansion,pauliSum)) {
    std::string body=expansion[3].str(),expression;size_t width=0;
    for(std::sregex_iterator it(body.begin(),body.end(),term),end;it!=end;++it) {
     std::string word=(*it)[3].str();
     if(width && word.size()!=width)throw std::runtime_error("Pauli strings in a Hamiltonian must have equal register width.");
     width=word.size();
     std::string coefficient=(*it)[2].matched ? (*it)[2].str() : "1";
     if((*it)[1].str()=="-")coefficient="-"+coefficient;
     std::string part="qmul("+coefficient+",pauli(\""+word+"\"))";
     expression=expression.empty() ? part : "qadd("+expression+","+part+")";
    }
    if(expansion[1].matched)return "qcompare(qoperatorref(\""+expansion[1].str()+"_"+expansion[2].str()+"\"),"+expression+",4)";
    return expression;
   }
  }
  // In variational notation rho inside a ket names a state, including
  // when rho elsewhere in the same document denotes a density operator.
  static const std::regex rhoKet(R"(\|\s*\\rho\s*\\rangle)");
  s=std::regex_replace(s,rhoKet,"qketstate(\"ρ_ref\")");
  static const std::regex unbracedTheta(R"(\\vec\s*\\theta(?![A-Za-z]))");
  s=std::regex_replace(s,unbracedTheta,"\\vec{\\theta}");
  static const std::regex optimum(R"(\\vec\{\\theta\}\^(?:\*|\{\*\}))");
  s=std::regex_replace(s,optimum,"qvectorref(\"θ_star\")");
  if(s.find("\\pmod")==std::string::npos && s.find("\\bmod")==std::string::npos &&
     (s.find("qketstate(\"ρ_ref\")")!=std::string::npos || s.find("U_R")!=std::string::npos ||
      s.find("U_{R}")!=std::string::npos || s.find("U_V")!=std::string::npos)) {
   static const std::regex definition(R"(\\equiv\b)");
   s=std::regex_replace(s,definition,"=");
  }
  if(s.find("\\rangle")!=std::string::npos && s.find('_')!=std::string::npos) {
   static const std::string local=R"((?:[XYZH]_(?:[0-9]|\{[0-9]+\})|CNOT_\{[0-9]{2}\}))";
   static const std::regex action("((?:"+local+"\\s*)+)\\|([01]+)\\\\rangle");
   static const std::regex gate(R"(([XYZH])_\{?([0-9]+)\}?|CNOT_\{([0-9])([0-9])\})");
   std::smatch match;
   while(std::regex_search(s,match,action)) {
    std::string gates=match[1].str(),state="|"+match[2].str()+">";
    if(std::regex_match(s.substr(0,match.position()),std::regex(R"(^\s*U_(?:R|\{R\})\s*=\s*$)")))
     throw std::runtime_error("A reference operator cannot equal a prepared ket. Apply the operator to the all-zero input to compare the two states.");
    std::vector<std::string> applications;
    for(std::sregex_iterator it(gates.begin(),gates.end(),gate),end;it!=end;++it) {
     auto &g=*it;
     applications.push_back(g[1].matched ? "qwireapply("+g[1].str()+","+g[2].str()+",-1," :
          "qwireapply(X,"+g[4].str()+","+g[3].str()+",");
    }
    for(auto it=applications.rbegin();it!=applications.rend();++it)state=*it+state+")";
    s.replace(match.position(),match.length(),state);
   }
  }
  static const std::regex referenceGate(R"(^\s*U_(?:R|\{R\})\s*=\s*(I|([XYZH])_\{?([0-9]+)\}?)\s*$)");
  std::smatch refGate;
  if(std::regex_match(s,refGate,referenceGate)) {
   const std::string ref="qoperatorref(\"U_R\")";
   std::string gate=refGate[1].str()=="I" ? "qidentitylike("+ref+")" :
      "qwireoperatorlike("+refGate[2].str()+","+refGate[3].str()+","+ref+")";
   return "qcompare("+ref+","+gate+",4)";
  }
  static const std::regex referenceZero(R"(U_(?:R|\{R\})\s*\|0\\rangle)");
  s=std::regex_replace(s,referenceZero,"qzeroimage(qoperatorref(\"U_R\"))");
  static const std::regex unitaryReference(R"(U_(?:R|\{R\})(?![A-Za-z0-9_\"']))");
  s=std::regex_replace(s,unitaryReference,"qoperatorref(\"U_R\")");
  static const std::regex layer(R"(U_(?:V|\{V\})\s*\()");
  s=std::regex_replace(s,layer,"qoperatorat(\"U_V\",");
  static const std::regex seriesCoefficients(R"(^\s*\\\{([a-z])_0,\s*\1_([a-z]),\s*([a-z])_\2\\\}_\{\2=1\}\^([A-Z])\s*$)");
  std::smatch coefficients;
  if(std::regex_match(s,coefficients,seriesCoefficients)) {
   std::string order="\""+coefficients[4].str()+"\"";
   return "qsetunion(qindexedset(\""+coefficients[1].str()+"_\",0,"+order+",vector()),qindexedset(\""+
        coefficients[3].str()+"_\",1,"+order+",vector()))";
  }
  static const std::regex normalEquations(R"(^\s*([A-Z])\^\\dagger\s*\1([a-z])\s*=\s*\1\^\\dagger\s*([a-z])\s*$)");
  if(std::regex_match(s,coefficients,normalEquations)) {
   std::string matrix="qoperatorref(\""+coefficients[1].str()+"\")",adjoint="qdag("+matrix+")";
   return "qcompare(qmul("+adjoint+",qmul("+matrix+",qvectorref(\""+coefficients[2].str()+
       "\"))),qmul("+adjoint+",qvectorref(\""+coefficients[3].str()+"\")),4)";
  }
  static const std::regex indexedCost(R"(\bC_([a-z0-9])\(\s*(?=\\vec))");
  s=std::regex_replace(s,indexedCost,"qscalarat(qindexedlabel(\"C_\",\"$1\",\"\"),");
  static const std::regex gradient(R"(\\vec\{\\nabla\}\s*C\s*\()");
  s=std::regex_replace(s,gradient,"qfeatureat(\"∇C\",");
  static const std::regex costOnIndexedInput(R"(\bC\(\s*x_(?:\{([a-z0-9]+)\}|([a-z0-9]))\s*\))");
  s=std::regex_replace(s,costOnIndexedInput,"qscalarat(\"C\",\"x_$1$2\")");
  static const std::regex costOnVector(R"(\bC\(\s*(?=\{?(?:\\vec|qvectorref)))");
  s=std::regex_replace(s,costOnVector,"qscalarat(\"C\",");
  static const std::regex probability(R"(^\s*P_([a-z0-9])\s*=\s*\|\\langle\s*\\phi_\1\s*\|\s*\\psi\s*\\rangle\|\^2\s*$)");
  std::smatch prob;
  if(std::regex_match(s,prob,probability)) {
   std::string index=prob[1].str();
   return "qcompare(\"P_"+index+"\",qpower(qbars(qmul(qdag(qketstate(\"φ_"+index+"\")),qketstate(\"ψ\"))),2),4)";
  }
  static const std::regex overlapProbability(R"(^\s*([pP]_(?:[A-Za-z0-9]|\\[a-zA-Z]+))\s*=\s*\|\s*(\\langle[^|]+\|[^|]+\\rangle)\s*\|\^\{?2\}?\s*$)");
  if(std::regex_match(s,prob,overlapProbability))
   return "qcompare("+quantumTeX(prob[1].str())+",qpower(qbars("+quantumTeX(prob[2].str())+"),2),4)";
  if(s.find("C_\\text{")!=std::string::npos && s.find("\\vec")!=std::string::npos) {
   static const std::regex costLabel(R"(C_\\text\{([A-Za-z]+)\}\s*\()");
   static const std::regex hamiltonian(R"(\\hat\{H\})");
   s=std::regex_replace(s,costLabel,"qscalarat(\"C_$1\",");
   s=std::regex_replace(s,hamiltonian,"qoperatorref(\"H\")");
  }
  static const std::regex evolutionOperator(R"(^\s*\\exp\(i([a-z])\\mathcal\{H\}\)\s*$)");
  if(std::regex_match(s,prob,evolutionOperator))return "qpropagator(\"H\",-\""+prob[1].str()+"\")";
  if(s.find("\\rangle_{b")!=std::string::npos) {
   static const std::regex circuitState(R"(\|\\psi\\rangle_\{b(\d+)\})");
   s=std::regex_replace(s,circuitState,"qketstate(\"ψ_b$1\")");
   static const std::regex azimuth(R"(e\^\{i\\theta_(\d)\})");
   s=std::regex_replace(s,azimuth,"qexp(i*\"θ_$1\")");
  }
  static const std::regex gap(R"(^\s*\\vert\s*(E)\s*-\s*E_(\d)\s*\\vert\s*>\s*\\delta\s*$)");
  std::smatch gapMatch;
  if(std::regex_match(s,gapMatch,gap))
   return "qdistancegreater(\"E\",\"E_"+gapMatch[2].str()+"\",\"δ\")";
  if(s.find("T_")!=std::string::npos && s.find("\\left(")!=std::string::npos) {
   static const std::regex chebyshev(R"(T_([a-z0-9])(\^\{-1\})?\s*\\left\()");
   std::smatch polynomial;
   bool found=false;
   while(std::regex_search(s,polynomial,chebyshev)) {
    std::string degree=polynomial[1].str();
    if(!isdigit((unsigned char)degree[0]))degree="\""+degree+"\"";
    std::string value=(polynomial[2].matched ? "1/" : "")+std::string("qchebyshev(")+degree+",";
    s.replace(polynomial.position(),polynomial.length(),value);found=true;
   }
   if(found) {
    static const std::regex trailingSpace(R"(,\s*\\quad\s*$)");
    s=std::regex_replace(s,trailingSpace,"");
    static const std::regex minimax(R"(\\beta\(\s*([a-z]),\s*([a-z]),\s*([a-z])\s*\))");
    s=std::regex_replace(s,minimax,"qscalarat(\"β\",vector(\"$1\",\"$2\",\"$3\"))");
    static const std::regex extremal(R"(p\^\*\s*(?:\\left)?\()");
    s=std::regex_replace(s,extremal,"qscalarat(\"p_star\",");
    static const std::regex energyFunction(R"(([fg])\(E\))");
    s=std::regex_replace(s,energyFunction,"qscalarat(\"$1\",\"E\")");
    static const std::regex step(R"((?:\\,)?dt)");
    s=std::regex_replace(s,step,"*\"dt\"");
   }
  }
  static const std::regex projectedEigenproblem(R"(^\s*\\tilde\{H\}\s*\\vec\{([a-z])\}\s*=\s*([a-z])\s+S\s*\\vec\{\1\}\s*$)");
  std::smatch eigenproblem;
  if(std::regex_match(s,eigenproblem,projectedEigenproblem)) {
   std::string state="qvectorref(\"vector_"+eigenproblem[1].str()+"\")";
   return "qcompare(qmul(qoperatorref(\"H_tilde\"),"+state+"),qmul(\""+eigenproblem[2].str()+
      "\",qmul(qoperatorref(\"S\"),"+state+")),4)";
  }
  if(s.find("f(H)")!=std::string::npos && s.find("f(E_")!=std::string::npos) {
   static const std::regex hFilter(R"(f\(H\))");
   static const std::regex energyFilter(R"(f\(E_([a-z])\))");
   static const std::regex amplitude(R"(\\gamma_([a-z])(?=f\(E_))");
   s=std::regex_replace(s,amplitude,"qindexedlabel(\"γ_\",$1,\"\")*");
   s=std::regex_replace(s,hFilter,"qpolynomialat(\"f\",qoperatorref(\"H\"))");
   s=std::regex_replace(s,energyFilter,"qpolynomialat(\"f\",E_$1)");
  }
  // A cost on a ket and a filter on an energy have scalar function values.
  static const std::regex scalarInput(R"((^|[^A-Za-z])f\(\s*(?=\||E_(?:[A-Za-z0-9]|\{)))");
  s=std::regex_replace(s,scalarInput,"$1qscalarat(\"f\",");
  if(s.find("qscalarat(")!=std::string::npos) {
   static const std::regex polynomialAtZero(R"((^|[^A-Za-z])p\(0\))");
   s=std::regex_replace(s,polynomialAtZero,"$1qscalarat(\"p\",0)");
  }
  // Indexed energies in a weighted energy sum are scalars, including E_0(1).
  if(s.find("\\sum")!=std::string::npos) {
   static const std::regex energyFactor(R"((E_(?:[0-9]|\{[0-9]+\}))\s*\(([0-9]+)\))");
   s=std::regex_replace(s,energyFactor,"$1 * ($2)");
  }
  // A named shot count is a single variable in sampling-error formulas.
  static const std::regex shotRoot(R"(\\sqrt\{\s*shots\s*\})");
  s=std::regex_replace(s,shotRoot,"qsqrt(\"shots\")");
  // Adjacent coefficient letters inside a squared modulus denote a product.
  // Quote both factors so physical constants cannot replace state amplitudes.
  if(s.find('|')!=std::string::npos) {
   static const std::regex productProbability(R"(\|([ab])([cd])\|\s*\^\s*(?:\{2\}|2)(?![0-9]))");
   s=std::regex_replace(s,productProbability,"qpower(qbars(qmul(\"$1\",\"$2\")),2)");
  }
  if(s.find("\\rangle")!=std::string::npos) {
   static const std::regex ketCoefficient(R"((^|[=(+\-]\s*)([a-d])\s*(?=\|[01]\\rangle))");
   s=std::regex_replace(s,ketCoefficient,"$1\"$2\"*");
  }
  // A proportionality coefficient between two named kets is a scalar.
  static const std::regex scaledKet(R"((\\rangle\s*=\s*)c\s*(?=\|))");
  s=std::regex_replace(s,scaledKet,"$1\"c\"*");
 }
 if(s.find("H_{\\mathcal{")!=std::string::npos) {
  static const std::regex projected(R"(H_\{\\mathcal\{([A-Z])\}\^\{\(([a-z])\)\}\})");
  std::smatch m;
  if(std::regex_search(s,m,projected)) {
   const std::string index=m[2].str();
   s=std::regex_replace(s,projected,"qoperatorref(qindexedlabel(\"H_$1(\",\"$2\",\")\"))");
   // The parenthesized superscripts in this subspace eigenproblem
   // identify the sampled batch on the eigenvector and energy as well.
   const std::string superscript="^{("+index+")}";
   for(const std::string &name:{std::string("\\psi"),std::string("E")}) {
    std::string token=name+superscript;
    std::string value=name=="E" ? "qindexedlabel(\"E(\",\""+index+"\",\")\")" : "\\psi("+index+")";
    for(size_t pos=s.find(token);pos!=std::string::npos;pos=s.find(token,pos+value.size()))
     s.replace(pos,token.size(),value);
   }
  }
 }
 if(s.find("U_{")!=std::string::npos) {
  static const std::regex applied(R"(U_\{\\text\{([A-Za-z]+)\}\}\s*\()");
  s=std::regex_replace(s,applied,"qoperatorat(\"U_$1\",");
  static const std::regex plainApplied(R"(U_\{([A-Za-z]{2,})\}\s*\()");
  s=std::regex_replace(s,plainApplied,"qoperatorat(\"U_$1\",");
  static const std::regex named(R"(U_\{\\text\{([A-Za-z]+)\}\})");
  s=std::regex_replace(s,named,"qoperatorref(\"U_$1\")");
 }
 if(s.find("\\vec{")!=std::string::npos) {
  const std::string vec=R"(\\vec\{[A-Za-z]\}(?:_(?:\{[A-Za-z0-9]+\}|[A-Za-z0-9]))?)";
  static const std::regex kernel("(^|[^A-Za-z])k\\(\\s*("+vec+"),\\s*("+vec+")\\s*\\)");
  static const std::regex dot("("+vec+")\\s*\\^(?:T|\\{T\\})\\s*(?:\\\\cdot\\s*)?("+vec+")");
  std::smatch call;
  const std::string phi=R"((?:\\vec\{\\Phi\}|\\Phi))";
  static const std::regex featureDot(phi+"\\^T\\(("+vec+")\\)\\s*(?:\\\\cdot\\s*)?"+phi+"\\(("+vec+")\\)");
  static const std::regex weightDot("\\\\Theta\\^T\\s*"+phi+"\\(("+vec+")\\)");
  static const std::regex featureCall(phi+"\\(("+vec+")\\)");
  static const std::regex modelCall("f_([0-9]+)\\(("+vec+")\\)");
  auto vectorArgument=[&](const std::string &arg) {
   static const std::regex subscript(R"(^\\vec\{([a-zA-Z])\}_\{?([a-z])\}?$)");
   std::smatch parts;
   if(std::regex_match(arg,parts,subscript) && s.find("\\sum_{"+parts[2].str()+"=")!=std::string::npos)
    return "qvectorref("+parts[1].str()+"_"+parts[2].str()+")";
   return quantumTeX("$"+arg+"$");
  };
  auto feature=[&](const std::string &arg) {
   return "qfeatureat(\"Φ\","+vectorArgument(arg)+")";
  };
  if(s.find("f_\\theta")!=std::string::npos) {
   const std::string model="f_\\\\theta\\(("+vec+")\\)";
   static const std::regex labels("^\\s*"+model+"\\s*\\\\rightarrow\\s*\\\\pm\\s*1\\s*$");
   if(std::regex_match(s,call,labels)) {
    std::string output="qscalarat(\"f\",vector(\"θ\","+vectorArgument(call[1].str())+"))";
    return "qcompare(qpower("+output+",2),1,4)";
   }
   static const std::regex expectation("^\\s*"+model+R"(\s*=\s*\\langle\s*0\|U\^\{\\dagger\}\(\1\)W\^\\dagger\(\\theta\)OW\(\\theta\)U\(\1\)\|0\\rangle\s*$)");
   if(std::regex_match(s,call,expectation)) {
    std::string input=vectorArgument(call[1].str());
    std::string state="qmul(qoperatorat(\"W\",\"θ\"),qzeroimage(qoperatorat(\"U\","+input+")))";
    return "qcompare(qscalarat(\"f\",vector(\"θ\","+input+")),qexpect(qoperatorref(\"O\"),"+state+"),4)";
   }
  }
  static const std::regex featureKet("\\|\\\\Phi\\(("+vec+")\\)\\\\rangle");
  static const std::regex featureOperator(R"(\\mathscr\{U\}_\{\\text\{([A-Za-z]+)\}\}\s*(?:\\left)?\()");
  s=std::regex_replace(s,featureOperator,"qoperatorat(\"U_$1\",");
  static const std::regex bareEncoder("(^|[^A-Za-z])U\\(("+vec+")\\)");
  while(std::regex_search(s,call,bareEncoder)) {
   std::string value=call[1].str()+"qoperatorat(\"U\","+vectorArgument(call[2].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  static const std::regex indexedPhase("\\\\phi_([A-Za-z])\\(("+vec+")\\)");
  while(std::regex_search(s,call,featureKet)) {
   std::string value="qstatecall(\"Φ\","+vectorArgument(call[1].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,indexedPhase)) {
   std::string value="qscalarat(\"φ_"+call[1].str()+"\","+vectorArgument(call[2].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,featureDot)) {
   std::string value="qvectordot("+feature(call[1].str())+","+feature(call[2].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,weightDot)) {
   std::string value="qvectordot(qvectorref(\"Θ\"),"+feature(call[1].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,featureCall)) {
   std::string value=feature(call[1].str());
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,modelCall)) {
   std::string value="qscalarat(\"f_"+call[1].str()+"\","+vectorArgument(call[2].str())+")";
   s.replace(call.position(),call.length(),value);
  }
  while(std::regex_search(s,call,kernel)) {
   std::string args="vector("+vectorArgument(call[2].str())+","+vectorArgument(call[3].str())+")";
   s.replace(call.position(),call.length(),call[1].str()+"qscalarat(\"k\","+args+")");
  }
  while(std::regex_search(s,call,dot)) {
   std::string args=vectorArgument(call[1].str())+","+vectorArgument(call[2].str());
   s.replace(call.position(),call.length(),"qvectordot("+args+")");
  }
  static const std::regex neuron(R"(^\s*f\(\\vec\{([a-z])\}\)\s*=\s*\\sigma\s*\(\\vec\{([a-z])\}\\cdot\s*\\vec\{\1\}\s*\+\s*\\vec\{([a-z])\}\)\s*$)");
  if(std::regex_match(s,call,neuron)) {
   std::string input="qvectorref(\""+call[1].str()+"\")",weights="qvectorref(\""+call[2].str()+"\")";
   // The displayed perceptron has one output, hence one bias component.
   return "qcompare(qscalarat(\"f\","+input+"),qscalarat(\"σ\",qadd(qvectordot("+weights+","+input+"),\""+call[3].str()+"\")),4)";
  }
  static const std::regex vectorLabel(R"(\\vec\{(\\[A-Za-z]+|[A-Za-z])(?:_([0-9a-zA-Z]))?\}(?:_(?:\\text\{([A-Za-z]+)\}|\{([A-Za-z](?:[+\-][0-9]+)?|[0-9]+)\}|([a-zA-Z0-9])))?)");
  std::smatch m;
  while(std::regex_search(s,m,vectorLabel)) {
   if(m[2].matched && (m[3].matched || m[4].matched || m[5].matched))
    throw std::runtime_error("A vector label has two subscripts.");
   std::string base=quantumTeX(m[1].str()),label;
   if(m[3].matched)label="\""+base+"_"+m[3].str()+"\"";
   else {
    std::string sub=m[2].str()+m[4].str()+m[5].str();
    if(!sub.empty() && asciiLetter(sub[0]))sub="\""+sub.substr(0,1)+"\""+sub.substr(1);
    label=sub.empty() ? "\""+base+"\"" : "qindexedlabel(\""+base+"_\",("+sub+"),\"\")";
   }
   s.replace(m.position(),m.length(),"qvectorref("+label+")");
  }
 }
 if(s.find("\\langle")!=std::string::npos) {
  // An observable in angle brackets needs a state. Carry the label so
  // ideal and measured expectations can later receive different states.
  static const std::regex average(R"(\\langle\s*([A-Z])\s*\\rangle(?:_\\text\{([A-Za-z]+)\})?(?![_A-Za-z]))");
  std::smatch m;
  while(std::regex_search(s,m,average)) {
   std::string observable=m[1].str();
   if(observable.find_first_not_of("IXYZ")!=std::string::npos)observable="qoperatorref(\""+observable+"\")";
   std::string state=m[2].matched ? m[2].str()+" state" : "measurement state";
   s.replace(m.position(),m.length(),"qexpect("+observable+",qoperatorref(\""+state+"\"))");
  }
 }
 if(mathWrapper && (trim(s)=="\\mu s" || trim(s)=="\\mu\\mathrm{s}"))
  return "qphysicalunit(\"s\",\"micro\")";
 if(s.find("\\hbar")!=std::string::npos && trim(s)=="\\hbar=1")return "qcompare(\"ℏ\",1,4)";
 if(mathWrapper && s.find("H_")!=std::string::npos) {
  // A sum of indexed Hamiltonian terms declares H as an operator.
  static const std::regex decomposition(R"(^\s*H\s*=\s*(H_(?:\{[0-9]+\}|[0-9]+)\s*(?:\+\s*H_(?:\{[0-9]+\}|[0-9]+)\s*)+)\s*$)");
  std::smatch sum;
  if(std::regex_match(s,sum,decomposition)) {
   static const std::regex term(R"(H_(?:\{([0-9]+)\}|([0-9]+)))");
   const std::string rhs=sum[1].str();
   std::string result;
   for(std::sregex_iterator it(rhs.begin(),rhs.end(),term),end;it!=end;++it) {
    const std::string op="qoperatorref(\"H_"+((*it)[1].matched ? (*it)[1].str() : (*it)[2].str())+"\")";
    result=result.empty() ? op : "qadd("+result+","+op+")";
   }
   return "qcompare(qoperatorref(\"H\"),"+result+",4)";
  }
 }
 if(s.find("\\neq")!=std::string::npos) {
  static const std::regex commutator(R"(^\s*\[H_([A-Z]),\s*H_([A-Z])\]\s*\\neq\s*0\s*$)");
  std::smatch m;if(std::regex_match(s,m,commutator)) {
   const std::string a="qoperatorref(\"H_"+m[1].str()+"\")",b="qoperatorref(\"H_"+m[2].str()+"\")";
   return "qoperatorunequal(qmul("+a+","+b+"),qmul("+b+","+a+"))";
  }
 }
 if(s.find("\\langle")!=std::string::npos && s.find("\\rangle")!=std::string::npos && s.find("\\lambda")!=std::string::npos) {
  static const std::regex mean(R"(\\langle\s*([A-Z])\((0|\\lambda(?:_[0-9]+)?)\)\s*\\rangle)");
  std::smatch m;
  while(std::regex_search(s,m,mean)) {
   std::string parameter=m[2]=="0" ? "0" : "\"λ"+m[2].str().substr(7)+"\"";
   s.replace(m.position(),m.length(),"qmeanat(\""+m[1].str()+"\","+parameter+")");
  }
 }
 if(s.find("\\min")!=std::string::npos) {
  static const std::regex minimum(R"(^\s*\\min\s+(f|𝑓)\(\s*(?:[a-z]|𝑥)\s*\)\s*$)");
  if(std::regex_match(s,minimum))return "qsetminimum(qfunctionrange(\"f\"))";
 }
 if(s.find("\\sum_{j}")!=std::string::npos) {
  static const std::regex field(R"(^\s*b_i\s*=\s*-\\sum_\{j\}\s*Q_\{ij\}\s*\+\s*Q_\{ji\}\s*$)");
  if(std::regex_match(s,field))return "qcompare(\"b_i\",qisingfield(\"Q\",\"i\"),4)";
 }
 if(s.find("Q")!=std::string::npos && (s.find("^T")!=std::string::npos || s.find("H_C")!=std::string::npos)) {
  std::string compact=s;compact.erase(std::remove_if(compact.begin(),compact.end(),asciiSpace),compact.end());
  if(compact=="z^TQz+b^Tz")return "qisingenergy(\"Q\",\"b\",\"z\")";
  if(compact=="H_C=\\sum_{ij}Q_{ij}Z_iZ_j+\\sum_ib_iZ_i")
   return "qcompare(qoperatorref(\"H_C\"),qisinghamiltonian(\"Q\",\"b\"),4)";
  static const std::regex equivalent(R"(^\\min_\{x\\in\\\{0,1\\\}\^([a-z])\}x\^TQx\\Longleftrightarrow\\min_\{z\\in\\\{-1,1\\\}\^\1\}z\^TQz\+b\^Tz$)");
  std::smatch m;if(std::regex_match(compact,m,equivalent))return "qisingequivalent(\"Q\",\"b\","+m[1].str()+")";
 }
 if(s.find("\\sum_{ij}")!=std::string::npos && s.find("Q_{ij}")!=std::string::npos) {
  // Each index ranges over the supplied square matrix. Evaluate the body
  // with the actual coefficient and the two selected vector entries.
  std::string compact=s;compact.erase(std::remove_if(compact.begin(),compact.end(),asciiSpace),compact.end());
  const std::string prefix="\\sum_{ij}",binders=",\"weight\",\"leftword\",\"rightword\")";
  auto side=[&](std::string term)->std::string {
   char word=term.find("x_i")!=std::string::npos || term=="x^TQx" ? 'x' : 'z';
   const std::string vector(1,word);
   if(term==vector+"^TQ"+vector)
    return "qpairtotal(\"Q\",\""+vector+"\",\"weight\"*\"leftword\"*\"rightword\""+binders;
   const std::string grouped=vector+"^TQ"+vector+"+(-"+prefix;
   bool subtractLinear=term.compare(0,grouped.size(),grouped)==0 && term.back()==')';
   if(subtractLinear)term=prefix+term.substr(grouped.size(),term.size()-grouped.size()-1);
   if(term.compare(0,prefix.size(),prefix)!=0)return "";
   term.erase(0,prefix.size());
   auto sub=[&](const std::string &from,const std::string &to) {
    size_t at=0;while((at=term.find(from,at))!=std::string::npos) {term.replace(at,from.size(),to);at+=to.size();}
   };
   // Only the coefficient, its two vector entries and scalar arithmetic
   // belong to this index scope. Leave other sums for the ordinary reader.
   sub("\\frac{Q_{ij}}{4}","(W/4)");sub("Q_{ij}","W");
   sub("\\frac{1-"+vector+"_i}{2}","((1-L)/2)");sub("\\frac{1-"+vector+"_j}{2}","((1-R)/2)");
   sub(vector+"_i","L");sub(vector+"_j","R");
   if(term.empty() || term.find_first_not_of("WLR0123456789+-*/()")!=std::string::npos)return "";
   std::string body;
   for(size_t k=0;k<term.size();++k) {
    char ch=term[k];
    if(k && (ch=='W' || ch=='L' || ch=='R' || ch=='(') &&
       (term[k-1]==')' || term[k-1]=='W' || term[k-1]=='L' || term[k-1]=='R' || std::isdigit((unsigned char)term[k-1])))body+='*';
    if(ch=='W')body+="\"weight\"";else if(ch=='L')body+="\"leftword\"";else if(ch=='R')body+="\"rightword\"";else body+=ch;
   }
   std::string sum="qpairtotal(\"Q\",\""+vector+"\","+body+binders;
   if(subtractLinear)return "(qpairtotal(\"Q\",\""+vector+"\",\"weight\"*\"leftword\"*\"rightword\""+binders+"-"+sum+")";
   return sum;
  };
  size_t eq=compact.find('=');
  std::string left=side(compact.substr(0,eq));
  if(!left.empty()) {
   if(eq==std::string::npos)return left;
   std::string right=side(compact.substr(eq+1));
   if(!right.empty())return "qcompare("+left+","+right+",4)";
  }
 }
 if(s.find("\\Delta n_")!=std::string::npos) {
  std::string compact=s;compact.erase(std::remove_if(compact.begin(),compact.end(),asciiSpace),compact.end());
  static const std::regex delta(R"re(^\\begin\{aligned\}\\Deltan_([a-z])\(([a-z]),([a-z])\)&=\\sum\\limits_\{([a-z])=\2\}\^\{\3\}\{\(-1\)\^\4f_\1\(\4\)\}\\end\{aligned\}$)re");
  std::smatch m;
  if(std::regex_match(compact,m,delta)) {
   const std::string a="\""+m[1].str()+"\"",from="\""+m[2].str()+"\"",to="\""+m[3].str()+"\"";
   return "qcompare(qwalkdelta(\"steps\","+a+","+from+","+to+"),qsum((-1)^k*qwalkindicator(\"steps\","+a+",k),"+from+","+to+",k),4)";
  }
  const std::string start="\\begin{aligned}d(i,j)&=\\sum\\limits_{a}{||\\Deltan_a(i,j)||^2}\\\\&=";
  if(compact.compare(0,start.size(),start)==0) {
   std::string tail,terms;
   for(int k=0;k<4;++k) {
    if(k) {tail+="+";terms+="+";}
    tail+="(\\Deltan_"+std::to_string(k)+"(i,j))^2";
    terms+="qwalkdelta(\"steps\","+std::to_string(k)+",\"i\",\"j\")^2";
   }
   if(compact.substr(start.size())==tail+"\\end{aligned}")
    return "qequalchain(vector(qwalkdistance(\"steps\",\"i\",\"j\"),qsum(qwalkdelta(\"steps\",a,\"i\",\"j\")^2,0,3,a),"+terms+"))";
  }
 }
 // In the mode-zero occupation identity every factor is local to that
 // mode; spectator identity factors cancel throughout the derivation.
 if(s.find("f_0^\\dagger")!=std::string::npos || s.find("[X_0,")!=std::string::npos) {
  static const std::regex prefix(R"(\\prod_\{k\s*<\s*0\}\s*\(-Z_k\)\^2)");
  std::string local=std::regex_replace(s,prefix,"I");
  static const std::regex otherSite(R"([A-Za-z]_(?!0\b))");
  if(!std::regex_search(local,otherSite)) {
   s.swap(local);
   static const std::regex commutator(R"(\[X_0,\s*Y_0\])");
   s=std::regex_replace(s,commutator,"qcomm(X,Y)");
   static const std::regex creator(R"(f_0\^\\dagger\s*f_0\b)");
   s=std::regex_replace(s,creator,"qmul(qfcreate(1,0),qfdestroy(1,0))");
   static const std::regex pauli(R"(\b([XYZ])_0\b)");
   s=std::regex_replace(s,pauli,"($1)");
  }
 }
 // Both occupation conventions occur in the lessons. The sign on iY,
 // not the operator's printed name, selects its actual ladder matrix.
 if(s.find("\\prod\\limits")!=std::string::npos && s.find("(-Z_")!=std::string::npos) {
  static const std::regex product(R"(\\Bigl\(\s*\\prod\\limits_\{([a-z])\s*\\lt\s+([a-z])\}\{\(-Z_\1\)\}\s*\\Bigr\)\\Bigl\(\s*\\frac\{X_\2\s*([+-])\s*i\s*Y_\2\}\{2\}\s*\\Bigr\))");
  std::smatch m;
  while(std::regex_search(s,m,product)) {
   const std::string value="qjwimage(N,"+m[2].str()+","+(m[3]=="-" ? "1" : "0")+")";
   s.replace(m.position(),m.length(),value);
  }
  if(s.find("qjwimage(")!=std::string::npos) {
   static const std::regex fermion(R"((?:\\hat\{f\}|\bf)_([a-z])(\^\\dagger)?)");
   while(std::regex_search(s,m,fermion)) {
    std::string op="qoperatorref(qindexedlabel(\"f_\","+m[1].str()+",\"\"))";
    if(m[2].matched)op="qdag("+op+")";
    s.replace(m.position(),m.length(),op);
   }
  }
 }
 if(s.find("\\sigma_")!=std::string::npos) {
  static const std::regex ladder(R"(\\sigma_([a-z]|[0-9]+)\^(?:\{([+-])\}|([+-])))");
  std::smatch m;
  while(std::regex_search(s,m,ladder)) {
   std::string selector=m[2]=="-" || m[3]=="-" ? "1" : "0";
   s.replace(m.position(),m.length(),"qspinladder(N,"+m[1].str()+","+selector+")");
  }
 }
 if(s.find("\\text{")!=std::string::npos && s.find("\\rangle")!=std::string::npos) {
  static const std::regex occupation(R"(\|([01])\\rangle\s*&\s*=\s*\\text\{\s*(empty|occupied)\s*\})");
  s=std::regex_replace(s,occupation,"|$1\\rangle &= qnamedket(\"$2\")");
 }
 if(s.find("\\sigma^")!=std::string::npos) {
  const std::string raising="((X+i*Y)/2)",lowering="((X-i*Y)/2)";
  static const std::regex pair(R"(^\s*\\sigma\^\{?\\pm\}?\s*$)");
  if(std::regex_match(s,pair))return "vector("+raising+","+lowering+")";
  // Preserve independent displayed action equations when their only
  // separator is a line break. A vanishing ket is the zero vector.
  static const std::regex action(R"(^\s*\\sigma\^\{?([+-])\}?\s*\|([01])\\rangle\s*=\s*(0|\|[01]\\rangle)\s*$)");
  std::string block;size_t start=0,count=0;
  while(start<s.size()) {
   size_t end=s.find('\n',start);std::string line=trim(s.substr(start,end-start));
   if(!line.empty()) {
    std::smatch m;if(!std::regex_match(line,m,action)) {block.clear();break;}
    std::string gate=m[1].str()=="+" ? raising : lowering;
    std::string target=m[3].str()=="0" ? "0*|0>" : "|"+m[3].str().substr(1,1)+">";
    if(count++)block+=",";
    block+="qcompare(qmul("+gate+",|"+m[2].str()+">),"+target+",4)";
   }
   if(end==std::string::npos)break;
   start=end+1;
  }
  if(!block.empty())return count==1 ? block : "vector("+block+")";
  static const std::regex plus(R"(\\sigma\^(?:\{\+\}|\+))"),minus(R"(\\sigma\^(?:\{-\}|-))");
  s=std::regex_replace(std::regex_replace(s,plus,raising),minus,lowering);
 }
 if(s.find("\\limits")!=std::string::npos && (s.find("\\min")!=std::string::npos || s.find("\\max")!=std::string::npos)) {
  std::string compact=s;compact.erase(std::remove_if(compact.begin(),compact.end(),asciiSpace),compact.end());
  static const std::regex optimization(R"(^\\(max|min)\\limits_\{([a-z])\\in\\\{0,1\\\}\^([a-z0-9])\}(.+)$)");
  std::smatch m;
  if(std::regex_match(compact,m,optimization)) {
   const std::string x=m[2],width=m[3],objective=m[4];
   if(m[1]=="min" && objective==x+"^TQ"+x)return "qbinaryminimum(\"Q\","+width+")";
   const std::string edges="\\sum\\limits_{(i,j)}{",a=x+"_i",b=x+"_j";
   if(m[1]=="max" && objective==edges+a+"+"+b+"-2"+a+b+"}")return "qmaxcut(\"E\","+width+")";
   if(m[1]=="min" && objective==edges+"2"+a+b+"-"+a+"-"+b+"}")return "-qmaxcut(\"E\","+width+")";
  }
 }
 // An error syndrome names a basis state of the measurement register.
 // Preserve the operator and its wire in both ket and bra labels.
 if(s.find("syndrome")!=std::string::npos) {
  static const std::regex identity(R"(\\mathbb\{I\}\s*\\text\{\s*syndrome\s*\})");
  static const std::regex pauli(R"(([XYZ])_([a-z])(?:\s+([XYZ])_\2)?\s*\\text\{\s*syndrome\s*\})");
  s=std::regex_replace(s,identity,"syndromeI");
  s=std::regex_replace(s,pauli,"syndrome$1$3_$2");
 }
 if(s.find("\\operatorname{dim}")!=std::string::npos) {
  static const std::regex subspace(R"(\\operatorname\{dim\}\s*\(\s*\\mathcal\{([A-Z])\}\s*\))");
  s=std::regex_replace(s,subspace,"qspacedimension(\"$1\")");
 }
 if(mathWrapper && s.find("[[")!=std::string::npos) {
  static const std::string term=R"([a-zA-Z0-9]+(?:\^[0-9]+)?)";
  static const std::string parameter="("+term+"(?:\\s*[+-]\\s*"+term+")*)";
  static const std::regex parameters("^\\s*\\[\\[\\s*"+parameter+"\\s*,\\s*"+parameter+"\\s*,\\s*"+parameter+"\\s*\\]\\]\\s*$");
  std::smatch m;
  if(std::regex_match(s,m,parameters))
   return "vector("+quantumTeX(m[1].str())+","+quantumTeX(m[2].str())+","+quantumTeX(m[3].str())+")";
 }
 if(s.find("\\vert")!=std::string::npos || s.find("\\ket")!=std::string::npos) {
  static const std::regex operators(R"(\b([CEPQU])([CEPQU])\s*(?=\\(?:vert|ket)\b))");
  s=std::regex_replace(s,operators,"qoperatorref(\"$1\")*qoperatorref(\"$2\")*");
 }
 // A single-qubit gate's dagger binds before composition with its neighbor.
 if(s.find("\\dagger")!=std::string::npos) {
  static const std::regex gates(R"(\b([HSTXYZ])([HSTXYZ])\^\{\\dagger\}\s*(?=\\(?:vert|ket)\b))");
  s=std::regex_replace(s,gates,"$1*qdag($2)*");
 }
 // A textual subscript on a scalar parameter names it (e.g. a threshold).
 if(s.find("_{\\text{")!=std::string::npos) {
  static const std::regex subscript(R"(\b([a-z])_\{\\text\{([a-z]+)\}\})");
  s=std::regex_replace(s,subscript,"\"$1_$2\"");
 }
 if(s.find("\\log^")!=std::string::npos) {
  static const std::regex power(R"(\\log\^([a-z]|[0-9]+)\s*\(([a-zA-Z]+)\))");
  s=std::regex_replace(s,power,"(ln($2)^$1)");
 }
 // In a scalar probability recurrence the adjacent symbols C and p multiply.
 if(mathWrapper && s.find("Cp")!=std::string::npos && s.find('=')!=std::string::npos &&
    s.find("\\vert")==std::string::npos && s.find("\\ket")==std::string::npos) {
  static const std::regex scalarProduct(R"(\bCp\b)");
  s=std::regex_replace(s,scalarProduct,"C*p");
  if(s.find("\\bigl")!=std::string::npos) {
   static const std::regex leadingConstant(R"(^\s*C\s*\\bigl)");
   s=std::regex_replace(s,leadingConstant,"C*\\bigl");
  }
 }
 // In this injection circuit the data qubit controls the auxiliary T|+>
 // register. The displayed tensor order places the auxiliary register first.
 const std::string cnotArrow="\\stackrel{\\text{CNOT}}{\\longmapsto}";
 const size_t cnotAt=s.find(cnotArrow);
 if(cnotAt!=std::string::npos) {
  const std::string input=trim(s.substr(0,cnotAt)),result=trim(s.substr(cnotAt+cnotArrow.size()));
  static const std::regex injection(R"(^T\s*\\vert\s*\{\+\}\s*\\rangle\s*\\otimes\s*\\vert\s*\\psi\s*\\rangle$)");
  if(std::regex_match(input,injection))
   return "qcompare(qmul(SWAP*CNOT*SWAP,"+quantumTeX(input)+"),"+quantumTeX(result)+",4)";
 }
 // Apply the stated domain of the representative to the whole coset identity.
 if(s.find("\\oplus")!=std::string::npos && s.find("\\text{(for")!=std::string::npos) {
  std::string compact=s;
  compact.erase(std::remove_if(compact.begin(),compact.end(),asciiSpace),compact.end());
  static const std::regex identity(R"re(^(H\^\{\\otimes([a-z])\})?\\vert([a-z])\\oplus\\mathcal\{([A-Z])\}_([A-Z])\\rangle=\\frac\{1\}\{\\sqrt\{2\^([a-z])\}\}\\sum_\{([a-z])\\in\\mathcal\{\4\}_\5\}(H\^\{\\otimes([a-z])\})?\\vert\3\\oplus\7\\rangle\\qquad\\text\{\(for(?:all)?\$\3\\in\\mathcal\{([A-Z])\}_([A-Z])\$\)\}$)re");
  std::smatch m;
  if(std::regex_match(compact,m,identity) && m[1].str()==m[8].str()) {
   std::string u=m[3],v=m[7],d="\""+m[4].str()+"_"+m[5].str()+"\"",c="\""+m[10].str()+"_"+m[11].str()+"\"";
   std::string lhs="qcosetket("+u+","+d+")",term="qketstate(qoplus("+u+","+v+"))";
   if(m[1].matched) {
    std::string transform="qhadamardpower("+m[2].str()+")";
    lhs="qmul("+transform+","+lhs+")";term="qmul("+transform+","+term+")";
   }
   std::string rhs="qmul(1/sqrt(2^"+m[6].str()+"),qsumset("+term+","+d+","+v+"))";
   return "qsubset("+c+",qsetfilter(qcompare("+lhs+","+rhs+",4),"+c+","+u+"))";
  }
 }
 // A binary code is specified by generators or homogeneous parity checks.
 if(s.find("\\bigl\\{")!=std::string::npos && s.find("\\cdots")!=std::string::npos) {
  static const std::regex span(R"(\\bigl\\\{\s*\\alpha_1\s+([a-z])_1\s*\\oplus\s*\\cdots\s*\\oplus\s*\\alpha_([a-z])\s+\1_\2\s*\\,\s*:\s*\\,\s*\\alpha_1\s*,\s*\\ldots\s*,\s*\\alpha_\2\s*\\in\s*\\\{0,1\\\}\s*\\bigr\\\})");
  static const std::regex kernel(R"(\\bigl\\\{\s*([a-z])\s*\\in\s*\\Sigma\^([a-z])\s*\\,\s*:\s*\\,\s*\1\s*\\cdot\s*([a-z])_1\s*=\s*\\cdots\s*=\s*\1\s*\\cdot\s*\3_([a-z])\s*=\s*0\s*\\bigr\\\})");
  s=std::regex_replace(s,span,"qwordspan(qindexedentries(\"$1_\",1,$2,vector()))");
  s=std::regex_replace(s,kernel,"qwordkernel(qindexedentries(\"$3_\",1,$4,vector()),$2)");
 }
 // Sigma is an alphabet in these set relations. Elsewhere its power
 // may be ordinary exponentiation or part of an existing register binder.
 if(mathWrapper) {
  std::smatch m;
  static const std::regex ordinal(R"(^\s*(\([A-Za-z0-9+\- ]+\)|[A-Za-z]|[0-9]+)\s*\^\\text\{(?:st|nd|rd|th)\}\s*$)");
  if(std::regex_match(s,m,ordinal))return quantumTeX(m[1].str());
  static const std::regex sampledSet(R"(^\s*\\\{([a-z])_([a-z])\\\}_\{\2=(\d+)\}\^([A-Za-z0-9]+)\s*$)");
  if(std::regex_match(s,m,sampledSet))return "qindexedset(\""+m[1].str()+"_\","+m[3].str()+","+m[4].str()+",vector())";
  static const std::regex unitary(R"(^\s*U\((\\theta)\)\s*$)");
  if(std::regex_match(s,m,unitary))return "qoperatorref(qindexedlabel(\"U(\","+quantumTeX(m[1].str())+",\")\"))";
 }
 if(s.find("\\subset")!=std::string::npos) {
  bool strict=s.find("\\subseteq")==std::string::npos;
  auto sides=indexedParts(s,strict ? "\\subset" : "\\subseteq");
  if(sides.size()==2) {
   auto domain=[](const std::string &side) {
    static const std::regex words(R"(\s*\\Sigma\^([a-z]|[0-9]+)\s*)");
    std::smatch m;
    if(std::regex_match(side,m,words))return "qwordpower(\"Σ\","+m[1].str()+")";
    std::string label=trim(side);
    if(label.size()==1 && label[0]>='A' && label[0]<='Z')return "\""+label+"\"";
    return quantumTeX(side);
   };
   std::string left=domain(sides[0]),right=domain(sides[1]);
   std::string subset="qsubset("+left+","+right+")";
   return strict ? "("+subset+" and !(qsubset("+right+","+left+")))" : subset;
  }
 }
 if(s.find("\\ldots")!=std::string::npos && s.find("\\Sigma^")!=std::string::npos) {
  static const std::regex membership(R"(^\s*([a-z])_1\s*,\s*\\ldots\s*,\s*\1_([a-z])\s*\\in\s*\\Sigma\^([a-z]|[0-9]+)\s*$)");
  std::smatch m;if(std::regex_match(s,m,membership))
   return "qallmembers(qindexedentries(\""+m[1].str()+"_\",1,"+m[2].str()+",vector()),qwordpower(\"Σ\","+m[3].str()+"))";
 }
 const std::string whole=trim(s);
 if(s.find("\\text{")!=std::string::npos && s.find("for")!=std::string::npos) {
  std::string clause=s;
  clause.erase(std::remove_if(clause.begin(),clause.end(),asciiSpace),clause.end());
  static const std::regex space(R"(\\(?:qquad|quad|;|,))");
  clause=std::regex_replace(clause,space,"");
  const std::string conjunction=",\\text{but}";
  size_t at=clause.find(conjunction);
  std::string first=quantifiedPaulis(clause.substr(0,at));
  if(!first.empty()) {
   if(at==std::string::npos)return first;
   std::string second=quantifiedPaulis(clause.substr(at+conjunction.size()));
   if(!second.empty())return "("+first+") and ("+second+")";
  }
 }

 if(whole=="\\wedge" || whole=="\\land")return booleanGraph("0001");
 if(whole=="\\vee" || whole=="\\lor")return booleanGraph("0111");
 if(whole=="\\neg" || whole=="\\lnot")return booleanGraph("10");
 // As a standalone circuit gate label, the circled plus toggles one bit
 // by the other. Infix \oplus retains its operand-dependent interpretation.
 if(whole=="\\oplus")return booleanGraph("0110");
 // Indexed Pauli expansions are operator equations, including at coefficients
 // equal to zero. Keep the factors matrix-valued during partial substitutions.
 if(s.find("\\mathbb{I}_")!=std::string::npos && s.find("X_")!=std::string::npos && s.find("Z_")!=std::string::npos &&
    s.find("syndrome")==std::string::npos && s.find("qnamedket")==std::string::npos) {
  static const std::regex pauliWire(R"((\\mathbb\{I\}|\b[UXYZ])_([a-z])\b)");
  std::string marked;
  size_t start=0;
  for(std::sregex_iterator it(s.begin(),s.end(),pauliWire),end;it!=end;++it) {
   const auto &item=*it;
   marked.append(s,start,item.position()-start);
   std::string gate=item[1].str();if(gate=="\\mathbb{I}")gate="I";
   marked+="qoperatorref(\""+gate+"_"+item[2].str()+"\")";
   start=item.position()+item.length();
  }
  marked.append(s,start,std::string::npos);s=marked;
 }
 // A channel defined by a Kraus sum acts on the entire density operator.
 if(s.find("\\Phi")!=std::string::npos && s.find("\\sum")!=std::string::npos) {
  static const std::regex channel(R"(^\s*\\Phi(?:_([a-z]))?\s*(?:\\bigl\s*)?\((.*?)\s*(?:\\bigr\s*)?\)\s*=)");
  std::smatch match;
  if(std::regex_search(s,match,channel)) {
   std::string name="Φ";if(match[1].matched)name+="_"+match[1].str();
   std::string argument=match[2].str(),body=s.substr(match.length());
   // An operator-sum term A_j sigma A_j^dagger stays a matrix
   // product even while the density operator or its entries are unknown.
   static const std::regex operatorSum(R"(^\s*\\sum_([a-z])\s+([A-Z])_\1\s+(\\[A-Za-z]+)\s+\2_\1\^\{\\dagger\}\s*$)");
   std::smatch term;
   if(std::regex_match(body,term,operatorSum) && trim(argument)==term[3].str()) {
    std::string op="qoperatorref("+term[2].str()+"_"+term[1].str()+")";
    argument="qoperatorref("+argument+")";
    body="\\sum_"+term[1].str()+" "+op+"*"+argument+"*"+op+"^{\\dagger}";
   }
   s="qkrausapply(\""+name+"\","+argument+")="+body;
  }
 }
 if(whole=="\\pm i" || whole=="\\pm 1") {
  const std::string value=whole.substr(4);
  return "qset(vector("+value+",-"+value+"))";
 }
 if(s.find("\\langle")!=std::string::npos) {
  static const std::regex pauliProduct(R"(\s*(?:[IXYZ]|\\mathbb\{I\})(?:\s*\\otimes\s*(?:[IXYZ]|\\mathbb\{I\}))*\s*)");
  static const std::regex family(R"(\s*([A-Z])_1\s*,\s*\\(?:ldots|cdots)\s*,\s*\1_([a-z])\s*)");
  size_t at=0;
  while((at=s.find("\\langle",at))!=std::string::npos) {
   size_t close=s.find("\\rangle",at+7);if(close==std::string::npos)break;
   std::string body=s.substr(at+7,close-at-7),group;
   auto generators=indexedParts(body,",");
   std::string prefix=trim(s.substr(0,at));
   bool membership=prefix.size()>=6 && prefix.compare(prefix.size()-6,6,"\\notin")==0;
   std::smatch match;
   if(std::regex_match(body,match,family))
    group="qpauligroup(qindexedentries(\""+match[1].str()+"_\",1,"+match[2].str()+",vector()))";
   else if((generators.size()>1 || membership) && std::all_of(generators.begin(),generators.end(),[](const std::string &g){return std::regex_match(g,pauliProduct);}))
    group="qpauligroup(vector("+body+"))";
   if(group.empty()) {at+=7;continue;}
   s.replace(at,close+7-at,group);at+=group.size();
  }
 }
 // Inside a Pauli tensor word every factor acts on a qubit.
 if(s.find("\\otimes")!=std::string::npos && s.find("\\mathbb{I}")!=std::string::npos) {
  static const std::regex word(R"((?:\b[XYZ]\b|\\mathbb\{I\})(?:\s*\\otimes\s*(?:\b[XYZ]\b|\\mathbb\{I\}))+)");
  std::string expanded;size_t start=0;
  for(std::sregex_iterator it(s.begin(),s.end(),word),end;it!=end;++it) {
   std::string term=it->str();
   if(term.find_first_of("XYZ")==std::string::npos)continue;
   expanded.append(s,start,it->position()-start);
   for(size_t at=0;(at=term.find("\\mathbb{I}",at))!=std::string::npos;++at)term.replace(at,10," I ");
   expanded+=term;start=it->position()+it->length();
  }
  if(start) {expanded.append(s,start,std::string::npos);s=expanded;}
 }
 if(s.find("\\cdots")!=std::string::npos) {
  static const std::regex monotone(R"(^\s*(\\?[A-Za-z]+)_1\s*([<>])\s*\1_2\s*\2\s*\\cdots\s*\2\s*\1_([a-z])\s*$)");
  std::smatch match;
  if(std::regex_match(s,match,monotone))
   return "qstrictorder(qindexedentries(\""+trim(quantumTeX(match[1].str()))+"_\",1,"+match[3].str()+",vector()),"+(match[2].str()==">" ? "1)" : "0)");
 }
 if(s.find("\\sum_")!=std::string::npos && s.find("\\cdots")!=std::string::npos) {
  const std::string bounds=R"(\\sum_\{\s*([a-z])_1\s*,\s*\\ldots\s*,\s*\1_([a-z])\s*\\in\s*\\\{0,1\\\}\s*\}\s*)";
  const std::string terms=R"(([A-Z])_1\^\{\1_1\}\s*\\cdots\s*\3_\2\^\{\1_\2\})";
  static const std::regex traced(bounds+R"(\\operatorname\{Tr\}\s*\(\s*)"+terms+R"(\s*\))");
  static const std::regex untraced(bounds+terms);
  const std::string product="qbinarypowersum(qindexedentries(\"$3_\",1,$2,vector()))";
  s=std::regex_replace(s,traced,"qtrace("+product+")");
  s=std::regex_replace(s,untraced,product);
 }
 if(s.find("\\biggl")!=std::string::npos && s.find("\\cdots")!=std::string::npos) {
  static const std::regex projectors(R"(\\biggl\(\\frac\{\\mathbb\{I\}\^\{\\otimes\s+([a-z])\}\s*\+\s*([A-Z])_1\}\{2\}\\biggr\)\s*\\cdots\s*\\biggl\(\\frac\{\\mathbb\{I\}\^\{\\otimes\s+\1\}\s*\+\s*\2_([a-z])\}\{2\}\\biggr\))");
  s=std::regex_replace(s,projectors,"qprojectorproduct(qindexedentries(\"$2_\",1,$3,vector()),2^($1))");
 }
 if(s.find("\\cdots")!=std::string::npos) {
  static const std::regex products(R"(((?:[A-Z]|\\Pi))_1(?:\^\{?([01]|[a-z]_1)\}?)?\s*\\cdots\s*\1_([a-z])(?:\^\{?([01]|[a-z]_[a-z])\}?)?)");
  std::string expanded;size_t start=0;
  for(std::sregex_iterator it(s.begin(),s.end(),products),end;it!=end;++it) {
   const auto &m=*it;
   std::string first=m[2].str(),last=m[4].str(),upper=m[3].str();
   std::string power=first.empty() ? "1" : first;
   if(first!=last) {
    if(first.size()!=3 || last!=first.substr(0,2)+upper)continue;
    power="qindexedentries(\""+first.substr(0,2)+"\",1,"+upper+",vector())";
   }
   expanded.append(s,start,m.position()-start);
   expanded+="qorderedpowers(qindexedentries(\""+trim(quantumTeX(m[1].str()))+"_\",1,"+upper+",vector()),"+power+")";
   start=m.position()+m.length();
  }
  if(start) {expanded.append(s,start,std::string::npos);s=expanded;}
 }
 if(s.find("\\in")!=std::string::npos && s.find("\\ldots")!=std::string::npos) {
  static const std::regex membership(R"(^\s*([a-z])_1\s*,\s*\\ldots\s*,\s*\1_([a-z]|[0-9]+)\s*\\in\s*(\\\{[^{}]+\\\})\s*$)");
  std::smatch match;
  if(std::regex_match(s,match,membership))
   return "qallmembers(qindexedentries(\""+match[1].str()+"_\",1,"+match[2].str()+",vector()),"+quantumTeX(match[3].str())+")";
 }
 if(s.find("\\cdots")!=std::string::npos && s.find("\\rangle")!=std::string::npos) {
  static const std::regex fixed(R"(([A-Z])_1\s*(\\vert\s*\\[A-Za-z]+\s*\\rangle)\s*=\s*\\cdots\s*=\s*\1_([a-z])\s*\2\s*=\s*\2)");
  std::smatch match;
  if(std::regex_search(s,match,fixed)) {
   std::string operators="qindexedentries(\""+match[1].str()+"_\",1,"+match[3].str()+",vector())";
   std::string before=trim(match.prefix().str()),after=trim(match.suffix().str());
   if(before.empty() && after.empty())return "qfixedby("+operators+","+quantumTeX(match[2].str())+")";
   const size_t brace=before.find("\\bigl\\{");
   if(brace!=std::string::npos && after=="\\bigr\\}") {
    std::string binder=trim(before.substr(brace+7));
    if(binder==match[2].str()+" \\,:\\,")s=before.substr(0,brace)+"qfixedspace("+operators+")";
   }
  }
 }
 std::string systems=systemNames(s);
 if(!systems.empty())return systems;
 // A sum written with an ellipsis must have matching indexed endpoints.
 if(s.find("\\cdots")!=std::string::npos || s.find("\\ldots")!=std::string::npos) {
  auto sides=indexedParts(s,"=");bool changed=false;
  for(auto &side:sides) {
   auto terms=indexedParts(side,"+");
   if(terms.size()!=3 || (terms[1]!="\\cdots" && terms[1]!="\\ldots") ||
      terms.front().find('_')==std::string::npos || terms.back().find('_')==std::string::npos)continue;
   size_t sub=terms.front().find('_');
   std::string base=terms.front().substr(0,sub);
   if(base.empty() || terms.back().compare(0,sub+1,base+"_")!=0)continue;
   size_t firstLetter=base.front()=='\\' ? 1 : 0;
   if(firstLetter==base.size() || !std::all_of(base.begin()+firstLetter,base.end(),
       [](unsigned char c){return c>=128 || asciiLetter(c);}))continue;
   std::string name=trim(TeXReader(base).run(nullptr));
   std::string family=indexedLabelRange(name+terms.front().substr(sub),name+terms.back().substr(sub),"qindexedsum(");
   if(!family.empty()) {side=family;changed=true;}
  }
  if(changed) {s=sides[0];for(size_t i=1;i<sides.size();++i)s+="="+sides[i];}
 }
 if(fractionBits) {
  std::string expansion=openBinaryFraction(s);
  if(!expansion.empty())s=expansion;
  std::string digits=trim(s);
  if(!digits.empty() && digits.front()=='.')digits.erase(0,1);
  if(!digits.empty() && digits.find_first_not_of("0123456789")==std::string::npos)
   s="."+digits+"₂";
 }
 // Unicode operators and rounding brackets share their TeX grammar.
 // Preserve quoted labels verbatim.
 static const auto unicodeOperators=std::map<std::string,std::string>{{"±","\\pm "},{"∑","\\sum "},{"∏","\\prod "},{"⨂","\\bigotimes "},{"⨁","\\bigoplus "},
  {"∪","\\cup "},{"∩","\\cap "},{"∖","\\setminus "},{"∅","\\emptyset "},{"⌊","\\lfloor "},{"⌋","\\rfloor "},{"⌈","\\lceil "},{"⌉","\\rceil "}};
 std::string normalized;char quote=0;
 int depth=0;bool splitDimensions=false;
 for(size_t k=0;k<s.size();) {
  if(s[k]=='"' || s[k]=='\'') {if(quote==s[k])quote=0;else if(!quote)quote=s[k];normalized+=s[k++];continue;}
  if(dimensions && !quote) {
   if(s[k]=='(' || s[k]=='[' || s[k]=='{')++depth;
   else if(s[k]==')' || s[k]==']' || s[k]=='}')--depth;
   size_t cross=s.compare(k,2,"×")==0 ? 2 : 0;
   if(s.compare(k,6,"\\times")==0 && (k+6==s.size() || !std::isalpha((unsigned char)s[k+6])))cross=6;
   if(depth==0 && cross) {
    if(splitDimensions)throw std::runtime_error("Matrix dimensions require one row count and one column count.");
    normalized="qmatrixdimensions(("+normalized+"),(";splitDimensions=true;k+=cross;continue;
   }
  }
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
  if(!quote && (s.compare(k,3,"∈")==0 || s.compare(k,3,"∉")==0)) {
   size_t next=s.find_first_not_of(" \t\r\n",k+3);
   if(next!=std::string::npos && (s[next]=='[' || s[next]=='(')) {
    normalized+=s.compare(k,3,"∈")==0 ? "\\in " : "\\notin ";k+=3;continue;
   }
  }
  bool matched=false;
  if(!quote)for(const auto &alias:unicodeOperators) {
   if(s.compare(k,alias.first.size(),alias.first)==0) {normalized+=alias.second;k+=alias.first.size();matched=true;break;}
  }
  if(!matched)normalized+=s[k++];
 }
 if(splitDimensions)normalized+="))";
 std::string result=TeXReader(normalized).run(lines);
 if(normalized.find("_{\\mathsf{")!=std::string::npos && result.find("qregket(")!=std::string::npos) {
  std::string value=trim(result),order;
  static const std::regex subscript(R"ket(qregket\(\|[^<>|]*>,"([A-Z]+)"\))ket");
  for(std::sregex_iterator it(value.begin(),value.end(),subscript),end;it!=end;++it)
   for(char wire:(*it)[1].str())if(order.find(wire)==std::string::npos)order+=wire;
  // Alignment environments group the entire equation. Remove that one
  // wrapper only when it encloses every operand.
  if(value.size()>1 && value.front()=='(' && value.back()==')') {
   size_t depth=0,end=0;
   for(;end<value.size();++end) {
    if(value[end]=='(')++depth;
    if(value[end]==')' && --depth==0)break;
   }
   if(end+1==value.size())value=value.substr(1,value.size()-2);
  }
  auto operands=indexedParts(value,"=");
  result.clear();
  for(const auto &operand:operands) {
   if(!result.empty())result+="=";
   result+=operand.find("qregket(")==std::string::npos ? operand : "qorderedket("+operand+",\""+order+"\")";
  }
 }
 if(bitWord)result=orderedBitWord(result);

 return result;
}

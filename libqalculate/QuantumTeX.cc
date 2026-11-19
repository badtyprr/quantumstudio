// GPL-2.0-or-later; see COPYING.
#include "QuantumTeX.h"
#include <algorithm>
#include <cctype>
#include <map>
#include <stdexcept>
#include <vector>

namespace {
bool asciiLetter(unsigned char c) {return (c>='A' && c<='Z') || (c>='a' && c<='z');}
// In binary-word mode, adjacent digits and named bits occupy consecutive
// positions, most significant first. Leave explicit calculator calls intact.
std::string orderedBitWord(const std::string &text) {
 std::string digits;
 for(unsigned char c:text)if(!std::isspace(c))digits+=c;
 if(!digits.empty() && digits.find_first_not_of("01")==std::string::npos)
  return "bitstring(\""+digits+"\")";
 std::string result="qbitword(vector(";size_t count=0;
 for(size_t i=0;i<text.size();) {
  unsigned char c=text[i];
  if(std::isspace(c)) {++i;continue;}
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
// Display mathematics may end with a sentence period or comma. Preserve decimals,
// quoted labels, ellipses and dots following incomplete operators.
std::string withoutDisplayPunctuation(std::string value) {
 size_t mark=value.find_last_not_of(" \t\r\n");
 if(mark==std::string::npos || mark==0 || (value[mark]!='.' && value[mark]!=','))return value;
 if(value[mark]=='.' && std::isdigit((unsigned char)value[mark-1])) {
  // An unbraced TeX superscript consumes one token. The following period
  // belongs to the sentence, while a number such as 1. keeps its decimal.
  size_t previous=mark>=2 ? value.find_last_not_of(" \t\r\n",mark-2) : std::string::npos;
  if(previous==std::string::npos || value[previous]!='^')return value;
 }
 size_t before=value.find_last_not_of(" \t\r\n",mark-1);
 if(before==std::string::npos)return value;
 unsigned char end=value[before];
 if(end<128 && !std::isalnum(end) && end!=')' && end!=']' && end!='}' && end!='>' && end!='\'' && end!='"')return value;
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
 auto space=[&]() {while(at<input.size() && std::isspace((unsigned char)input[at]))++at;};
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
    if(!std::isspace((unsigned char)input[at]))index+=input[at];
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
 auto space=[&]() {while(at<input.size() && std::isspace((unsigned char)input[at]))++at;};
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
   size_t begin=k+1;while(begin<text.size() && std::isspace((unsigned char)text[begin]))++begin;
   if(begin==text.size())continue;
   size_t end=begin;std::string index;
   if(text[begin]=='{') {
    unsigned depth=1;end=begin+1;
    while(end<text.size() && depth) {if(text[end]=='{')++depth;if(text[end]=='}')--depth;++end;}
    if(depth)continue;index=text.substr(begin+1,end-begin-2);
   } else {end=begin+1;index=text.substr(begin,1);}
   std::string compact;bool scalar=true;
   for(unsigned char c:index) {
    if(std::isspace(c))continue;
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
   if(std::isspace((unsigned char)text[k]))continue;
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
std::string scalarProductSum(const std::string &input,size_t start,size_t &end) {
 size_t at=start;
 auto space=[&]() {while(at<input.size() && std::isspace((unsigned char)input[at]))++at;};
 auto token=[&](const std::string &text) {space();if(input.compare(at,text.size(),text)!=0)return false;at+=text.size();return true;};
 auto factor=[&](std::string &family,std::string &index) {
  space();size_t begin=at;while(at<input.size() && asciiLetter((unsigned char)input[at]))++at;
  if(at==begin || at-begin>127)return false;
  family=input.substr(begin,at-begin);if(!token("_"))return false;
  space();if(at==input.size())return false;
  if(input[at]=='{') {
   ++at;while(at<input.size() && input[at]!='}') {
    if(!std::isspace((unsigned char)input[at]))index+=input[at];
    if(index.size()>32)return false;++at;
   }
   if(at==input.size())return false;++at;
  } else if(input[at]>='0' && input[at]<='9')index+=input[at++];
  else return false;
  return !index.empty();
 };
 std::string first,second,lastFirst,lastSecond,upperA,upperB,lowerA,lowerB;
 if(!factor(first,upperA) || !factor(second,upperB) || !token("+") || !token("\\cdots") || !token("+") ||
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
 auto invalid=[]() {throw std::runtime_error("An indexed column requires consecutive entries from index 0, a vertical ellipsis, and an endpoint in the same family; group compound subscripts");};
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
  for(unsigned char c:index)if(c<128 && !std::isalnum(c) && !std::isspace(c) && ( !grouped || (c!='+' && c!='-' && c!='*' && c!='/')))invalid();
  indices.push_back(index);
 }
 if(indices.size()+1!=rows.size())invalid();
 bool descending=rows[1]==marker && indices.back()=="0" && !(rows[rows.size()-2]==marker && indices.front()=="0");
 if(descending)std::reverse(indices.begin(),indices.end());
 else if(rows[rows.size()-2]!=marker)invalid();
 for(size_t i=0;i+1<indices.size();++i)if(indices[i]!=std::to_string(i))invalid();
 const char *operation=descending ? "qdescendingcolumn" : "qindexedcolumn";
 return std::string(operation)+"(\""+quantumTeX(family)+"_\",("+indices.back()+"),"+std::to_string(rows.size()-3)+")";
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
     if(std::isspace(ch)) {compact+=ch;continue;}
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
// Open-ended families need a common label and consecutive integer subscripts.
// Keep only the first index; a trailing comma after the ellipsis is typography.
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
  size_t pos=index.find_last_not_of('9');
  if(pos==std::string::npos)index="1"+std::string(index.size(),'0');
  else {++index[pos];std::fill(index.begin()+pos+1,index.end(),'0');}
 }
 return "qindexedfamily(\""+prefix+"\","+start+")";
}
// A finite family of kets uses the same prefix at both endpoints.
std::string indexedKetSet(const std::vector<std::string> &entries) {
 if(entries.size()!=3 || entries[1]!="...")return "";
 auto label=[](const std::string &entry) {
  return entry.size()>2 && entry.front()=='|' && entry.back()=='>' ? trim(entry.substr(1,entry.size()-2)) : std::string();
 };
 std::string first=label(entries.front()),last=label(entries.back());
 size_t split=first.rfind('_');
 if(split==std::string::npos || split==0)return "";
 std::string prefix=first.substr(0,split+1);
 if(last.compare(0,prefix.size(),prefix)!=0)return "";
 for(size_t k=0;k<split;++k)if((unsigned char)prefix[k]<128 && !asciiLetter(prefix[k]))return "";
 std::string from=first.substr(split+1),to=last.substr(split+1);
 auto integer=[](const std::string &s){return !s.empty() && s.find_first_not_of("0123456789")==std::string::npos && (s.size()==1 || s.front()!='0');};
 // Grouped offsets belong to the index. Ungrouped arithmetic does not.
 if(to.size()>2 && to.front()=='{' && to.back()=='}') {
  std::string bound=trim(to.substr(1,to.size()-2));
  if(bound.empty() || !asciiLetter(bound.front()))return "";
  std::string offset=trim(bound.substr(1));
  if(offset.empty() || (offset.front()!='+' && offset.front()!='-'))return "";
  std::string magnitude=trim(offset.substr(1));
  if(!integer(magnitude))return "";
  to=bound.substr(0,1)+offset.front()+magnitude;
 } else if(!integer(to) && !(to.size()==1 && asciiLetter(to[0])))return "";
 if(!integer(from))return "";
 return "qindexedketset(\""+prefix+"\","+from+","+to+",vector())";
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
 unsigned setExpressions=0;
 unsigned matrixDepth=0;
 void space() { while(pos<input.size() && std::isspace((unsigned char)input[pos])) ++pos; }
 // Check the displayed initial powers and the final base before consuming
 // an ellipsis. Keep the endpoint expression available for substitution.
 std::string geometricSum() {
  size_t at=pos;
  auto token=[&](const std::string &s) {
   while(at<input.size() && std::isspace((unsigned char)input[at]))++at;
   if(input.compare(at,s.size(),s)!=0)return false;
   at+=s.size();return true;
  };
  if(!token("1") || !token("+"))return "";
  while(at<input.size() && std::isspace((unsigned char)input[at]))++at;
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
 bool takeModulusLabel() {
  size_t start=pos;
  space();
  if(input.compare(pos,5,"\\text")==0) {
   pos+=5;space();
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
 std::string setLiteral(bool escaped) {
  ++setExpressions;std::string contents=read(escaped ? 0 : '}',false,"",escaped);--setExpressions;
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
    if(alphabet.empty())alphabet=indexedKetSet(entries);
    if(alphabet.empty()) {
     if(entries.size()!=3 || entries[1]!="..." || entries[0].empty() || entries[2].empty() || entries[0]=="..." || entries[2]=="...")throw std::runtime_error(error("Use two endpoints around one ellipsis for an ascending integer index range"));
     alphabet="qindexrange("+entries[0]+","+entries[2]+")";
    }
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
   return "qsetimage("+body+","+collection+","+index+")";
  }
  if(membership==std::string::npos || separator==std::string::npos)throw std::runtime_error(error("Use an index, finite collection and predicate in a set builder"));
  std::string index=trim(contents.substr(0,membership)),collection=trim(contents.substr(membership+3,separator-membership-3)),predicate=trim(contents.substr(separator+1));
  if(index.empty() || std::isdigit((unsigned char)index[0]) || collection.empty() || predicate.empty())throw std::runtime_error(error("A set builder requires an index, collection and predicate"));
  for(unsigned char ch:index)if(ch<128 && !std::isalnum(ch) && ch!='_')throw std::runtime_error(error("A set builder requires a symbol index"));
  return "qsetfilter("+predicate+","+collection+","+index+")";
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
   if(c==',' || c==';' || c==':' || c=='!' || c==' ') return " ";
   if(c=='%')return " qtexpercent ";
   if(c=='|') { if(norms) { --norms; return closeNorm(); } ++norms; return "norm("; }
   throw std::runtime_error(error("Unsupported TeX control symbol"));
  }
  size_t start=pos; while(pos<input.size() && asciiLetter((unsigned char)input[pos])) ++pos;
  std::string name=input.substr(start,pos-start);
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
    std::string compactPower;for(unsigned char c:power)if(!std::isspace(c))compactPower+=c;
    if(compactPower=="-1")return "a"+name+"("+operand+")";
    return "("+name+"("+operand+"))^("+power+")";
   }
   pos=afterName;
  }
  if(name=="left" || name=="right" || name=="big" || name=="Big" || name=="bigl" || name=="bigr" || name=="Bigl" || name=="Bigr" || name=="bigg" || name=="Bigg" || name=="biggl" || name=="biggr" || name=="Biggl" || name=="Biggr") {
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
  if(name=="mid" && setExpressions)return ":";
  if((name=="ldots" || name=="dots" || name=="cdots") && pos>name.size()+1) {
   size_t before=input.find_last_not_of(" \t\r\n",pos-name.size()-2);
   size_t after=input.find_first_not_of(" \t\r\n",pos);
   if(before!=std::string::npos && after!=std::string::npos && input[before]==',' && input[after]==',')return "...";
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
  if(setExpressions && (name=="ldots" || name=="cdots" || name=="dots"))return "...";
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
   if(name=="mathbb" && a=="I")return " qimplicitidentity() ";
   if(name=="mathbb" && a=="T")return " qunitcircle() ";
   if(name=="mathbb" && a=="C")return " qcomplexplane() ";
   if(name=="operatorname" && a=="lg")a="qbitlength";
   if(name=="operatorname" && a=="range")a="qfunctionrange";
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
   if(m.empty())m="["+body+"]";
   if(env=="vmatrix") return "det("+m+")";
   if(env=="Vmatrix") return "norm("+m+closeNorm(true);
   return m;
  }
  if(name=="vdots" && matrix)return "⋮";
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
   {"pm"," ± "},{"rightarrow"," → "},{"to"," → "},{"Leftrightarrow"," iff "},{"iff"," iff "},{"land"," and "},{"wedge"," and "},{"lor"," or "},{"vee"," or "},{"lnot"," not "},{"neg"," not "},{"veebar"," xor "},
   {"uparrow","↑"},{"downarrow","↓"},
   {"infty","infinity"},{"pi","pi"},{"alpha","α"},{"beta","β"},{"gamma","γ"},{"delta","δ"},{"theta","θ"},
   {"phi","φ"},{"Phi","Φ"},{"varphi","φ"},{"psi","ψ"},{"Psi","Ψ"},{"rho","ρ"},{"sigma","σ"},
   {"lambda","λ"},{"omega","ω"},{"epsilon","ε"},{"varepsilon","ε"},{"chi","χ"},
   {"zeta","ζ"},{"eta","η"},{"iota","ι"},{"kappa","κ"},{"nu","ν"},{"xi","ξ"},
   {"clubsuit","♣"},{"diamondsuit","♢"},{"heartsuit","♡"},{"spadesuit","♠"},
   {"omicron","ο"},{"tau","τ"},{"upsilon","υ"},{"vartheta","θ"},{"varrho","ρ"},
   {"varkappa","κ"},{"varpi","ϖ"},{"varsigma","ς"},
   {"Gamma","Γ"},{"Delta","Δ"},{"Theta","Θ"},{"Lambda","Λ"},{"Xi","Ξ"},
   {"Pi","Π"},{"Sigma","Σ"},{"Upsilon","Υ"},{"Omega","Ω"},
   {"sin","sin"},{"cos","cos"},{"tan","tan"},{"arcsin","asin"},{"arccos","acos"},{"arctan","atan"},{"exp","exp"},{"log","ln"},{"ln","ln"},
   {"det","det"},{"tr","tr"},{"Tr","Tr"},{"quad"," "},{"qquad"," "}
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
  std::string result; int norms=0; bool closed=false;
  const bool alignment=environment=="aligned" || environment=="align" || environment=="align*" || environment=="gathered" || environment=="gather" || environment=="gather*" || environment=="split";
  const bool gathered=environment=="gathered" || environment=="gather" || environment=="gather*";
  std::vector<std::string> alignmentCells,expressions;
  std::vector<size_t> preceding;
  unsigned alignmentRows=0;
  auto finishAlignment=[&]() {
   if(++alignmentRows>128)throw std::runtime_error(error("Alignment is limited to 128 rows"));
   alignmentCells.push_back(trim(result));result.clear();
   for(size_t cell=0;cell<alignmentCells.size();cell+=2) {
    std::string value=alignmentCells[cell];bool indented=value.empty() && cell+1<alignmentCells.size();
    if(cell+1<alignmentCells.size())value+=" "+alignmentCells[cell+1];
    value=trim(withoutDisplayPunctuation(value));
    if(value.empty())throw std::runtime_error(error("Empty aligned expression"));
    size_t column=cell/2;
    if(preceding.size()<=column)preceding.resize(column+1,std::string::npos);
    bool relation=value[0]=='=' || value.compare(0,2,"<=")==0 || value.compare(0,2,">=")==0 || value.compare(0,2,"!=")==0;
    bool operation=value[0]=='+' || value[0]=='-' || value[0]=='*' || value[0]=='/' || value[0]=='@' || value[0]=='#';
    bool continuation=relation || (indented && operation && preceding[column]!=std::string::npos);
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
   if(!matrixDepth && !stateLabel && !setExpressions && !setBound) {
    const std::string preceding=trim(result);
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
     if(product.empty())product=scalarProductSum(input,pos,end);
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
       for(unsigned char c:first)if(!std::isalnum(c) && !(grouped && (std::isspace(c) || c=='+' || c=='-' || c=='*' || c=='/')))valid=false;
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
    if(open=='(' && takeModulusLabel()) {
     auto modulus=trim(read(end));
     if(modulus.empty())throw std::runtime_error(error("Expected a modulus"));
     result=trim(result)+" pmod ("+modulus+")";continue;
    }
    // Mixed delimiters denote a half-open interval only after membership.
    // The recursive reader still checks grouping inside either endpoint.
    size_t tail=result.find_last_not_of(" \t\r\n");
    bool membership=tail!=std::string::npos && tail>=2 &&
     (result.compare(tail-2,3,"∈")==0 || result.compare(tail-2,3,"∉")==0);
    size_t bodyStart=pos;auto body=read(end,false,"",false,"",membership);
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
    size_t stateDelimiter=result.find_last_of("|<>");
    bool stateSubscript=stateLabel;
    if(!stateSubscript && stateDelimiter!=std::string::npos && result[stateDelimiter]!='>') {
     std::string prefix=trim(result.substr(stateDelimiter+1));stateSubscript=!prefix.empty();
     for(unsigned char c:prefix)if(c<128 && !std::isalnum(c) && c!='_')stateSubscript=false;
    }
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
     bool compound=false;for(unsigned char c:index)if(c<128 && !std::isalnum(c) && c!='_' && !std::isspace(c))compound=true;
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
    while(!result.empty() && std::isspace((unsigned char)result.back()))result.pop_back();
    // The displayed open-ended family uses ordinary braces and an ellipsis.
    if(value.find("…")!=std::string::npos || value.find("...")!=std::string::npos) {
     std::string family=openIndexedFamily(indexedParts(value,","));
     if(!family.empty()) {result+=family;continue;}
    }
    // Braces around an entire Dirac label are typesetting, not arithmetic.
    size_t after=pos;while(after<input.size() && std::isspace((unsigned char)input[after]))++after;
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
 if(dimensions || fractionBits || bitWord) {
  first=input.find_first_not_of(" \t\r\n",first+(dimensions ? 11 : fractionBits ? 13 : 8));
  if(first==std::string::npos)return "";
 } else if(input.compare(first,5,"sets:")==0) {
  if(setNotation)*setNotation=true;
  first=input.find_first_not_of(" \t\r\n",first+5);
  if(first==std::string::npos)return "";
 }
 // Session declarations surround the translated expression. Keep the lesson's
 // math delimiters and punctuation available to the ordinary TeX reader.
 std::vector<std::string> contexts;
 while(input.compare(first,14,"matrixcontext(")==0) {
  size_t end=input.find("):",first+14);
  if(end==std::string::npos || contexts.size()>=32)throw std::runtime_error("Invalid matrix declaration context.");
  contexts.push_back(input.substr(first,end-first));
  first=input.find_first_not_of(" \t\r\n",end+2);
  if(first==std::string::npos)throw std::runtime_error("Expected an expression after the matrix declaration.");
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
 if(mathWrapper)s=withoutDisplayPunctuation(s);
 if(fractionBits) {
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
 if(bitWord)result=orderedBitWord(result);
 for(auto context=contexts.rbegin();context!=contexts.rend();++context)result=*context+",("+result+"))";
 return result;
}

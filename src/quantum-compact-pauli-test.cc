// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumCompactPauli.h"
#include "QuantumNotation.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
unsigned checks=0;
EvaluationOptions eo;
void equal(const std::string &a,const std::string &b) {
 MathStructure result=CALCULATOR->calculate("("+a+")==("+b+")",eo);
 if(!result.isNumber() || !result.number().isOne())throw std::runtime_error(a+" != "+b);
 ++checks;
}
void rejects(const std::string &a) {
 while(CALCULATOR->message())CALCULATOR->nextMessage();
 CALCULATOR->calculate(a,eo);bool error=false;
 while(CALCULATOR->message()) {error|=CALCULATOR->message()->type()==MESSAGE_ERROR;CALCULATOR->nextMessage();}
 if(!error)throw std::runtime_error("Expected rejection: "+a);
 ++checks;
}
std::string compact(unsigned n,unsigned x,unsigned z,unsigned p=0) {
 return "qcompactpauli("+std::to_string(n)+","+std::to_string(x)+","+std::to_string(z)+","+std::to_string(p)+")";
}
std::string vector(const std::vector<std::string> &items) {
 std::string out="vector(";
 for(const auto &item:items) {if(out!="vector(")out+=",";out+=item;}
 return out+")";
}
unsigned edge(unsigned x,unsigned y,bool vertical=false) {return 1u<<(17-(9*vertical+3*(y%3)+x%3));}
}
int main() {try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumCompactPauli(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal(translateQuantum("compact_pauli(-iYIIIIIIIIIIIIIIIII)"),"[18,131072,131072,2]");
 equal(translateQuantum("compact_multiply(compact_pauli(X),compact_pauli(Y))"),"[1,0,1,1]");
 // Independent one-qubit matrix table: I, X, Y, Z. Row/column dot products
 // establish every product including all four scalar phases.
 const unsigned xs[]={0,1,1,0},zs[]={0,0,1,1},phases[]={0,0,3,0};
 const unsigned target[4][4]={{0,1,2,3},{1,0,3,2},{2,3,0,1},{3,2,1,0}};
 const unsigned extra[4][4]={{0,0,0,0},{0,0,1,3},{0,3,0,1},{0,1,3,0}};
 for(unsigned a=0;a<4;++a)for(unsigned b=0;b<4;++b)for(unsigned p=0;p<4;++p)for(unsigned q=0;q<4;++q) {
  unsigned c=target[a][b];
  equal("qcompactmultiply("+compact(1,xs[a],zs[a],(phases[a]+p)%4)+","+compact(1,xs[b],zs[b],(phases[b]+q)%4)+")",compact(1,xs[c],zs[c],(phases[c]+extra[a][b]+p+q)%4));
 }
 std::vector<std::string> stars,faces,all;
 for(unsigned y=0;y<3;++y)for(unsigned x=0;x<3;++x) {
  stars.push_back(compact(18,edge(x,y)|edge(x+2,y)|edge(x,y,true)|edge(x,y+2,true),0));
  faces.push_back(compact(18,0,edge(x,y)|edge(x,y+1)|edge(x,y,true)|edge(x+1,y,true)));
 }
 all=stars;all.insert(all.end(),faces.begin(),faces.end());std::string group=vector(all);
 for(const auto &a:all)for(const auto &b:all)equal("qcompactcommutes("+a+","+b+")","1");
 for(const auto &family:{stars,faces}) {
  std::string product=compact(18,0,0);
  for(const auto &p:family)product="qcompactmultiply("+product+","+p+")";
  equal(product,compact(18,0,0));
 }
 equal("qcompactrank("+group+")","16");
 equal("qcompactdimension("+group+")","4");
 equal("qcompactdistance("+group+",3)","3");
 rejects("qcompactdistance("+group+",2)");
 // Independent geometric syndrome oracle: Z meets its two endpoint vertices;
 // X meets the two incident faces. Y has both endpoint pairs.
 for(unsigned vertical=0;vertical<2;++vertical)for(unsigned y=0;y<3;++y)for(unsigned x=0;x<3;++x)for(unsigned letter=1;letter<=3;++letter) {
  unsigned bit=edge(x,y,vertical);std::vector<std::string> expected(18,"0");
  if(letter&2) {
   expected[3*y+x]="1";
   expected[3*((y+vertical)%3)+(x+!vertical)%3]="1";
  }
  if(letter&1) {
   expected[9+3*y+x]="1";
   expected[9+3*((y+(!vertical ? 2:0))%3)+(x+(vertical ? 2:0))%3]="1";
  }
  equal("qcompactsyndrome("+group+","+compact(18,(letter&1)?bit:0,(letter&2)?bit:0,letter==3?3:0)+")",vector(expected));
 }
 unsigned zh=0,zv=0,xh=0,xv=0;
 for(unsigned q=0;q<3;++q) {zh|=edge(q,0);zv|=edge(0,q,true);xh|=edge(0,q);xv|=edge(q,0,true);}
 std::vector<std::string> loops={compact(18,0,zh),compact(18,0,zv),compact(18,xh,0),compact(18,xv,0)};
 for(const auto &loop:loops)for(const auto &g:all)equal("qcompactcommutes("+loop+","+g+")","1");
 for(unsigned a=0;a<4;++a)for(unsigned b=0;b<4;++b)
  equal("qcompactcommutes("+loops[a]+","+loops[b]+")",((a+2)%4==b)?"0":"1");
 for(const auto &bad:{"qcompactpauli(0,0,0,0)","qcompactpauli(26,0,0,0)","qcompactpauli(18,262144,0,0)","qcompactpauli(18,0,0,4)","qcompactpauli(18,0,0,1/2)","qcompactrank(vector([1,1,0,0],[1,0,1,0]))","qcompactrank(vector([1,0,0,2]))","qcompactrank(vector([1,0,0,1]))","qcompactrank(vector([1,1,0,0],[1,1,0,2]))","qcompactmultiply([1,0,0,0],[2,0,0,0])","qcompactdistance(vector([1,0,0,0]),4)","qcompactdistance(vector([1,0,1,0]),3)"})rejects(bad);
 equal(compact(25,33554431,33554431,3),"[25,33554431,33554431,3]");
 std::cout<<"PASS: "<<checks<<" compact Pauli checks\n";return 0;
}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}

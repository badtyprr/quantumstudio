// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include "QuantumNotation.h"
#include <iostream>
#include <stdexcept>

static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate(expression,eo),reference=CALCULATOR->calculate(expected,eo);
 if(!value.equals(reference))throw std::runtime_error("Mismatch: "+expression+" -> "+value.print()+"; expected "+reference.print());
 ++checks;
}
static void rejects(const std::string &expression) {
 while(CALCULATOR->message())CALCULATOR->nextMessage();
 CALCULATOR->calculate(expression,eo);bool error=false;
 while(CALCULATOR->message()) {error=error || CALCULATOR->message()->type()==MESSAGE_ERROR;CALCULATOR->nextMessage();}
 if(!error)throw std::runtime_error("Accepted invalid scalar product: "+expression);
 ++checks;
}
int main() {try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
 eo.approximation=APPROXIMATION_EXACT;
 const std::string family="qscalarproductsum(\"x_\",\"y_\",\"n\",vector())";
 equal("qreplace("+family+",vector(\"n\",\"x_0\",\"x_1\",\"y_0\",\"y_1\"),vector(2,1,1,1,1))","2");
 equal("qreplace("+family+",vector(\"x_0\",\"x_1\",\"y_0\",\"y_1\",\"n\"),vector(1,1,1,1,2))","2");
 equal("qreplace(qreplace(qreplace(qreplace("+family+",\"x_0\",\"x_0\"+1),\"x_0\",0),\"y_0\",3),\"n\",1)","3");
 equal("qscalarproductsum(\"x_\",\"x_\",1,vector(1,0,3))","9");
 equal("qreplace(qreplace(qscalarproductsum(\"x_\",\"x_\",\"n\",vector(1,0,3)),\"x_0\",4),\"n\",1)","9");
 equal("qscalarproductsum(\"x_\",\"y_\",1,vector(0,0,1+i,1,0,1-i))","2");
 const std::string captured="qsumset(qsum(qscalarproductsum(\"x_\",\"y_\",1,vector(1,0,1)),0,1,\"y\"),vector(\"y\"),\"x_0\")";
 equal(captured,"qsumset(qsum(qscalarproductsum(\"x_\",\"y_\",1,vector(1,0,1)),0,1,\"z\"),vector(\"y\"),\"x_0\")");
 equal("qreplace("+captured+",\"y\",3)","6");
 const std::string replacementCapture="qsumset(qsum(qscalarproductsum(\"a_\",\"b_\",1,vector(1,0,1)),0,1,\"x_0\"),vector(qscalarproductsum(\"x_\",\"y_\",1,vector(1,0,1))),\"a_0\")";
 equal("qreplace("+replacementCapture+",\"x_0\",3)","6");
 MathStructure saved=calculator.parse(family);
 auto savedVariable=new KnownVariable("","m11_saved",saved);calculator.addVariable(savedVariable);
 equal("qreplace(m11_saved,vector(\"x_0\",\"y_0\",\"n\"),vector(3,4,1))","12");
 if(!savedVariable->get().equals(saved))throw std::runtime_error("Substitution mutated a known-variable definition");
 ++checks;
 MathStructure savedReplacement=calculator.parse("qscalarproductsum(\"x_\",\"y_\",1,vector(1,0,1))");
 auto replacementVariable=new KnownVariable("","m11_replacement",savedReplacement);calculator.addVariable(replacementVariable);
 equal("qreplace(qsumset(qsum(qscalarproductsum(\"a_\",\"b_\",1,vector(1,0,1)),0,1,\"x_0\"),vector(m11_replacement),\"a_0\"),\"x_0\",3)","6");
 if(!replacementVariable->get().equals(savedReplacement))throw std::runtime_error("Capture avoidance mutated a replacement definition");
 ++checks;
 equal("qreplace(vector("+family+",qregisterfamily(\"b_\",\"m\"-1,0,vector())),\"b_0\",1)",
       "vector("+family+",qregisterfamily(\"b_\",\"m\"-1,0,vector(0,1)))");
 // Independent integer oracle covers every pair of binary vectors at widths
 // 1..4. This checks the ordinary sum, including values greater than one.
 for(unsigned width=1;width<=4;++width)for(unsigned a=0;a<(1u<<width);++a)for(unsigned b=0;b<(1u<<width);++b) {
  unsigned expected=0;std::string bindings;
  for(unsigned k=0;k<width;++k) {
   unsigned x=(a>>k)&1,y=(b>>k)&1;expected+=x*y;
   if(k)bindings+=",";
   bindings+="0,"+std::to_string(k)+","+std::to_string(x)+",1,"+std::to_string(k)+","+std::to_string(y);
  }
  equal("qscalarproductsum(\"x_\",\"y_\","+std::to_string(width)+",vector("+bindings+"))",std::to_string(expected));
 }
 for(const char *width:{"0","-1","1/2","1025","infinity"})
  rejects("qscalarproductsum(\"x_\",\"y_\","+std::string(width)+",vector())");
 for(const char *bindings:{"0,0,1,0,0,2","2,0,1","0,-1,1","0,1024,1","0,0,infinity","0,0,interval(0,1)","0,0,[1;2]","0,0,2*m"})
  rejects("qscalarproductsum(\"x_\",\"y_\",1,vector("+std::string(bindings)+"))");
 rejects("qscalarproductsum(\"x_\",\"x_\",1,vector(0,0,1,1,0,1))");
 rejects("qreplace("+family+",\"x_0\",interval(0,1))");
 rejects("qreplace("+family+",vector(\"x_0\",2),vector(1,2))");
 // Construct the boundary through the native interface, avoiding an unrelated
 // parser nesting or input-length limit.
 MathStructure bindings;bindings.clearVector();
 for(unsigned k=0;k<1024;++k)for(unsigned slot=0;slot<2;++slot) {
  bindings.addChild(MathStructure(Number(slot)));bindings.addChild(MathStructure(Number(k)));bindings.addChild(MathStructure(1));
 }
 MathStructure prefixX("x_",true),prefixY("y_",true),width(1024),value;
 value.set(calculator.getFunction("qscalarproductsum"),&prefixX,&prefixY,&width,NULL);value.addChild(bindings);value.eval(eo);
 if(!value.isNumber() || value.number()!=1024)throw std::runtime_error("Width 1024 boundary failed");
 ++checks;
 const std::string source=R"(x_{n-1}y_{n-1} + \cdots + x_0 y_0)";
 equal(translateQuantum("replace("+source+",vector(n,x_0,x_1,y_0,y_1),vector(2,1,1,1,1))"),"2");
 equal(translateQuantum("replace("+source+",vector(x_0,x_1,y_0,y_1,n),vector(1,1,1,1,2))"),"2");
 equal(translateQuantum(R"(replace(u_{i-1}v_{i-1} + \cdots + u_0 v_0,vector("i",u_0,v_0),vector(1,3,4)))"),"12");
 equal(translateQuantum("sum(replace("+source+",vector(x_0,x_1,y_0,y_1),vector(1,1,1,1)),1,2,n)"),"3");
 equal(translateQuantum("sum(replace(qscalarproductsum(\"x_\",\"y_\",'n',vector()),vector(x_0,x_1,y_0,y_1),vector(1,1,1,1)),1,2,n)"),"3");
 equal(translateQuantum(R"(sum(replace(x_0 y_0 + \cdots + x_0 y_0,y_0,1),0,1,"x_0"))"),"1");
 equal(translateQuantum(R"(sum(qscalarproductsum("x_","x_",1,vector(1,0,3)),0,1,"x_0"))"),"18");
 equal(translateQuantum(R"(sum(qscalarproductsum("x_",'x_',1,vector(1,0,3)),0,1,"x_0"))"),"18");
 equal(translateQuantum(R"(sum(qscalarproductsum("x_","x_",1,vector((1),(0),3)),0,1,"x_0"))"),"18");
 const std::string metadata=translateQuantum(R"(sum(qscalarproductsum("a_","b_",1,vector(0,0,qindexedlabel("n",n,""),1,0,1)),0,1,n))");
 if(metadata.find("qindexedlabel(\"n\",\"qboundindex_0\",\"\")")==std::string::npos)throw std::runtime_error("Indexed prefix metadata was captured: "+metadata);
 ++checks;
 std::cout<<"PASS: "<<checks<<" scalar product checks\n";return 0;
 } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}

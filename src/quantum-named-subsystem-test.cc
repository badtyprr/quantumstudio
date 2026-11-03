// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "Variable.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void clearMessages() {while(CALCULATOR->message())CALCULATOR->nextMessage();}
static MathStructure evaluate(const std::string &input) {
 clearMessages();MathStructure value=CALCULATOR->calculate("quantum: "+input,eo);
 while(CALCULATOR->message()) {
  std::string message=CALCULATOR->message()->message();bool error=CALCULATOR->message()->type()==MESSAGE_ERROR;
  CALCULATOR->nextMessage();if(error)throw std::runtime_error(input+": "+message);
 }
 return value;
}
static void equal(const std::string &input,const std::string &expected) {
 MathStructure value=evaluate(input),reference=evaluate(expected);
 if(value.isMatrix()!=reference.isMatrix() || (value.isMatrix() && (value.rows()!=reference.rows() || value.columns()!=reference.columns())))
  throw std::runtime_error("Wrong matrix shape: "+input);
 value.transform(COMPARISON_EQUALS,reference);value.eval(eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Wrong full exact value: "+input+" expected "+expected);
 ++checks;
}
static void rejects(const std::string &input,const std::string &diagnostic) {
 try {evaluate(input);}catch(const std::exception &e) {
  if(std::string(e.what()).find(diagnostic)==std::string::npos)throw;
  ++checks;return;
 }
 throw std::runtime_error("Invalid named trace accepted: "+input);
}
int main() {try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
 eo.approximation=APPROXIMATION_EXACT;
 const std::string rho="[1/2,0,0,0;0,0,0,0;0,0,1/4,1/4;0,0,1/4,1/4]";
 // Independent expected matrices: orthogonality eliminates Bell cross terms;
 // the IBM mixture is half |00><00| plus half |1+><1+|.
 for(const auto &state:{"(|00>+|11>)/sqrt(2)","(|00>-|11>)/sqrt(2)","(|01>+|10>)/sqrt(2)","(|01>-|10>)/sqrt(2)"})
  for(const auto &label:{"B","A"})equal("ptrace(subsystems(density("+std::string(state)+"),[B,A],[2,2]),"+label+")","[1/2,0;0,1/2]");
 for(const auto &labels:{"[A,B]","[Z,X]","[pi,i]","[sin,cos]","[right,left]"}) {
  std::string names=labels;size_t comma=names.find(',');std::string left=names.substr(1,comma-1),right=names.substr(comma+1,names.size()-comma-2);
  std::string mapped="subsystems("+rho+","+names+",[2,2])";
  equal("ptrace("+mapped+","+left+")","[3/4,1/4;1/4,1/4]");
  equal("ptrace("+mapped+","+right+")","[1/2,0;0,1/2]");
 }
 equal("ptrace(subsystems("+rho+",[B,A],[2,2]),B)","[3/4,1/4;1/4,1/4]");
 equal("\\operatorname{Tr}_{\\mathsf{B}}(subsystems("+rho+",[B,A],[2,2]))","[3/4,1/4;1/4,1/4]");
 equal("ptrace(subsystems(density(|01>),[B,A],[2,2]),B)","[0,0;0,1]");
 equal("ptrace(subsystems(density(|01>),[B,A],[2,2]),A)","[1,0;0,0]");
 equal("ptrace(subsystems(density(basis(5,6)),[qutrit,qubit],[2,3]),qutrit)","[0,0,0;0,0,0;0,0,1]");
 equal("ptrace(subsystems(density(basis(5,6)),[qutrit,qubit],[2,3]),qubit)","[0,0;0,1]");
 equal("ptrace(subsystems(density(|101>),[C,A,B],[2,2,2]),A)","[0,0,0,0;0,0,0,0;0,0,0,0;0,0,0,1]");
 equal("ptrace(subsystems(density(|101>),[C,A,B],[2,2,2]),[B,C])","[1,0;0,0]");
 equal("\\operatorname{Tr}_{\\mathsf{B},\\mathsf{C}}(subsystems(density(|101>),[C,A,B],[2,2,2]))","[1,0;0,0]");
 equal("ptrace(subsystems("+rho+",[A,B],[2,2]),[B,A])","1");
 equal("ptrace(subsystems("+rho+",[A,B],[2,2]),[])",rho);
 // Labels remain literal even with an assigned calculator variable.
 calculator.addVariable(new KnownVariable("","A",MathStructure(17)));
 equal("ptrace(subsystems("+rho+",[A,B],[2,2]),A)","[3/4,1/4;1/4,1/4]");
 MathStructure mapped=evaluate("subsystems("+rho+",[A,B],[2,2])");
 if(!mapped.isFunction() || mapped.function()->referenceName()!="qsubsystems" || mapped.size()!=3 || !mapped[0].isMatrix() || mapped[1][0].symbol()!="A")
  throw std::runtime_error("Evaluated declaration lost its mapping");
 ++checks;
 calculator.addVariable(new KnownVariable("","k",MathStructure(0)));
 equal("ptrace("+rho+",k)","[3/4,1/4;1/4,1/4]");
 equal("ptrace("+rho+",[k])","[3/4,1/4;1/4,1/4]");
 equal("ptrace("+rho+",k,[2,2])","[3/4,1/4;1/4,1/4]");
 equal("sum(ptrace("+rho+",j),0,1,j)","[5/4,1/4;1/4,3/4]");
 equal("ptrace(subsystems(identity(2),[A,B],[1,2]),B)","2");
 equal("ptrace(subsystems(identity(2),[A,B],[1,2]),[A,B])","2");
 rejects("ptrace(subsystems("+rho+",[A,B],[2,2]),missing)","Unknown subsystem label");
 rejects("ptrace(subsystems("+rho+",[A,B],[2,2]),[B,B])","Duplicate traced subsystem labels");
 rejects("subsystems("+rho+",[A,A],[2,2])","Duplicate subsystem labels");
 rejects("subsystems("+rho+",[A,B],[2,3])","dimension product must equal");
 rejects("subsystems("+rho+",[A,B],[2])","matching lengths");
 rejects("subsystems([1,0,0;0,1,0],[A,B],[2,3])","square matrix");
 rejects("subsystems("+rho+",[A,B],[0,2])","integers from 1 to 512");
 rejects("subsystems("+rho+",[A,B],[2,3/2])","integers from 1 to 512");
 rejects("subsystems("+rho+",[\"bad-name\",B],[2,2])","Subsystem labels must");
 rejects("subsystems(subsystems("+rho+",[A,B],[2,2]),[B,A],[2,2])","nested redeclarations");
 rejects("ptrace(subsystems("+rho+",[A,B],[2,2]),0)","not numeric indices");
 rejects("ptrace(subsystems("+rho+",[A,B],[2,2]),A,[2,2])","already supplies dimensions");
 rejects("ptrace("+rho+",B)","explicit subsystems");
 rejects("ptrace(ptrace(subsystems("+rho+",[A,B],[2,2]),A),B)","explicit subsystems");
 equal("ptrace(subsystems(ptrace(subsystems("+rho+",[A,B],[2,2]),A),[B],[2]),B)","1");
 std::cout<<"PASS: "<<checks<<" named subsystem checks\n";return 0;
}catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}}

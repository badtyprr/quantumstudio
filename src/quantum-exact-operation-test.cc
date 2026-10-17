// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactOperation.h"
#include "libqalculate/Calculator.h"
#include "libqalculate/Variable.h"
#include <iostream>
#include <stdexcept>
#include <utility>
using namespace QuantumExact;
namespace {
unsigned checks=0;EvaluationOptions exact;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact operation check failed: "+std::to_string(checks));}
MathStructure calc(const std::string &text){return CALCULATOR->calculate(text,exact);}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 for(const char *gate:{"H","X","Y","Z","Rx(x)","Ry(x)","Rz(x)","[1,0;0,exp(i*x)]","exp(i*x)*I"}) {
  TracePreservingMap map({calc(std::string("quantum: ")+gate)},16,exact);
  check(map.dimension()==2 && map.operators().size()==1);
 }
 TracePreservingMap measurement({calc("[1,0;0,0]"),calc("[0,0;0,1]")},8,exact);
 check(measurement.operators().size()==2);
 TracePreservingMap damping({calc("[1,0;0,sqrt(3)/2]"),calc("[0,1/2;0,0]")},8,exact);
 check(damping.dimension()==2);
 TracePreservingMap reset({calc("[1,0;0,0]"),calc("[0,1;0,0]")},8,exact);
 check(reset.dimension()==2);
 std::vector<MathStructure> source={calc("identity(2)")};TracePreservingMap snapshot(source,4,exact);
 *source[0].getElement(1,1)=MathStructure(2);
 check(snapshot.operators()[0].getElement(1,1)->isOne());
 TracePreservingMap copiedFromRvalue(std::move(snapshot));
 check(copiedFromRvalue.operators().size()==1 && snapshot.operators().size()==1);
 copiedFromRvalue=measurement;check(copiedFromRvalue.operators().size()==2 && snapshot.operators().size()==1);
 rejects<std::invalid_argument>([&]{TracePreservingMap map(source,4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("2*identity(2)")},4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("[0,0;0,0]")},4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("identity(2)"),calc("identity(2)")},8,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("[1,0;0,0]")},4,exact);});
 rejects<std::domain_error>([&]{TracePreservingMap map({calc("[1,0;0,x]")},4,exact);});
 auto z=new UnknownVariable("","complexphase");auto assumptions=new Assumptions;assumptions->setType(ASSUMPTION_TYPE_COMPLEX);
 z->setAssumptions(assumptions);calculator.addVariable(z);
 rejects<std::domain_error>([&]{TracePreservingMap map({calc("[1,0;0,exp(i*complexphase)]")},4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({},4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("[1;0]")},4,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("identity(3)")},9,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("identity(2)"),calc("identity(4)")},32,exact);});
 rejects<std::invalid_argument>([&]{TracePreservingMap map({calc("[infinity,0;0,1]")},4,exact);});
 rejects<std::length_error>([&]{TracePreservingMap map({calc("identity(2)")},3,exact);});
 rejects<std::length_error>([&]{TracePreservingMap map(std::vector<MathStructure>(257,calc("identity(2)")),2048,exact);});
 EvaluationOptions numeric=exact;numeric.approximation=APPROXIMATION_APPROXIMATE;
 MathStructure approximate=calculator.calculate("[1,1;1,-1]/sqrt(2)",numeric);
 rejects<std::domain_error>([&]{TracePreservingMap map({approximate},4,exact);});
 MathStructure singleton;singleton.clearMatrix();singleton.resizeMatrix(1,1,calc("exp(i*x)"));
 TracePreservingMap phase({singleton},1,exact);check(phase.dimension()==1 && phase.operators()[0].isMatrix());
 calculator.startControl();calculator.abort();
 rejects<std::runtime_error>([&]{TracePreservingMap map({singleton},1,exact);});calculator.stopControl();
 std::cout<<"PASS: "<<checks<<" exact operation validation checks.\n";return 0;
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "quantum-display.h"
#include <iostream>

int main() {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())return 1;
 PrintOptions options;unsigned checks=0,failures=0;
 auto show=[&](const MathStructure &body) {
  MathStructure alphabet("S",true),first("n",true),last(0),prefix("y_",true),width("n",true),history;
  history.clearVector();MathStructure sum;
  sum.set(calculator.getFunction("qregistersum"),&body,&alphabet,&first,&last,&prefix,&width,&history,NULL);
  return QuantumDisplay::print(sum,options);
 };
 auto expect=[&](const std::string &text,const std::string &present,const std::string &absent) {
  ++checks;if(text.find(present)==std::string::npos || (!absent.empty() && text.find(absent)!=std::string::npos)) {
   ++failures;std::cerr << "Indexed display mismatch: " << text << "\nExpected " << present << "; excluded " << absent << '\n';
  }
 };
 expect(show(MathStructure("y_",true)),"y_","");
 MathStructure component("y_0",true),ket;
 ket.set(calculator.getFunction("qnamedket"),&component,NULL);
 expect(show(ket),"|k_0⟩","y_0");
 auto variable=new UnknownVariable("","k_0");calculator.addVariable(variable);
 MathStructure freeVariable(variable),body;
 body.set(calculator.getFunction("qadd"),&freeVariable,&component,NULL);
 std::string display=show(body);
 expect(display,"∑_{j_","∑_{k_");expect(display,"k_0","");expect(display,"j_0","");
 // An unsupported function containing a renamed component must fall back as
 // a whole expression, rather than mixing original and displayed binders.
 MathStructure unsupported;unsupported.set(calculator.getFunction("abs"),&component,NULL);
 expect(show(unsupported),"qregistersum", "∑_");
 MathStructure radicand("n",true),root;root.set(calculator.getFunction("qsqrt"),&radicand,NULL);
 expect(QuantumDisplay::print(root,options),"√(n)","qsqrt");
 expect(show(MathStructure("y_00",true)),"y_00","k_00");
 auto freeComponent=new UnknownVariable("","y_0");calculator.addVariable(freeComponent);
 expect(show(MathStructure(freeComponent)),"y_0", "k_0");
 MathStructure otherPrefix("y_0",true),first(2),last(0),assignments,family;
 assignments.clearVector();family.set(calculator.getFunction("qregisterfamily"),&otherPrefix,&first,&last,&assignments,NULL);
 expect(show(family),"|y_02 ⋯ y_00⟩", "|k_");
 MathStructure boundPrefix("y_",true);family.set(calculator.getFunction("qregisterfamily"),&boundPrefix,&first,&last,&assignments,NULL);
 unsupported.set(calculator.getFunction("abs"),&family,NULL);
 expect(show(unsupported),"qregistersum", "∑_");
 if(failures)return 1;std::cout << "Indexed display binding checks: " << checks << '\n';return 0;
}

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
 // Deferred quantum Copy uses qmatrix and can retain a horzcat argument.
 // Render entries recursively without evaluating the constructor or its cells.
 MathStructure two(2),one(1),zero(0),exponent("n",true),power,entries,constructor;
 power.set(calculator.getFunction("qpower"),&two,&exponent,NULL);
 for(const char *name:{"matrix","qmatrix"})for(bool concatenated:{false,true}) {
  entries.clearVector();entries.addChild(power);entries.addChild(one);entries.addChild(zero);entries.addChild(one);
  if(concatenated) {
   entries.set(calculator.getFunction("horzcat"),&power,&one,&zero,&one,NULL);
  }
  constructor.set(calculator.getFunction(name),&two,&two,&entries,NULL);
  MathStructure before(constructor);
  std::string text=QuantumDisplay::print(constructor,options);
  expect(text,"2^n","qpower");expect(text,"[","matrix");
  ++checks;if(!constructor.equals(before)) {++failures;std::cerr << "Display changed matrix input\n";}
 }
 // Malformed or oversized constructors must retain the original fallback.
 entries.clearVector();entries.addChild(one);
 constructor.set(calculator.getFunction("qmatrix"),&two,&two,&entries,NULL);
 expect(QuantumDisplay::print(constructor,options),"qmatrix","");
 MathStructure large(2049);
 constructor.set(calculator.getFunction("qmatrix"),&large,&one,&entries,NULL);
 expect(QuantumDisplay::print(constructor,options),"qmatrix","");
 MathStructure nested(entries);entries.addChild(nested);
 constructor.set(calculator.getFunction("qmatrix"),&one,&two,&entries,NULL);
 expect(QuantumDisplay::print(constructor,options),"qmatrix","");
 // Recursive cells must use the surrounding register binder's fresh name.
 entries.clearVector();entries.addChild(component);
 constructor.set(calculator.getFunction("qmatrix"),&one,&one,&entries,NULL);
 expect(show(constructor),"[k_0]","y_0");
 if(failures)return 1;std::cout << "Indexed display binding checks: " << checks << '\n';return 0;
}

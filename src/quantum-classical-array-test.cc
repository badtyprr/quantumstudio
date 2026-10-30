// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalArray.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include "libqalculate/QuantumClassicalRealExpression.h"
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/QuantumTrajectory.h"
#include "libqalculate/Calculator.h"
#include <cmath>
#include <iostream>
#include <limits>
using namespace QuantumClassical;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Array check "+std::to_string(checks));}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
IntegerExpression index(std::int64_t value){return IntegerExpression::constant(TypedInteger::fromBits(QuantumClassical::IntegerType::machine(Integer::Signedness::Signed),static_cast<std::uint64_t>(value)));}
template<class Step,class Run>void engineChecks(Run run,const Step &superposition) {
 const auto integer=QuantumClassical::IntegerType::sized(Integer::Signedness::Signed,16);
 const auto floating=NumericType::floating(32);
 ArraySelection first(0,{index(0)}),last(0,{index(-1)}),floatFirst(1,{index(0)});
 auto read=IntegerExpression::arrayElement(integer,first);
 auto bit=IntegerExpression::read(QuantumClassical::IntegerType::sized(Integer::Signedness::Unsigned,1),{0});
 auto output=Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,read,index(7)));
 run({Step::storeArray(first,index(7)),output},{{1,1.0}});
 run({Step::storeArray(last,index(7)),Step::storeArray(first,IntegerExpression::arrayElement(integer,last)),output},{{1,1.0}});
 // Histories with identical quantum/classical registers must still retain
 // distinct array values until the final marginalization.
 auto saved=Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,read,index(1)));
 run({superposition,Step::measure(0,0),Step::storeArray(first,bit),Step::reset(0),Step::assign({0},Bits::constant(1,0)),saved},{{0,.5},{1,.5}});
 auto numeric=RealExpression::arrayElement(floating,floatFirst);
 auto rounded=IntegerExpression::fromNumeric(integer,RealExpression::binary(RealExpression::Operation::Subtract,numeric,RealExpression::constant(16777216)));
 run({Step::storeArray(floatFirst,RealExpression::constant(16777217)),Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,rounded,index(0)))},{{1,1.0}});
 // Declaration validation covers untaken bodies without evaluating indices.
 run({Step::branch(1,1,{Step::storeArray(ArraySelection(0,{IntegerExpression::variable(integer,2)}),index(1))})},{{0,1.0}});
 rejects<std::domain_error>([&]{run({output},{});});
 rejects<std::domain_error>([&]{run({Step::storeArray(first,index(7)),Step::clearInteger(0),output},{});});
 rejects<std::out_of_range>([&]{run({Step::storeArray(ArraySelection(0,{index(2)}),index(1))},{});});
 rejects<std::invalid_argument>([&]{run({Step::branch(1,1,{Step::storeArray(ArraySelection(0,{index(0),index(0)}),index(1))})},{});});
 rejects<std::invalid_argument>([&]{run({Step::storeArray(floatFirst,index(1))},{});});
 rejects<std::invalid_argument>([&]{run({Step::storeArray(first,RealExpression::constant(1))},{});});
 // Invalid destination wins over an undefined RHS (defined evaluation order).
 rejects<std::out_of_range>([&]{run({Step::storeArray(ArraySelection(0,{index(2)}),IntegerExpression::variable(integer,2))},{});});
 // A valid destination does not suppress a failed RHS.
 rejects<std::domain_error>([&]{run({Step::storeArray(first,IntegerExpression::variable(integer,2))},{});});
}
int main(){try {
 const auto integer=QuantumClassical::IntegerType::sized(Integer::Signedness::Signed,16);const auto floating=NumericType::floating(32);
 const auto angle=NumericType::angle(8);
 RuntimeStorage storage(std::vector<QuantumClassical::IntegerType>(7,integer),{floating,floating,angle,angle},
  {ArrayDeclaration::integers(integer,0,{2,3}),ArrayDeclaration::numerics(floating,0,{2}),ArrayDeclaration::numerics(angle,2,{2}),ArrayDeclaration::integers(integer,7,{0,4096})});
 for(unsigned r=0;r<2;++r)for(unsigned c=0;c<3;++c) {
  ArraySelection selection(0,{index(r),index(c)});selection.validate(0,storage);check(selection.evaluate(0,0,storage)==r*3+c);
  auto extent=IntegerExpression::arrayExtent(selection);extent.validate(0,storage);check(extent.evaluate(0,0,storage).value().bits()==1);
  auto read=IntegerExpression::arrayElement(integer,selection);read.validate(0,storage);
  rejects<std::domain_error>([&]{read.evaluate(0,0,storage);});
  storage.write(r*3+c,TypedInteger::fromBits(integer,10*r+c));check(read.evaluate(0,0,storage).value().bits()==10*r+c);
  check(ArraySelection(0,{index(static_cast<int>(r)-2),index(static_cast<int>(c)-3)}).evaluate(0,0,storage)==r*3+c);
 }
 for(auto invalid:std::vector<std::vector<IntegerExpression>>{{index(-3),index(0)},{index(2),index(0)},{index(0),index(-4)},{index(0),index(3)},
   {index(std::numeric_limits<std::int64_t>::min()),index(0)}})
  rejects<std::out_of_range>([&]{ArraySelection(0,invalid,"array.qasm:7:2").evaluate(0,0,storage);});
 for(unsigned array:{1u,2u})check(IntegerExpression::arrayExtent(ArraySelection(array,{index(0)})).evaluate(0,0,storage).value().bits()==1);
 rejects<std::out_of_range>([&]{IntegerExpression::arrayExtent(ArraySelection(0,{index(2),index(0)})).evaluate(0,0,storage);});
 auto huge=IntegerExpression::constant(TypedInteger::fromBits(QuantumClassical::IntegerType::machine(Integer::Signedness::Unsigned),~std::uint64_t(0)));
 rejects<std::out_of_range>([&]{ArraySelection(0,{huge,index(0)}).evaluate(0,0,storage);});
 rejects<std::invalid_argument>([&]{ArraySelection(0,{index(0)}).validate(0,storage);});
 rejects<std::out_of_range>([&]{ArraySelection(3,{index(0),index(0)}).evaluate(0,0,storage);});
 rejects<std::out_of_range>([&]{ArraySelection(4,{index(0)}).validate(0,storage);});
 auto undefined=IntegerExpression::variable(integer,6);
 ArraySelection deferred(0,{index(0),undefined});deferred.validate(0,storage);
 rejects<std::domain_error>([&]{deferred.evaluate(0,0,storage);});
 storage.write(6,TypedInteger::fromBits(integer,2));check(deferred.evaluate(0,0,storage)==2);
 auto branch=storage;branch.write(2,TypedInteger::fromBits(integer,99));check(storage.read(2).value().bits()==2);check(branch.read(2).value().bits()==99);
 auto floatRead=RealExpression::arrayElement(floating,ArraySelection(1,{index(-1)}));floatRead.validate(0,storage);
 rejects<std::domain_error>([&]{floatRead.evaluateTyped(0,0,storage);});
 storage.numeric().write(1,NumericValue::floating(16777217));check(floatRead.evaluateTyped(0,0,storage).floatingValue()==16777216);
 auto angleRead=RealExpression::arrayElement(angle,ArraySelection(2,{index(0)}));storage.numeric().write(2,NumericValue::fromBits(angle,255));check(angleRead.evaluateTyped(0,0,storage).bits()==255);
 rejects<std::invalid_argument>([&]{IntegerExpression::arrayElement(integer,ArraySelection(1,{index(0)})).validate(0,storage);});
 rejects<std::invalid_argument>([&]{RealExpression::arrayElement(NumericType::floating(64),ArraySelection(1,{index(0)})).validate(0,storage);});
 rejects<std::invalid_argument>([&]{RuntimeStorage bad(std::vector<QuantumClassical::IntegerType>(6,integer),{}, {ArrayDeclaration::integers(integer,0,{4}),ArrayDeclaration::integers(integer,3,{3})});});
 rejects<std::out_of_range>([&]{RuntimeStorage bad({integer},{},{ArrayDeclaration::integers(integer,0,{2})});});
 rejects<std::invalid_argument>([&]{RuntimeStorage bad({integer},{},{ArrayDeclaration::integers(QuantumClassical::IntegerType::machine(Integer::Signedness::Signed),0,{1})});});
 rejects<std::length_error>([&]{ArrayDeclaration::integers(integer,0,{65,64});});
 rejects<std::length_error>([&]{ArrayDeclaration::integers(integer,0,{4097});});
 rejects<std::invalid_argument>([&]{ArrayDeclaration::integers(integer,0,{1,1,1,1,1,1,1,1});});
 rejects<std::invalid_argument>([&]{ArraySelection(0,{index(0)},std::string(513,'a'));});
 auto bitIndex=IntegerExpression::read(QuantumClassical::IntegerType::sized(Integer::Signedness::Unsigned,1),{1});
 rejects<std::out_of_range>([&]{IntegerExpression::arrayElement(integer,ArraySelection(0,{index(0),bitIndex})).validate(1,storage);});
 auto deep=index(0);for(unsigned k=0;k<30;++k)deep=IntegerExpression::cast(deep.type(),deep);
 rejects<std::length_error>([&]{IntegerExpression::arrayElement(integer,ArraySelection(0,{index(0),deep}));});
 const std::vector<QuantumClassical::IntegerType> types(3,integer);
 const std::vector<NumericType> numericTypes{floating};
 const std::vector<ArrayDeclaration> arrays{ArrayDeclaration::integers(integer,0,{2}),ArrayDeclaration::numerics(floating,0,{1})};
 using S=QuantumNumerics::TrajectoryStep;
 const double h=std::sqrt(.5);
 engineChecks<S>([&](const std::vector<S> &steps,const std::map<std::uint64_t,double> &expected) {
  const auto result=QuantumNumerics::sampleTrajectories(1,2,10000,731,{1},steps,types,1024,{},100,numericTypes,arrays);
  check(result.size()==expected.size());for(const auto &item:expected)check(std::abs(result.at(item.first)/10000.0-item.second)<.03);
 },S::gate({h,h,h,-h},{0}));
 Calculator calculator;check(calculator.loadGlobalDefinitions());EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 using E=QuantumExact::CircuitStep;
 QuantumExact::TracePreservingMap hadamard({calculator.calculate("[1,1;1,-1]/sqrt(2)",exact)},4,exact);
 engineChecks<E>([&](const std::vector<E> &steps,const std::map<std::uint64_t,double> &expected) {
  const auto records=QuantumExact::evaluateCircuit(1,2,steps,types,65536,exact,100,numericTypes,arrays);
  const auto result=QuantumExact::weights(records,1,2,{1},65536,exact);
  check(result.size()==expected.size());for(const auto &item:expected){auto difference=result.at(item.first);difference-=MathStructure(item.second);difference.eval(exact);check(difference.isZero());}
 },E::map(hadamard,{0}));
 std::cout<<"PASS: "<<checks<<" checked array storage and expression checks\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}

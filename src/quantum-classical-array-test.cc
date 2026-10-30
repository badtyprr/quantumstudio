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
void wireReferenceChecks() {
 const auto type=QuantumClassical::IntegerType::machine(Integer::Signedness::Signed);
 RuntimeStorage storage({type});
 std::vector<WireSelection::Target> targets;
 for(unsigned wire=0;wire<25;wire++)targets.push_back({{24-wire},index(0)});
 auto all=WireSelection::references(targets,"call entry");all.validate(25,0,storage);
 auto resolved=all.evaluate(0,0,storage);check(resolved.size()==25);
 for(unsigned wire=0;wire<25;wire++)check(resolved[wire]==24-wire);
 rejects<std::invalid_argument>([&]{WireSelection gate(targets);});
 targets.push_back({{0},index(0)});rejects<std::invalid_argument>([&]{WireSelection::references(targets);});
 rejects<std::invalid_argument>([&]{WireSelection::references({});});
 rejects<std::invalid_argument>([&]{WireSelection::references({{{0},index(0)},{{1,0},index(1)}}).evaluate(0,0,storage);});
 rejects<std::out_of_range>([&]{WireSelection::references({{{25},index(0)}}).validate(25,0,storage);});
 rejects<std::out_of_range>([&]{WireSelection::references({{{0},index(-1)}}).evaluate(0,0,storage);});
 auto huge=IntegerExpression::constant(TypedInteger::fromBits(QuantumClassical::IntegerType::machine(Integer::Signedness::Unsigned),~std::uint64_t(0)));
 rejects<std::out_of_range>([&]{WireSelection::references({{{0},huge}}).evaluate(0,0,storage);});
 auto variable=IntegerExpression::variable(type,0);
 auto deferred=WireSelection::references({{{2,0,1},variable}});deferred.validate(3,0,storage);
 rejects<std::domain_error>([&]{deferred.evaluate(0,0,storage);});
 storage.write(0,TypedInteger::fromBits(type,1));check(deferred.evaluate(0,0,storage)==std::vector<unsigned>{0});
 storage.write(0,TypedInteger::fromBits(type,2));check(deferred.evaluate(0,0,storage)==std::vector<unsigned>{1});
 auto deep=index(0);for(unsigned k=0;k<30;k++)deep=IntegerExpression::cast(type,deep);
 rejects<std::length_error>([&]{WireSelection::references(std::vector<WireSelection::Target>(25,{{0},deep}));});
}
void copyChecks() {
 const auto type=QuantumClassical::IntegerType::machine(Integer::Signedness::Signed);
 auto slice=[](std::size_t array,std::int64_t start,std::int64_t stop,std::int64_t stride=1) {
  auto a=index(start),b=index(stop),c=index(stride);
  return ArrayView(array,{ArrayViewAxis::range(&a,&b,&c)},true);
 };
 RuntimeStorage storage(std::vector<QuantumClassical::IntegerType>(12,type),{},
  {ArrayDeclaration::integers(type,0,{6}),ArrayDeclaration::integers(type,6,{6})});
 auto reset=[&]{for(unsigned k=0;k<12;++k)storage.write(k,TypedInteger::fromBits(type,k));};
 auto equals=[&](std::size_t slot,std::uint64_t value){check(storage.read(slot).value().bits()==value);};
 reset();ArrayCopy(slice(0,1,5),{slice(0,0,4)}).execute(0,0,storage);
 for(unsigned k=0;k<6;++k)equals(k,k?k-1:0);
 reset();ArrayCopy(slice(0,0,4),{slice(0,1,5)}).execute(0,0,storage);
 for(unsigned k=0;k<6;++k)equals(k,k<5?k+1:5);
 reset();ArrayCopy(slice(0,0,5),{slice(0,0,2),slice(0,0,2)}).execute(0,0,storage);
 for(unsigned k=0;k<6;++k)equals(k,k%3);
 reset();ArrayCopy(slice(0,5,0,-1),{slice(0,0,5)}).execute(0,0,storage);
 for(unsigned k=0;k<6;++k)equals(k,5-k);
 reset();ArrayCopy(slice(0,0,4,2),{slice(0,-3,-1)}).execute(0,0,storage);
 equals(0,3);equals(2,4);equals(4,5);equals(1,1);
 reset();storage.clear(5);
 rejects<std::domain_error>([&]{ArrayCopy(slice(1,0,5),{slice(0,0,5)}).execute(0,0,storage);});
 for(unsigned k=6;k<12;++k)equals(k,k); // no partial writes on a late undefined read
 rejects<std::invalid_argument>([&]{ArrayCopy(slice(1,0,4),{slice(0,0,5)}).execute(0,0,storage);});
 rejects<std::invalid_argument>([&]{ArrayCopy(ArrayView(0,{ArrayViewAxis::range()},false),{slice(1,0,5)});});
 const auto floating=NumericType::floating(32),angle=NumericType::angle(8);
 RuntimeStorage numeric({}, {floating,floating,angle,angle},
  {ArrayDeclaration::numerics(floating,0,{2}),ArrayDeclaration::numerics(angle,2,{2})});
 numeric.numeric().write(0,NumericValue::floating(16777217));numeric.numeric().write(1,NumericValue::floating(-0.0));
 ArrayCopy(slice(0,0,1),{slice(0,1,0,-1)}).execute(0,0,numeric);
 check(numeric.numeric().read(0).bits()==0x80000000u);check(numeric.numeric().read(1).floatingValue()==16777216);
 numeric.numeric().write(2,NumericValue::fromBits(angle,255));numeric.numeric().write(3,NumericValue::fromBits(angle,1));
 ArrayCopy(slice(1,0,1),{slice(1,1,0,-1)}).execute(0,0,numeric);
 check(numeric.numeric().read(2).bits()==1);check(numeric.numeric().read(3).bits()==255);
 rejects<std::invalid_argument>([&]{ArrayCopy(slice(0,0,1),{slice(1,0,1)}).validate(0,numeric);});
 RuntimeStorage empty({}, {}, {ArrayDeclaration::integers(type,0,{0}),ArrayDeclaration::integers(type,0,{1,0}),ArrayDeclaration::integers(type,0,{2,0})});
 ArrayView zero(0,{ArrayViewAxis::range()},true),oneByZero(1,{ArrayViewAxis::range(),ArrayViewAxis::range()},true),twoByZero(2,{ArrayViewAxis::range(),ArrayViewAxis::range()},true);
 ArrayCopy(zero,{zero}).execute(0,0,empty);check(true);
 ArrayCopy(twoByZero,{oneByZero,oneByZero}).execute(0,0,empty);check(true);
 ArrayCopy(zero,std::vector<ArrayView>(64,zero)).execute(0,0,empty);check(true);
 rejects<std::invalid_argument>([&]{ArrayCopy(zero,std::vector<ArrayView>(65,zero));});
 rejects<std::invalid_argument>([&]{ArrayCopy(twoByZero,{zero});});
 RuntimeStorage shaped(std::vector<QuantumClassical::IntegerType>(12,type),{},
  {ArrayDeclaration::integers(type,0,{2,3}),ArrayDeclaration::integers(type,6,{3,2})});
 ArrayView left(0,{ArrayViewAxis::range(),ArrayViewAxis::range()},true),right(1,{ArrayViewAxis::range(),ArrayViewAxis::range()},false);
 rejects<std::invalid_argument>([&]{ArrayCopy(left,{right}).execute(0,0,shaped);});
}

template<class Step,class Run>void engineChecks(Run run,const Step &superposition) {
 const auto integer=QuantumClassical::IntegerType::sized(Integer::Signedness::Signed,16);
 const auto floating=NumericType::floating(32);
 run({Step::checkWireReferences(WireSelection::references({{{0},index(0)}}))},{{0,1.0}});
 rejects<std::invalid_argument>([&]{run({Step::checkWireReferences(WireSelection::references({{{0},index(0)},{{0},index(0)}}))},{});});
 rejects<std::out_of_range>([&]{run({Step::checkWireReferences(WireSelection::references({{{0},index(-1)}}))},{});});
 rejects<std::domain_error>([&]{run({Step::checkWireReferences(WireSelection::references({{{0},IntegerExpression::variable(integer,2)}}))},{});});
 auto invalidWire=Step::checkWireReferences(WireSelection::references({{{1},index(0)}}));
 rejects<std::out_of_range>([&]{run({Step::branch(1,1,{invalidWire},{})},{});});
 ArraySelection first(0,{index(0)}),last(0,{index(-1)}),floatFirst(1,{index(0)});
 ArrayView writable(0,{ArrayViewAxis::range()},true),readonly(0,{ArrayViewAxis::range()},false);
 ArraySelection throughView(writable,{index(0)}),throughReadonly(readonly,{index(0)});
 run({Step::checkArrayReferences(ArrayReferenceCheck({readonly},{{2}}))},{{0,1.0}});
 run({Step::checkArrayReferences(ArrayReferenceCheck({readonly,writable}))},{{0,1.0}});
 rejects<std::invalid_argument>([&]{run({Step::checkArrayReferences(ArrayReferenceCheck({writable,writable}))},{});});
 rejects<std::invalid_argument>([&]{run({Step::checkArrayReferences(ArrayReferenceCheck({readonly},{{1}})),Step::storeInteger(0,IntegerExpression::variable(integer,2))},{});});

 rejects<std::invalid_argument>([&]{run({Step::storeArray(throughReadonly,index(7))},{});});
 auto zeroIndex=index(0),oneIndex=index(1);
 ArrayView firstView(0,{ArrayViewAxis::range(&zeroIndex,&zeroIndex)},true),lastView(0,{ArrayViewAxis::range(&oneIndex,&oneIndex)},true);
 run({Step::storeArray(first,index(7)),Step::copyArray(ArrayCopy(lastView,{firstView})),Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,IntegerExpression::arrayElement(integer,last),index(7)))},{{1,1.0}});
 rejects<std::domain_error>([&]{run({Step::copyArray(ArrayCopy(lastView,{firstView}))},{});});
 auto read=IntegerExpression::arrayElement(integer,first);
 auto bit=IntegerExpression::read(QuantumClassical::IntegerType::sized(Integer::Signedness::Unsigned,1),{0});
 auto output=Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,read,index(7)));
 run({Step::storeArray(first,index(7)),output},{{1,1.0}});
 run({Step::storeArray(throughView,index(7)),output},{{1,1.0}});
 run({Step::storeArray(throughView,index(7)),Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,IntegerExpression::arrayElement(integer,throughReadonly),index(7)))},{{1,1.0}});
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
void viewChecks() {
 const auto integer=QuantumClassical::IntegerType::machine(Integer::Signedness::Signed);
 RuntimeStorage storage(std::vector<QuantumClassical::IntegerType>(13,integer),{},
  {ArrayDeclaration::integers(integer,0,{3,4}),ArrayDeclaration::integers(integer,12,{4096,4096,0})});
 const auto all=ArrayViewAxis::range();const auto one=index(1),two=index(2),three=index(3),minusOne=index(-1),zero=index(0);
 ArrayView full(0,{all,all},true);auto complete=full.evaluate(0,0,storage);
 check(complete.dimensions==std::vector<unsigned>({3,4}) && complete.slots.size()==12);
 // No backing element is initialized: binding must remain address-only.
 auto extent=IntegerExpression::viewExtent(full,1);extent.validate(0,storage);check(extent.evaluate(0,0,storage).value().bits()==4);
 rejects<std::out_of_range>([&]{IntegerExpression::viewExtent(full,2);});
 ArrayView row(full,{ArrayViewAxis::scalar(minusOne),all},true);
 ArraySelection lastInRow(row,{minusOne});check(lastInRow.evaluate(0,0,storage)==11);
 ArrayView scalar(row,{ArrayViewAxis::scalar(zero)},false);check(ArraySelection(scalar,{}).evaluate(0,0,storage)==8);
 auto resolved=row.evaluate(0,0,storage);check(resolved.dimensions==std::vector<unsigned>({4}) && resolved.slots==std::vector<std::size_t>({8,9,10,11}));
 ArrayView reverse(row,{ArrayViewAxis::range(nullptr,nullptr,&minusOne)},false);
 check(reverse.evaluate(0,0,storage).slots==std::vector<std::size_t>({11,10,9,8}));
 rejects<std::invalid_argument>([&]{ArrayView illegal(reverse,{all},true);});
 ArrayView even(row,{ArrayViewAxis::range(&zero,&three,&two)},true),odd(row,{ArrayViewAxis::range(&one,&three,&two)},true);
 ArrayView::validateBindings({even.evaluate(0,0,storage),odd.evaluate(0,0,storage)});check(true);
 rejects<std::invalid_argument>([&]{ArrayView::validateBindings({row.evaluate(0,0,storage),even.evaluate(0,0,storage)});});
 ArrayView::validateBindings({reverse.evaluate(0,0,storage),row.evaluate(0,0,storage)});check(true);
 ArrayView::validateBindings({reverse.evaluate(0,0,storage),reverse.evaluate(0,0,storage)});check(true);
 auto variable=IntegerExpression::variable(integer,12);
 ArrayView dynamic(0,{ArrayViewAxis::scalar(variable),all},true);dynamic.validate(0,storage);
 rejects<std::domain_error>([&]{dynamic.evaluate(0,0,storage);});
 storage.write(12,TypedInteger::fromBits(integer,1));check(dynamic.evaluate(0,0,storage).slots==std::vector<std::size_t>({4,5,6,7}));
 storage.write(12,TypedInteger::fromBits(integer,3));rejects<std::out_of_range>([&]{dynamic.evaluate(0,0,storage);});
 auto huge=IntegerExpression::constant(TypedInteger::fromBits(QuantumClassical::IntegerType::machine(Integer::Signedness::Unsigned),~std::uint64_t(0)));
 rejects<std::out_of_range>([&]{ArrayView(0,{ArrayViewAxis::scalar(huge),all},false).evaluate(0,0,storage);});
 rejects<std::invalid_argument>([&]{ArrayView(row,{ArrayViewAxis::range(nullptr,nullptr,&zero)},false).evaluate(0,0,storage);});
 ArrayView empty(1,{all,all,all},false);auto emptyResult=empty.evaluate(0,0,storage);
 ArrayReferenceCheck({empty},{{4096,4096,0}}).evaluate(0,0,storage);check(true);
 ArrayReferenceCheck({full},{{3,4}}).evaluate(0,0,storage);check(true);
 rejects<std::invalid_argument>([&]{ArrayReferenceCheck({full},{{4,3}}).evaluate(0,0,storage);});
 rejects<std::invalid_argument>([&]{ArrayReferenceCheck({full},{{12}});});
 rejects<std::out_of_range>([&]{ArrayReferenceCheck({dynamic}).evaluate(0,0,storage);});
 check(emptyResult.dimensions==std::vector<unsigned>({4096,4096,0}) && emptyResult.slots.empty());
 rejects<std::out_of_range>([&]{ArrayView(1,{all,all,ArrayViewAxis::scalar(zero)},false).evaluate(0,0,storage);});
 rejects<std::invalid_argument>([&]{ArrayView(0,{all},false).validate(0,storage);});
 // A huge stride selects at most one element without overflowing arithmetic.
 check(ArrayView(row,{ArrayViewAxis::range(nullptr,nullptr,&huge)},false).evaluate(0,0,storage).slots==std::vector<std::size_t>({8}));
 auto minimum=index(std::numeric_limits<std::int64_t>::min());
 check(ArrayView(row,{ArrayViewAxis::range(nullptr,nullptr,&minimum)},false).evaluate(0,0,storage).slots==std::vector<std::size_t>({11}));
 check(ArrayView(row,{ArrayViewAxis::range(&three,&zero)},false).evaluate(0,0,storage).slots.empty());
}
int main(){try {
 wireReferenceChecks();
 copyChecks();
 viewChecks();
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
 check(IntegerExpression::arrayExtent(ArraySelection(0,{index(1)})).evaluate(0,0,storage).value().bits()==1);
 RuntimeStorage emptyShape({}, {}, {ArrayDeclaration::integers(integer,0,{1,0})});
 check(IntegerExpression::arrayExtent(ArraySelection(0,{index(0)})).evaluate(0,0,emptyShape).value().bits()==1);
 rejects<std::out_of_range>([&]{IntegerExpression::arrayExtent(ArraySelection(0,{index(0),index(0)})).evaluate(0,0,emptyShape);});
 rejects<std::invalid_argument>([&]{IntegerExpression::arrayElement(integer,ArraySelection(0,{index(0)})).validate(0,emptyShape);});
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

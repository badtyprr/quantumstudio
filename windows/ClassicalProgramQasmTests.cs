// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;
using S=ClassicalCircuit.Step;
using N=ClassicalCircuit.ExpressionNode;

static class ClassicalProgramQasmTests {
 static readonly List<object> cases=new List<object>();
 static int rejected;
 static N Constant(int width,string value){return new N {Kind="Constant",Width=width,Value=value};}
 static N Read(params int[] bits){return new N {Kind="Read",Bits=bits};}
 static S Gate(string expression,params int[] wires){return new S {Kind="Gate",Expression=expression,Wires=wires};}
 static S Measure(int wire,int bit){return new S {Kind="Measure",Wires=new[]{wire},ClassicalBit=bit};}
 static ClassicalCircuit Circuit(int qubits,int bits,int[] outputs,S[] steps,ClassicalCircuit.Variable[] variables=null,int budget=1000000,int version=9) {
  return ClassicalCircuit.From(new ClassicalCircuit.Document {Version=version,Qubits=qubits,
   Registers=bits==0 ? new ClassicalCircuit.Register[0] : new[]{new ClassicalCircuit.Register{Name="c",Size=bits}},
   Variables=variables??new ClassicalCircuit.Variable[0],OutputBits=outputs,Steps=steps,LoopConditionBudget=budget});
 }
 static void Case(string name,ClassicalCircuit circuit,string expected,bool error=false,bool approximate=false,bool runtimeRange=false) {
  cases.Add(new {name=name,source=ClassicalProgramQasm.Export(circuit),expected=expected,runtime_error=error,approximate_probabilities=approximate,runtime_range=runtimeRange});
 }
 static void Reject(ClassicalCircuit circuit,string expected) {
  try {ClassicalProgramQasm.Export(circuit);}
  catch(InvalidDataException e){if(e.Message.Contains(expected)){rejected++;return;}throw;}
  throw new Exception("Unsupported program accepted: "+expected);
 }
 static void Main(string[] args) {
  if(args.Length!=1 || File.Exists(args[0]))throw new ArgumentException("Pass a fresh case path.");
  RuntimeAngles();
  Case("zero-initial-bits",Circuit(0,3,new[]{2,0,1},new S[0]),"000");
  Case("empty-program",Circuit(0,0,new int[0],new S[0]),"");
  Case("version-two-without-variables",ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=1,
   Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new[]{Gate("X",0),Measure(0,0)}}),"1");
  Case("measured-x",Circuit(1,1,new[]{0},new[]{Gate("X",0),Measure(0,0)}),"1");
  Case("reset",Circuit(1,1,new[]{0},new[]{Gate("X",0),new S{Kind="Reset",Wires=new[]{0}},Measure(0,0)}),"0");
  Case("phase-interference",Circuit(1,1,new[]{0},new[]{Gate("H",0),Gate("P(pi)",0),Gate("H",0),Measure(0,0)}),"1",false,true);
  Case("conditional",Circuit(1,2,new[]{1},new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")},new S{Kind="Conditional",Mask="1",Value="1",Expression="X",Wires=new[]{0}},Measure(0,1)}),"1");
  Case("branch",Circuit(0,2,new[]{1},new[]{new S{Kind="Branch",Mask="1",Value="1",WhenTrue=new[]{new S{Kind="Assign",Wires=new[]{1},ClassicalValue=Constant(1,"0")}},WhenFalse=new[]{new S{Kind="Assign",Wires=new[]{1},ClassicalValue=Constant(1,"1")}}}}),"1");
  Case("expression-branch",Circuit(0,1,new[]{0},new[]{new S{Kind="ExpressionBranch",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")}},WhenFalse=new S[0]}}),"1");
  Case("end",Circuit(0,1,new[]{0},new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")},new S{Kind="End"},new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"0")}}),"1");
  var loop=new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"0")},new S{Kind="Continue"}}};
  Case("while-continue",Circuit(0,1,new[]{0},new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")},loop}),"0");
  Case("while-break",Circuit(0,1,new[]{0},new[]{new S{Kind="While",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")},new S{Kind="Break"}}}}),"1");
  var variable=new[]{new ClassicalCircuit.Variable{Name="original",Signedness="Unsigned",Width=1}};
  var read=new N{Kind="IntegerVariable",Signedness="Unsigned",Width=1,Slot=0};
  var assign=new S{Kind="Assign",Wires=new[]{0},ClassicalValue=new N{Kind="IntegerBits",Left=read}};
  Case("integer-store",Circuit(0,1,new[]{0},new[]{new S{Kind="StoreInteger",VariableSlot=0,IntegerValue=new N{Kind="IntegerConstant",Signedness="Unsigned",Width=1,Value="1"}},assign},variable),"1");
  Case("undefined-integer",Circuit(0,1,new int[0],new[]{assign},variable),"",true);
  Case("end-before-undefined",Circuit(0,1,new int[0],new[]{new S{Kind="End"},assign},variable),"");
  Reject(Circuit(1,1,new[]{0},new[]{Gate("matrix(2,2,[0,1,1,0])",0)}),"cannot decompose");
  Reject(Circuit(1,1,new[]{0},new[]{new S{Kind="Channel",Expression="depolarizing(1/2)",Wires=new[]{0}}}),"noise");
  var store=new S{Kind="StoreInteger",VariableSlot=0,IntegerValue=new N{Kind="IntegerConstant",Signedness="Unsigned",Width=1,Value="1"}};
  var clear=new S{Kind="ClearInteger",VariableSlot=0};
  Reject(Circuit(0,1,new[]{0},new[]{store,clear,assign},variable),"lifetime");
  Reject(Circuit(0,1,new[]{0},new[]{loop},null,12),"loop budget");
  Case("branch-local",Circuit(0,1,new[]{0},new[]{new S{Kind="ExpressionBranch",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{store,assign,clear},WhenFalse=new S[0]}},variable),"1");
  var repeat=new S{Kind="Branch",Mask="2",Value="0",
   WhenTrue=new[]{store,new S{Kind="Assign",Wires=new[]{1},ClassicalValue=Constant(1,"1")}},
   WhenFalse=new[]{new S{Kind="Assign",Wires=new[]{2},ClassicalValue=new N{Kind="IntegerBits",Left=read}},new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"0")}}};
  var begin=new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"1")};
  Case("global-loop-carry",Circuit(0,3,new[]{2},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{repeat}}},variable),"1");
  Case("fresh-loop-local",Circuit(0,3,new[]{2},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{repeat,clear}}},variable),"0",true);
  Case("conditional-undefined-local",Circuit(0,1,new[]{0},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{new S{Kind="ExpressionBranch",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{assign},WhenFalse=new S[0]},clear}}},variable),"0",true);
  var stop=new S{Kind="Assign",Wires=new[]{0},ClassicalValue=Constant(1,"0")};
  Case("local-continue",Circuit(0,1,new[]{0},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,stop,clear,new S{Kind="Continue"}}}},variable),"0");
  Case("local-break",Circuit(0,1,new[]{0},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,stop,clear,new S{Kind="Break"}}}},variable),"0");
  Reject(Circuit(0,1,new[]{0},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,stop,new S{Kind="Continue"},clear}}},variable),"lifetime");
  var rangeType=new[]{new ClassicalCircuit.Variable{Name="iterator",Signedness="Unsigned",Width=2}};
  var rangeRead=new N{Kind="IntegerVariable",Signedness="Unsigned",Width=2,Slot=0};
  var rangeAssign=new S{Kind="Assign",Wires=new[]{0,1},ClassicalValue=new N{Kind="IntegerBits",Left=rangeRead}};
  var bounds=new ClassicalCircuit.RangeNode{Start=I(0),Stop=I(2),Step=I(1)};
  var range=new S{Kind="ForRange",VariableSlot=0,Range=bounds,WhenTrue=new[]{rangeAssign}};
  Case("range-last",Circuit(0,2,new[]{1,0},new[]{range},rangeType,1000000,10),"10");
  Case("range-mutation",Circuit(0,2,new[]{1,0},new[]{new S{Kind="ForRange",VariableSlot=0,Range=bounds,WhenTrue=new[]{rangeAssign,new S{Kind="StoreInteger",VariableSlot=0,IntegerValue=I(0)}}}},rangeType,1000000,10),"10");
  Case("range-continue",Circuit(0,2,new[]{1,0},new[]{new S{Kind="ForRange",VariableSlot=0,Range=bounds,WhenTrue=new[]{rangeAssign,new S{Kind="Continue"}}}},rangeType,1000000,10),"10");
  Case("range-break",Circuit(0,2,new[]{1,0},new[]{new S{Kind="ForRange",VariableSlot=0,Range=new ClassicalCircuit.RangeNode{Start=I(1),Stop=I(2),Step=I(1)},WhenTrue=new[]{rangeAssign,new S{Kind="Break"}}}},rangeType,1000000,10),"01");
  Case("range-empty",Circuit(0,2,new[]{1,0},new[]{new S{Kind="ForRange",VariableSlot=0,Range=new ClassicalCircuit.RangeNode{Start=I(2),Stop=I(1),Step=I(1)},WhenTrue=new[]{rangeAssign}}},rangeType,1000000,10),"00");
  Reject(Circuit(0,2,new[]{1,0},new[]{range,rangeAssign},rangeType,1000000,10),"lifetime");
  var twoTypes=new[]{rangeType[0],new ClassicalCircuit.Variable{Name="bound",Signedness="Unsigned",Width=2}};
  var boundRead=new N{Kind="IntegerVariable",Signedness="Unsigned",Width=2,Slot=1};
  var measuredBound=new S{Kind="StoreInteger",VariableSlot=1,IntegerValue=new N{Kind="IntegerCast",Signedness="Unsigned",Width=2,Left=new N{Kind="IntegerRead",Signedness="Unsigned",Width=1,Bits=new[]{2}}}};
  var dynamicBounds=new ClassicalCircuit.RangeNode{Start=I(0),Stop=boundRead,Step=I(1)};
  Case("runtime-range-bound",Circuit(1,3,new[]{1,0},new[]{Gate("X",0),Measure(0,2),measuredBound,new S{Kind="ForRange",VariableSlot=0,Range=dynamicBounds,WhenTrue=new[]{rangeAssign}}},twoTypes,1000000,10),"01",runtimeRange:true);
  Case("runtime-range-snapshot",Circuit(1,3,new[]{1,0},new[]{Gate("X",0),Measure(0,2),measuredBound,new S{Kind="ForRange",VariableSlot=0,Range=dynamicBounds,WhenTrue=new[]{rangeAssign,new S{Kind="StoreInteger",VariableSlot=1,IntegerValue=I(0)}}}},twoTypes,1000000,10),"01",runtimeRange:true);
  var innerRange=new S{Kind="ForRange",VariableSlot=1,Range=new ClassicalCircuit.RangeNode{Start=I(0),Stop=rangeRead,Step=I(1)},WhenTrue=new[]{new S{Kind="Assign",Wires=new[]{0,1},ClassicalValue=new N{Kind="IntegerBits",Left=boundRead}}}};
  Case("nested-ranges",Circuit(0,2,new[]{1,0},new[]{new S{Kind="ForRange",VariableSlot=0,Range=new ClassicalCircuit.RangeNode{Start=I(0),Stop=I(1),Step=I(1)},WhenTrue=new[]{innerRange}}},twoTypes,1000000,10),"01");
  Case("nested-local-continue",Circuit(0,1,new[]{0},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,new S{Kind="ExpressionBranch",ClassicalValue=Read(0),WhenTrue=new[]{stop,clear,new S{Kind="Continue"}},WhenFalse=new S[0]},clear}}},variable),"0");
  var innerBreak=new S{Kind="While",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{new S{Kind="Break"}}};
  var keep=new S{Kind="Assign",Wires=new[]{1},ClassicalValue=new N{Kind="IntegerBits",Left=read}};
  Case("inner-break-keeps-outer-local",Circuit(0,2,new[]{1},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,innerBreak,keep,stop,clear}}},variable),"1");
  Reject(Circuit(0,2,new[]{1},new[]{begin,new S{Kind="While",ClassicalValue=Read(0),WhenTrue=new[]{store,new S{Kind="While",ClassicalValue=Constant(1,"1"),WhenTrue=new[]{clear,new S{Kind="Break"}}},keep,stop,clear}}},variable),"lifetime");
  File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(cases));
  Console.WriteLine("PASS: "+cases.Count+" program cases; "+rejected+" unsupported programs rejected.");
 }
 static N I(int value){return new N{Kind="IntegerConstant",Signedness="Unsigned",Width=2,Value=value.ToString()};}
 static void RuntimeAngles() {
  var variables=new[]{new ClassicalCircuit.Variable{Name="angle",Signedness="Unsigned",Width=2}};
  var read=new N{Kind="IntegerVariable",Signedness="Unsigned",Width=2,Slot=0};
  var angle=new ClassicalCircuit.RealNode{Kind="Binary",Operator="Divide",
   Left=new ClassicalCircuit.RealNode{Kind="Integer",IntegerValue=read},
   Right=new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="4611686018427387904"}};
  foreach(string axis in new[]{"X","Y","Z"}) {
   var rotation=new S{Kind="Rotation",Axis=axis,Angle=angle,Wires=new[]{0}};
   var circuit=Circuit(1,0,new int[0],new[]{rotation},variables,1000000,11);
   string source=ClassicalProgramQasm.Export(circuit);
   if(!source.Contains("r"+axis.ToLowerInvariant()+"((float[64](v0) / (2.0))) q[0];"))
    throw new Exception("Runtime angle lost real division: "+source);
   // A use after a lexical clear must not be moved into the earlier scope.
   var clear=new S{Kind="ClearInteger",VariableSlot=0};
   Reject(Circuit(1,0,new int[0],new[]{new S{Kind="Branch",Mask="0",Value="0",WhenTrue=new[]{clear},WhenFalse=new S[0]},rotation},variables,1000000,11),"lifetime");
  }
  var expressions=new ClassicalExpressionQasm(0);
  if(expressions.Real(ClassicalRealExpression.Constant(BitConverter.Int64BitsToDouble(long.MinValue)))!="(-0.0)")throw new Exception("Signed zero changed.");
  foreach(double value in new[]{0.0,1.0,-1.0,0.1,double.Epsilon,double.MaxValue}) {
   string text=expressions.Real(ClassicalRealExpression.Constant(value));
   double parsed=Double.Parse(text.Substring(1,text.Length-2),System.Globalization.CultureInfo.InvariantCulture);
   if(BitConverter.DoubleToInt64Bits(parsed)!=BitConverter.DoubleToInt64Bits(value))throw new Exception("Binary64 export changed a constant.");
  }
 }
}

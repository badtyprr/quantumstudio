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
 static ClassicalCircuit Circuit(int qubits,int bits,int[] outputs,S[] steps,ClassicalCircuit.Variable[] variables=null,int budget=1000000) {
  return ClassicalCircuit.From(new ClassicalCircuit.Document {Version=9,Qubits=qubits,
   Registers=bits==0 ? new ClassicalCircuit.Register[0] : new[]{new ClassicalCircuit.Register{Name="c",Size=bits}},
   Variables=variables??new ClassicalCircuit.Variable[0],OutputBits=outputs,Steps=steps,LoopConditionBudget=budget});
 }
 static void Case(string name,ClassicalCircuit circuit,string expected,bool error=false,bool approximate=false) {
  cases.Add(new {name=name,source=ClassicalProgramQasm.Export(circuit),expected=expected,runtime_error=error,approximate_probabilities=approximate});
 }
 static void Reject(ClassicalCircuit circuit,string expected) {
  try {ClassicalProgramQasm.Export(circuit);}
  catch(InvalidDataException e){if(e.Message.Contains(expected)){rejected++;return;}throw;}
  throw new Exception("Unsupported program accepted: "+expected);
 }
 static void Main(string[] args) {
  if(args.Length!=1 || File.Exists(args[0]))throw new ArgumentException("Pass a fresh case path.");
  Case("zero-initial-bits",Circuit(0,3,new[]{2,0,1},new S[0]),"000");
  Case("empty-program",Circuit(0,0,new int[0],new S[0]),"");
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
  Reject(Circuit(0,1,new[]{0},new[]{new S{Kind="ClearInteger",VariableSlot=0}},variable),"lifetime");
  Reject(Circuit(0,1,new[]{0},new[]{loop},null,12),"loop budget");
  File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(cases));
  Console.WriteLine("PASS: "+cases.Count+" program cases; "+rejected+" unsupported programs rejected.");
 }
}

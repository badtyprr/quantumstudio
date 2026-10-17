// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class ClassicalCircuitTests {
 static int checks;
 static void Check(bool ok) {if(!ok)throw new Exception("Check failed: "+checks);checks++;}
 static void Reject(Action action) {try {action();}catch(ArgumentException){checks++;return;}catch(InvalidDataException){checks++;return;}throw new Exception("Invalid circuit accepted: "+checks);}
 static ClassicalCircuit.Step Measure(int bit) {return new ClassicalCircuit.Step {Kind="Measure",Wires=new[]{0},ClassicalBit=bit};}
 static ClassicalCircuit.Document Program() {return new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="flag",Size=1},new ClassicalCircuit.Register {Name="record",Size=63}},OutputBits=new[]{63,0},Steps=new[]{Measure(63),new ClassicalCircuit.Step {Kind="Branch",Mask="9223372036854775808",Value="9223372036854775808",WhenTrue=new[]{Measure(0)},WhenFalse=new ClassicalCircuit.Step[0]}}};}
 static ClassicalCircuit.ExpressionNode Constant(int width,string value) {return new ClassicalCircuit.ExpressionNode {Kind="Constant",Width=width,Value=value};}
 static ClassicalCircuit.Document Expressions() {
  var result=Program();result.Version=3;
  result.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=new[]{63},ClassicalValue=Constant(1,"1")},
   new ClassicalCircuit.Step {Kind="ExpressionBranch",ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Read",Bits=new[]{63}},WhenTrue=new[]{Measure(0)},WhenFalse=new ClassicalCircuit.Step[0]}};
  return result;
 }
 static void Main() {
  var draft=Program();var circuit=ClassicalCircuit.From(draft);var text=circuit.Serialize();
  Check(circuit.ClassicalBits==64 && circuit.Qubits==1);
  Check(ClassicalCircuit.Load(text).Serialize()==text);
  Check(circuit.Snapshot().Registers[1].Name=="record");
  Check(circuit.SamplingGates()[1].Mask==1UL<<63);
  Check(circuit.SamplingGates()[1].WhenTrue[0].ClassicalBit==0);
  draft.Registers[0].Name="changed";draft.Steps[0].Wires[0]=7;
  var snapshot=circuit.Snapshot();snapshot.Steps[1].WhenTrue[0].ClassicalBit=8;
  var gates=circuit.SamplingGates();gates[0].Wires[0]=8;gates[1].WhenTrue.Clear();
  var output=circuit.OutputBits;output[0]=9;
  Check(circuit.Serialize()==text && circuit.SamplingGates()[0].Wires[0]==0 && circuit.SamplingGates()[1].WhenTrue.Count==1 && circuit.OutputBits[0]==63);
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=1,d=>d.Qubits=26,d=>d.Registers[1].Name="flag",d=>d.Registers[0].Name=" flag",
   d=>d.Registers[0].Size=0,d=>d.Registers[1].Size=64,d=>d.OutputBits=new[]{64},
   d=>d.Steps[0].ClassicalBit=null,d=>d.Steps[0].ClassicalBit=64,d=>d.Steps[0].Expression="X",
   d=>d.Steps[0].Kind="0",d=>d.Steps[0].Mask="0",d=>d.Steps[1].Value="18446744073709551616",
   d=>d.Steps[1].Mask="-1",d=>d.Steps[1].WhenFalse=null,d=>d.Steps[1].WhenFalse=new[]{Measure(64)}
  }) {var bad=Program();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));}
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Version\":2","\"Version\":\"2\"")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Qubits\":1","\"Qubits\":1.0")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Name\":\"flag\"","\"Name\":\"flag\",\"Unknown\":0")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Kind\":\"Measure\"","\"Kind\":\"Measure\",\"Unknown\":0")));
  var many=Program();many.Steps=new ClassicalCircuit.Step[512];for(int i=0;i<512;i++)many.Steps[i]=Measure(0);
  Check(ClassicalCircuit.From(many).SamplingGates().Count==512);
  many.Steps=new ClassicalCircuit.Step[513];for(int i=0;i<513;i++)many.Steps[i]=Measure(0);
  Reject(()=>ClassicalCircuit.From(many));
  var empty=Program();empty.Registers=new ClassicalCircuit.Register[0];empty.OutputBits=new int[0];empty.Steps=new ClassicalCircuit.Step[0];
  Check(ClassicalCircuit.From(empty).ClassicalBits==0);
  var nested=Program();var body=new[]{Measure(0)};
  for(int depth=0;depth<32;depth++)body=new[]{new ClassicalCircuit.Step {Kind="Branch",Mask="1",Value="1",WhenTrue=body,WhenFalse=new ClassicalCircuit.Step[0]}};
  nested.Steps=body;Check(ClassicalCircuit.From(nested).SamplingGates().Count==1);
  nested.Steps=new[]{new ClassicalCircuit.Step {Kind="Branch",Mask="1",Value="1",WhenTrue=body,WhenFalse=new ClassicalCircuit.Step[0]}};
  Reject(()=>ClassicalCircuit.From(nested));
  Reject(()=>ClassicalCircuit.Load(new string(' ',262145)));
  var expressionDraft=Expressions();var expressionCircuit=ClassicalCircuit.From(expressionDraft);string expressionText=expressionCircuit.Serialize();
  Check(ClassicalCircuit.Load(expressionText).Serialize()==expressionText);
  var wide=Expressions();var allBits=new int[64];for(int bit=0;bit<64;bit++)allBits[bit]=bit;
  wide.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=allBits,ClassicalValue=Constant(64,"18446744073709551615")}};
  Check(ClassicalCircuit.Load(ClassicalCircuit.From(wide).Serialize()).SamplingGates()[0].ClassicalExpression.Value==UInt64.MaxValue);
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(1,64,new[]{63,0},expressionCircuit.SamplingGates())).StartsWith("QEXACT2\n"));
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestClassical(1,64,1,0,new[]{63,0},expressionCircuit.SamplingGates())).StartsWith("QSAMPLE3\n"));
  expressionDraft.Steps[0].ClassicalValue.Value="0";expressionCircuit.Snapshot().Steps[1].ClassicalValue.Bits[0]=0;
  Check(expressionCircuit.Snapshot().Steps[0].ClassicalValue.Value=="1" && expressionCircuit.SamplingGates()[1].ClassicalExpression.Indices[0]==63);
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=2,d=>d.Version=4,d=>d.Steps[0].ClassicalValue=null,
   d=>d.Steps[0].ClassicalValue.Width=null,d=>d.Steps[0].ClassicalValue.Width=0,d=>d.Steps[0].ClassicalValue.Value="2",
   d=>d.Steps[0].ClassicalValue.Value="18446744073709551616",d=>d.Steps[0].ClassicalValue.Value="-1",
   d=>d.Steps[0].ClassicalValue.Value=" 1",d=>d.Steps[0].ClassicalValue.Bits=new[]{0},
   d=>d.Steps[0].Kind="Reset",d=>d.Steps[0].Mask="0",d=>d.Steps[0].Expression="X",
   d=>d.Steps[1].ClassicalValue.Bits=new[]{64},d=>d.Steps[1].ClassicalValue.Bits=new[]{0,1},
   d=>d.Steps[1].ClassicalValue.Kind="Unknown",d=>d.Steps[1].ClassicalValue.Left=Constant(1,"0")
  }) {var bad=Expressions();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));}
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Width\":1","\"Width\":1.0")));
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Value\":\"1\"","\"Value\":1")));
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Kind\":\"Read\"","\"Kind\":\"Read\",\"Unknown\":null")));
  var expr=Constant(1,"0");for(int k=1;k<32;k++)expr=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};
  var bounded=Expressions();bounded.Steps[0].ClassicalValue=expr;Check(ClassicalCircuit.From(bounded).SamplingGates()[0].ClassicalExpression.Width==1);
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};Reject(()=>ClassicalCircuit.From(bounded));
  expr=Constant(1,"1");for(int k=0;k<8;k++)expr=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator="Xor",Left=expr,Right=expr};
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};Check(ClassicalCircuit.From(bounded).SamplingGates()[0].ClassicalExpression.Width==1);
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator="Xor",Left=expr,Right=Constant(1,"1")};Reject(()=>ClassicalCircuit.From(bounded));
  foreach(string op in new[]{"0","XOR","Unknown"}) {bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator=op,Left=Constant(1,"0"),Right=Constant(1,"1")};Reject(()=>ClassicalCircuit.From(bounded));}
  foreach(string direction in new[]{"Left","Right"})foreach(string signedness in new[]{"Unsigned","Signed"}) {
   var rotated=Expressions();rotated.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=allBits,ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Rotate",RotationDirection=direction,DistanceInterpretation=signedness,Left=Constant(64,"1"),Right=Constant(8,"255")}}};
   var rotation=ClassicalCircuit.From(rotated);var loaded=ClassicalCircuit.Load(rotation.Serialize());
   Check(loaded.Serialize()==rotation.Serialize());
   var node=loaded.SamplingGates()[0].ClassicalExpression;
   Check(node.Width==64 && node.RotationDirection.ToString()==direction && node.DistanceInterpretation.ToString()==signedness && node.Right.Width==8);
   foreach(var mutate in new Action<ClassicalCircuit.ExpressionNode>[] {n=>n.RotationDirection=null,n=>n.RotationDirection="0",n=>n.RotationDirection="left",n=>n.DistanceInterpretation="Unknown",n=>n.DistanceInterpretation=null,n=>n.Left=null,n=>n.Right=null,n=>n.Width=64,n=>n.Operator="And"}) {
    var bad=loaded.Snapshot();mutate(bad.Steps[0].ClassicalValue);Reject(()=>ClassicalCircuit.From(bad));
   }
  }
  wide.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="PopulationCount",Left=Constant(64,"18446744073709551615")};
  var counted=ClassicalCircuit.From(wide);Check(ClassicalCircuit.Load(counted.Serialize()).SamplingGates()[0].ClassicalExpression.Width==64);
  wide.Steps[0].ClassicalValue.Right=Constant(1,"0");Reject(()=>ClassicalCircuit.From(wide));wide.Steps[0].ClassicalValue.Right=null;
  wide.Steps[0].ClassicalValue.RotationDirection="Left";Reject(()=>ClassicalCircuit.From(wide));
  Console.WriteLine("PASS: "+checks+" classical circuit storage checks.");
 }
}

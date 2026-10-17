// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
class ClassicalCircuitTests {
 static int checks;
 static void Check(bool ok) {if(!ok)throw new Exception("Check failed: "+checks);checks++;}
 static void Reject(Action action) {try {action();}catch(ArgumentException){checks++;return;}catch(InvalidDataException){checks++;return;}throw new Exception("Invalid circuit accepted: "+checks);}
 static ClassicalCircuit.Step Measure(int bit) {return new ClassicalCircuit.Step {Kind="Measure",Wires=new[]{0},ClassicalBit=bit};}
 static ClassicalCircuit.Document Program() {return new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="flag",Size=1},new ClassicalCircuit.Register {Name="record",Size=63}},OutputBits=new[]{63,0},Steps=new[]{Measure(63),new ClassicalCircuit.Step {Kind="Branch",Mask="9223372036854775808",Value="9223372036854775808",WhenTrue=new[]{Measure(0)},WhenFalse=new ClassicalCircuit.Step[0]}}};}
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
  Console.WriteLine("PASS: "+checks+" classical circuit storage checks.");
 }
}

// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;

static class ClassicalQasmExportTests {
 static int checks;
 static void Check(bool value){if(!value)throw new Exception("Export invariant failed.");checks++;}
 static ClassicalCircuit Circuit(int qubits=1) {
  return ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=qubits,
   Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},
   Steps=new[]{new ClassicalCircuit.Step{Kind="Gate",Expression="X",Wires=new[]{0}}}});
 }
 static void Main(string[] args) {
  if(args.Length!=1 || Directory.Exists(args[0]))throw new ArgumentException("Pass a fresh test directory.");
  Directory.CreateDirectory(args[0]);string path=Path.Combine(args[0],"existing.qasm");
  File.WriteAllText(path,"keep these bytes",new UTF8Encoding(false));byte[] original=File.ReadAllBytes(path);
  try {QasmImport.CompileBytes(null);throw new Exception("Null compiler input accepted.");}
  catch(ArgumentNullException){checks++;}
  try {QasmImport.CompileBytes(new byte[262145]);throw new Exception("Oversized compiler input accepted.");}
  catch(InvalidDataException){checks++;}
  var circuit=Circuit();string snapshot=circuit.Serialize();int calls=0;
  var prepared=ClassicalQasmExport.Prepare(circuit,bytes=>{
   calls++;Check(Encoding.UTF8.GetString(bytes).Contains("x q[0];"));
   // A compiler callback cannot mutate the bytes that will be written.
   bytes[0]=0;return circuit.Serialize();
  });
  Check(calls==1 && circuit.Serialize()==snapshot);
  Check(File.ReadAllText(path)=="keep these bytes");
  prepared.SaveTo(path);string source=File.ReadAllText(path,new UTF8Encoding(false,true));
  Check(source.StartsWith("OPENQASM 3.0;") && source.Contains("x q[0];"));
  Check(File.ReadAllBytes(path)[0]==(byte)'O');
  string fresh=Path.Combine(args[0],"new \u03b1.qasm");prepared.SaveTo(fresh);
  Check(File.ReadAllText(fresh)==source);
  File.WriteAllBytes(path,original);
  try {ClassicalQasmExport.Prepare(circuit,bytes=>{throw new InvalidDataException("compiler rejected");}).SaveTo(path);throw new Exception("Compiler failure accepted.");}
  catch(InvalidDataException){Check(File.ReadAllText(path)=="keep these bytes");}
  try {ClassicalQasmExport.Prepare(circuit,bytes=>"{}").SaveTo(path);throw new Exception("Malformed compiler output accepted.");}
  catch(InvalidDataException){Check(File.ReadAllText(path)=="keep these bytes");}
  try {ClassicalQasmExport.Prepare(circuit,bytes=>Circuit(2).Serialize()).SaveTo(path);throw new Exception("Changed interface accepted.");}
  catch(InvalidDataException){Check(File.ReadAllText(path)=="keep these bytes");}
  var unsupported=circuit.Snapshot();unsupported.Steps[0].Expression="matrix(2,2,[0,1,1,0])";
  try {ClassicalQasmExport.Prepare(ClassicalCircuit.From(unsupported),bytes=>{calls++;return snapshot;}).SaveTo(path);throw new Exception("Unsupported program accepted.");}
  catch(InvalidDataException){Check(calls==1 && File.ReadAllText(path)=="keep these bytes");}
  using(var locked=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.None)) {
   try {prepared.SaveTo(path);throw new Exception("Locked destination replaced.");}
   catch(IOException){checks++;}
  }
  Check(File.ReadAllText(path)=="keep these bytes");
  // A transient external lock must recover without discarding the validated
  // snapshot. The permanent-lock case above still must fail without truncation.
  var transient=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.None);
  var release=new System.Threading.Thread(delegate() {System.Threading.Thread.Sleep(100);transient.Dispose();});
  release.Start();
  try {prepared.SaveTo(path);}finally {release.Join();transient.Dispose();}
  Check(File.ReadAllText(path)==source);
  string directory=Path.Combine(args[0],"directory");Directory.CreateDirectory(directory);
  try {prepared.SaveTo(directory);throw new Exception("Directory destination accepted.");}
  catch(IOException){Check(Directory.Exists(directory));}
  Check(Directory.GetFiles(args[0],"*.tmp").Length==0);
  Check(circuit.Serialize()==snapshot);
  Console.WriteLine("PASS: "+checks+" atomic OpenQASM export checks.");
 }
}

// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class SourceImportBridgeTests {
 static int checks;
 static void Check(bool ok) {if(!ok)throw new Exception("Source bridge check "+checks+" failed.");++checks;}
 static void Main(string[] args) {
  if(args.Length!=1)throw new ArgumentException("Pass the validation fixture directory.");
  string folder=Path.Combine(args[0],"Unicode \u03ba "+Guid.NewGuid().ToString("N"));
  Directory.CreateDirectory(folder);
  string entry=Path.Combine(folder,"main \u03ba.qasm"),helper=Path.Combine(folder,"helper.qasm");
  File.WriteAllText(helper,"gate flip a { x a; }\n",new UTF8Encoding(false));
  File.WriteAllText(entry,"OPENQASM 3.0; include \"stdgates.inc\"; include \"helper.qasm\"; qubit q; bit c; flip q; c=measure q;\n",new UTF8Encoding(true));
  var history=new ClassicalProgramHistory(ClassicalCircuit.From(new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new ClassicalCircuit.Register[0],OutputBits=new int[0],Steps=new ClassicalCircuit.Step[0]}));
  history.ImportSource(QasmImport.CompileSource(entry,false,true),false);
  Check(history.Source!=null && history.Source.SourceJson.Contains("\"Bom\":true") && history.Source.SourceJson.Contains("helper.qasm"));
  string imported=history.Serialize();
  history.Edit(d=>d.Qubits=2);history.Undo();Check(history.Serialize()==imported);
  history.Open(imported);Check(history.Serialize()==imported && !history.Source.CircuitEdited);
  File.WriteAllText(helper,"OPENQASM 3.0; include \"stdgates.inc\"; gate flip a { x a; }\n",new UTF8Encoding(false));
  try{history.ImportSource(QasmImport.CompileSource(entry,false,true),false);throw new Exception("Strict import accepted module headers.");}
  catch(InvalidDataException){Check(history.Serialize()==imported);}
  history.ImportSource(QasmImport.CompileSource(entry,true,true,true),true);
  Check(history.Source.PublishedU && history.Source.SourceJson.Contains("\"ModuleHeaders\":true"));
  imported=history.Serialize();
  File.WriteAllText(entry,"OPENQASM 3.0; include \"../outside.qasm\"; qubit q;",new UTF8Encoding(false));
  try{history.ImportSource(QasmImport.CompileSource(entry,false,true),false);throw new Exception("Escaping include accepted.");}
  catch(InvalidDataException){Check(history.Serialize()==imported);}
  Console.WriteLine("PASS: "+checks+" frozen source-import bridge checks.");
 }
}

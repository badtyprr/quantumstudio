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
  Check(QasmImport.CheckSource(history.Source.SourceJson,folder).Contains("\"Unchanged\": true"));
  history.Edit(d=>d.Qubits=2);history.Undo();Check(history.Serialize()==imported);
  history.Open(imported);Check(history.Serialize()==imported && !history.Source.CircuitEdited);
  File.WriteAllText(helper,"OPENQASM 3.0; include \"stdgates.inc\"; gate flip a { x a; }\n",new UTF8Encoding(false));
  Check(QasmImport.CheckSource(history.Source.SourceJson,folder).Contains("\"Status\": \"changed\"") && history.Serialize()==imported);
  try{history.ImportSource(QasmImport.CompileSource(entry,false,true),false);throw new Exception("Strict import accepted module headers.");}
  catch(InvalidDataException){Check(history.Serialize()==imported);}
  File.Delete(helper);
  Check(QasmImport.CheckSource(history.Source.SourceJson,folder).Contains("\"Status\": \"missing\"") && history.Serialize()==imported);
  try{QasmImport.CheckSource(history.Source.SourceJson,Path.Combine(folder,"missing root"));throw new Exception("Missing root accepted.");}
  catch(InvalidDataException){Check(history.Serialize()==imported);}
  File.WriteAllText(helper,"OPENQASM 3.0; include \"stdgates.inc\"; gate flip a { x a; }\n",new UTF8Encoding(false));
  history.ImportSource(QasmImport.CompileSource(entry,true,true,true),true);
  Check(history.Source.PublishedU && history.Source.SourceJson.Contains("\"ModuleHeaders\":true"));
  imported=history.Serialize();
  File.WriteAllText(entry,"OPENQASM 3.0; include \"../outside.qasm\"; qubit q;",new UTF8Encoding(false));
  try{history.ImportSource(QasmImport.CompileSource(entry,false,true),false);throw new Exception("Escaping include accepted.");}
  catch(InvalidDataException){Check(history.Serialize()==imported);}
  string nested=Path.Combine(folder,"sub dir");Directory.CreateDirectory(nested);
  string nestedEntry=Path.Combine(nested,"entry.qasm");
  File.WriteAllText(nestedEntry,"OPENQASM 3.0; include \"../helper.qasm\"; qubit q; flip q;",new UTF8Encoding(false));
  string nestedResult=QasmImport.CompileSource(nestedEntry,false,true,true,folder);
  Check(nestedResult.Contains("sub dir/entry.qasm") && nestedResult.Contains("helper.qasm"));
  File.WriteAllText(entry,"OPENQASM 3; include \"helper.qasm\"; qubit q; flip q;",new UTF8Encoding(false));
  File.WriteAllText(helper,"// line one\ngate flip a { x a }\n",new UTF8Encoding(false));
  try{QasmImport.CompileSource(entry);throw new Exception("Malformed dependency accepted.");}
  catch(InvalidDataException error){Check(error.Message.Contains("helper.qasm:2:19:") && error.Message.Contains("Unexpected token") && history.Serialize()==imported);}
  File.WriteAllText(helper,"// line one\ngate flip a { undefined_gate a; }\n",new UTF8Encoding(false));
  try{history.ImportSource(QasmImport.CompileSource(entry,false,true),false);throw new Exception("Undefined dependency gate accepted.");}
  catch(InvalidDataException error){Check(error.Message.Contains("helper.qasm:2:") && error.Message.Contains("Unsupported / undeclared QASM operation") && history.Serialize()==imported);}
  Console.WriteLine("PASS: "+checks+" frozen source-import bridge checks.");
 }
}

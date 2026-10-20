// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;

// Only a fully serialized, compiler-validated snapshot can reach file writing.
sealed class ClassicalQasmExport {
 readonly byte[] source;
 ClassicalQasmExport(byte[] value){source=value;}
 public static ClassicalQasmExport Prepare(ClassicalCircuit circuit) {
  return Prepare(circuit,bytes=>QasmImport.CompileBytes(bytes,false,true));
 }
 internal static ClassicalQasmExport Prepare(ClassicalCircuit circuit,Func<byte[],string> compile) {
  if(compile==null)throw new ArgumentNullException("compile");
  byte[] bytes=new UTF8Encoding(false,true).GetBytes(ClassicalProgramQasm.Export(circuit));
  var imported=ClassicalCircuit.Load(compile((byte[])bytes.Clone()));
  if(imported.Qubits!=circuit.Qubits || imported.OutputBits.Length!=circuit.OutputBits.Length)
   throw new InvalidDataException("Compiled export changed the circuit's qubits or output width.");
  return new ClassicalQasmExport(bytes);
 }
 public void SaveTo(string path) {
  string target=Path.GetFullPath(path);
  string temporary=target+"."+Guid.NewGuid().ToString("N")+".tmp";
  try {
   // A same-directory temporary makes replacement atomic. Neither validation
   // failure nor a failed write truncates the user's existing destination.
   using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
    file.Write(source,0,source.Length);file.Flush(true);
   }
   if(File.Exists(target))File.Replace(temporary,target,null);
   else File.Move(temporary,target);
  } finally {
   if(File.Exists(temporary))File.Delete(temporary);
  }
 }
}

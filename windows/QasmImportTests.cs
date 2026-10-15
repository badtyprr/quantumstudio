// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class QasmImportTests {
 static int checks;
 static void Same(byte[] expected,byte[] actual) {
  if(Convert.ToBase64String(expected)!=Convert.ToBase64String(actual))throw new Exception("Source bytes changed.");
  ++checks;
 }
 static void Reject(string path,byte[] source) {
  File.WriteAllBytes(path,source);
  try {QasmImport.ReadSource(path);} catch(InvalidDataException) {++checks;return;}
  catch(DecoderFallbackException) {++checks;return;}
  throw new Exception("Invalid source accepted.");
 }
 static int Main() {
  string path=Path.Combine(Path.GetTempPath(),"quantum-qasm-"+Guid.NewGuid().ToString("N")+".qasm");
  try {
   byte[] valid=Encoding.UTF8.GetBytes("OPENQASM 3.0; // Unicode: \u03c0\n");
   File.WriteAllBytes(path,valid);Same(valid,QasmImport.ReadSource(path));
   byte[] bom=new byte[valid.Length+3];bom[0]=0xef;bom[1]=0xbb;bom[2]=0xbf;valid.CopyTo(bom,3);
   File.WriteAllBytes(path,bom);Same(valid,QasmImport.ReadSource(path));
   byte[] boundary=Encoding.ASCII.GetBytes(new string(' ',262144));
   File.WriteAllBytes(path,boundary);Same(boundary,QasmImport.ReadSource(path));
   File.WriteAllBytes(path,new byte[0]);Same(new byte[0],QasmImport.ReadSource(path));
   Reject(path,new byte[262145]);
   Reject(path,new byte[]{0xc3,0x28});
   Reject(path,new byte[]{0xe2,0x82});
   Reject(path,new byte[]{0xff,0xfe,0x41,0});
   Console.WriteLine("PASS: "+checks+" OpenQASM input checks");return 0;
  } catch(Exception error) {Console.Error.WriteLine(error);return 1;}
  finally {if(File.Exists(path))File.Delete(path);}
 }
}

// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Windows;
class CircuitFileTests {
 static int checks;
 static void Check(bool condition) {if(!condition)throw new Exception("Circuit file assertion failed.");++checks;}
 [STAThread] static int Main() {
  string path=Path.Combine(Path.GetTempPath(),"quantum-circuit-"+Guid.NewGuid().ToString("N")+".qcircuit");
  var owner=new Window {ShowInTaskbar=false,Opacity=0};owner.Show();var composer=new CircuitComposer(owner,delegate(string expression){});
  try {
   composer.BellState(0);string expected=composer.Expression();
   composer.SaveCircuit(path);byte[] valid=File.ReadAllBytes(path);
   composer.BellState(1);composer.OpenCircuit(path);Check(composer.Expression()==expected);
   byte[] bom=new byte[valid.Length+3];bom[0]=0xef;bom[1]=0xbb;bom[2]=0xbf;valid.CopyTo(bom,3);
   File.WriteAllBytes(path,bom);composer.OpenCircuit(path);Check(composer.Expression()==expected);
   foreach(byte[] invalid in new[]{new byte[262145],new byte[]{0xc3,0x28},new byte[]{0xff,0xfe,0x41,0},Encoding.UTF8.GetBytes("{\"Version\":2,\"Qubits\":2,\"Steps\":[]}")}) {
    File.WriteAllBytes(path,invalid);bool rejected=false;
    try {composer.OpenCircuit(path);}catch(InvalidDataException){rejected=true;}catch(DecoderFallbackException){rejected=true;}
    Check(rejected);Check(composer.Expression()==expected);
   }
   Check(composer.Undo());Check(composer.Expression()!=expected);
   Check(composer.Redo());Check(composer.Expression()==expected);
   Console.WriteLine("PASS: "+checks+" circuit file and state preservation checks");return 0;
  }catch(Exception error){Console.Error.WriteLine(error);return 1;}
  finally {composer.Close();owner.Close();if(File.Exists(path))File.Delete(path);}
 }
}

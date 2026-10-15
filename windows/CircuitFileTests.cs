// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
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
   var serializer=new JavaScriptSerializer();
   foreach(int count in new[]{65,CircuitComposer.MaxSteps}) {
    var gates=new CircuitComposer.Step[count];
    for(int k=0;k<count;++k)gates[k]=new CircuitComposer.Step {Gate="X",Angle="",Wires=new[]{0}};
    composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=1,Steps=gates}));
    string longExpression=composer.Expression();Check(longExpression.StartsWith("sequence(["));
    composer.SaveCircuit(path);composer.BellState(0);composer.OpenCircuit(path);Check(composer.Expression()==longExpression);
    Check(composer.Undo());Check(composer.Redo());Check(composer.Expression()==longExpression);
   }
   foreach(string angle in new[]{"qstate_0","qstate_{0}"}) {
    Check(composer.UpdateGate(0,"Rz","0",angle));
    Check(composer.Expression().Contains("Rz("+angle+")"));
    Check(composer.Expression().EndsWith(",qstate_1)"));
   }
   string preserved=composer.Expression();
   var excessive=new CircuitComposer.Step[CircuitComposer.MaxSteps+1];
   for(int k=0;k<excessive.Length;++k)excessive[k]=new CircuitComposer.Step {Gate="X",Angle="",Wires=new[]{0}};
   bool overLimit=false;
   try {composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=1,Steps=excessive}));}catch(InvalidDataException){overLimit=true;}
   Check(overLimit);Check(composer.Expression()==preserved);
   var measurements=new[]{
    new CircuitComposer.Step {Gate="H",Angle="",Wires=new[]{0}},
    new CircuitComposer.Step {Gate="Measure",Angle="",Wires=new[]{1}},
    new CircuitComposer.Step {Gate="Measure",Angle="",Wires=new[]{0}},
    new CircuitComposer.Step {Gate="Measure",Angle="",Wires=new[]{1}}};
   composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=2,Steps=measurements}));
   string grouped=composer.Expression();Check(grouped=="dephase(apply(H,|00⟩,[0]),[1,0])");
   composer.SaveCircuit(path);var saved=serializer.Deserialize<CircuitComposer.CircuitFile>(File.ReadAllText(path));
   Check(saved.Steps.Length==4 && saved.Steps[1].Wires[0]==1 && saved.Steps[3].Wires[0]==1);
   Check(composer.OpenQasm().Split(new[]{"measure"},StringSplitOptions.None).Length==4);
   composer.BellState(0);composer.OpenCircuit(path);Check(composer.Expression()==grouped);
   Check(composer.UpdateGate(2,"H","0",""));
   Check(composer.Expression()=="dephase(apply(H,dephase(apply(H,|00⟩,[0]),[1]),[0]),[1])");
   Check(composer.Undo());Check(composer.Expression()==grouped);
   Console.WriteLine("PASS: "+checks+" circuit file and state preservation checks");return 0;
  }catch(Exception error){Console.Error.WriteLine(error);return 1;}
  finally {composer.Close();owner.Close();if(File.Exists(path))File.Delete(path);}
 }
}

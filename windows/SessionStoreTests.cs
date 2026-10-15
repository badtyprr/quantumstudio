// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class SessionStoreTests {
 static int checks;
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static void Reject(Action action) {try{action();}catch(InvalidDataException){checks++;return;}catch(ArgumentException){checks++;return;}throw new Exception("Invalid session accepted");}
 static CalculationSession Valid() {return new CalculationSession {Version=1,Expression="⟨0|H|0⟩",Mode=0,Evaluation=1,History=new[]{new SessionEntry {Expression="|0⟩",Result="[1;0]",Mode=0,Evaluation=0}}};}
 static int Main() {
  string directory=Path.Combine(Path.GetTempPath(),"QuantumStudio-session-test-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
  try {
   string path=Path.Combine(directory,"roundtrip.qsession");var expected=Valid();SessionStore.Save(path,expected);
   var actual=SessionStore.Load(path);Require(actual.Expression==expected.Expression && actual.History[0].Result==expected.History[0].Result,"Unicode roundtrip failed");
   expected.Expression="replacement";SessionStore.Save(path,expected);Require(SessionStore.Load(path).Expression=="replacement","Atomic replacement failed");
   string before=File.ReadAllText(path);expected.Version=2;Reject(delegate {SessionStore.Save(path,expected);});Require(File.ReadAllText(path)==before,"Invalid save damaged destination");
   expected=Valid();expected.History=new SessionEntry[51];Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.Expression=new string('x',32001);Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.Expression=new string('界',10667);Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.Mode=2;Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.Evaluation=-1;Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.History[0].Expression=" ";Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.History[0].Result=new string('x',32769);Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.Expression="\uD800";Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.History[0].Result="\uD800";Reject(delegate {SessionStore.Validate(expected);});
   File.WriteAllBytes(path,new byte[]{0xff,0xfe,0x61});Reject(delegate {SessionStore.Load(path);});
   File.WriteAllBytes(path,new byte[]{0xc3,0x28});Reject(delegate {SessionStore.Load(path);});
   SessionStore.Save(path,Valid());byte[] valid=File.ReadAllBytes(path),bom=new byte[valid.Length+3];bom[0]=239;bom[1]=187;bom[2]=191;Array.Copy(valid,0,bom,3,valid.Length);File.WriteAllBytes(path,bom);Require(SessionStore.Load(path).Expression==Valid().Expression,"UTF-8 BOM rejected");
   using(var file=new FileStream(path,FileMode.Create)){file.SetLength(8*1024*1024+1);}Reject(delegate {SessionStore.Load(path);});
   Require(Directory.GetFiles(directory,"*.tmp").Length==0,"Temporary files left behind");
   Console.WriteLine("PASS: "+checks+" session storage checks");return 0;
  }catch(Exception e){Console.Error.WriteLine(e);return 1;}
  finally {foreach(string file in Directory.GetFiles(directory))File.Delete(file);Directory.Delete(directory);}
 }
}

// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class SessionStoreTests {
 static int checks;
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static void Reject(Action action) {try{action();}catch(InvalidDataException){checks++;return;}catch(ArgumentException){checks++;return;}throw new Exception("Invalid session accepted");}
 static CalculationSession Valid() {return new CalculationSession {Version=1,Expression="⟨0|H|0⟩",Mode=0,Evaluation=1,History=new[]{new SessionEntry {Expression="|0⟩",Result="[1;0]",Mode=0,Evaluation=0}}};}
 static StateDefinition[] States() {return new[]{new StateDefinition {Name="Bell",Expression="|Phi+>"},new StateDefinition {Name="after CZ",Expression="CZ|Bell>"}};}
 static CalculationSession WithStates() {
  var session=Valid();session.Version=2;session.States=States();
  session.History[0].States=new[]{new StateDefinition {Name="état",Expression="[1;\r\n0]"}};
  return session;
 }
 static int Main() {
  string directory=Path.Combine(Path.GetTempPath(),"QuantumStudio-session-test-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
  try {
   string path=Path.Combine(directory,"roundtrip.qsession");var expected=Valid();SessionStore.Save(path,expected);
   var actual=SessionStore.Load(path);Require(actual.Expression==expected.Expression && actual.History[0].Result==expected.History[0].Result,"Unicode roundtrip failed");
   expected.Expression="replacement";SessionStore.Save(path,expected);Require(SessionStore.Load(path).Expression=="replacement","Atomic replacement failed");
   string before=File.ReadAllText(path);expected.Version=3;Reject(delegate {SessionStore.Save(path,expected);});Require(File.ReadAllText(path)==before,"Invalid save damaged destination");
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
   // Load old JSON without the new fields, rather than only serializing the current model.
   File.WriteAllText(path,"{\"Version\":1,\"Expression\":\"1\",\"Mode\":0,\"Evaluation\":0,\"History\":[{\"Expression\":\"2\",\"Result\":\"2\",\"Mode\":0,\"Evaluation\":0}]}");
   actual=SessionStore.Load(path);Require(SessionStore.CopyStates(actual.States).Length==0 && SessionStore.CopyStates(actual.History[0].States).Length==0,"Legacy definitions were not empty");
   expected=WithStates();SessionStore.Save(path,expected);actual=SessionStore.Load(path);
   Require(actual.Version==2 && actual.States.Length==2 && actual.States[1].Name=="after CZ" && actual.States[1].Expression=="CZ|Bell>","Current state definitions did not roundtrip");
   Require(actual.History[0].States.Length==1 && actual.History[0].States[0].Name=="état" && actual.History[0].States[0].Expression=="[1;\r\n0]","History lost its original state definitions");
   var snapshot=SessionStore.CopyStates(expected.States);expected.States[0].Expression="|0>";expected.States[1]=null;
   Require(snapshot[0].Expression=="|Phi+>" && snapshot[1].Name=="after CZ","State history copy shares mutable objects");
   before=File.ReadAllText(path);Reject(delegate {SessionStore.Save(path,expected);});Require(File.ReadAllText(path)==before,"Invalid definitions damaged saved session");
   foreach(var invalid in new StateDefinition[][] {
    null, new StateDefinition[33], new StateDefinition[]{null},
    new[]{new StateDefinition {Name="",Expression="|0>"}},
    new[]{new StateDefinition {Name=" Bell",Expression="|0>"}},
    new[]{new StateDefinition {Name="Bell\n",Expression="|0>"}},
    new[]{new StateDefinition {Name="bad\0name",Expression="|0>"}},
    new[]{new StateDefinition {Name=new string('界',43),Expression="|0>"}},
    new[]{new StateDefinition {Name="\uD800",Expression="|0>"}},
    new[]{new StateDefinition {Name="Bell",Expression=null}},
    new[]{new StateDefinition {Name="Bell",Expression=" "}},
    new[]{new StateDefinition {Name="Bell",Expression="|0>\0ignored"}},
    new[]{new StateDefinition {Name="Bell",Expression=new string('x',32769)}},
    new[]{new StateDefinition {Name="Bell",Expression="\uD800"}},
    new[]{new StateDefinition {Name="Bell",Expression="|0>"},new StateDefinition {Name="Bell",Expression="|1>"}}
   }) {
    expected=WithStates();expected.States=invalid;Reject(delegate {SessionStore.Validate(expected);});
    expected=WithStates();expected.History[0].States=invalid;Reject(delegate {SessionStore.Validate(expected);});
   }
   expected=Valid();expected.States=States();Reject(delegate {SessionStore.Validate(expected);});
   expected=Valid();expected.History[0].States=States();Reject(delegate {SessionStore.Validate(expected);});
   var maximum=new StateDefinition[32];for(int i=0;i<32;i++)maximum[i]=new StateDefinition {Name="state"+i,Expression="|0>"};
   SessionStore.ValidateStates(maximum);Require(SessionStore.CopyStates(maximum).Length==32,"32 states rejected");
   SessionStore.ValidateStates(new[]{new StateDefinition {Name=new string('a',128),Expression=new string('x',32768)}});checks++;
   Require(Encoding.UTF8.GetString(SessionStore.StateRequest(new[]{new StateDefinition {Name="état",Expression="[1;\r\n0]"}},"quantum:|état>"))=="QSTATES1\n1\n5\n7\nétat[1;\r\n0]quantum:|état>","Worker framing changed UTF-8 or newline byte lengths");
   Reject(delegate {SessionStore.StateRequest(States(),"1\0ignored");});
   Reject(delegate {SessionStore.StateRequest(States(),new string('x',32769));});
   Require(Directory.GetFiles(directory,"*.tmp").Length==0,"State save left temporary files behind");
   Console.WriteLine("PASS: "+checks+" session storage checks");return 0;
  }catch(Exception e){Console.Error.WriteLine(e);return 1;}
  finally {foreach(string file in Directory.GetFiles(directory))File.Delete(file);Directory.Delete(directory);}
 }
}

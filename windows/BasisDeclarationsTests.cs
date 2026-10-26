// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
class BasisDeclarationsTests {
 static int checks;
 static void Check(bool value) {if(!value)throw new Exception("Basis declaration check failed");checks++;}
 static void Reject(Action action) {try {action();}catch(InvalidDataException){checks++;return;}throw new Exception("Invalid basis declaration accepted");}
 static BasisDeclaration[] Bases() {return new[]{new BasisDeclaration {Name="Colors",Kind="Named labels",Labels="red, blue"},new BasisDeclaration {Name="B",Kind="Indexed family",Family="b",Dimension="n"}};}
 static int Main() {
  string path=Path.Combine(Path.GetTempPath(),"QuantumStudio-bases-"+Guid.NewGuid().ToString("N")+".qsession");
  try {
   var bases=Bases();BasisDeclarations.Validate(bases);var copy=BasisDeclarations.Copy(bases);copy[0].Labels="one";Check(bases[0].Labels=="red, blue");
   string expression=BasisDeclarations.Apply("<red|blue>+<b(j)|b(k)>",bases);Check(expression.Contains("orthobasis") && expression.Contains("orthofamily") && expression.Contains("[|red>,|blue>]") && expression.Contains("(n)"));
   var session=new CalculationSession {Version=5,Expression="<b(j)|b(k)>",Mode=0,Evaluation=0,States=new StateDefinition[0],Matrices=new MatrixDeclaration[0],Bases=bases,History=new[]{new SessionEntry {Expression="<red|blue>",Result="0",States=new StateDefinition[0],Matrices=new MatrixDeclaration[0],Bases=BasisDeclarations.Copy(bases)}}};
   SessionStore.Save(path,session);session.Bases[1].Dimension="3";var loaded=SessionStore.Load(path);Check(loaded.Bases[1].Dimension=="n" && loaded.History[0].Bases[1].Dimension=="n");loaded.Bases[0].Labels="green";Check(loaded.History[0].Bases[0].Labels=="red, blue");
   for(int version=1;version<=4;version++) {session.Version=version;Reject(delegate {SessionStore.Validate(session);});}
   session.Version=5;session.History[0].Bases=null;Reject(delegate {SessionStore.Validate(session);});
   foreach(string dimension in new[]{"0","-1","1.5","n),evil(","n\n"}) {var invalid=Bases();invalid[1].Dimension=dimension;Reject(delegate {BasisDeclarations.Validate(invalid);});}
   foreach(string labels in new[]{"red,red","red,","b_j,blue","red\",evil"}) {var invalid=Bases();invalid[0].Labels=labels;Reject(delegate {BasisDeclarations.Validate(invalid);});}
   var duplicate=Bases();duplicate[1].Name=duplicate[0].Name;Reject(delegate {BasisDeclarations.Validate(duplicate);});
   var mixed=Bases();mixed[0].Dimension="2";Reject(delegate {BasisDeclarations.Validate(mixed);});
   mixed=Bases();mixed[1].Labels="red";Reject(delegate {BasisDeclarations.Validate(mixed);});
   File.WriteAllText(path,"{\"Version\":1,\"Expression\":\"1\",\"History\":[]}");Check(BasisDeclarations.Copy(SessionStore.Load(path).Bases).Length==0);
   Console.WriteLine("PASS: "+checks+" basis declaration and session checks");return 0;
  } finally {if(File.Exists(path))File.Delete(path);}
 }
}

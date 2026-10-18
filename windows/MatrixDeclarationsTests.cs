// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
class MatrixDeclarationsTests {
 static int checks;
 static void Require(bool value,string why) {if(!value)throw new Exception(why);checks++;}
 static void Reject(Action action) {try {action();}catch(InvalidDataException){checks++;return;}catch(ArgumentException){checks++;return;}throw new Exception("Invalid declaration accepted");}
 static MatrixDeclaration M(string name,string rows,string columns) {return new MatrixDeclaration {Name=name,Rows=rows,Columns=columns};}
 static CalculationSession Session() {return new CalculationSession {Version=3,Expression="Tr(A)",States=new StateDefinition[0],Matrices=new[]{M("A","n","n")},History=new[]{new SessionEntry {Expression="Tr(A)",Result="Tr(A)",States=new StateDefinition[0],Matrices=new[]{M("A","2","2")}}}};}
 static int Main() {
  string directory=Path.Combine(Path.GetTempPath(),"QuantumStudio-matrices-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
  try {
   var declarations=new[]{M("A","n","n"),M("B","max(2,n)","2^k")};
   var copy=MatrixDeclarations.Copy(declarations);declarations[0].Rows="3";declarations[1]=null;
   Require(copy[0].Rows=="n" && copy[1].Name=="B","History shares mutable declarations");
   Require(MatrixDeclarations.Copy(null).Length==0,"Legacy declarations not empty");
   Require(MatrixDeclarations.Apply("Tr(A)",new[]{M("A","n","n")})=="matrixassume((Tr(A)),\"A\",(n),(n))","Unexpected request framing");
   Require(MatrixDeclarations.Apply("1",new MatrixDeclaration[0])=="1","Empty declarations change expression");
   MatrixDeclarations.Validate(new[]{M("Ω","max(2,n)","2^k")});checks++;
   foreach(var invalid in new MatrixDeclaration[][] {
    null,new MatrixDeclaration[33],new MatrixDeclaration[]{null},new[]{M("","2","2")},
    new[]{M("A\n","2","2")},new[]{M("A\"","2","2")},new[]{M("1A","2","2")},
    new[]{M("\uD800","2","2")},new[]{M(new string('界',43),"2","2")},
    new[]{M("A","2","2"),M("A","3","3")},new[]{M("A","A","2")},
    new[]{M("A","B","2"),M("B","2","2")},new[]{M("A",null,"2")},
    new[]{M("A"," ","2")},new[]{M("A","\uD800","2")},new[]{M("A","2\0","2")},
    new[]{M("A","2,3","2")},new[]{M("A","(2","2")},new[]{M("A","2)","2")},
    new[]{M("A","2);1(","2")},new[]{M("A","\"n\"","2")},new[]{M("A",new string('n',257),"2")},
    new[]{M("A",new string('(',33)+"2"+new string(')',33),"2")}
   }) Reject(delegate {MatrixDeclarations.Validate(invalid);});
   // Positive integer and symbolic dimension semantics belong to the native evaluator.
   MatrixDeclarations.Validate(new[]{M("A","0","n+1")});checks++;
   Reject(delegate {MatrixDeclarations.Apply("\uD800",copy);});
   Reject(delegate {MatrixDeclarations.Apply("1\0ignored",copy);});
   Reject(delegate {MatrixDeclarations.Apply(" ",copy);});
   Reject(delegate {MatrixDeclarations.Apply(new string('x',32000),copy);});
   Require(MatrixDeclarations.Apply(new string('x',32000),new MatrixDeclaration[0]).Length==32000,"Exact request limit rejected");
   var maximum=new MatrixDeclaration[32];for(int i=0;i<maximum.Length;i++)maximum[i]=M("A"+i,"2","2");
   MatrixDeclarations.Validate(maximum);checks++;
   string path=Path.Combine(directory,"session.qsession");var original=Session();SessionStore.Save(path,original);
   var loaded=SessionStore.Load(path);
   Require(loaded.Version==3 && loaded.Matrices[0].Rows=="n" && loaded.History[0].Matrices[0].Rows=="2","Session lost distinct history dimensions");
   string before=File.ReadAllText(path);original.Matrices[0].Name="bad\"";
   Reject(delegate {SessionStore.Save(path,original);});Require(File.ReadAllText(path)==before,"Invalid save damaged existing session");
   foreach(int version in new[]{1,2}) {
    var old=Session();old.Version=version;old.States=new StateDefinition[0];old.History[0].States=new StateDefinition[0];
    Reject(delegate {SessionStore.Validate(old);});old.Matrices=null;
    Reject(delegate {SessionStore.Validate(old);});old.History[0].Matrices=null;
    SessionStore.Save(path,old);Require(SessionStore.Load(path).Version==version,"Legacy session rejected");
   }
   var missing=Session();missing.Matrices=null;Reject(delegate {SessionStore.Validate(missing);});
   missing=Session();missing.History[0].Matrices=null;Reject(delegate {SessionStore.Validate(missing);});
   Require(Directory.GetFiles(directory,"*.tmp").Length==0,"Temporary save files remain");
   Console.WriteLine("PASS: "+checks+" matrix declaration checks");return 0;
  } catch(Exception ex) {Console.Error.WriteLine(ex);return 1;}
  finally {Directory.Delete(directory,true);}
 }
}

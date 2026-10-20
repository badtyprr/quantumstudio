// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
static class ComposerSourceTests {
 const string EmptyHash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
 static int checks;
 static JavaScriptSerializer Json() {return new JavaScriptSerializer {MaxJsonLength=16*SourceCircuitDocument.MaxDocumentBytes,RecursionLimit=128};}
 static Dictionary<string,object> Obj(object value) {return (Dictionary<string,object>)value;}
 static void Check(bool value) {if(!value)throw new Exception("Composer source check "+checks+" failed.");checks++;}
 static string Save(CircuitComposer composer,string path) {composer.SaveCircuit(path);return File.ReadAllText(path);}
 static void Reject(Action action) {try{action();}catch(InvalidDataException){checks++;return;}throw new Exception("Invalid source document accepted.");}
 static Dictionary<string,object> Envelope() {
  return Obj(Json().DeserializeObject("{\"Version\":1,\"Circuit\":{\"Version\":1,\"Qubits\":1,\"Steps\":[]},\"Source\":{\"Version\":1,\"Root\":\"C:/not-read\",\"Entry\":\"main.qasm\",\"ModuleHeaders\":false,\"Files\":[{\"Name\":\"main.qasm\",\"Text\":\"\",\"Bom\":false,\"Sha256\":\""+EmptyHash+"\"}],\"Bindings\":[{\"Path\":\"main.qasm\",\"Target\":\"main.qasm\"}]}}"));
 }
 public static int Run(CircuitComposer composer,string path) {
  var envelope=Envelope();composer.ImportSource(Json().Serialize(envelope),true);
  string original=Save(composer,path);var saved=Obj(Json().DeserializeObject(original));
  Check((string)saved["Format"]=="QuantumStudio.SourceCircuit" && !(bool)saved["Classical"] && (bool)saved["PublishedU"]);
  string source=Json().Serialize(saved["Source"]),hash=(string)saved["OriginalCircuitSha256"];
  Check(composer.AddGate("X","0",""));string edited=Save(composer,path);
  var changed=Obj(Json().DeserializeObject(edited));
  Check(Json().Serialize(changed["Source"])==source && (string)changed["OriginalCircuitSha256"]==hash);
  Check(composer.Undo() && Save(composer,path)==original);
  Reject(()=>composer.LoadCircuit(original.Replace("\"Classical\":false","\"Classical\":true")));
  Check(Save(composer,path)==original && composer.Redo() && Save(composer,path)==edited);
  Reject(()=>composer.ImportSource(Json().Serialize(envelope).Replace(EmptyHash,new string('0',64))));
  Check(Save(composer,path)==edited);
  composer.OpenCircuit(path);Check(Save(composer,path)==edited);
  Check(composer.OpenQasm().Contains("x q[0]") && !composer.OpenQasm().Contains("main.qasm"));
  composer.LoadCircuit("{\"Version\":1,\"Qubits\":2,\"Steps\":[]}");
  Check(!Obj(Json().DeserializeObject(Save(composer,path))).ContainsKey("Source"));
  Check(composer.Undo() && Save(composer,path)==edited);
  // A valid snapshot can sit just below the saved-document size limit.
  // A rejected edit must restore both controls and provenance without history loss.
  var boundary=Envelope();var metadata=Obj(boundary["Source"]);
  var files=new object[64];var bindings=new object[64];
  for(int i=0;i<64;i++) {
   string name=new string('<',3600)+i;
   if(i==0)metadata["Entry"]=name;
   files[i]=new Dictionary<string,object>{{"Name",name},{"Text",""},{"Bom",false},{"Sha256",EmptyHash}};
   bindings[i]=new Dictionary<string,object>{{"Path",name},{"Target",name}};
  }
  metadata["Files"]=files;metadata["Bindings"]=bindings;
  Func<string> compact=()=>Json().Serialize(boundary).Replace("\\u003c","<");
  composer.ImportSource(compact());
  string smaller=Save(composer,path);
  int gap=SourceCircuitDocument.MaxDocumentBytes-Encoding.UTF8.GetByteCount(smaller)-1;
  Check(gap>0 && gap<30000);
  metadata["Root"]=(string)metadata["Root"]+new string('r',gap);
  composer.ImportSource(compact());string full=Save(composer,path);
  Check(Encoding.UTF8.GetByteCount(full)==SourceCircuitDocument.MaxDocumentBytes-1);
  Check(!composer.AddGate("H","0","") && Save(composer,path)==full);
  Check(composer.Undo() && Save(composer,path)==smaller);
  Check(composer.Redo() && Save(composer,path)==full);
  composer.LoadCircuit("{\"Version\":1,\"Qubits\":1,\"Steps\":[]}");
  return checks;
 }
}

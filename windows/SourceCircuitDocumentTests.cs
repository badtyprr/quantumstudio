// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

class SourceCircuitDocumentTests {
 const string EmptyHash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
 static int checks,validations;static bool lastKind;
 static JavaScriptSerializer Json() {return new JavaScriptSerializer {MaxJsonLength=SourceCircuitDocument.MaxDocumentBytes,RecursionLimit=128};}
 static Dictionary<string,object> Object(object value) {return (Dictionary<string,object>)value;}
 static void Check(bool value) {if(!value)throw new Exception("Check "+checks+" failed.");++checks;}
 // A small stand-in proves validation is mandatory on every construction/edit.
 // The editors will supply their own full circuit validators.
 static string Validate(string text,bool classical) {
  ++validations;lastKind=classical;
  var circuit=Object(Json().DeserializeObject(text));
  if(!(circuit["Qubits"] is int) || (int)circuit["Qubits"]<1 || (int)circuit["Qubits"]>25)
   throw new InvalidDataException("Invalid circuit dimensions.");
  return text;
 }
 static Dictionary<string,object> Envelope() {
  return Object(Json().DeserializeObject(
   "{\"Version\":1,\"Circuit\":{\"Version\":1,\"Qubits\":1,\"Steps\":[]},"+
   "\"Source\":{\"Version\":1,\"Root\":\"C:/nonexistent/source\",\"Entry\":\"main.qasm\",\"ModuleHeaders\":false,"+
   "\"Files\":[{\"Name\":\"main.qasm\",\"Sha256\":\""+EmptyHash+"\",\"Text\":\"\",\"Bom\":false}],"+
   "\"Bindings\":[{\"Path\":\"main.qasm\",\"Target\":\"main.qasm\"}]}}"));
 }
 static Dictionary<string,object> Source(Dictionary<string,object> envelope) {return Object(envelope["Source"]);}
 static Dictionary<string,object> File(Dictionary<string,object> envelope) {return Object(((object[])Source(envelope)["Files"])[0]);}
 static Dictionary<string,object> Binding(Dictionary<string,object> envelope) {return Object(((object[])Source(envelope)["Bindings"])[0]);}
 static Dictionary<string,object> Captured(string name,string text,bool bom) {
  byte[] bytes=Encoding.UTF8.GetBytes((bom ? "\ufeff" : "")+text);
  string hash;using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
  return new Dictionary<string,object>{{"Name",name},{"Text",text},{"Bom",bom},{"Sha256",hash}};
 }
 static void Reject(Action action) {
  try {action();}catch(InvalidDataException){++checks;return;}
  throw new Exception("Accepted an invalid source circuit.");
 }
 static void RejectChange(Action<Dictionary<string,object>> change) {
  var envelope=Envelope();change(envelope);
  Reject(()=>SourceCircuitDocument.FromCompiler(Json().Serialize(envelope),false,false,Validate));
 }
 static void Main(string[] args) {
  var original=SourceCircuitDocument.FromCompiler(Json().Serialize(Envelope()),true,true,Validate);
  Check(validations==1 && lastKind && original.PublishedU && original.Classical && !original.CircuitEdited);
  string saved=original.Serialize(),source=original.SourceJson;
  var reopened=SourceCircuitDocument.Load(saved,Validate);
  Check(reopened.Serialize()==saved && !reopened.CircuitEdited && lastKind);
  var edited=original.WithCircuit("{\"Steps\":[],\"Qubits\":2,\"Version\":1}");
  Check(edited.CircuitEdited && edited.SourceJson==source && original.Serialize()==saved);
  Check(SourceCircuitDocument.Load(edited.Serialize(),Validate).CircuitEdited);
  var restored=edited.WithCircuit("{\"Steps\":[],\"Qubits\":1,\"Version\":1}");
  Check(!restored.CircuitEdited && restored.Serialize()==saved);
  Reject(()=>edited.WithCircuit("{\"Version\":1,\"Qubits\":0,\"Steps\":[]}"));
  Check(edited.CircuitEdited && original.Serialize()==saved);
  RejectChange(e=>e["Extra"]=true);
  RejectChange(e=>e["Version"]=2);
  RejectChange(e=>e.Remove("Source"));
  RejectChange(e=>Source(e)["ModuleHeaders"]="false");
  RejectChange(e=>Source(e)["Version"]=2);
  RejectChange(e=>Source(e)["Root"]="");
  RejectChange(e=>Source(e)["Entry"]="missing.qasm");
  RejectChange(e=>File(e)["Text"]="changed without updating its hash");
  RejectChange(e=>File(e)["Bom"]=true); // BOM participates in the hash.
  RejectChange(e=>File(e)["Sha256"]="not-a-hash");
  RejectChange(e=>File(e)["Text"]=new string('x',262145));
  RejectChange(e=>File(e)["Text"]="\ud800");
  RejectChange(e=>Source(e)["Files"]=new object[0]);
  RejectChange(e=>Source(e)["Bindings"]=new object[0]);
  RejectChange(e=>Source(e)["Files"]=new object[65]);
  RejectChange(e=>Source(e)["Bindings"]=new object[65]);
  RejectChange(e=>Source(e)["Files"]=new object[]{File(e),File(e)});
  RejectChange(e=>Source(e)["Bindings"]=new object[]{Binding(e),Binding(e)});
  RejectChange(e=>Binding(e)["Target"]="absent.qasm");
  foreach(string path in new[]{"../main.qasm","/main.qasm","C:main.qasm","a\\main.qasm","a/../../main.qasm","./main.qasm","a//main.qasm","a/.."})
   RejectChange(e=>Binding(e)["Path"]=path);
  RejectChange(e=>File(e)["Name"]="a/../main.qasm");
  var alias=Envelope();
  Source(alias)["Bindings"]=new object[]{Binding(alias),new Dictionary<string,object>{{"Path","nested/../main.qasm"},{"Target","main.qasm"}}};
  Check(SourceCircuitDocument.FromCompiler(Json().Serialize(alias),false,false,Validate).SourceJson.Contains("nested/../main.qasm"));
  var badSave=Object(Json().DeserializeObject(saved));badSave["OriginalCircuitSha256"]="bad";
  Reject(()=>SourceCircuitDocument.Load(Json().Serialize(badSave),Validate));
  badSave=Object(Json().DeserializeObject(saved));badSave["Format"]="Another.Format";
  Reject(()=>SourceCircuitDocument.Load(Json().Serialize(badSave),Validate));
  Reject(()=>SourceCircuitDocument.Load("{",Validate));
  Reject(()=>SourceCircuitDocument.Load(new string(' ',SourceCircuitDocument.MaxDocumentBytes+1),Validate));
  bool missing=false;
  try {SourceCircuitDocument.FromCompiler(Json().Serialize(Envelope()),false,false,null);}catch(ArgumentNullException){missing=true;}
  Check(missing);
  Reject(()=>SourceCircuitDocument.FromCompiler(Json().Serialize(Envelope()),false,false,(text,kind)=>"1"));
  Reject(()=>SourceCircuitDocument.FromCompiler(Json().Serialize(Envelope()),false,false,(text,kind)=>null));
  var excessive=Envelope();var manyFiles=new object[64];var manyBindings=new object[64];
  for(int i=0;i<64;i++) {
   string name=new string('<',4000)+i;
   if(i==0)Source(excessive)["Entry"]=name;
   manyFiles[i]=new Dictionary<string,object>{{"Name",name},{"Sha256",EmptyHash},{"Text",""},{"Bom",false}};
   manyBindings[i]=new Dictionary<string,object>{{"Path",name},{"Target",name}};
  }
  Source(excessive)["Files"]=manyFiles;Source(excessive)["Bindings"]=manyBindings;
  // The oversized escaped representation belongs only to the fixture builder.
  // Production receives the compact JSON, within its normal input limit.
  var fixtureJson=Json();fixtureJson.MaxJsonLength=8*SourceCircuitDocument.MaxDocumentBytes;
  string compact=fixtureJson.Serialize(excessive).Replace("\\u003c","<");
  Check(Encoding.UTF8.GetByteCount(compact)<SourceCircuitDocument.MaxDocumentBytes);
  Reject(()=>SourceCircuitDocument.FromCompiler(compact,false,false,Validate));
  var boundary=Envelope();
  Source(boundary)["Files"]=new object[]{Captured("main.qasm",new string('x',131072),false),Captured("other.qasm",new string('y',131069),true)};
  Source(boundary)["Bindings"]=new object[]{Binding(boundary),new Dictionary<string,object>{{"Path","other.qasm"},{"Target","other.qasm"}}};
  Check(!SourceCircuitDocument.FromCompiler(Json().Serialize(boundary),false,false,Validate).CircuitEdited);
  ((object[])Source(boundary)["Files"])[1]=Captured("other.qasm",new string('y',131070),true);
  Reject(()=>SourceCircuitDocument.FromCompiler(Json().Serialize(boundary),false,false,Validate));
  if(args.Length==1) {
   var actual=SourceCircuitDocument.FromCompiler(System.IO.File.ReadAllText(args[0],new UTF8Encoding(false,true)),false,false,Validate);
   Check(!actual.CircuitEdited && SourceCircuitDocument.Load(actual.Serialize(),Validate).Serialize()==actual.Serialize());
   Check(actual.SourceJson.Contains("\"Bom\":true") && actual.SourceJson.Contains("\"ModuleHeaders\":true"));
  }
  Console.WriteLine("PASS: "+checks+" source circuit provenance checks; no source files were read by the model.");
 }
}

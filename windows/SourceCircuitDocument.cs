// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

// Circuit validation stays with the existing circuit model. This immutable
// wrapper owns provenance and saved-document identity, and never reads files.
sealed class SourceCircuitDocument {
 public const int MaxDocumentBytes=4194304;
 const int MaxSourceBytes=262144, MaxCircuitBytes=262144;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 readonly Func<string,bool,string> validateCircuit;
 readonly string circuit,source,originalHash;
 public bool PublishedU {get;private set;}
 public bool Classical {get;private set;}
 public string CircuitJson {get{return circuit;}}
 public string SourceJson {get{return source;}}
 public bool CircuitEdited {get{return Hash(Utf8.GetBytes(circuit))!=originalHash;}}

 SourceCircuitDocument(string current,string snapshot,string initialHash,bool published,bool classical,Func<string,bool,string> validate) {
  circuit=current;source=snapshot;originalHash=initialHash;
  PublishedU=published;Classical=classical;validateCircuit=validate;
  // Reject an unsavable document during construction, before an editor can
  // replace its current state. JSON escaping can enlarge the captured text.
  Serialize();
 }
 static JavaScriptSerializer Serializer() {return new JavaScriptSerializer {MaxJsonLength=MaxDocumentBytes,RecursionLimit=128};}
 static InvalidDataException Invalid(string text) {return new InvalidDataException(text);}
 static void Size(string text,int maximum,string name) {
  if(text==null)throw Invalid("Missing "+name+".");
  try {if(Utf8.GetByteCount(text)>maximum)throw Invalid(name+" is too large.");}
  catch(EncoderFallbackException) {throw Invalid(name+" contains invalid Unicode.");}
 }
 static object Parse(string text) {
  Size(text,MaxDocumentBytes,"Source circuit document");
  try {return Serializer().DeserializeObject(text);}
  catch(ArgumentException error) {throw new InvalidDataException("Invalid source circuit JSON.",error);}
  catch(InvalidOperationException error) {throw new InvalidDataException("Invalid source circuit JSON.",error);}
 }
 static Dictionary<string,object> Fields(object value,string allowed) {
  var fields=value as Dictionary<string,object>;
  if(fields==null)throw Invalid("Expected a source circuit object.");
  var names=new HashSet<string>(allowed.Split(','),StringComparer.Ordinal);
  foreach(string key in fields.Keys)if(!names.Contains(key))throw Invalid("Unknown source circuit field: "+key);
  foreach(string key in names)if(!fields.ContainsKey(key) || fields[key]==null)throw Invalid("Missing source circuit field: "+key);
  return fields;
 }
 static string Text(object value,int maximum,string name,bool empty=false) {
  var text=value as string;
  Size(text,maximum,name);
  if(!empty && String.IsNullOrEmpty(text))throw Invalid("Missing "+name+".");
  return text;
 }
 static bool Boolean(object value) {
  if(!(value is bool))throw Invalid("Expected a Boolean source circuit field.");
  return (bool)value;
 }
 static void Version(object value) {if(!(value is int) || (int)value!=1)throw Invalid("Expected source circuit version 1.");}
 static object[] Array(object value) {
  var array=value as object[];
  if(array==null || array.Length==0 || array.Length>64)throw Invalid("Source snapshots require 1 to 64 files and dependency paths.");
  return array;
 }
 static string Relative(object value,bool canonical) {
  string path=Text(value,32768,"Relative source path");
  if(path[0]=='/' || path.IndexOfAny(new[]{'\\',':','\0'})>=0)throw Invalid("Source paths must be relative and use '/' separators.");
  int depth=0;
  foreach(string part in path.Split('/')) {
   if(part.Length==0 || part==".")throw Invalid("Empty or dot source path components are not supported.");
   if(part=="..") {if(canonical || --depth<0)throw Invalid("Source path escapes its root.");}
   else ++depth;
  }
  if(depth==0)throw Invalid("A source path must identify a file.");
  return path;
 }
 static string HexHash(object value) {
  string hash=Text(value,64,"Source hash").ToLowerInvariant();
  if(hash.Length!=64)throw Invalid("Expected a SHA-256 source hash.");
  foreach(char c in hash)if(!(c>='0' && c<='9') && !(c>='a' && c<='f'))throw Invalid("Expected a SHA-256 source hash.");
  return hash;
 }
 static string Hash(byte[] bytes) {
  using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
 }
 // Sorting object keys makes fingerprints independent of JSON property order.
 static string Canonical(object value,int depth=0) {
  if(depth>128)throw Invalid("Source circuit JSON is too deeply nested.");
  var fields=value as Dictionary<string,object>;
  if(fields!=null) {
   var keys=new List<string>(fields.Keys);keys.Sort(StringComparer.Ordinal);
   var entries=new List<string>();
   foreach(string key in keys)entries.Add(Serializer().Serialize(key)+":"+Canonical(fields[key],depth+1));
   return "{"+String.Join(",",entries.ToArray())+"}";
  }
  var array=value as object[];
  if(array!=null) {
   var entries=new List<string>();
   foreach(object item in array)entries.Add(Canonical(item,depth+1));
   return "["+String.Join(",",entries.ToArray())+"]";
  }
  return Serializer().Serialize(value);
 }
 static string ValidateSource(object value) {
  var root=Fields(value,"Version,Root,Entry,ModuleHeaders,Files,Bindings");Version(root["Version"]);
  string location=Text(root["Root"],32768,"Source root");
  if(location.IndexOf('\0')>=0)throw Invalid("Source root contains NUL.");
  string entry=Relative(root["Entry"],true);Boolean(root["ModuleHeaders"]);
  var files=new HashSet<string>(StringComparer.Ordinal);long total=0;
  foreach(object item in Array(root["Files"])) {
   var file=Fields(item,"Name,Sha256,Text,Bom");
   string name=Relative(file["Name"],true);
   if(!files.Add(name))throw Invalid("Duplicate source file: "+name);
   string text=Text(file["Text"],MaxSourceBytes,"Source text",true);
   bool bom=Boolean(file["Bom"]);byte[] content=Utf8.GetBytes(text);
   total+=content.Length+(bom ? 3 : 0);
   if(total>MaxSourceBytes)throw Invalid("Source snapshot exceeds 262144 bytes.");
   if(bom) {var bytes=new byte[content.Length+3];bytes[0]=239;bytes[1]=187;bytes[2]=191;Buffer.BlockCopy(content,0,bytes,3,content.Length);content=bytes;}
   if(Hash(content)!=HexHash(file["Sha256"]))throw Invalid("Source hash mismatch: "+name);
  }
  var paths=new HashSet<string>(StringComparer.Ordinal);var referenced=new HashSet<string>(StringComparer.Ordinal);
  foreach(object item in Array(root["Bindings"])) {
   var binding=Fields(item,"Path,Target");
   string path=Relative(binding["Path"],false),target=Relative(binding["Target"],true);
   if(!paths.Add(path) || !files.Contains(target))throw Invalid("Duplicate or unresolved source dependency binding.");
   referenced.Add(target);
  }
  if(!paths.Contains(entry) || !referenced.SetEquals(files))throw Invalid("Source entry or dependency identity is missing.");
  return Canonical(root);
 }
 static string ValidateCircuit(object value,bool classical,Func<string,bool,string> validate) {
  if(validate==null)throw new ArgumentNullException("validate");
  if(!(value is Dictionary<string,object>))throw Invalid("Expected a circuit object.");
  string input=Canonical(value);Size(input,MaxCircuitBytes,"Circuit");
  string normalized=validate(input,classical);
  Size(normalized,MaxCircuitBytes,"Validated circuit");
  object parsed=Parse(normalized);
  if(!(parsed is Dictionary<string,object>))throw Invalid("Circuit validator must return an object.");
  string result=Canonical(parsed);Size(result,MaxCircuitBytes,"Validated circuit");return result;
 }
 public static SourceCircuitDocument FromCompiler(string text,bool publishedU,bool classical,Func<string,bool,string> validate) {
  var root=Fields(Parse(text),"Version,Circuit,Source");Version(root["Version"]);
  string snapshot=ValidateSource(root["Source"]),current=ValidateCircuit(root["Circuit"],classical,validate);
  return new SourceCircuitDocument(current,snapshot,Hash(Utf8.GetBytes(current)),publishedU,classical,validate);
 }
 public static SourceCircuitDocument Load(string text,Func<string,bool,string> validate) {
  var root=Fields(Parse(text),"Format,Version,Circuit,Source,PublishedU,Classical,OriginalCircuitSha256");
  if(Text(root["Format"],64,"Document format")!="QuantumStudio.SourceCircuit")throw Invalid("Unknown source circuit document format.");
  Version(root["Version"]);bool classical=Boolean(root["Classical"]),published=Boolean(root["PublishedU"]);
  string snapshot=ValidateSource(root["Source"]),current=ValidateCircuit(root["Circuit"],classical,validate);
  return new SourceCircuitDocument(current,snapshot,HexHash(root["OriginalCircuitSha256"]),published,classical,validate);
 }
 public SourceCircuitDocument WithCircuit(string text) {
  string current=ValidateCircuit(Parse(text),Classical,validateCircuit);
  return new SourceCircuitDocument(current,source,originalHash,PublishedU,Classical,validateCircuit);
 }
 public string Serialize() {
  var root=new Dictionary<string,object> {
   {"Format","QuantumStudio.SourceCircuit"},{"Version",1},{"Circuit",Parse(circuit)},{"Source",Parse(source)},
   {"PublishedU",PublishedU},{"Classical",Classical},{"OriginalCircuitSha256",originalHash}
  };
  string result=Canonical(root);Size(result,MaxDocumentBytes,"Source circuit document");return result;
 }
}

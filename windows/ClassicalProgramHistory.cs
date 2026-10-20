// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;

// All mutations are validated on a private draft before history changes.
sealed class ClassicalProgramHistory {
 const int Limit=64;
 sealed class Entry {
  public readonly ClassicalCircuit Circuit;
  public readonly SourceCircuitDocument Source;
  public Entry(ClassicalCircuit circuit,SourceCircuitDocument source) {Circuit=circuit;Source=source;}
  public string Serialize() {return Source==null ? Circuit.Serialize() : Source.Serialize();}
 }
 readonly List<Entry> past=new List<Entry>(),future=new List<Entry>();
 Entry current;
 public ClassicalCircuit Current {get{return current.Circuit;}}
 public SourceCircuitDocument Source {get{return current.Source;}}
 public bool CanUndo {get{return past.Count!=0;}}
 public bool CanRedo {get{return future.Count!=0;}}
 public ClassicalProgramHistory(ClassicalCircuit circuit) {if(circuit==null)throw new ArgumentNullException("circuit");current=new Entry(circuit,null);}
 public string Serialize() {return current.Serialize();}
 static string ValidateSourceCircuit(string text,bool classical) {
  if(!classical)throw new InvalidDataException("This editor requires a classical circuit document.");
  return ClassicalCircuit.Load(text).Serialize();
 }
 // Compile and validate before replacing history; failed imports leave redo intact.
 public void ImportSource(string envelope,bool publishedU) {
  var source=SourceCircuitDocument.FromCompiler(envelope,publishedU,true,ValidateSourceCircuit);
  Replace(new Entry(ClassicalCircuit.Load(source.CircuitJson),source));
 }
 void Replace(Entry next) {
  if(next.Serialize()==current.Serialize())return;
  past.Add(current);if(past.Count>Limit)past.RemoveAt(0);
  current=next;future.Clear();
 }
 public void Edit(Action<ClassicalCircuit.Document> change) {
  if(change==null)throw new ArgumentNullException("change");
  var draft=Current.Snapshot();change(draft);var next=ClassicalCircuit.From(draft);
  var source=Source==null ? null : Source.WithCircuit(next.Serialize());
  Replace(new Entry(next,source));
 }
 public void Open(string json) {
  // Only saved-document dispatch happens here; each model validates its own schema.
  if(json==null || json.Length>SourceCircuitDocument.MaxDocumentBytes)throw new InvalidDataException("Circuit document is missing or too large.");
  Dictionary<string,object> fields;
  try {fields=new JavaScriptSerializer {MaxJsonLength=SourceCircuitDocument.MaxDocumentBytes,RecursionLimit=128}.DeserializeObject(json) as Dictionary<string,object>;}
  catch(ArgumentException error) {throw new InvalidDataException("Invalid circuit JSON.",error);}
  catch(InvalidOperationException error) {throw new InvalidDataException("Invalid circuit JSON.",error);}
  Entry next;
  if(fields!=null && fields.ContainsKey("Format")) {
   var source=SourceCircuitDocument.Load(json,ValidateSourceCircuit);
   next=new Entry(ClassicalCircuit.Load(source.CircuitJson),source);
  } else next=new Entry(ClassicalCircuit.Load(json),null);
  current=next;past.Clear();future.Clear();
 }
 public void Undo() {if(!CanUndo)return;future.Add(current);current=past[past.Count-1];past.RemoveAt(past.Count-1);}
 public void Redo() {if(!CanRedo)return;past.Add(current);current=future[future.Count-1];future.RemoveAt(future.Count-1);}
}

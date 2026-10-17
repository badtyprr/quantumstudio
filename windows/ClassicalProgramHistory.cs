// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;

// All mutations are validated on a private draft before history changes.
sealed class ClassicalProgramHistory {
 const int Limit=64;
 readonly List<ClassicalCircuit> past=new List<ClassicalCircuit>(),future=new List<ClassicalCircuit>();
 public ClassicalCircuit Current {get;private set;}
 public bool CanUndo {get{return past.Count!=0;}}
 public bool CanRedo {get{return future.Count!=0;}}
 public ClassicalProgramHistory(ClassicalCircuit circuit) {if(circuit==null)throw new ArgumentNullException("circuit");Current=circuit;}
 public void Edit(Action<ClassicalCircuit.Document> change) {
  if(change==null)throw new ArgumentNullException("change");
  var draft=Current.Snapshot();change(draft);var next=ClassicalCircuit.From(draft);
  if(next.Serialize()==Current.Serialize())return;
  past.Add(Current);if(past.Count>Limit)past.RemoveAt(0);
  Current=next;future.Clear();
 }
 public void Open(string json) {
  var next=ClassicalCircuit.Load(json);
  Current=next;past.Clear();future.Clear();
 }
 public void Undo() {if(!CanUndo)return;future.Add(Current);Current=past[past.Count-1];past.RemoveAt(past.Count-1);}
 public void Redo() {if(!CanRedo)return;past.Add(Current);Current=future[future.Count-1];future.RemoveAt(future.Count-1);}
}

// GPL-2.0-or-later; see COPYING.
using System;
class ClassicalProgramHistoryTests {
 static int checks;
 static void Check(bool ok) {checks++;if(!ok)throw new Exception("History check "+checks+" failed.");}
 static void Main() {
  var initial=ClassicalCircuit.From(new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new ClassicalCircuit.Register[0],OutputBits=new int[0],Steps=new ClassicalCircuit.Step[0]});
  var history=new ClassicalProgramHistory(initial);
  history.Edit(d=>d.Qubits=2);Check(history.Current.Qubits==2 && history.CanUndo && !history.CanRedo);
  history.Undo();Check(history.Current.Qubits==1 && history.CanRedo);
  try {history.Edit(d=>d.Qubits=26);throw new Exception("Invalid edit accepted");}catch(ArgumentException) {}
  Check(history.Current.Qubits==1 && history.CanRedo && !history.CanUndo);
  history.Edit(d=>{});Check(history.CanRedo && !history.CanUndo);
  history.Redo();Check(history.Current.Qubits==2 && history.CanUndo && !history.CanRedo);
  history.Undo();history.Edit(d=>d.Qubits=3);Check(!history.CanRedo);
  string saved=history.Current.Serialize();
  try {history.Open("{}");throw new Exception("Invalid document accepted");}catch(System.IO.InvalidDataException) {}
  Check(history.Current.Serialize()==saved && history.CanUndo);
  ClassicalCircuit.Document retained=null;history.Edit(d=>{retained=d;d.Qubits=4;});retained.Qubits=20;
  Check(history.Current.Qubits==4);
  history.Open(initial.Serialize());Check(!history.CanRedo && !history.CanUndo && history.Current.Qubits==1);
  for(int i=0;i<70;i++)history.Edit(d=>d.Qubits=d.Qubits==1 ? 2 : 1);
  int count=0;while(history.CanUndo) {history.Undo();count++;}Check(count==64);
  while(history.CanRedo)history.Redo();Check(history.Current.Qubits==1);
  Console.WriteLine("PASS: "+checks+" atomic classical edit and history checks.");
 }
}

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
  history.Edit(d=>{d.Version=3;d.Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}};d.OutputBits=new[]{0};d.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="1"}}};});
  string expressions=history.Current.Serialize();history.Edit(d=>d.Steps[0].ClassicalValue.Value="0");
  history.Undo();Check(history.Current.Serialize()==expressions && history.CanRedo);
  try {history.Edit(d=>d.Steps[0].ClassicalValue.Value="2");throw new Exception("Invalid expression edit accepted");}catch(ArgumentException) {}
  Check(history.Current.Serialize()==expressions && history.CanRedo);
  history.Redo();Check(history.Current.Snapshot().Steps[0].ClassicalValue.Value=="0");
  history.Open(expressions);Check(history.Current.Serialize()==expressions && !history.CanUndo && !history.CanRedo);
  history.Edit(d=>{d.Version=4;d.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerCompare",Operator="Equal",Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="1"},Right=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=64,Value="1"}};});
  string typed=history.Current.Serialize();history.Edit(d=>d.Steps[0].ClassicalValue.Left.Signedness="Unsigned");
  history.Undo();Check(history.Current.Serialize()==typed && history.Current.Snapshot().Version==4);
  try{history.Edit(d=>d.Version=3);throw new Exception("Typed circuit downgrade accepted");}catch(System.IO.InvalidDataException){}
  Check(history.Current.Serialize()==typed && history.CanRedo);
  history.Redo();Check(history.Current.Snapshot().Steps[0].ClassicalValue.Left.Signedness=="Unsigned");
  history.Open(typed);Check(history.Current.Serialize()==typed && !history.CanUndo);
  Console.WriteLine("PASS: "+checks+" atomic classical edit and history checks.");
 }
}

// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

sealed class ClassicalProgramWindow : Window {
 sealed class OperationChoice {public string Key {get;set;} public string Label {get;set;} public override string ToString() {return Label;}}
 sealed class Selection {public int[] Route;public int Index;}
 readonly ClassicalProgramHistory history;
 readonly TreeView tree=new TreeView();
 readonly TextBox qubits=new TextBox {Text="1"},registers=new TextBox {Text="c:1"},outputs=new TextBox {Text="0"};
 readonly TextBox variables=new TextBox(),variableTarget=new TextBox {Text="counter"};
 readonly ComboBox kind=new ComboBox();
 readonly TextBox expression=new TextBox {Text="H"},wires=new TextBox {Text="0"},destination=new TextBox {Text="0"},mask=new TextBox {Text="1"},value=new TextBox {Text="1"};
 readonly TextBlock status=new TextBlock {TextWrapping=TextWrapping.Wrap};
 readonly Button undo=new Button {Content="Undo"},redo=new Button {Content="Redo"};
 string saved;
 bool verifying;
 public ClassicalProgramWindow(Window owner) {
  Owner=owner;Resources=owner.Resources;Title="Classical circuit editor";Width=980;Height=850;MinWidth=720;MinHeight=550;
  Background=WorkspaceTheme.Background;Foreground=WorkspaceTheme.Text;FontFamily=new FontFamily("Segoe UI");WindowStartupLocation=WindowStartupLocation.CenterOwner;
  history=new ClassicalProgramHistory(ClassicalCircuit.From(new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}));
  saved=history.Current.Serialize();Closing+=delegate(object sender,System.ComponentModel.CancelEventArgs e) {if(!Discard())e.Cancel=true;};
  var root=new DockPanel {Margin=new Thickness(20)};Content=new ScrollViewer {Content=root,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  tree.Height=140;SizeChanged+=delegate {tree.Height=Math.Max(140,ActualHeight-760);};
  var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);root.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Quantum circuit · classical control",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text="Measurements save into registers. Variables hold typed values; branches choose a body once.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,6,0,12)});
  var commands=new WrapPanel();top.Children.Add(commands);
  Button(commands,"Open…",Open);Button(commands,"Save…",Save);Button(commands,"Sample…",()=>new SamplingWindow(this,history.Current).Show());
  Button(commands,"Exact probabilities…",()=>new ExactCircuitWindow(this,history.Current).Show());
  var convention=new ComboBox {Width=180,VerticalAlignment=VerticalAlignment.Center};convention.Items.Add("IBM / Qiskit U");convention.Items.Add("Published OpenQASM 3 U");convention.SelectedIndex=0;commands.Children.Add(convention);System.Windows.Automation.AutomationProperties.SetName(convention,"Imported U gate convention");
  Button(commands,"Import OpenQASM…",()=>{var picker=new Microsoft.Win32.OpenFileDialog {Filter="OpenQASM (*.qasm)|*.qasm|All files (*.*)|*.*"};if(picker.ShowDialog(this)==true)Import(picker.FileName,convention.SelectedIndex==1);});
  commands.Children.Add(undo);commands.Children.Add(redo);undo.Click+=delegate {history.Undo();Refresh();};redo.Click+=delegate {history.Redo();Refresh();};
  var settings=new WrapPanel();top.Children.Add(settings);Field(settings,"Qubits",qubits,65);Field(settings,"Registers · name:size, …",registers,260);Field(settings,"Output bit indices · left to right",outputs,200);
  Button(settings,"Apply registers",()=>history.Edit(d=>{d.Qubits=Int(qubits.Text);d.Registers=ParseRegisters(registers.Text);d.OutputBits=Indices(outputs.Text);}));
  top.Children.Add(new TextBlock {Text="Registers occupy consecutive bits starting at 0. Output order is explicit; no final measurements are added. Changing register sizes changes bit allocation.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,4,0,10)});
  var declarations=new WrapPanel();top.Children.Add(declarations);
  Field(declarations,"Integer variables · name:type",variables,440);Button(declarations,"Apply variables",ApplyVariables);
  top.Children.Add(new TextBlock {Text="Example: counter:int[8], attempts:uint[16]. Assign a value before using it. Keep existing variables in order.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted});
  var bottom=new StackPanel();DockPanel.SetDock(bottom,Dock.Bottom);root.Children.Add(bottom);
  bottom.Children.Add(status);
  var editor=new WrapPanel();bottom.Children.Add(editor);
  kind.DisplayMemberPath="Label";kind.SelectedValuePath="Key";
  string[] keys={"Gate","Measure","Reset","Conditional","Channel","Readout","Branch","Assign","ExpressionBranch","StoreInteger","ClearInteger"};
  string[] labels={"Gate","Measure","Reset","Conditional gate","Noise channel","Readout error","If mask","Assign bits","If expression","Assign variable","Clear variable"};
  for(int i=0;i<keys.Length;i++)kind.Items.Add(new OperationChoice {Key=keys[i],Label=labels[i]});kind.SelectedValue="Gate";
  Field(editor,"Operation",kind,150);Field(editor,"Expression / matrix / channel",expression,240);Field(editor,"Target wires / bits",wires,120);Field(editor,"Save to classical bit",destination,120);
  Field(editor,"Variable name",variableTarget,170);
  Field(editor,"Condition mask · decimal",mask,170);Field(editor,"Condition value · decimal",value,170);
  kind.SelectionChanged+=delegate {SetFields();};SetFields();
  var edits=new WrapPanel();bottom.Children.Add(edits);Button(edits,"Add to selected body",()=>ChangeStep(false));Button(edits,"Replace selected",()=>ChangeStep(true));Button(edits,"Delete selected",Delete);
  bottom.Children.Add(new TextBlock {Text="Expressions: counter + 1, c[0] ^ c[1], popcount(c) == 1. Select Program, Then or Else to add an operation. Clear variable makes its value undefined. Exact preserves fractions and symbols; Sample estimates outcomes.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,8,0,0)});
  tree.Resources[SystemColors.HighlightBrushKey]=WorkspaceTheme.Selection;
  tree.Resources[SystemColors.HighlightTextBrushKey]=WorkspaceTheme.Text;
  tree.Resources[SystemColors.InactiveSelectionHighlightBrushKey]=WorkspaceTheme.Selection;
  tree.Resources[SystemColors.InactiveSelectionHighlightTextBrushKey]=WorkspaceTheme.Text;
  tree.Background=WorkspaceTheme.Surface;tree.Foreground=WorkspaceTheme.Text;tree.Margin=new Thickness(0,8,0,12);root.Children.Add(tree);
  tree.SelectedItemChanged+=delegate {var node=tree.SelectedItem as TreeViewItem;var selected=node==null ? null : node.Tag as Selection;if(selected==null || selected.Index<0)return;var doc=history.Current.Snapshot();var step=Body(doc,selected.Route)[selected.Index];kind.SelectedValue=step.Kind;expression.Text=step.IntegerValue!=null ? ClassicalExpressionText.Format(step.IntegerValue,doc) : step.ClassicalValue==null ? step.Expression ?? "" : ClassicalExpressionText.Format(step.ClassicalValue,doc);variableTarget.Text=step.VariableSlot.HasValue ? doc.Variables[step.VariableSlot.Value].Name : "";wires.Text=String.Join(",",step.Wires ?? new int[0]);destination.Text=step.ClassicalBit.HasValue ? step.ClassicalBit.Value.ToString(CultureInfo.InvariantCulture) : "";mask.Text=step.Mask ?? "1";value.Text=step.Value ?? "1";};
  Refresh();
 }
 static int Int(string text) {int result;if(!Int32.TryParse(text.Trim(),NumberStyles.None,CultureInfo.InvariantCulture,out result))throw new ArgumentException("Enter nonnegative integer indices and sizes.");return result;}
 static int[] Indices(string text) {return String.IsNullOrWhiteSpace(text) ? new int[0] : text.Split(',').Select(Int).ToArray();}
 static ClassicalCircuit.Register[] ParseRegisters(string text) {
  if(String.IsNullOrWhiteSpace(text))return new ClassicalCircuit.Register[0];
  return text.Split(',').Select(entry=>{string[] parts=entry.Split(':');if(parts.Length!=2)throw new ArgumentException("Write each register as name:size, such as c:2, flag:1.");return new ClassicalCircuit.Register {Name=parts[0].Trim(),Size=Int(parts[1])};}).ToArray();
 }
 void ApplyVariables() {
  var parsed=String.IsNullOrWhiteSpace(variables.Text) ? new ClassicalCircuit.Variable[0] : variables.Text.Split(',').Select(entry=>{
   var parts=entry.Split(':');if(parts.Length!=2)throw new ArgumentException("Write variables as counter:int[8], attempts:uint[16].");
   string type=parts[1].Trim();bool unsigned=type.StartsWith("uint",StringComparison.Ordinal);string prefix=unsigned ? "uint" : "int";
   if(!type.StartsWith(prefix,StringComparison.Ordinal))throw new ArgumentException("Use int, uint, int[width] or uint[width].");
   string suffix=type.Substring(prefix.Length);int width=0;
   if(suffix.Length!=0){if(!suffix.StartsWith("[") || !suffix.EndsWith("]"))throw new ArgumentException("Write a width in brackets.");width=Int(suffix.Substring(1,suffix.Length-2));if(width<1 || width>64)throw new ArgumentException("Integer widths must be 1-64.");}
   return new ClassicalCircuit.Variable{Name=parts[0].Trim(),Signedness=unsigned ? "Unsigned" : "Signed",Width=width};
  }).ToArray();
  history.Edit(d=>{
   var previous=d.Variables ?? new ClassicalCircuit.Variable[0];
   for(int k=0;k<parsed.Length;k++){int old=Array.FindIndex(previous,v=>v.Name==parsed[k].Name);if(old>=0 && old!=k)throw new ArgumentException("Keep existing variables in their original order.");}
   d.Version=Math.Max(5,d.Version);d.Variables=parsed;
  });
 }
 static bool IsBranch(string op) {return op=="Branch" || op=="ExpressionBranch";}
 void SetFields() {string op=kind.SelectedItem==null ? null : ((OperationChoice)kind.SelectedItem).Key;bool branch=IsBranch(op),condition=op=="Branch" || op=="Conditional";variableTarget.IsEnabled=op=="StoreInteger" || op=="ClearInteger";expression.IsEnabled=op=="StoreInteger" || op=="Assign" || op=="ExpressionBranch" || op=="Gate" || op=="Conditional" || op=="Channel" || op=="Readout";wires.IsEnabled=!branch && op!="StoreInteger" && op!="ClearInteger";destination.IsEnabled=op=="Measure";mask.IsEnabled=value.IsEnabled=condition;}
 static void Field(Panel panel,string label,Control control,int width) {var group=new StackPanel {Margin=new Thickness(0,6,12,6)};group.Children.Add(new TextBlock {Text=label});control.Width=width;group.Children.Add(control);panel.Children.Add(group);System.Windows.Automation.AutomationProperties.SetName(control,label);}
 void Button(Panel panel,string title,Action action) {var button=new Button {Content=title,VerticalAlignment=VerticalAlignment.Bottom};panel.Children.Add(button);button.Click+=delegate {try {action();Refresh();status.Text="Ready · Changes are captured for undo.";}catch(Exception error) {status.Text=error.Message;}};}
 static ClassicalCircuit.Step[] Body(ClassicalCircuit.Document doc,int[] route) {var body=doc.Steps;for(int i=0;i<route.Length;i+=2)body=route[i+1]==0 ? body[route[i]].WhenTrue : body[route[i]].WhenFalse;return body;}
 static void ReplaceBody(ClassicalCircuit.Document doc,int[] route,ClassicalCircuit.Step[] body) {if(route.Length==0){doc.Steps=body;return;}var parent=Body(doc,route.Take(route.Length-2).ToArray())[route[route.Length-2]];if(route[route.Length-1]==0)parent.WhenTrue=body;else parent.WhenFalse=body;}
 Selection Selected() {var node=tree.SelectedItem as TreeViewItem;return node==null ? new Selection {Route=new int[0],Index=-1} : (Selection)node.Tag;}
 void ChangeStep(bool replace) {
  var selected=Selected();if(replace && selected.Index<0)throw new ArgumentException("Select an operation to replace.");
  string op=(string)kind.SelectedValue;bool branch=IsBranch(op),condition=op=="Branch" || op=="Conditional",integer=op=="StoreInteger" || op=="ClearInteger";
  var step=new ClassicalCircuit.Step {Kind=op,Expression=op=="Gate" || op=="Conditional" || op=="Channel" || op=="Readout" ? expression.Text.Trim() : null,Wires=branch || integer ? null : Indices(wires.Text),ClassicalBit=op=="Measure" ? (int?)Int(destination.Text) : null,Mask=condition ? mask.Text.Trim() : null,Value=condition ? value.Text.Trim() : null,WhenTrue=branch ? new ClassicalCircuit.Step[0] : null,WhenFalse=branch ? new ClassicalCircuit.Step[0] : null};
  if(integer) {
   var doc=history.Current.Snapshot();int slot=Array.FindIndex(doc.Variables ?? new ClassicalCircuit.Variable[0],v=>v.Name==variableTarget.Text.Trim());
   if(slot<0)throw new ArgumentException("Declare the target variable first.");step.VariableSlot=slot;
   if(op=="StoreInteger")step.IntegerValue=ClassicalExpressionText.ParseInteger(expression.Text,doc);
  }
  bool classical=op=="Assign" || op=="ExpressionBranch";
  if(classical)step.ClassicalValue=ClassicalExpressionText.Parse(expression.Text,history.Current.Snapshot(),op=="Assign" ? step.Wires.Length : 1);
  history.Edit(d=>{if(classical || step.IntegerValue!=null)d.Version=Math.Max(ClassicalExpressionText.RequiredVersion(step.IntegerValue ?? step.ClassicalValue),d.Version);if(d.Version>=5 && d.Variables==null)d.Variables=new ClassicalCircuit.Variable[0];var list=Body(d,selected.Route).ToList();if(replace) {var old=list[selected.Index];if(IsBranch(old.Kind)) {if(!branch && (old.WhenTrue.Length!=0 || old.WhenFalse.Length!=0))throw new ArgumentException("Delete the branch's children before changing it to another operation.");if(branch){step.WhenTrue=old.WhenTrue;step.WhenFalse=old.WhenFalse;}}list[selected.Index]=step;}else list.Add(step);ReplaceBody(d,selected.Route,list.ToArray());});
 }
 void Delete() {var selected=Selected();if(selected.Index<0)throw new ArgumentException("Select an operation to delete.");history.Edit(d=>{var list=Body(d,selected.Route).ToList();list.RemoveAt(selected.Index);ReplaceBody(d,selected.Route,list.ToArray());});}
 void Refresh() {
  var doc=history.Current.Snapshot();qubits.Text=doc.Qubits.ToString(CultureInfo.InvariantCulture);registers.Text=String.Join(", ",doc.Registers.Select(r=>r.Name+":"+r.Size.ToString(CultureInfo.InvariantCulture)));outputs.Text=String.Join(",",doc.OutputBits);
  variables.Text=String.Join(", ",(doc.Variables ?? new ClassicalCircuit.Variable[0]).Select(v=>v.Name+":"+(v.Signedness=="Unsigned" ? "uint" : "int")+(v.Width==0 ? "" : "["+v.Width.ToString(CultureInfo.InvariantCulture)+"]")));
  tree.Items.Clear();tree.Items.Add(BodyNode("Program",doc.Steps,new int[0],doc));undo.IsEnabled=history.CanUndo;redo.IsEnabled=history.CanRedo;
 }
 static TreeViewItem BodyNode(string title,ClassicalCircuit.Step[] body,int[] route,ClassicalCircuit.Document context) {
  var node=new TreeViewItem {Header=title,IsExpanded=true,Tag=new Selection {Route=route,Index=-1}};
  for(int i=0;i<body.Length;i++) {var step=body[i];string description=step.Kind=="StoreInteger" ? context.Variables[step.VariableSlot.Value].Name+" = "+ClassicalExpressionText.Format(step.IntegerValue,context) : step.Kind=="ClearInteger" ? "Clear "+context.Variables[step.VariableSlot.Value].Name : step.Kind=="Assign" ? "Assign ["+String.Join(",",step.Wires)+"] ← "+ClassicalExpressionText.Format(step.ClassicalValue,context) : step.Kind=="ExpressionBranch" ? "If "+ClassicalExpressionText.Format(step.ClassicalValue,context) : step.Kind=="Branch" ? "If (record & "+step.Mask+") = "+step.Value : step.Kind+" "+(step.Expression ?? "")+" ["+String.Join(",",step.Wires ?? new int[0])+"]"+(step.ClassicalBit.HasValue ? " → bit "+step.ClassicalBit : "")+(step.Kind=="Conditional" ? " if (record & "+step.Mask+") = "+step.Value : "");
   var child=new TreeViewItem {Header=new TextBlock {Text=description,TextWrapping=TextWrapping.Wrap,FontFamily=new FontFamily("Consolas")},IsExpanded=true,Tag=new Selection {Route=route,Index=i}};node.Items.Add(child);
   if(IsBranch(step.Kind)) {child.Items.Add(BodyNode("Then",step.WhenTrue,route.Concat(new[]{i,0}).ToArray(),context));child.Items.Add(BodyNode("Else",step.WhenFalse,route.Concat(new[]{i,1}).ToArray(),context));}
  }return node;
 }
 bool Discard() {return verifying || history.Current.Serialize()==saved || MessageBox.Show(this,"Discard unsaved circuit changes?","Classical circuit",MessageBoxButton.YesNo,MessageBoxImage.Question)==MessageBoxResult.Yes;}
 void Import(string path,bool published) {var next=ClassicalCircuit.Load(QasmImport.Compile(path,published,true)).Snapshot();history.Edit(d=>{d.Version=next.Version;d.Qubits=next.Qubits;d.Registers=next.Registers;d.Variables=next.Variables;d.OutputBits=next.OutputBits;d.Steps=next.Steps;});}
 public void VerifyImport(string path,string report) {
  verifying=true;string before=history.Current.Serialize();Import(path,false);string imported=history.Current.Serialize();
  history.Undo();if(history.Current.Serialize()!=before)throw new Exception("Import undo lost the previous circuit.");history.Redo();if(history.Current.Serialize()!=imported)throw new Exception("Import redo lost classical circuit data.");
  File.WriteAllText(report+".qcircuit",imported);Refresh();status.Text="Imported · Classical registers, saved measurements and branches preserved.";Capture(report+".png");
 }
 void Open() {var picker=new Microsoft.Win32.OpenFileDialog {Filter="Classical circuits (*.qcircuit)|*.qcircuit|JSON (*.json)|*.json"};if(picker.ShowDialog(this)!=true)return;string text=new UTF8Encoding(false,true).GetString(BoundedUtf8File.Read(picker.FileName,262144,"Classical circuit"));var next=ClassicalCircuit.Load(text);if(!Discard())return;history.Open(next.Serialize());saved=history.Current.Serialize();}
 void Save() {var picker=new Microsoft.Win32.SaveFileDialog {Filter="Classical circuit (*.qcircuit)|*.qcircuit",DefaultExt=".qcircuit",AddExtension=true,OverwritePrompt=true};if(picker.ShowDialog(this)!=true)return;string temp=picker.FileName+"."+Guid.NewGuid().ToString("N")+".tmp";try {File.WriteAllText(temp,history.Current.Serialize(),new UTF8Encoding(false));if(File.Exists(picker.FileName))File.Replace(temp,picker.FileName,null);else File.Move(temp,picker.FileName);saved=history.Current.Serialize();}finally {if(File.Exists(temp))File.Delete(temp);}}
 public void VerifyEditing(string screenshot) {
  verifying=true;
  history.Edit(d=>{d.Qubits=2;d.Registers=ParseRegisters("c:2");d.OutputBits=new[]{1,0};});Refresh();
  kind.SelectedValue="Gate";expression.Text="H";wires.Text="0";ChangeStep(false);Refresh();
  kind.SelectedValue="Measure";destination.Text="1";ChangeStep(false);Refresh();
  kind.SelectedValue="Branch";mask.Text="2";value.Text="2";ChangeStep(false);Refresh();
  var branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];((TreeViewItem)branch.Items[0]).IsSelected=true;
  kind.SelectedValue="Gate";expression.Text="X";wires.Text="1";ChangeStep(false);Refresh();
  string valid=history.Current.Serialize();
  kind.SelectedValue="Measure";wires.Text="9";destination.Text="0";
  try {ChangeStep(false);throw new Exception("Invalid wire accepted.");}catch(ArgumentException) {}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid edit changed the program.");
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  kind.SelectedValue="Gate";wires.Text="0";expression.Text="H";
  try {ChangeStep(true);throw new Exception("Branch children were discarded.");}catch(ArgumentException) {}
  if(history.Current.Serialize()!=valid)throw new Exception("Rejected replacement changed the program.");
  history.Undo();history.Redo();if(history.Current.Serialize()!=valid)throw new Exception("Undo/redo lost a nested operation.");
  history.Open(valid);Refresh();if(history.Current.Serialize()!=valid || history.CanUndo)throw new Exception("Reload did not preserve the program.");
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  kind.SelectedValue="ExpressionBranch";expression.Text="popcount(c) == 1";ChangeStep(true);Refresh();
  var converted=history.Current.Snapshot();
  if(converted.Version!=3 || converted.Steps[2].Kind!="ExpressionBranch" || converted.Steps[2].WhenTrue.Length!=1)throw new Exception("Expression replacement lost branch children.");
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];
  if(branch.Items.Count!=2)throw new Exception("Expression branch bodies are hidden.");
  ((TreeViewItem)branch.Items[1]).IsSelected=true;kind.SelectedValue="Assign";wires.Text="1,0";expression.Text="rotl(~c, -1)";ChangeStep(false);Refresh();
  var expressionProgram=history.Current.Snapshot();
  if(expressionProgram.Steps[2].ClassicalValue.Left.Kind!="PopulationCount" || expressionProgram.Steps[2].WhenFalse[0].ClassicalValue.Kind!="Rotate" || expressionProgram.Steps[2].WhenFalse[0].ClassicalValue.DistanceInterpretation!="Signed")throw new Exception("Bit-function editing lost its operation or signed distance.");
  valid=history.Current.Serialize();
  var assignment=(TreeViewItem)((TreeViewItem)((TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2]).Items[1]).Items[0];assignment.IsSelected=true;
  if((string)kind.SelectedValue!="Assign" || expression.Text!=ClassicalExpressionText.Format(history.Current.Snapshot().Steps[2].WhenFalse[0].ClassicalValue))throw new Exception("Assignment selection lost its expression.");
  expression.Text="c[99]";try {ChangeStep(true);throw new Exception("Invalid expression accepted.");}catch(ArgumentException) {}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid expression changed history.");
  history.Undo();history.Redo();if(history.Current.Serialize()!=valid)throw new Exception("Expression undo/redo lost data.");
  history.Open(valid);Refresh();if(history.Current.Serialize()!=valid)throw new Exception("Expression reload lost data.");
  assignment=(TreeViewItem)((TreeViewItem)((TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2]).Items[1]).Items[0];assignment.IsSelected=true;
  if(kind.SelectedItem.ToString()!="Assign bits" || !expression.IsEnabled || !wires.IsEnabled || destination.IsEnabled || mask.IsEnabled || value.IsEnabled)throw new Exception("Assignment controls have stale labels or enabled states.");
  history.Edit(d=>d.Version=4);
  kind.SelectedValue="Assign";wires.Text="1,0";expression.Text="c";ChangeStep(true);
  if(history.Current.Snapshot().Version!=4)throw new Exception("Editing downgraded a version-4 circuit.");
  history.Edit(d=>d.Steps[2].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerCompare",Operator="Less",Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerRead",Signedness="Signed",Width=2,Bits=new[]{0,1}},Right=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"}});
  string typed=history.Current.Serialize();history.Open(typed);Refresh();
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  File.WriteAllText(screenshot+".typed-before.json",typed);File.WriteAllText(screenshot+".typed-after.json",history.Current.Serialize());
  if(!expression.Text.Contains("int[2](read(0,1))") || history.Current.Serialize()!=typed)throw new Exception("Typed circuit reload lost its display or data: "+expression.Text+"; unchanged="+(history.Current.Serialize()==typed));
  history.Open(valid);Refresh();
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  kind.SelectedValue="ExpressionBranch";expression.Text="int[2](c) < 0";ChangeStep(true);Refresh();
  if(history.Current.Snapshot().Version!=4 || history.Current.Snapshot().Steps[2].ClassicalValue.Kind!="IntegerCompare")throw new Exception("Typed text did not upgrade and preserve the circuit.");
  typed=history.Current.Serialize();branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  ChangeStep(true);if(history.Current.Serialize()!=typed)throw new Exception("Formatted typed text changed the stored expression.");
  expression.Text="int[3](c) < 0";try{ChangeStep(true);throw new Exception("Mismatched integer cast accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=typed)throw new Exception("Invalid typed edit changed the circuit.");
  history.Open(valid);Refresh();
  saved=valid;
  File.WriteAllText(screenshot+".qcircuit",valid);
  status.Text="Verified · Bit assignments, expression branches, preserved children, invalid edits and undo/redo.";
  Capture(screenshot);
  Width=MinWidth;Height=MinHeight;UpdateLayout();var scroll=(ScrollViewer)Content;
  if(scroll.ScrollableHeight<=0)throw new Exception("Short editor did not make all controls scrollable.");
  scroll.ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
  VerifyVariables(screenshot+".variables");
  VerifyComputedCasts(screenshot+".computed-casts");
 }
 void VerifyVariables(string screenshot) {
  Width=980;Height=850;
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize());Refresh();
  variables.Text="counter:int[8], attempts:uint[16]";ApplyVariables();Refresh();
  kind.SelectedValue="StoreInteger";variableTarget.Text="counter";expression.Text="3";ChangeStep(false);Refresh();
  kind.SelectedValue="StoreInteger";variableTarget.Text="counter";expression.Text="counter ** 2 - 1";ChangeStep(false);Refresh();
  kind.SelectedValue="Assign";wires.Text="0";expression.Text="counter == 8";ChangeStep(false);Refresh();
  string before=history.Current.Serialize();
  var selected=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];selected.IsSelected=true;
  if((string)kind.SelectedValue!="StoreInteger" || variableTarget.Text!="counter" || !expression.Text.Contains("counter"))throw new Exception("Variable selection lost its name or expression.");
  ChangeStep(true);if(history.Current.Serialize()!=before)throw new Exception("Variable text replacement changed its expression.");
  variables.Text="attempts:uint[16], counter:int[8]";try{ApplyVariables();throw new Exception("Variable reorder accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=before)throw new Exception("Variable reorder changed stored slots.");
  variables.Text="";try{ApplyVariables();throw new Exception("Referenced variable removal accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=before)throw new Exception("Invalid declaration edit changed circuit.");
  Refresh();kind.SelectedValue="ClearInteger";variableTarget.Text="counter";ChangeStep(false);Refresh();
  if(history.Current.Snapshot().Steps[3].Kind!="ClearInteger")throw new Exception("Clear variable did not append.");
  history.Undo();if(history.Current.Serialize()!=before)throw new Exception("Variable undo lost the program.");history.Redo();
  string cleared=history.Current.Serialize();history.Open(cleared);Refresh();if(history.Current.Serialize()!=cleared)throw new Exception("Variable save/reopen changed the program.");
  File.WriteAllText(screenshot+".qcircuit",cleared);status.Text="Verified · Typed variables, expressions, safe declaration edits and undo/redo.";saved=cleared;
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();var scroll=(ScrollViewer)Content;
  if(scroll.ScrollableHeight<=0)throw new Exception("Variable controls do not scroll at minimum size.");scroll.ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void VerifyComputedCasts(string screenshot) {
  Width=980;Height=850;
  var initial=ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize();
  history.Open(initial);Refresh();kind.SelectedValue="Assign";wires.Text="0";expression.Text="uint[1](c == 0) == 1";ChangeStep(false);Refresh();
  if(history.Current.Snapshot().Version!=6 || history.Current.Snapshot().Variables.Length!=0)throw new Exception("Computed cast did not upgrade a variable-free circuit.");
  string assigned=history.Current.Serialize();history.Undo();if(history.Current.Serialize()!=initial)throw new Exception("Computed cast undo changed the original document.");history.Redo();if(history.Current.Serialize()!=assigned)throw new Exception("Computed cast redo lost version 6.");
  variables.Text="counter:uint[1]";ApplyVariables();Refresh();if(history.Current.Snapshot().Version!=6)throw new Exception("Variable edits downgraded computed casts.");
  history.Open(initial);Refresh();variables.Text="counter:uint[1]";ApplyVariables();Refresh();
  kind.SelectedValue="StoreInteger";variableTarget.Text="counter";expression.Text="uint[1](c == 0)";ChangeStep(false);Refresh();
  if(history.Current.Snapshot().Version!=6)throw new Exception("Computed variable store did not upgrade the document.");
  kind.SelectedValue="Assign";wires.Text="0";expression.Text="counter == 1";ChangeStep(false);Refresh();
  string valid=history.Current.Serialize();var selected=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[0];selected.IsSelected=true;
  ChangeStep(true);if(history.Current.Serialize()!=valid)throw new Exception("Computed cast formatting changed a selected store.");
  expression.Text="uint[2](c == 0)";try{ChangeStep(true);throw new Exception("Mismatched computed cast accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid computed cast changed the document.");
  history.Open(valid);Refresh();if(history.Current.Serialize()!=valid)throw new Exception("Computed cast save/reopen changed the document.");
  File.WriteAllText(screenshot+".qcircuit",valid);saved=valid;status.Text="Verified · Computed bit casts, declaration edits, selection, save/reopen and undo/redo.";
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void Capture(string path) {UpdateLayout();var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(this);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);}
}

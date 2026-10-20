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
 readonly TextBox loopLimit=new TextBox {Text="1000000"};
 readonly ComboBox kind=new ComboBox();
 readonly WrapPanel rangeFields=new WrapPanel();
 readonly WrapPanel rotationFields=new WrapPanel();
 readonly ComboBox rotationAxis=new ComboBox();
 readonly TextBox rotationAngle=new TextBox {Text="pi/2"};
 readonly TextBox rangeStart=new TextBox {Text="0"},rangeStop=new TextBox {Text="3"},rangeStep=new TextBox {Text="1"};
 readonly TextBox expression=new TextBox {Text="H"},wires=new TextBox {Text="0"},destination=new TextBox {Text="0"},mask=new TextBox {Text="1"},value=new TextBox {Text="1"};
 readonly TextBlock status=new TextBlock {TextWrapping=TextWrapping.Wrap};
 readonly TextBlock sourceStatus=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,4,0,4)};
 readonly Button undo=new Button {Content="Undo"},redo=new Button {Content="Redo"};
 readonly Button export=new Button {Content="Export OpenQASM…"};
 string saved;
 bool verifying;
 public ClassicalProgramWindow(Window owner) {
  Owner=owner;Resources=owner.Resources;Title="Classical circuit editor";Width=980;Height=920;MinWidth=720;MinHeight=550;
  Background=WorkspaceTheme.Background;Foreground=WorkspaceTheme.Text;FontFamily=new FontFamily("Segoe UI");WindowStartupLocation=WindowStartupLocation.CenterOwner;
  history=new ClassicalProgramHistory(ClassicalCircuit.From(new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}));
  saved=history.Serialize();Closing+=delegate(object sender,System.ComponentModel.CancelEventArgs e) {if(!Discard())e.Cancel=true;};
  var root=new DockPanel {Margin=new Thickness(20)};Content=new ScrollViewer {Content=root,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  tree.Height=140;SizeChanged+=delegate {tree.Height=Math.Max(140,ActualHeight-760);};
  var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);root.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Quantum circuit · classical control",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text="Measurements save into registers. Variables hold typed values; if chooses once, while repeats while its condition is true; for visits an inclusive integer range.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,6,0,12)});
  var commands=new WrapPanel();top.Children.Add(commands);
  Button(commands,"Open…",Open);Button(commands,"Save…",Save);
  commands.Children.Add(export);export.Click+=async delegate {await Export();};
  Button(commands,"Sample…",()=>new SamplingWindow(this,history.Current).Show());
  Button(commands,"Exact probabilities…",()=>new ExactCircuitWindow(this,history.Current).Show());
  var convention=new ComboBox {Width=180,VerticalAlignment=VerticalAlignment.Center};convention.Items.Add("IBM / Qiskit U");convention.Items.Add("Published OpenQASM 3 U");convention.SelectedIndex=0;commands.Children.Add(convention);System.Windows.Automation.AutomationProperties.SetName(convention,"Imported U gate convention");
  var moduleHeaders=new CheckBox {Content="Generated module headers",VerticalAlignment=VerticalAlignment.Center,ToolTip="Allow matching version headers and repeated standard-library includes in generated modules."};commands.Children.Add(moduleHeaders);
  Button(commands,"Import OpenQASM…",()=>{var picker=new Microsoft.Win32.OpenFileDialog {Filter="OpenQASM (*.qasm)|*.qasm|All files (*.*)|*.*"};if(picker.ShowDialog(this)==true)Import(picker.FileName,convention.SelectedIndex==1,moduleHeaders.IsChecked==true);});
  top.Children.Add(sourceStatus);
  Button(commands,"Source files…",()=>new SourceFilesWindow(this,history.Source,envelope=>history.ImportSource(envelope,history.Source.PublishedU)).ShowDialog());
  commands.Children.Add(undo);commands.Children.Add(redo);undo.Click+=delegate {history.Undo();Refresh();};redo.Click+=delegate {history.Redo();Refresh();};
  var settings=new WrapPanel();top.Children.Add(settings);Field(settings,"Qubits",qubits,65);Field(settings,"Registers · name:size, …",registers,260);Field(settings,"Output bit indices · left to right",outputs,200);
  Button(settings,"Apply registers",()=>history.Edit(d=>{d.Qubits=Int(qubits.Text);d.Registers=ParseRegisters(registers.Text);d.OutputBits=Indices(outputs.Text);}));
  top.Children.Add(new TextBlock {Text="Registers occupy consecutive bits starting at 0. Output order is explicit; no final measurements are added. Changing register sizes changes bit allocation.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,4,0,10)});
  var declarations=new WrapPanel();top.Children.Add(declarations);
  Field(declarations,"Integer variables · name:type",variables,440);Button(declarations,"Apply variables",ApplyVariables);
  top.Children.Add(new TextBlock {Text="Example: counter:int[8], attempts:uint[16]. Assign a value before using it. Keep existing variables in order.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted});
  var loops=new WrapPanel();top.Children.Add(loops);
  Field(loops,"Loop condition limit",loopLimit,170);Button(loops,"Apply loop limit",ApplyLoopLimit);
  top.Children.Add(new TextBlock {Text="Limit 0–1,000,000 checks: per shot for Sample, across all histories for Exact. Exceeding it reports an error, not partial results.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted});
  var bottom=new StackPanel();DockPanel.SetDock(bottom,Dock.Bottom);root.Children.Add(bottom);
  bottom.Children.Add(status);
  var editor=new WrapPanel();bottom.Children.Add(editor);
  kind.DisplayMemberPath="Label";kind.SelectedValuePath="Key";
  string[] keys={"Gate","Measure","Reset","Conditional","Channel","Readout","Branch","Assign","ExpressionBranch","StoreInteger","ClearInteger","While","Break","Continue","End","ForRange","Rotation"};
  string[] labels={"Gate","Measure","Reset","Conditional gate","Noise channel","Readout error","If mask","Assign bits","If expression","Assign variable","Clear variable","While expression","Break loop","Continue loop","End program","For integer range","Runtime rotation"};
  for(int i=0;i<keys.Length;i++)kind.Items.Add(new OperationChoice {Key=keys[i],Label=labels[i]});kind.SelectedValue="Gate";
  Field(editor,"Operation",kind,150);Field(editor,"Expression / matrix / channel",expression,240);Field(editor,"Target wires / bits",wires,120);Field(editor,"Save to classical bit",destination,120);
  Field(editor,"Variable name",variableTarget,170);
  Field(editor,"Condition mask · decimal",mask,170);Field(editor,"Condition value · decimal",value,170);
  bottom.Children.Add(rangeFields);Field(rangeFields,"Start · inclusive",rangeStart,170);Field(rangeFields,"Stop · inclusive",rangeStop,170);Field(rangeFields,"Step · nonzero",rangeStep,170);
  bottom.Children.Add(rotationFields);
  foreach(string axis in new[]{"X","Y","Z"})rotationAxis.Items.Add(axis);rotationAxis.SelectedIndex=1;
  Field(rotationFields,"Rotation axis",rotationAxis,110);Field(rotationFields,"Angle · radians",rotationAngle,350);
  rotationAngle.ToolTip="Real arithmetic: pi*n/2. Use float(n/2) to evaluate integer division first. Cast measured bits with uint[width](...).";
  kind.SelectionChanged+=delegate {SetFields();};SetFields();
  var edits=new WrapPanel();bottom.Children.Add(edits);Button(edits,"Add to selected body",()=>ChangeStep(false));Button(edits,"Replace selected",()=>ChangeStep(true));Button(edits,"Delete selected",Delete);
  bottom.Children.Add(new TextBlock {Text="Expressions: counter + 1, c[0] ^ c[1], popcount(c) == 1. Select Program, Then, Else or Loop body to add an operation. Break exits the nearest loop; Continue advances to the next iteration. Range bounds are captured at entry; the binding is cleared on exit. End stops the whole program and keeps saved results. Clear variable makes its value undefined. Exact preserves fractions and symbols; Sample estimates outcomes.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,8,0,0)});
  tree.Resources[SystemColors.HighlightBrushKey]=WorkspaceTheme.Selection;
  tree.Resources[SystemColors.HighlightTextBrushKey]=WorkspaceTheme.Text;
  tree.Resources[SystemColors.InactiveSelectionHighlightBrushKey]=WorkspaceTheme.Selection;
  tree.Resources[SystemColors.InactiveSelectionHighlightTextBrushKey]=WorkspaceTheme.Text;
  tree.Background=WorkspaceTheme.Surface;tree.Foreground=WorkspaceTheme.Text;tree.Margin=new Thickness(0,8,0,12);root.Children.Add(tree);
  tree.SelectedItemChanged+=delegate {var node=tree.SelectedItem as TreeViewItem;var selected=node==null ? null : node.Tag as Selection;if(selected==null || selected.Index<0)return;var doc=history.Current.Snapshot();var step=Body(doc,selected.Route)[selected.Index];kind.SelectedValue=step.Kind;rotationAxis.SelectedItem=step.Axis ?? "Y";rotationAngle.Text=step.Angle==null ? "pi/2" : ClassicalRealExpressionText.Format(step.Angle,doc);rangeStart.Text=step.Range==null ? "0" : RangeText(step.Range.Start,doc);rangeStop.Text=step.Range==null ? "3" : RangeText(step.Range.Stop,doc);rangeStep.Text=step.Range==null ? "1" : RangeText(step.Range.Step,doc);expression.Text=step.IntegerValue!=null ? ClassicalExpressionText.Format(step.IntegerValue,doc) : step.ClassicalValue==null ? step.Expression ?? "" : ClassicalExpressionText.Format(step.ClassicalValue,doc);variableTarget.Text=step.VariableSlot.HasValue ? doc.Variables[step.VariableSlot.Value].Name : "";wires.Text=String.Join(",",step.Wires ?? new int[0]);destination.Text=step.ClassicalBit.HasValue ? step.ClassicalBit.Value.ToString(CultureInfo.InvariantCulture) : "";mask.Text=step.Mask ?? "1";value.Text=step.Value ?? "1";};
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
 void ApplyLoopLimit() {
  int limit=Int(loopLimit.Text);
  history.Edit(d=>{d.Version=Math.Max(7,d.Version);d.LoopConditionBudget=limit;if(d.Variables==null)d.Variables=new ClassicalCircuit.Variable[0];});
 }
 static bool IsTransfer(string op) {return op=="Break" || op=="Continue";}
 static bool IsLoop(string op) {return op=="While" || op=="ForRange";}
 static string RangeText(ClassicalCircuit.ExpressionNode node,ClassicalCircuit.Document context) {
  string text=ClassicalExpressionText.Format(node,context);
  // Plain signed machine literals round-trip without a cast. Keep explicit
  // widths and unsigned casts where dropping the type could change meaning.
  return node.Kind=="IntegerConstant" && node.Signedness=="Signed" && node.Width==0 ? text.Substring(4,text.Length-5) : text;
 }
 static bool IsBranch(string op) {return op=="Branch" || op=="ExpressionBranch" || IsLoop(op);}
 void SetFields() {string op=kind.SelectedItem==null ? null : ((OperationChoice)kind.SelectedItem).Key;bool branch=IsBranch(op),condition=op=="Branch" || op=="Conditional";rotationFields.Visibility=op=="Rotation" ? Visibility.Visible : Visibility.Collapsed;rangeFields.Visibility=op=="ForRange" ? Visibility.Visible : Visibility.Collapsed;foreach(Control unused in new Control[]{expression,wires,destination,mask,value})((FrameworkElement)unused.Parent).Visibility=op=="ForRange" ? Visibility.Collapsed : Visibility.Visible;variableTarget.IsEnabled=op=="StoreInteger" || op=="ClearInteger" || op=="ForRange";expression.IsEnabled=op=="StoreInteger" || op=="Assign" || op=="ExpressionBranch" || op=="While" || op=="Gate" || op=="Conditional" || op=="Channel" || op=="Readout";wires.IsEnabled=!branch && op!="End" && !IsTransfer(op) && op!="StoreInteger" && op!="ClearInteger";destination.IsEnabled=op=="Measure";mask.IsEnabled=value.IsEnabled=condition;((FrameworkElement)variableTarget.Parent).Visibility=op=="Rotation" ? Visibility.Collapsed : Visibility.Visible;if(op=="Rotation")foreach(Control unused in new Control[]{expression,destination,mask,value})((FrameworkElement)unused.Parent).Visibility=Visibility.Collapsed;}
 static void Field(Panel panel,string label,Control control,int width) {var group=new StackPanel {Margin=new Thickness(0,6,12,6)};group.Children.Add(new TextBlock {Text=label});control.Width=width;group.Children.Add(control);panel.Children.Add(group);System.Windows.Automation.AutomationProperties.SetName(control,label);}
 void Button(Panel panel,string title,Action action) {var button=new Button {Content=title,VerticalAlignment=VerticalAlignment.Bottom};panel.Children.Add(button);button.Click+=delegate {try {action();Refresh();status.Text="Ready · Changes are captured for undo.";}catch(Exception error) {status.Text=error.Message;}};}
 static ClassicalCircuit.Step[] Body(ClassicalCircuit.Document doc,int[] route) {var body=doc.Steps;for(int i=0;i<route.Length;i+=2)body=route[i+1]==0 ? body[route[i]].WhenTrue : body[route[i]].WhenFalse;return body;}
 static void ReplaceBody(ClassicalCircuit.Document doc,int[] route,ClassicalCircuit.Step[] body) {if(route.Length==0){doc.Steps=body;return;}var parent=Body(doc,route.Take(route.Length-2).ToArray())[route[route.Length-2]];if(route[route.Length-1]==0)parent.WhenTrue=body;else parent.WhenFalse=body;}
 Selection Selected() {var node=tree.SelectedItem as TreeViewItem;return node==null ? new Selection {Route=new int[0],Index=-1} : (Selection)node.Tag;}
 void ChangeStep(bool replace) {
  var selected=Selected();if(replace && selected.Index<0)throw new ArgumentException("Select an operation to replace.");
  string op=(string)kind.SelectedValue;bool branch=IsBranch(op),condition=op=="Branch" || op=="Conditional",integer=op=="StoreInteger" || op=="ClearInteger",range=op=="ForRange";
  if(IsTransfer(op)) {
   var body=history.Current.Snapshot().Steps;bool insideLoop=false;
   for(int i=0;i<selected.Route.Length;i+=2) {var parent=body[selected.Route[i]];insideLoop|=IsLoop(parent.Kind);body=selected.Route[i+1]==0 ? parent.WhenTrue : parent.WhenFalse;}
   if(!insideLoop)throw new ArgumentException("Select a body inside a loop before adding Break or Continue.");
  }
  var step=new ClassicalCircuit.Step {Kind=op,Expression=op=="Gate" || op=="Conditional" || op=="Channel" || op=="Readout" ? expression.Text.Trim() : null,Wires=branch || integer || IsTransfer(op) || op=="End" ? null : Indices(wires.Text),ClassicalBit=op=="Measure" ? (int?)Int(destination.Text) : null,Mask=condition ? mask.Text.Trim() : null,Value=condition ? value.Text.Trim() : null,WhenTrue=branch ? new ClassicalCircuit.Step[0] : null,WhenFalse=branch && !IsLoop(op) ? new ClassicalCircuit.Step[0] : null};
  if(integer || range) {
   var doc=history.Current.Snapshot();int slot=Array.FindIndex(doc.Variables ?? new ClassicalCircuit.Variable[0],v=>v.Name==variableTarget.Text.Trim());
   if(slot<0)throw new ArgumentException("Declare the target variable first.");step.VariableSlot=slot;
   if(op=="StoreInteger")step.IntegerValue=ClassicalExpressionText.ParseInteger(expression.Text,doc);
   if(range)step.Range=new ClassicalCircuit.RangeNode{Start=ClassicalExpressionText.ParseInteger(rangeStart.Text,doc),Stop=ClassicalExpressionText.ParseInteger(rangeStop.Text,doc),Step=ClassicalExpressionText.ParseInteger(rangeStep.Text,doc)};
  }
  if(op=="Rotation") {step.Axis=rotationAxis.SelectedItem as string;step.Angle=ClassicalRealExpressionText.Parse(rotationAngle.Text,history.Current.Snapshot());}
  bool classical=op=="Assign" || op=="ExpressionBranch" || op=="While";
  if(classical)step.ClassicalValue=ClassicalExpressionText.Parse(expression.Text,history.Current.Snapshot(),op=="Assign" ? step.Wires.Length : 1);
  history.Edit(d=>{if(op=="Rotation"){d.Version=Math.Max(11,d.Version);if(!d.LoopConditionBudget.HasValue)d.LoopConditionBudget=1000000;}if(range){d.Version=Math.Max(10,d.Version);if(!d.LoopConditionBudget.HasValue)d.LoopConditionBudget=1000000;}if(op=="End"){d.Version=Math.Max(9,d.Version);if(!d.LoopConditionBudget.HasValue)d.LoopConditionBudget=1000000;}if(IsTransfer(op))d.Version=Math.Max(8,d.Version);if(op=="While"){d.Version=Math.Max(7,d.Version);if(!d.LoopConditionBudget.HasValue)d.LoopConditionBudget=1000000;}if(classical || step.IntegerValue!=null)d.Version=Math.Max(ClassicalExpressionText.RequiredVersion(step.IntegerValue ?? step.ClassicalValue),d.Version);if(d.Version>=5 && d.Variables==null)d.Variables=new ClassicalCircuit.Variable[0];var list=Body(d,selected.Route).ToList();if(replace) {var old=list[selected.Index];if(IsBranch(old.Kind)) {
    var otherwise=old.WhenFalse ?? new ClassicalCircuit.Step[0];
    if((!branch && old.WhenTrue.Length!=0) || ((!branch || IsLoop(op)) && otherwise.Length!=0))throw new ArgumentException("Delete the body's children before a change that would discard them.");
    if(branch){step.WhenTrue=old.WhenTrue;step.WhenFalse=IsLoop(op) ? null : otherwise;}
   }list[selected.Index]=step;}else list.Add(step);ReplaceBody(d,selected.Route,list.ToArray());});
 }
 void Delete() {var selected=Selected();if(selected.Index<0)throw new ArgumentException("Select an operation to delete.");history.Edit(d=>{var list=Body(d,selected.Route).ToList();list.RemoveAt(selected.Index);ReplaceBody(d,selected.Route,list.ToArray());});}
 void Refresh() {
  sourceStatus.Text=history.Source==null ? "" : "Original OpenQASM source retained · "+(history.Source.CircuitEdited ? "Circuit edited since import" : "Circuit matches imported snapshot")+" · "+(history.Source.PublishedU ? "Published OpenQASM 3 U" : "IBM / Qiskit U");
  var doc=history.Current.Snapshot();qubits.Text=doc.Qubits.ToString(CultureInfo.InvariantCulture);registers.Text=String.Join(", ",doc.Registers.Select(r=>r.Name+":"+r.Size.ToString(CultureInfo.InvariantCulture)));outputs.Text=String.Join(",",doc.OutputBits);
  loopLimit.Text=(doc.LoopConditionBudget ?? 1000000).ToString(CultureInfo.InvariantCulture);
  variables.Text=String.Join(", ",(doc.Variables ?? new ClassicalCircuit.Variable[0]).Select(v=>v.Name+":"+(v.Signedness=="Unsigned" ? "uint" : "int")+(v.Width==0 ? "" : "["+v.Width.ToString(CultureInfo.InvariantCulture)+"]")));
  tree.Items.Clear();tree.Items.Add(BodyNode("Program",doc.Steps,new int[0],doc));undo.IsEnabled=history.CanUndo;redo.IsEnabled=history.CanRedo;
 }
 static TreeViewItem BodyNode(string title,ClassicalCircuit.Step[] body,int[] route,ClassicalCircuit.Document context) {
  var node=new TreeViewItem {Header=title,IsExpanded=true,Tag=new Selection {Route=route,Index=-1}};
  for(int i=0;i<body.Length;i++) {var step=body[i];string description=step.Kind=="Rotation" ? "R"+step.Axis+"("+ClassicalRealExpressionText.Format(step.Angle,context)+") ["+String.Join(",",step.Wires)+"]" : step.Kind=="ForRange" ? "For "+context.Variables[step.VariableSlot.Value].Name+" in ["+RangeText(step.Range.Start,context)+" : "+RangeText(step.Range.Step,context)+" : "+RangeText(step.Range.Stop,context)+"]" : step.Kind=="End" ? "End program · keep saved results" : IsTransfer(step.Kind) ? (step.Kind=="Break" ? "Break nearest loop" : "Continue nearest loop") : step.Kind=="StoreInteger" ? context.Variables[step.VariableSlot.Value].Name+" = "+ClassicalExpressionText.Format(step.IntegerValue,context) : step.Kind=="ClearInteger" ? "Clear "+context.Variables[step.VariableSlot.Value].Name : step.Kind=="Assign" ? "Assign ["+String.Join(",",step.Wires)+"] ← "+ClassicalExpressionText.Format(step.ClassicalValue,context) : (step.Kind=="ExpressionBranch" || step.Kind=="While") ? (step.Kind=="While" ? "While " : "If ")+ClassicalExpressionText.Format(step.ClassicalValue,context) : step.Kind=="Branch" ? "If (record & "+step.Mask+") = "+step.Value : step.Kind+" "+(step.Expression ?? "")+" ["+String.Join(",",step.Wires ?? new int[0])+"]"+(step.ClassicalBit.HasValue ? " → bit "+step.ClassicalBit : "")+(step.Kind=="Conditional" ? " if (record & "+step.Mask+") = "+step.Value : "");
   var child=new TreeViewItem {Header=new TextBlock {Text=description,TextWrapping=TextWrapping.Wrap,FontFamily=new FontFamily("Consolas")},IsExpanded=true,Tag=new Selection {Route=route,Index=i}};node.Items.Add(child);
   if(IsBranch(step.Kind)) {child.Items.Add(BodyNode(IsLoop(step.Kind) ? "Loop body" : "Then",step.WhenTrue,route.Concat(new[]{i,0}).ToArray(),context));if(!IsLoop(step.Kind))child.Items.Add(BodyNode("Else",step.WhenFalse,route.Concat(new[]{i,1}).ToArray(),context));}
  }return node;
 }
 bool Discard() {return verifying || history.Serialize()==saved || MessageBox.Show(this,"Discard unsaved circuit changes?","Classical circuit",MessageBoxButton.YesNo,MessageBoxImage.Question)==MessageBoxResult.Yes;}
 void Import(string path,bool published,bool moduleHeaders=false) {history.ImportSource(QasmImport.CompileSource(path,published,true,moduleHeaders),published);}
 public async System.Threading.Tasks.Task VerifySourceFiles(string path,string report) {
  verifying=true;Import(path,false);Refresh();
  await SourceFilesWindow.Verify(this,history.Source,Path.GetDirectoryName(path),report,envelope=>history.ImportSource(envelope,false),()=>history.Serialize(),()=>history.Undo());
 }
 public void VerifyImport(string path,string report,bool moduleHeaders=false) {
  verifying=true;
  // Import replaces all metadata and undo restores even a loop-bearing document.
  history.Edit(d=>{d.Version=7;d.Variables=new ClassicalCircuit.Variable[0];d.LoopConditionBudget=3;d.Steps=new[]{new ClassicalCircuit.Step{Kind="While",ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"},WhenTrue=new ClassicalCircuit.Step[0]}};});
  string before=history.Current.Serialize();Import(path,false,moduleHeaders);string imported=history.Current.Serialize();
  if(history.Source==null || history.Source.CircuitEdited)throw new Exception("Import lost original source.");
  string originalSource=history.Source.SourceJson,full=history.Serialize();
  history.Undo();if(history.Current.Serialize()!=before)throw new Exception("Import undo lost the previous circuit.");history.Redo();if(history.Current.Serialize()!=imported)throw new Exception("Import redo lost classical circuit data.");
  if(history.Serialize()!=full)throw new Exception("Import redo lost source metadata.");
  SaveTo(report+".source.qcircuit");
  history.Open(File.ReadAllText(report+".source.qcircuit",new UTF8Encoding(false,true)));
  if(history.Serialize()!=full || saved!=full)throw new Exception("Source document save/reopen changed data.");
  history.Edit(d=>d.Steps=new ClassicalCircuit.Step[0]);
  if(history.Current.Serialize()!=imported && (!history.Source.CircuitEdited || history.Source.SourceJson!=originalSource))throw new Exception("Circuit edit lost source identity.");
  string edited=history.Serialize();
  try{history.Open("{");throw new Exception("Malformed source document accepted.");}catch(InvalidDataException){}
  if(history.Serialize()!=edited)throw new Exception("Invalid open changed the current source document.");
  Refresh();Capture(report+".edited.png");
  history.Open(full);
  File.WriteAllText(report+".qcircuit",imported);Refresh();status.Text="Imported · Classical registers, saved measurements and branches preserved.";Capture(report+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(report+".minimum.png");
 }
 void Open() {var picker=new Microsoft.Win32.OpenFileDialog {Filter="Classical circuits (*.qcircuit)|*.qcircuit|JSON (*.json)|*.json"};if(picker.ShowDialog(this)!=true)return;string text=new UTF8Encoding(false,true).GetString(BoundedUtf8File.Read(picker.FileName,SourceCircuitDocument.MaxDocumentBytes,"Classical circuit"));var next=new ClassicalProgramHistory(history.Current);next.Open(text);if(!Discard())return;history.Open(next.Serialize());saved=history.Serialize();}
 void Save() {var picker=new Microsoft.Win32.SaveFileDialog {Filter="Classical circuit (*.qcircuit)|*.qcircuit",DefaultExt=".qcircuit",AddExtension=true,OverwritePrompt=true};if(picker.ShowDialog(this)!=true)return;SaveTo(picker.FileName);}
 async System.Threading.Tasks.Task<ClassicalQasmExport> PrepareExport() {
  string before=history.Serialize();var snapshot=history.Current;
  var prepared=await System.Threading.Tasks.Task.Run(()=>ClassicalQasmExport.Prepare(snapshot));
  if(history.Serialize()!=before)throw new InvalidDataException("The circuit changed while checking the export. Export again to use the current circuit.");
  return prepared;
 }
 async System.Threading.Tasks.Task Export() {
  if(!export.IsEnabled)return;
  export.IsEnabled=false;status.Text="Checking OpenQASM export…";
  try {
   string before=history.Serialize();
   var prepared=await PrepareExport();
   if(!IsVisible)return;
   var picker=new Microsoft.Win32.SaveFileDialog {Filter="OpenQASM 3 (*.qasm)|*.qasm",DefaultExt=".qasm",AddExtension=true,FileName="My classical circuit.qasm",OverwritePrompt=true};
   if(picker.ShowDialog(this)!=true){status.Text="Export canceled.";return;}
   if(history.Serialize()!=before)throw new InvalidDataException("The circuit changed. Export again to use the current circuit.");
   prepared.SaveTo(picker.FileName);
   status.Text="Exported OpenQASM · "+Path.GetFileName(picker.FileName);
  } catch(Exception error) {status.Text=error.Message;}
  finally {export.IsEnabled=true;}
 }
 public async System.Threading.Tasks.Task VerifyExport(string path,string report,bool modules=false) {
  verifying=true;Import(path,false,modules);Refresh();
  if(history.Current.Qubits<1)throw new ArgumentException("Export GUI fixture needs a qubit.");
  string originalSource=history.Source.SourceJson;
  var originalExport=await PrepareExport();originalExport.SaveTo(report+".original.qasm");
  history.Edit(d=>{var edit=new[]{new ClassicalCircuit.Step{Kind="Gate",Expression="X",Wires=new[]{0}}};
   d.Steps=modules?edit.Concat(d.Steps).ToArray():d.Steps.Concat(edit).ToArray();});
  Refresh();string before=history.Serialize(),savedBefore=saved;
  bool undoBefore=history.CanUndo,redoBefore=history.CanRedo;
  var prepared=await PrepareExport();string target=report+".qasm";
  File.WriteAllText(target,"existing export",new UTF8Encoding(false));
  prepared.SaveTo(target);string exported=File.ReadAllText(target,new UTF8Encoding(false,true));
  if(exported!=ClassicalProgramQasm.Export(history.Current) || history.Serialize()!=before || saved!=savedBefore ||
   history.CanUndo!=undoBefore || history.CanRedo!=redoBefore || history.Source.SourceJson!=originalSource || !history.Source.CircuitEdited)
   throw new Exception("Export changed history/source metadata or ignored edits.");
  status.Text="Exported OpenQASM · "+Path.GetFileName(target);Capture(report+".png");
  foreach(string bad in new[]{"matrix(2,2,[0,1,1,0])","Rx(1/0)"}) {
   history.Edit(d=>d.Steps=d.Steps.Concat(new[]{new ClassicalCircuit.Step{Kind="Gate",Expression=bad,Wires=new[]{0}}}).ToArray());
   string invalid=history.Serialize();bool failed=false;
   try {var rejected=await PrepareExport();rejected.SaveTo(target);}
   catch(InvalidDataException error){failed=true;status.Text=error.Message;}
   if(!failed || history.Serialize()!=invalid || saved!=savedBefore || File.ReadAllText(target)!=exported)
    throw new Exception("Rejected export changed the document or destination.");
   if(bad.StartsWith("matrix"))Capture(report+".rejected.png");
   history.Undo();if(history.Serialize()!=before)throw new Exception("Export failure damaged undo.");
  }
  SaveTo(report+".qcircuit");history.Open(File.ReadAllText(report+".qcircuit",new UTF8Encoding(false,true)));
  if(history.Serialize()!=before || history.Source.SourceJson!=originalSource)throw new Exception("Export changed save/reopen behavior.");
  Refresh();status.Text="Exported OpenQASM · "+Path.GetFileName(target);
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(report+".minimum.png");
 }
 void SaveTo(string path) {string text=history.Serialize(),temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";try {File.WriteAllText(temp,text,new UTF8Encoding(false));if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);saved=text;}finally {if(File.Exists(temp))File.Delete(temp);}}
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
  VerifyLoops(screenshot+".loops");
  VerifyTransfers(screenshot+".transfers");
  VerifyTermination(screenshot+".termination");
  VerifyRanges(screenshot+".ranges");
  VerifyRotations(screenshot+".rotations");
 }
 void VerifyRotations(string screenshot) {
  Width=980;Height=920;
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize());Refresh();
  variables.Text="n:int";ApplyVariables();Refresh();
  kind.SelectedValue="Rotation";rotationAxis.SelectedItem="Y";rotationAngle.Text="pi*n/2";wires.Text="0";ChangeStep(false);Refresh();
  Func<TreeViewItem> node=()=> (TreeViewItem)((TreeViewItem)tree.Items[0]).Items[0];node().IsSelected=true;
  if(rotationFields.Visibility!=Visibility.Visible || rotationAxis.SelectedItem.ToString()!="Y" || !((TextBlock)node().Header).Text.Contains("RY("))throw new Exception("Rotation selection lost its visible axis or expression: "+rotationFields.Visibility+" / "+rotationAxis.SelectedItem+" / "+((TextBlock)node().Header).Text);
  string original=history.Current.Serialize();ChangeStep(true);
  if(history.Current.Serialize()!=original)throw new Exception("Unchanged angle edit changed its meaning.");
  rotationAxis.SelectedItem="Z";rotationAngle.Text="float(n/2)";ChangeStep(true);Refresh();string edited=history.Current.Serialize();
  var doc=history.Current.Snapshot();
  if(doc.Version!=11 || doc.Steps[0].Axis!="Z" || doc.Steps[0].Angle.Kind!="Integer")throw new Exception("Rotation replacement lost integer division or axis.");
  history.Undo();if(history.Current.Serialize()!=original)throw new Exception("Rotation undo failed.");
  history.Redo();if(history.Current.Serialize()!=edited)throw new Exception("Rotation redo failed.");Refresh();node().IsSelected=true;
  rotationAngle.Text="missing +";try{ChangeStep(true);throw new Exception("Invalid angle accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=edited)throw new Exception("Invalid angle changed document.");
  history.Open(edited);Refresh();node().IsSelected=true;
  if(history.Current.Serialize()!=edited)throw new Exception("Rotation save/reopen failed.");
  saved=edited;File.WriteAllText(screenshot+".qcircuit",edited);
  status.Text="Verified · Runtime rotation axis, real/integer arithmetic, replacement, invalid edits, undo/redo and save/reopen.";
  ((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void VerifyRanges(string screenshot) {
  Width=980;Height=920;
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize());Refresh();
  variables.Text="i:int, total:int";ApplyVariables();Refresh();
  kind.SelectedValue="StoreInteger";variableTarget.Text="total";expression.Text="0";ChangeStep(false);Refresh();
  kind.SelectedValue="ForRange";variableTarget.Text="i";rangeStart.Text="0";rangeStop.Text="3";rangeStep.Text="1";
  expression.Text="ignored matrix";wires.Text="invalid";mask.Text=value.Text=destination.Text="invalid";
  if(rangeFields.Visibility!=Visibility.Visible || !variableTarget.IsEnabled || expression.IsEnabled || wires.IsEnabled || destination.IsEnabled || mask.IsEnabled)throw new Exception("Range field visibility is incorrect.");
  ChangeStep(false);Refresh();
  Func<TreeViewItem> rangeNode=()=> (TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];
  Action selectBody=()=>((TreeViewItem)rangeNode().Items[0]).IsSelected=true;
  if(rangeNode().Items.Count!=1)throw new Exception("Range should have one loop body.");
  selectBody();kind.SelectedValue="StoreInteger";variableTarget.Text="total";expression.Text="total + i";ChangeStep(false);Refresh();
  selectBody();kind.SelectedValue="Continue";ChangeStep(false);Refresh();
  ((TreeViewItem)tree.Items[0]).IsSelected=true;kind.SelectedValue="Assign";wires.Text="0";expression.Text="total == 6";ChangeStep(false);Refresh();
  string original=history.Current.Serialize();rangeNode().IsSelected=true;
  if(rangeStart.Text!="0" || rangeStop.Text!="3" || rangeStep.Text!="1" || variableTarget.Text!="i")throw new Exception("Selecting a range lost its fields.");
  rangeStart.Text="int[8](-3)";rangeStop.Text="uint[16](5)";rangeStep.Text="int[8](2)";ChangeStep(true);Refresh();rangeNode().IsSelected=true;
  if(rangeStart.Text!="int[8](-3)" || rangeStop.Text!="uint[16](5)" || rangeStep.Text!="int[8](2)")throw new Exception("Selecting a range erased its explicit types.");
  string typed=history.Current.Serialize();ChangeStep(true);
  if(history.Current.Serialize()!=typed)throw new Exception("Unchanged typed range edit changed its meaning.");
  history.Open(original);Refresh();rangeNode().IsSelected=true;
  rangeStop.Text="5";rangeStep.Text="2";ChangeStep(true);Refresh();string edited=history.Current.Serialize();
  var doc=history.Current.Snapshot();
  if(doc.Version!=10 || doc.Steps[1].WhenTrue.Length!=2 || doc.Steps[1].WhenTrue[1].Kind!="Continue" || doc.Steps[1].Range.Stop.Value!="5")throw new Exception("Range replacement lost its body or bounds.");
  history.Undo();if(history.Current.Serialize()!=original)throw new Exception("Range undo failed.");
  history.Redo();if(history.Current.Serialize()!=edited)throw new Exception("Range redo failed.");Refresh();
  rangeNode().IsSelected=true;rangeStart.Text="missing +";
  try{ChangeStep(true);throw new Exception("Invalid range expression accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=edited)throw new Exception("Rejected range edit changed program.");Refresh();
  rangeNode().IsSelected=true;kind.SelectedValue="Gate";expression.Text="X";wires.Text="0";
  try{ChangeStep(true);throw new Exception("Range body silently discarded.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=edited)throw new Exception("Rejected range replacement changed program.");Refresh();
  ((TreeViewItem)tree.Items[0]).IsSelected=true;kind.SelectedValue="End";ChangeStep(false);Refresh();
  if(history.Current.Snapshot().Version!=10)throw new Exception("End downgraded a range document.");
  history.Undo();if(history.Current.Serialize()!=edited)throw new Exception("End undo changed range document.");Refresh();
  rangeNode().IsSelected=true;Delete();Refresh();history.Undo();
  if(history.Current.Serialize()!=edited)throw new Exception("Range delete undo failed.");
  history.Open(edited);Refresh();if(history.Current.Serialize()!=edited)throw new Exception("Range save/reopen failed.");
  saved=edited;File.WriteAllText(screenshot+".qcircuit",edited);rangeNode().IsSelected=true;
  status.Text="Verified · Inclusive range, preserved body, invalid edits, undo/redo and save/reopen.";
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void VerifyTermination(string screenshot) {
  Width=980;Height=920;
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize());Refresh();
  string initial=history.Current.Serialize();
  ((TreeViewItem)tree.Items[0]).IsSelected=true;kind.SelectedValue="End";
  expression.Text=wires.Text=destination.Text=mask.Text=value.Text=variableTarget.Text="invalid";
  if(expression.IsEnabled || wires.IsEnabled || destination.IsEnabled || mask.IsEnabled || value.IsEnabled || variableTarget.IsEnabled)throw new Exception("End enabled payload fields.");
  ChangeStep(false);Refresh();string ended=history.Current.Serialize();
  var doc=history.Current.Snapshot();
  if(doc.Version!=9 || doc.Steps[0].Kind!="End" || doc.Variables==null || doc.LoopConditionBudget!=1000000)throw new Exception("End metadata was not saved.");
  history.Undo();if(history.Current.Serialize()!=initial)throw new Exception("End undo failed.");
  history.Redo();if(history.Current.Serialize()!=ended)throw new Exception("End redo failed.");Refresh();
  ((TreeViewItem)((TreeViewItem)tree.Items[0]).Items[0]).IsSelected=true;
  kind.SelectedValue="Assign";wires.Text="0";expression.Text="1";ChangeStep(true);Refresh();
  if(history.Current.Snapshot().Version!=9)throw new Exception("Replacement downgraded End file.");
  history.Undo();Refresh();if(history.Current.Serialize()!=ended)throw new Exception("End replacement undo failed.");
  loopLimit.Text="0";ApplyLoopLimit();Refresh();
  string bounded=history.Current.Serialize();history.Open(bounded);Refresh();
  if(history.Current.Serialize()!=bounded || history.Current.Snapshot().Version!=9)throw new Exception("End save/reopen failed.");
  saved=bounded;File.WriteAllText(screenshot+".qcircuit",bounded);
  ((TreeViewItem)((TreeViewItem)tree.Items[0]).Items[0]).IsSelected=true;
  status.Text="Verified · End program, zero condition budget, undo/redo and save/reopen.";
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void VerifyTransfers(string screenshot) {
  Width=980;Height=920;
  var yes=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="1"};
  var no=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"};
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=7,LoopConditionBudget=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],OutputBits=new[]{0},Steps=new[]{
   new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes},
   new ClassicalCircuit.Step{Kind="While",ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Read",Bits=new[]{0}},WhenTrue=new[]{
    new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=no},
    new ClassicalCircuit.Step{Kind="ExpressionBranch",ClassicalValue=yes,WhenTrue=new ClassicalCircuit.Step[0],WhenFalse=new ClassicalCircuit.Step[0]},
    new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes}}}}}).Serialize());Refresh();
  string initial=history.Current.Serialize();
  foreach(string op in new[]{"Break","Continue"}) {
   ((TreeViewItem)tree.Items[0]).IsSelected=true;kind.SelectedValue=op;
   // Disabled inputs must not become hidden payload when the selection changes.
   expression.Text="not an expression";wires.Text="not indices";variableTarget.Text="missing";mask.Text=value.Text=destination.Text="invalid";
   if(expression.IsEnabled || wires.IsEnabled || variableTarget.IsEnabled || destination.IsEnabled || mask.IsEnabled || value.IsEnabled)throw new Exception("Transfer enabled payload fields.");
   try{ChangeStep(false);throw new Exception("Transfer outside loop accepted.");}catch(ArgumentException){}
   if(history.Current.Serialize()!=initial)throw new Exception("Rejected transfer changed program.");Refresh();
  }
  Func<TreeViewItem> loopNode=()=> (TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];
  Func<TreeViewItem> branchNode=()=> (TreeViewItem)((TreeViewItem)loopNode().Items[0]).Items[1];
  ((TreeViewItem)branchNode().Items[0]).IsSelected=true;kind.SelectedValue="Break";ChangeStep(false);Refresh();
  string broken=history.Current.Serialize();var doc=history.Current.Snapshot();
  if(doc.Version!=8 || doc.Steps[1].WhenTrue[1].WhenTrue[0].Kind!="Break")throw new Exception("Nested break was not saved.");
  ((TreeViewItem)((TreeViewItem)branchNode().Items[0]).Items[0]).IsSelected=true;
  if((string)kind.SelectedValue!="Break")throw new Exception("Transfer selection lost its kind.");
  kind.SelectedValue="Continue";ChangeStep(true);Refresh();string continued=history.Current.Serialize();
  history.Undo();if(history.Current.Serialize()!=broken)throw new Exception("Transfer undo lost break.");
  history.Redo();if(history.Current.Serialize()!=continued)throw new Exception("Transfer redo lost continue.");
  loopNode().IsSelected=true;kind.SelectedValue="Break";
  try{ChangeStep(true);throw new Exception("Transfer replacement discarded loop body.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=continued)throw new Exception("Rejected transfer replacement changed program.");Refresh();
  loopNode().IsSelected=true;kind.SelectedValue="ExpressionBranch";expression.Text="c[0]";
  try{ChangeStep(true);throw new Exception("Removing enclosing loop stranded transfer.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=continued)throw new Exception("Invalid loop conversion changed program.");Refresh();
  ((TreeViewItem)((TreeViewItem)branchNode().Items[0]).Items[0]).IsSelected=true;Delete();Refresh();
  history.Undo();if(history.Current.Serialize()!=continued)throw new Exception("Transfer delete undo lost program.");
  history.Open(continued);Refresh();if(history.Current.Serialize()!=continued)throw new Exception("Transfer save/reopen changed program.");
  saved=continued;File.WriteAllText(screenshot+".qcircuit",continued);
  status.Text="Verified · Break and Continue, nested branches, invalid edits, undo/redo and save/reopen.";
  ((TreeViewItem)((TreeViewItem)branchNode().Items[0]).Items[0]).IsSelected=true;
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();((ScrollViewer)Content).ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void VerifyLoops(string screenshot) {
  Width=980;Height=920;
  history.Open(ClassicalCircuit.From(new ClassicalCircuit.Document{Version=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},OutputBits=new[]{0},Steps=new ClassicalCircuit.Step[0]}).Serialize());Refresh();
  variables.Text="counter:int[8]";ApplyVariables();Refresh();
  kind.SelectedValue="StoreInteger";variableTarget.Text="counter";expression.Text="3";ChangeStep(false);Refresh();
  kind.SelectedValue="While";expression.Text="counter > 0";ChangeStep(false);Refresh();
  Action selectBody=()=>{var block=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];((TreeViewItem)block.Items[0]).IsSelected=true;};
  selectBody();kind.SelectedValue="StoreInteger";variableTarget.Text="counter";expression.Text="counter - 1";ChangeStep(false);Refresh();
  selectBody();kind.SelectedValue="Assign";wires.Text="0";expression.Text="counter == 0";ChangeStep(false);Refresh();
  selectBody();kind.SelectedValue="While";expression.Text="0 == 1";ChangeStep(false);Refresh();
  loopLimit.Text="7";ApplyLoopLimit();Refresh();
  string valid=history.Current.Serialize();var doc=history.Current.Snapshot();
  if(doc.Version!=7 || doc.LoopConditionBudget!=7 || doc.Steps[1].WhenFalse!=null || doc.Steps[1].WhenTrue.Length!=3)throw new Exception("Loop creation lost body or budget.");
  loopLimit.Text="1000001";try{ApplyLoopLimit();throw new Exception("Excessive loop budget accepted.");}catch(InvalidDataException){}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid loop budget changed program.");Refresh();
  Action selectLoop=()=>{((TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1]).IsSelected=true;};
  selectLoop();if((string)kind.SelectedValue!="While" || !expression.Text.Contains("counter"))throw new Exception("Loop selection lost condition text.");
  ChangeStep(true);if(history.Current.Serialize()!=valid)throw new Exception("Loop condition round trip changed program.");
  expression.Text="counter + 1";try{ChangeStep(true);throw new Exception("Integer-valued loop condition accepted.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid loop condition changed program.");
  selectLoop();kind.SelectedValue="Gate";expression.Text="H";wires.Text="0";
  try{ChangeStep(true);throw new Exception("Loop body was discarded.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=valid)throw new Exception("Rejected loop replacement changed program.");
  selectLoop();kind.SelectedValue="ExpressionBranch";expression.Text="counter > 0";ChangeStep(true);Refresh();
  var branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];((TreeViewItem)branch.Items[1]).IsSelected=true;
  kind.SelectedValue="Assign";wires.Text="0";expression.Text="0";ChangeStep(false);Refresh();
  string withElse=history.Current.Serialize();selectLoop();kind.SelectedValue="While";expression.Text="counter > 0";
  try{ChangeStep(true);throw new Exception("Populated Else body was discarded.");}catch(ArgumentException){}
  if(history.Current.Serialize()!=withElse)throw new Exception("Rejected Else conversion changed program.");
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[1];((TreeViewItem)((TreeViewItem)branch.Items[1]).Items[0]).IsSelected=true;Delete();Refresh();
  selectLoop();kind.SelectedValue="While";expression.Text="counter > 0";ChangeStep(true);Refresh();
  if(history.Current.Serialize()!=valid)throw new Exception("Safe branch/loop conversion changed children.");
  history.Undo();history.Redo();if(history.Current.Serialize()!=valid)throw new Exception("Loop undo/redo changed program.");
  history.Open(valid);Refresh();if(history.Current.Serialize()!=valid)throw new Exception("Loop save/reopen changed program.");
  history.Edit(d=>{d.Version=8;var body=d.Steps[1].WhenTrue.ToList();body.Add(new ClassicalCircuit.Step{Kind="Break"});d.Steps[1].WhenTrue=body.ToArray();});Refresh();
  loopLimit.Text="9";ApplyLoopLimit();Refresh();
  if(history.Current.Snapshot().Version!=8 || history.Current.LoopConditionBudget!=9)throw new Exception("Budget edit downgraded transfer file.");
  selectLoop();ChangeStep(true);Refresh();
  if(history.Current.Snapshot().Version!=8 || history.Current.Snapshot().Steps[1].WhenTrue.Last().Kind!="Break")throw new Exception("Loop edit lost transfer file version or body.");
  history.Open(valid);Refresh();
  saved=valid;File.WriteAllText(screenshot+".qcircuit",valid);status.Text="Verified · Nested loops, safe body conversion, limits, saved files and undo/redo.";
  ((ScrollViewer)Content).ScrollToTop();UpdateLayout();Capture(screenshot+".png");
  Width=MinWidth;Height=MinHeight;UpdateLayout();var scroll=(ScrollViewer)Content;
  if(scroll.ScrollableHeight<=0)throw new Exception("Loop controls do not scroll at minimum size.");scroll.ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
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

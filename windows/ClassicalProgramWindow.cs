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
 sealed class Selection {public int[] Route;public int Index;}
 readonly ClassicalProgramHistory history;
 readonly TreeView tree=new TreeView();
 readonly TextBox qubits=new TextBox {Text="1"},registers=new TextBox {Text="c:1"},outputs=new TextBox {Text="0"};
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
  tree.Height=270;SizeChanged+=delegate {tree.Height=Math.Max(180,ActualHeight-580);};
  var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);root.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Quantum circuit · classical control",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text="Measurements save into named registers. Branches read the saved bits once when entered.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,6,0,12)});
  var commands=new WrapPanel();top.Children.Add(commands);
  Button(commands,"Open…",Open);Button(commands,"Save…",Save);Button(commands,"Sample…",()=>new SamplingWindow(this,history.Current).Show());
  var convention=new ComboBox {Width=180,VerticalAlignment=VerticalAlignment.Center};convention.Items.Add("IBM / Qiskit U");convention.Items.Add("Published OpenQASM 3 U");convention.SelectedIndex=0;commands.Children.Add(convention);System.Windows.Automation.AutomationProperties.SetName(convention,"Imported U gate convention");
  Button(commands,"Import OpenQASM…",()=>{var picker=new Microsoft.Win32.OpenFileDialog {Filter="OpenQASM (*.qasm)|*.qasm|All files (*.*)|*.*"};if(picker.ShowDialog(this)==true)Import(picker.FileName,convention.SelectedIndex==1);});
  commands.Children.Add(undo);commands.Children.Add(redo);undo.Click+=delegate {history.Undo();Refresh();};redo.Click+=delegate {history.Redo();Refresh();};
  var settings=new WrapPanel();top.Children.Add(settings);Field(settings,"Qubits",qubits,65);Field(settings,"Registers · name:size, …",registers,260);Field(settings,"Output bit indices · left to right",outputs,200);
  Button(settings,"Apply registers",()=>history.Edit(d=>{d.Qubits=Int(qubits.Text);d.Registers=ParseRegisters(registers.Text);d.OutputBits=Indices(outputs.Text);}));
  top.Children.Add(new TextBlock {Text="Registers occupy consecutive bits starting at 0. Output order is explicit; no final measurements are added. Changing register sizes changes bit allocation.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,4,0,10)});
  var bottom=new StackPanel();DockPanel.SetDock(bottom,Dock.Bottom);root.Children.Add(bottom);
  bottom.Children.Add(status);
  var editor=new WrapPanel();bottom.Children.Add(editor);
  foreach(string item in Enum.GetNames(typeof(NumericalSampling.Operation)))kind.Items.Add(item);kind.SelectedItem="Gate";
  Field(editor,"Operation",kind,125);Field(editor,"Matrix / channel",expression,180);Field(editor,"Target wires / bits",wires,120);Field(editor,"Save to classical bit",destination,120);
  Field(editor,"Condition mask · decimal",mask,170);Field(editor,"Condition value · decimal",value,170);
  kind.SelectionChanged+=delegate {SetFields();};SetFields();
  var edits=new WrapPanel();bottom.Children.Add(edits);Button(edits,"Add to selected body",()=>ChangeStep(false));Button(edits,"Replace selected",()=>ChangeStep(true));Button(edits,"Delete selected",Delete);
  bottom.Children.Add(new TextBlock {Text="Select Program, Then or Else to append operations. Select an operation to replace or delete it. Use Sample for classical outcomes; exact classical-record evaluation is not yet available.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,8,0,0)});
  tree.Background=WorkspaceTheme.Surface;tree.Foreground=WorkspaceTheme.Text;tree.Margin=new Thickness(0,8,0,12);root.Children.Add(tree);
  tree.SelectedItemChanged+=delegate {var node=tree.SelectedItem as TreeViewItem;var selected=node==null ? null : node.Tag as Selection;if(selected==null || selected.Index<0)return;var step=Body(history.Current.Snapshot(),selected.Route)[selected.Index];kind.SelectedItem=step.Kind;expression.Text=step.Expression ?? "";wires.Text=String.Join(",",step.Wires ?? new int[0]);destination.Text=step.ClassicalBit.HasValue ? step.ClassicalBit.Value.ToString(CultureInfo.InvariantCulture) : "";mask.Text=step.Mask ?? "1";value.Text=step.Value ?? "1";};
  Refresh();
 }
 static int Int(string text) {int result;if(!Int32.TryParse(text.Trim(),NumberStyles.None,CultureInfo.InvariantCulture,out result))throw new ArgumentException("Enter nonnegative integer indices and sizes.");return result;}
 static int[] Indices(string text) {return String.IsNullOrWhiteSpace(text) ? new int[0] : text.Split(',').Select(Int).ToArray();}
 static ClassicalCircuit.Register[] ParseRegisters(string text) {
  if(String.IsNullOrWhiteSpace(text))return new ClassicalCircuit.Register[0];
  return text.Split(',').Select(entry=>{string[] parts=entry.Split(':');if(parts.Length!=2)throw new ArgumentException("Write each register as name:size, such as c:2, flag:1.");return new ClassicalCircuit.Register {Name=parts[0].Trim(),Size=Int(parts[1])};}).ToArray();
 }
 void SetFields() {string op=kind.SelectedItem as string;bool branch=op=="Branch",condition=branch || op=="Conditional";expression.IsEnabled=op=="Gate" || op=="Conditional" || op=="Channel" || op=="Readout";wires.IsEnabled=!branch;destination.IsEnabled=op=="Measure";mask.IsEnabled=value.IsEnabled=condition;}
 static void Field(Panel panel,string label,Control control,int width) {var group=new StackPanel {Margin=new Thickness(0,6,12,6)};group.Children.Add(new TextBlock {Text=label});control.Width=width;group.Children.Add(control);panel.Children.Add(group);System.Windows.Automation.AutomationProperties.SetName(control,label);}
 void Button(Panel panel,string title,Action action) {var button=new Button {Content=title,VerticalAlignment=VerticalAlignment.Bottom};panel.Children.Add(button);button.Click+=delegate {try {action();Refresh();status.Text="Ready · Changes are captured for undo.";}catch(Exception error) {status.Text=error.Message;}};}
 static ClassicalCircuit.Step[] Body(ClassicalCircuit.Document doc,int[] route) {var body=doc.Steps;for(int i=0;i<route.Length;i+=2)body=route[i+1]==0 ? body[route[i]].WhenTrue : body[route[i]].WhenFalse;return body;}
 static void ReplaceBody(ClassicalCircuit.Document doc,int[] route,ClassicalCircuit.Step[] body) {if(route.Length==0){doc.Steps=body;return;}var parent=Body(doc,route.Take(route.Length-2).ToArray())[route[route.Length-2]];if(route[route.Length-1]==0)parent.WhenTrue=body;else parent.WhenFalse=body;}
 Selection Selected() {var node=tree.SelectedItem as TreeViewItem;return node==null ? new Selection {Route=new int[0],Index=-1} : (Selection)node.Tag;}
 void ChangeStep(bool replace) {
  var selected=Selected();if(replace && selected.Index<0)throw new ArgumentException("Select an operation to replace.");
  string op=(string)kind.SelectedItem;bool branch=op=="Branch",condition=branch || op=="Conditional";
  var step=new ClassicalCircuit.Step {Kind=op,Expression=expression.IsEnabled ? expression.Text.Trim() : null,Wires=branch ? null : Indices(wires.Text),ClassicalBit=op=="Measure" ? (int?)Int(destination.Text) : null,Mask=condition ? mask.Text.Trim() : null,Value=condition ? value.Text.Trim() : null,WhenTrue=branch ? new ClassicalCircuit.Step[0] : null,WhenFalse=branch ? new ClassicalCircuit.Step[0] : null};
  history.Edit(d=>{var list=Body(d,selected.Route).ToList();if(replace) {var old=list[selected.Index];if(old.Kind=="Branch") {if(!branch && (old.WhenTrue.Length!=0 || old.WhenFalse.Length!=0))throw new ArgumentException("Delete the branch's children before changing it to another operation.");if(branch){step.WhenTrue=old.WhenTrue;step.WhenFalse=old.WhenFalse;}}list[selected.Index]=step;}else list.Add(step);ReplaceBody(d,selected.Route,list.ToArray());});
 }
 void Delete() {var selected=Selected();if(selected.Index<0)throw new ArgumentException("Select an operation to delete.");history.Edit(d=>{var list=Body(d,selected.Route).ToList();list.RemoveAt(selected.Index);ReplaceBody(d,selected.Route,list.ToArray());});}
 void Refresh() {
  var doc=history.Current.Snapshot();qubits.Text=doc.Qubits.ToString(CultureInfo.InvariantCulture);registers.Text=String.Join(", ",doc.Registers.Select(r=>r.Name+":"+r.Size.ToString(CultureInfo.InvariantCulture)));outputs.Text=String.Join(",",doc.OutputBits);
  tree.Items.Clear();tree.Items.Add(BodyNode("Program",doc.Steps,new int[0]));undo.IsEnabled=history.CanUndo;redo.IsEnabled=history.CanRedo;
 }
 static TreeViewItem BodyNode(string title,ClassicalCircuit.Step[] body,int[] route) {
  var node=new TreeViewItem {Header=title,IsExpanded=true,Tag=new Selection {Route=route,Index=-1}};
  for(int i=0;i<body.Length;i++) {var step=body[i];string description=step.Kind=="Branch" ? "If (record & "+step.Mask+") = "+step.Value : step.Kind+" "+(step.Expression ?? "")+" ["+String.Join(",",step.Wires ?? new int[0])+"]"+(step.ClassicalBit.HasValue ? " → bit "+step.ClassicalBit : "")+(step.Kind=="Conditional" ? " if (record & "+step.Mask+") = "+step.Value : "");
   var child=new TreeViewItem {Header=new TextBlock {Text=description,TextWrapping=TextWrapping.Wrap,FontFamily=new FontFamily("Consolas")},IsExpanded=true,Tag=new Selection {Route=route,Index=i}};node.Items.Add(child);
   if(step.Kind=="Branch") {child.Items.Add(BodyNode("Then",step.WhenTrue,route.Concat(new[]{i,0}).ToArray()));child.Items.Add(BodyNode("Else",step.WhenFalse,route.Concat(new[]{i,1}).ToArray()));}
  }return node;
 }
 bool Discard() {return verifying || history.Current.Serialize()==saved || MessageBox.Show(this,"Discard unsaved circuit changes?","Classical circuit",MessageBoxButton.YesNo,MessageBoxImage.Question)==MessageBoxResult.Yes;}
 void Import(string path,bool published) {var next=ClassicalCircuit.Load(QasmImport.Compile(path,published,true)).Snapshot();history.Edit(d=>{d.Version=next.Version;d.Qubits=next.Qubits;d.Registers=next.Registers;d.OutputBits=next.OutputBits;d.Steps=next.Steps;});}
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
  kind.SelectedItem="Gate";expression.Text="H";wires.Text="0";ChangeStep(false);Refresh();
  kind.SelectedItem="Measure";destination.Text="1";ChangeStep(false);Refresh();
  kind.SelectedItem="Branch";mask.Text="2";value.Text="2";ChangeStep(false);Refresh();
  var branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];((TreeViewItem)branch.Items[0]).IsSelected=true;
  kind.SelectedItem="Gate";expression.Text="X";wires.Text="1";ChangeStep(false);Refresh();
  string valid=history.Current.Serialize();
  kind.SelectedItem="Measure";wires.Text="9";destination.Text="0";
  try {ChangeStep(false);throw new Exception("Invalid wire accepted.");}catch(ArgumentException) {}
  if(history.Current.Serialize()!=valid)throw new Exception("Invalid edit changed the program.");
  branch=(TreeViewItem)((TreeViewItem)tree.Items[0]).Items[2];branch.IsSelected=true;
  kind.SelectedItem="Gate";wires.Text="0";expression.Text="H";
  try {ChangeStep(true);throw new Exception("Branch children were discarded.");}catch(ArgumentException) {}
  if(history.Current.Serialize()!=valid)throw new Exception("Rejected replacement changed the program.");
  history.Undo();history.Redo();if(history.Current.Serialize()!=valid)throw new Exception("Undo/redo lost a nested operation.");
  history.Open(valid);Refresh();if(history.Current.Serialize()!=valid || history.CanUndo)throw new Exception("Reload did not preserve the program.");
  saved=valid;
  File.WriteAllText(screenshot+".qcircuit",valid);
  status.Text="Verified · Nested branch, saved measurement, output order, invalid edits and undo/redo.";
  Capture(screenshot);
  Width=MinWidth;Height=MinHeight;UpdateLayout();var scroll=(ScrollViewer)Content;
  if(scroll.ScrollableHeight<=0)throw new Exception("Short editor did not make all controls scrollable.");
  scroll.ScrollToEnd();UpdateLayout();Capture(screenshot+".minimum.png");
 }
 void Capture(string path) {UpdateLayout();var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(this);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);}
}

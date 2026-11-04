// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;

// This dialog owns the explicit filesystem selection. Saved provenance never
// supplies a default root, and check results never replace the editor document.
sealed class SourceFilesWindow : Window {
 readonly SourceCircuitDocument document;
 readonly Action<string> import;
 readonly TextBox root=new TextBox {MinWidth=220};
 readonly TextBlock result=new TextBlock {TextWrapping=TextWrapping.Wrap};
 readonly string entry;
 readonly bool modules;
 bool busy;
 public bool Imported {get;private set;}
 sealed class DialogOwner : System.Windows.Forms.IWin32Window {
  public IntPtr Handle {get;private set;}
  public DialogOwner(Window window) {Handle=new WindowInteropHelper(window).Handle;}
 }
 public SourceFilesWindow(Window owner,SourceCircuitDocument source,Action<string> importEnvelope) {
  if(source==null)throw new InvalidDataException("Import or open a circuit with retained OpenQASM source first.");
  document=source;import=importEnvelope;
  var fields=(Dictionary<string,object>)new JavaScriptSerializer {MaxJsonLength=SourceCircuitDocument.MaxDocumentBytes}.DeserializeObject(source.SourceJson);
  entry=(string)fields["Entry"];modules=(bool)fields["ModuleHeaders"];
  Owner=owner;Resources=owner.Resources;Title="OpenQASM source files";Width=720;Height=560;MinWidth=520;MinHeight=480;
  Background=WorkspaceTheme.Background;Foreground=WorkspaceTheme.Text;FontFamily=new FontFamily("Segoe UI");WindowStartupLocation=WindowStartupLocation.CenterOwner;
  var layout=new DockPanel {Margin=new Thickness(20)};Content=layout;
  var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);layout.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Check original source files",FontSize=24,FontWeight=FontWeights.SemiBold,TextWrapping=TextWrapping.Wrap});
  top.Children.Add(new TextBlock {Text="Choose the folder containing the entry file below. Checking compares files with the saved snapshot and leaves your circuit unchanged.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,8)});
  top.Children.Add(new TextBlock {Text="Entry: "+entry,TextTrimming=TextTrimming.CharacterEllipsis,ToolTip=entry,Margin=new Thickness(0,0,0,12)});
  var selection=new DockPanel();top.Children.Add(selection);
  var browse=new Button {Content="Browse…",Margin=new Thickness(8,0,0,0)};DockPanel.SetDock(browse,Dock.Right);selection.Children.Add(browse);selection.Children.Add(root);
  System.Windows.Automation.AutomationProperties.SetName(root,"Source folder");
  browse.Click+=delegate {
   using(var picker=new System.Windows.Forms.FolderBrowserDialog {Description="Select the source root containing "+entry,ShowNewFolderButton=false})
    if(picker.ShowDialog(new DialogOwner(this))==System.Windows.Forms.DialogResult.OK)root.Text=picker.SelectedPath;
  };
  var actions=new WrapPanel {Margin=new Thickness(0,12,0,12)};top.Children.Add(actions);
  var check=new Button {Content="Check files"};var reload=new Button {Content="Reimport from folder",Margin=new Thickness(8,0,0,0)};
  actions.Children.Add(check);actions.Children.Add(reload);
  top.Children.Add(new TextBlock {Text="Reimport replaces the circuit with the current source files, using the original import options. You can undo it in the editor.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,0,0,12)});
  layout.Children.Add(new ScrollViewer {Content=result,VerticalScrollBarVisibility=ScrollBarVisibility.Auto});
  result.Text="No files checked. Select a folder to begin.";
  check.Click+=async delegate {await Run(false);};reload.Click+=async delegate {await Run(true);};
  Closing+=delegate(object sender,System.ComponentModel.CancelEventArgs args) {if(busy)args.Cancel=true;};
 }
 async Task Run(bool reimport) {
  if(busy)return;
  busy=true;IsEnabled=false;
  try {
   if(String.IsNullOrWhiteSpace(root.Text))throw new InvalidDataException("Select a source folder first.");
   string selected=Path.GetFullPath(root.Text);
   result.Text=reimport ? "Compiling current source files…" : "Checking source files…";
   if(reimport) {
    string envelope=await Task.Run(()=>QasmImport.CompileSource(Path.Combine(selected,entry.Replace('/',Path.DirectorySeparatorChar)),document.PublishedU,document.Classical,modules,selected));
    import(envelope);Imported=true;busy=false;Close();
   } else {
    string report=await Task.Run(()=>QasmImport.CheckSource(document.SourceJson,selected));
    result.Text=Describe(report);
   }
  } catch(Exception error) {result.Text=(reimport ? "Could not reimport: " : "Could not check: ")+error.Message;}
  finally {busy=false;IsEnabled=true;}
 }
 internal static string Describe(string json) {
  var data=(Dictionary<string,object>)new JavaScriptSerializer {MaxJsonLength=SourceCircuitDocument.MaxDocumentBytes}.DeserializeObject(json);
  var text=new StringBuilder((bool)data["Unchanged"] ? "All source files match the saved snapshot." : "Source differences found. Your circuit has not changed.");
  foreach(Dictionary<string,object> file in (object[])data["Files"]) {
   string status=(string)file["Status"];
   if(status=="retargeted")status="points to a different file";
   else if(status=="unavailable")status="cannot be checked (inaccessible, outside the folder, or too large)";
   text.Append("\n\n").Append((string)file["Path"]).Append(" · ").Append(status);
  }
  return text.ToString();
 }
 internal static async Task Verify(Window owner,SourceCircuitDocument source,string folder,string report,Action<string> importEnvelope,Func<string> snapshot,Action undo) {
  string before=snapshot();var dialog=new SourceFilesWindow(owner,source,importEnvelope);
  try {
   dialog.Show();
   await dialog.Run(false);
   if(!dialog.result.Text.Contains("Select a source folder") || snapshot()!=before)throw new Exception("Empty selection changed the document.");
   dialog.root.Text=folder;await dialog.Run(false);
   if(!dialog.result.Text.StartsWith("All source files match") || snapshot()!=before)throw new Exception("Unchanged source check failed.");
   dialog.Capture(report+".unchanged.png");
   string helper=Path.Combine(folder,"helper.qasm");
   File.WriteAllText(helper,"gate flip a { h a; }\n",new UTF8Encoding(false));
   await dialog.Run(false);
   if(!dialog.result.Text.Contains("helper.qasm · changed") || snapshot()!=before)throw new Exception("Changed source check modified the circuit.");
   dialog.Capture(report+".changed.png");
   File.Delete(helper);await dialog.Run(false);
   if(!dialog.result.Text.Contains("helper.qasm · missing"))throw new Exception("Missing source not displayed.");
   await dialog.Run(true);
   if(!dialog.result.Text.StartsWith("Could not reimport:") || dialog.Imported || snapshot()!=before)throw new Exception("Failed reimport lost the circuit.");
   dialog.Width=dialog.MinWidth;dialog.Height=dialog.MinHeight;dialog.Capture(report+".minimum.png");
   File.WriteAllText(helper,"gate flip a { h a; }\n",new UTF8Encoding(false));
   await dialog.Run(true);
   if(!dialog.Imported || snapshot()==before)throw new Exception("Reimport did not update the circuit.");
   undo();if(snapshot()!=before)throw new Exception("Reimport undo did not restore the original document.");
  } finally {dialog.Close();}
 }
 // Test-only observation uses real reversible editor operations, never private history state.
 internal sealed class ObservedHistory {
  public string Current {get;set;}
  public List<string> Undo {get;set;}
  public List<string> Redo {get;set;}
 }
 static void Require(bool value,string message) {if(!value)throw new InvalidDataException(message);}
 // Preserve raw evidence. Only the finite unsourced H/X/CNOT CircuitFile subset
 // tolerates member-order differences; source-bearing documents stay byte-exact.
 static bool HasFields(Dictionary<string,object> value,params string[] names) {
  if(value==null || value.Count!=names.Length)return false;
  foreach(string name in names)if(!value.ContainsKey(name))return false;
  return true;
 }
 static Dictionary<string,object> PlainHistory(string text) {
  if(text==null || text.Length>262144)return null;
  try {
   var json=new JavaScriptSerializer {MaxJsonLength=262144,RecursionLimit=128};
   var value=json.DeserializeObject(text) as Dictionary<string,object>;
   // Round-trip identity also rejects duplicate members and alternate number
   // spellings. This exception is only for object member order, not coercion.
   if(!HasFields(value,"Version","Qubits","Steps") || json.Serialize(value)!=text)return null;
   if(!(value["Version"] is int) || (int)value["Version"]!=1 || !(value["Qubits"] is int))return null;
   int count=(int)value["Qubits"];var steps=value["Steps"] as object[];
   if(count<1 || count>25 || steps==null || steps.Length>512)return null;
   foreach(object item in steps) {
    var step=item as Dictionary<string,object>;
    if(!HasFields(step,"Gate","Angle","Wires") || !(step["Gate"] is string) || !(step["Angle"] is string) || (string)step["Angle"]!="")return null;
    string gate=(string)step["Gate"];var wires=step["Wires"] as object[];
    if((gate!="H" && gate!="X" && gate!="CNOT") || wires==null || wires.Length!=(gate=="CNOT" ? 2 : 1))return null;
    var seen=new HashSet<int>();
    foreach(object wire in wires)if(!(wire is int) || (int)wire<0 || (int)wire>=count || !seen.Add((int)wire))return null;
   }
   return value;
  } catch(ArgumentException) {return null;} catch(InvalidOperationException) {return null;}
 }
 static bool HistoryEntryEqual(string left,string right) {
  if(left==right)return true;
  var a=PlainHistory(left);var b=PlainHistory(right);
  if(a==null || b==null || (int)a["Qubits"]!=(int)b["Qubits"])return false;
  var x=(object[])a["Steps"];var y=(object[])b["Steps"];
  if(x.Length!=y.Length)return false;
  for(int i=0;i<x.Length;i++) {
   var first=(Dictionary<string,object>)x[i];var second=(Dictionary<string,object>)y[i];
   if((string)first["Gate"]!=(string)second["Gate"] || (string)first["Angle"]!=(string)second["Angle"])return false;
   var firstWires=(object[])first["Wires"];var secondWires=(object[])second["Wires"];
   if(firstWires.Length!=secondWires.Length)return false;
   for(int j=0;j<firstWires.Length;j++)if((int)firstWires[j]!=(int)secondWires[j])return false;
  }
  return true;
 }
 static bool HistoryChainEqual(List<string> left,List<string> right) {
  if(left.Count!=right.Count)return false;
  for(int i=0;i<left.Count;i++)if(!HistoryEntryEqual(left[i],right[i]))return false;
  return true;
 }
 static bool HistoryEqual(ObservedHistory left,ObservedHistory right) {
  return left.Current==right.Current && HistoryChainEqual(left.Undo,right.Undo) && HistoryChainEqual(left.Redo,right.Redo);
 }
 static ObservedHistory Observe(Func<string> snapshot,Func<bool> undo,Func<bool> redo,int limit) {
  var record=new ObservedHistory {Current=snapshot(),Undo=new List<string>(),Redo=new List<string>()};
  while(undo()) {Require(record.Undo.Count<limit,"Undo history exceeded bound.");record.Undo.Add(snapshot());}
  for(int i=record.Undo.Count-1;i>=0;i--)Require(redo() && HistoryEntryEqual(snapshot(),i==0 ? record.Current : record.Undo[i-1]),"Undo probe could not restore chain.");
  while(redo()) {Require(record.Redo.Count<limit,"Redo history exceeded bound.");record.Redo.Add(snapshot());}
  for(int i=record.Redo.Count-1;i>=0;i--)Require(undo() && HistoryEntryEqual(snapshot(),i==0 ? record.Current : record.Redo[i-1]),"Redo probe could not restore chain.");
  Require(snapshot()==record.Current,"History probe changed current document.");return record;
 }
 internal static async Task VerifyFailures(Window owner,SourceCircuitDocument source,string folder,string report,
  Action<string> importEnvelope,Func<string> snapshot,Func<bool> undo,Func<bool> redo,int limit,
  Action seed,Action<string> save,Action<string> capture) {
  var json=new JavaScriptSerializer {MaxJsonLength=Int32.MaxValue,RecursionLimit=128};
  var records=new Dictionary<string,object>();
  Func<ObservedHistory> probe=()=>Observe(snapshot,undo,redo,limit);
  Action<string,object> record=(stage,value)=>{records.Add(stage,value);File.WriteAllText(report+".history.json",json.Serialize(records),new UTF8Encoding(false));};
  var baseline=probe();record("reopened",baseline);
  seed();string marker=snapshot();Require(marker!=baseline.Current,"Marker did not change document.");
  Require(undo() && snapshot()==baseline.Current,"Marker undo failed.");
  var seeded=probe();record("seeded",seeded);
  Require(HistoryChainEqual(seeded.Undo,baseline.Undo) && seeded.Redo.Count==1 && seeded.Redo[0]==marker,"Marker history differs from baseline.");
  Action<string> preserved=stage=>{var value=probe();record(stage,value);Require(HistoryEqual(value,seeded),stage+" changed document or history.");};
  string wrapper=Path.Combine(folder,"wrapper.inc");string originalWrapper=File.ReadAllText(wrapper,new UTF8Encoding(false,true));
  Require(originalWrapper.EndsWith("gate after a { x a; x a; }\n"),"Unexpected authored wrapper.");
  string module=originalWrapper.StartsWith("include \"nested modules λ/oracle.qasm\";\n") ? "oracle" : "bernvaz";
  string relative="nested modules λ/"+module+".qasm";
  Require(originalWrapper=="include \""+relative+"\";\ngate after a { x a; x a; }\n","Unexpected wrapper graph.");
  string dependency=Path.Combine(folder,relative.Replace('/',Path.DirectorySeparatorChar));byte[] original=File.ReadAllBytes(dependency);
  var dialog=new SourceFilesWindow(owner,source,importEnvelope);
  Action<string> reportText=stage=>File.WriteAllText(report+"."+stage+".txt",dialog.result.Text,new UTF8Encoding(false));
  try {
   dialog.Show();Require(dialog.root.Text=="","Initial root was not blank.");await dialog.Run(false);reportText("blank");
   Require(dialog.result.Text.Contains("Select a source folder first.") && !dialog.Imported,"Blank selection accepted.");preserved("blank");dialog.Capture(report+".blank.png");
   dialog.root.Text=folder;await dialog.Run(false);reportText("unchanged");
   Require(dialog.result.Text.StartsWith("All source files match") && dialog.result.Text.Contains(relative+" · unchanged") && dialog.result.Text.Contains("wrapper.inc · unchanged") && dialog.result.Text.Contains("main κ.qasm · unchanged"),"Unchanged graph check failed.");preserved("unchanged");dialog.Capture(report+".unchanged.png");
   File.Delete(dependency);await dialog.Run(false);reportText("missing-check");Require(dialog.result.Text.Contains(relative+" · missing"),"Missing dependency not identified.");preserved("missing-check");
   await dialog.Run(true);reportText("missing-reimport");Require(!dialog.Imported && dialog.result.Text.StartsWith("Could not reimport:"),"Missing dependency import did not fail.");preserved("missing-reimport");
   dialog.Width=dialog.MinWidth;dialog.Height=dialog.MinHeight;dialog.Capture(report+".missing.png");
   File.WriteAllBytes(dependency,original);Require(Convert.ToBase64String(File.ReadAllBytes(dependency))==Convert.ToBase64String(original),"Module restoration changed bytes.");
   await dialog.Run(false);reportText("restored");Require(dialog.result.Text.StartsWith("All source files match"),"Restored graph did not match.");preserved("restored");
   File.WriteAllText(wrapper,originalWrapper.Replace("x a; x a;","x a;"),new UTF8Encoding(false));
   await dialog.Run(false);reportText("changed");Require(dialog.result.Text.Contains("wrapper.inc · changed") && dialog.result.Text.Contains(relative+" · unchanged") && dialog.result.Text.Contains("main κ.qasm · unchanged"),"Changed wrapper report failed.");preserved("changed");
   dialog.Width=720;dialog.Height=560;dialog.Capture(report+".changed.png");await dialog.Run(true);reportText("reimport");
   Require(dialog.Imported && snapshot()!=baseline.Current,"Successful reimport did not change document.");
   var replaced=probe();record("reimported",replaced);var expectedUndo=new List<string> {baseline.Current};expectedUndo.AddRange(baseline.Undo);
   Require(replaced.Redo.Count==0 && HistoryChainEqual(replaced.Undo,expectedUndo),"Reimport history transition incorrect.");
   save(report+".reimported.qcircuit");capture(report+".reimported.png");
   Require(undo() && snapshot()==baseline.Current,"Reimport undo did not restore exact document.");var undone=probe();record("undone",undone);
   Require(HistoryChainEqual(undone.Undo,baseline.Undo) && undone.Redo.Count==1 && undone.Redo[0]==replaced.Current,"Undo history transition incorrect.");
   Require(redo(),"Reimport redo unavailable.");var redone=probe();record("redone",redone);Require(HistoryEqual(redone,replaced),"Redo did not restore full history.");
   Require(undo(),"Final undo unavailable.");var final=probe();record("final",final);Require(HistoryEqual(final,undone),"Final undo changed history.");
   save(report+".undone.qcircuit");capture(report+".undone.png");
   var fresh=new SourceFilesWindow(owner,source,importEnvelope);try {fresh.Show();Require(fresh.root.Text=="","Fresh dialog reused selected root.");}finally {fresh.Close();}
   record("fresh-root",true);
  } finally {File.WriteAllBytes(dependency,original);dialog.Close();}
 }
 void Capture(string path) {
  UpdateLayout();
  var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);
  bitmap.Render(this);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();
  encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
  using(var file=File.Create(path))encoder.Save(file);
 }
}

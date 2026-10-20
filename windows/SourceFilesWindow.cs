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
 void Capture(string path) {
  UpdateLayout();
  var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);
  bitmap.Render(this);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();
  encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
  using(var file=File.Create(path))encoder.Save(file);
 }
}

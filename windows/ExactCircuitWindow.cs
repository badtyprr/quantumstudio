// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

sealed class ExactCircuitWindow : Window {
 readonly ClassicalCircuit circuit;
 readonly Button run=new Button {Content="Calculate exact",IsDefault=true,Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};
 readonly Button cancel=new Button {Content="Cancel",IsEnabled=false},copy=new Button {Content="Copy results",IsEnabled=false},save=new Button {Content="Save results…",IsEnabled=false};
 readonly TextBlock status=new TextBlock {Text="Ready · This window holds a snapshot of your circuit.",TextWrapping=TextWrapping.Wrap};
 readonly StackPanel rows=new StackPanel();
 CancellationTokenSource cancellation;
 ExactCircuit.Result result;
 bool closed;
 public ExactCircuitWindow(Window owner,ClassicalCircuit captured) {
  circuit=captured;Owner=owner;Resources=owner.Resources;Title="Exact circuit probabilities";
  Width=820;Height=650;MinWidth=600;MinHeight=430;WindowStartupLocation=WindowStartupLocation.CenterOwner;
  Background=WorkspaceTheme.Background;Foreground=WorkspaceTheme.Text;FontFamily=new FontFamily("Segoe UI");
  var root=new DockPanel {Margin=new Thickness(24)};Content=root;
  var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);root.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Exact circuit probabilities",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text=circuit.Qubits+" qubits · "+circuit.ClassicalBits+" classical bits · Fractions and symbolic parameters",Margin=new Thickness(0,6,0,12),TextWrapping=TextWrapping.Wrap});
  var controls=new WrapPanel();top.Children.Add(controls);foreach(var button in new[]{run,cancel,copy,save})controls.Children.Add(button);
  var names=circuit.Snapshot().Registers.SelectMany(r=>Enumerable.Range(0,r.Size).Select(bit=>r.Name+"["+bit+"]")).ToArray();
  string order=circuit.OutputBits.Length==0 ? "No output bits selected: the result is total probability." : "Output order: "+String.Join(", ",circuit.OutputBits.Select(bit=>names[bit]))+".";
  top.Children.Add(new TextBlock {Text=order+" Measurements save their outcomes; reset preserves those saved bits. No final measurements are added.",TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,10,0,12)});
  status.Margin=new Thickness(0,0,0,12);DockPanel.SetDock(status,Dock.Top);root.Children.Add(status);
  root.Children.Add(new Border {Background=WorkspaceTheme.Surface,CornerRadius=new CornerRadius(10),Padding=new Thickness(16),Child=new ScrollViewer {VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled,Content=rows}});
  run.Click+=async delegate {await Calculate();};
  cancel.Click+=delegate {if(cancellation!=null)cancellation.Cancel();};
  Closed+=delegate {closed=true;if(cancellation!=null)cancellation.Cancel();};
  copy.Click+=delegate {try {Clipboard.SetText(CopyText());status.Text="Copied all "+result.probabilities.Count+" exact probabilities.";}catch(Exception error){status.Text="Could not copy results: "+error.Message;}};
  save.Click+=delegate {Save();};
 }
 async Task Calculate() {
  if(cancellation!=null || closed)return;
  result=null;rows.Children.Clear();run.IsEnabled=false;copy.IsEnabled=false;save.IsEnabled=false;cancel.IsEnabled=true;
  cancellation=new CancellationTokenSource();status.Text="Calculating exact probabilities… · Cancel is available.";
  try {
   var calculated=await ExactCircuit.Run(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"quantum-worker.exe"),circuit,cancellation.Token);
   if(closed)return;result=calculated;Render();copy.IsEnabled=true;save.IsEnabled=true;
  }catch(OperationCanceledException){if(!closed)status.Text="Calculation cancelled. You can run it again.";}
  catch(Exception error){if(!closed)status.Text=error.Message;}
  finally {cancellation.Dispose();cancellation=null;if(!closed){run.IsEnabled=true;cancel.IsEnabled=false;}}
 }
 void Render() {
  rows.Children.Clear();
  foreach(var item in result.probabilities.OrderBy(pair=>pair.Key,StringComparer.Ordinal).Take(128)) {
   var row=new StackPanel {Margin=new Thickness(0,0,0,16)};
   row.Children.Add(new TextBlock {Text=item.Key.Length==0 ? "Total probability" : "Record "+item.Key,Foreground=WorkspaceTheme.Muted,TextWrapping=TextWrapping.Wrap});
   row.Children.Add(new TextBox {Text=item.Value,IsReadOnly=true,TextWrapping=TextWrapping.Wrap,FontFamily=new FontFamily("Cambria Math"),FontSize=23,BorderThickness=new Thickness(0),Background=Brushes.Transparent,Foreground=WorkspaceTheme.Text,Padding=new Thickness(0,5,0,5)});
   rows.Children.Add(row);
  }
  status.Text=result.probabilities.Count+" exact outcomes · "+(result.probabilities.Count>128 ? "Showing the first 128. Copy or save includes all outcomes." : "Symbolic parameters remain unevaluated; proven zero outcomes are omitted.");
 }
 string CopyText() {return "record\tprobability\r\n"+String.Join("\r\n",result.probabilities.OrderBy(pair=>pair.Key,StringComparer.Ordinal).Select(pair=>pair.Key+"\t"+pair.Value));}
 string Json() {return new JavaScriptSerializer {MaxJsonLength=16000000,RecursionLimit=128}.Serialize(new {Circuit=circuit.Snapshot(),Result=result});}
 void Save() {
  if(result==null)return;
  var picker=new Microsoft.Win32.SaveFileDialog {Filter="Exact circuit results (*.json)|*.json",DefaultExt=".json",AddExtension=true,FileName="Exact circuit probabilities.json",OverwritePrompt=true};
  if(picker.ShowDialog(this)!=true)return;
  string temp=picker.FileName+"."+Guid.NewGuid().ToString("N")+".tmp";
  try {File.WriteAllText(temp,Json(),new UTF8Encoding(false));if(File.Exists(picker.FileName))File.Replace(temp,picker.FileName,null);else File.Move(temp,picker.FileName);status.Text="Saved all probabilities and the captured circuit.";}
  catch(Exception error){status.Text="Could not save results: "+error.Message;}
  finally {if(File.Exists(temp))File.Delete(temp);}
 }
 public async Task Verify(string report) {
  await Calculate();
  if(result==null || !run.IsEnabled || cancel.IsEnabled || !copy.IsEnabled || !save.IsEnabled || rows.Children.Count!=Math.Min(128,result.probabilities.Count))throw new Exception("Exact results were not displayed: "+status.Text);
  File.WriteAllText(report+".json",Json());File.WriteAllText(report+".tsv",CopyText());Capture(report+".png");
  Width=MinWidth;Height=MinHeight;Capture(report+".minimum.png");
 }
 void Capture(string path) {
  UpdateLayout();var image=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);image.Render(this);
  var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(image));using(var file=File.Create(path))encoder.Save(file);
 }
}

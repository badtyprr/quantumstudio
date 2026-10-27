// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

sealed class SamplingWindow : Window {
 readonly int qubits;
 readonly ClassicalCircuit classical;
 readonly IList<NumericalSampling.Gate> gates;
 readonly TextBox shots=new TextBox {Text="10000",Width=105}, seed=new TextBox {Text="7",Width=180};
 readonly Button run=new Button {Content="Run samples",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};
 readonly Button cancel=new Button {Content="Cancel",IsEnabled=false}, save=new Button {Content="Save counts…",IsEnabled=false};
 readonly TextBlock status=new TextBlock {Text="Ready · The circuit is captured when this window opens.",TextWrapping=TextWrapping.Wrap};
 readonly StackPanel rows=new StackPanel();
 readonly SamplingReadout readout=new SamplingReadout();
 NumericalSampling.Readout[] resultReadout=new NumericalSampling.Readout[0];
 CancellationTokenSource cancellation;
 NumericalSampling.Result result;
 public SamplingWindow(Window owner,int count,IList<NumericalSampling.Gate> circuit) : this(owner,count,circuit,null) {}
 public SamplingWindow(Window owner,ClassicalCircuit circuit) : this(owner,circuit.Qubits,circuit.SamplingGates(),circuit) {}
 SamplingWindow(Window owner,int count,IList<NumericalSampling.Gate> circuit,ClassicalCircuit program) {
  classical=program;
  Owner=owner;Resources=owner.Resources;qubits=count;gates=circuit;Title="Circuit samples";
  Width=780;Height=800;MinWidth=600;MinHeight=420;WindowStartupLocation=WindowStartupLocation.CenterOwner;
  Background=WorkspaceTheme.Background;Foreground=WorkspaceTheme.Text;FontFamily=new FontFamily("Segoe UI");
  var root=new DockPanel {Margin=new Thickness(24)};Content=root;
  var top=new StackPanel();var settings=new ScrollViewer {Content=top,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,MaxHeight=360};DockPanel.SetDock(settings,Dock.Top);root.Children.Add(settings);
  SizeChanged+=delegate {settings.MaxHeight=Math.Max(180,ActualHeight*0.65);};
  top.Children.Add(new TextBlock {Text="Sample the circuit",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text=count+" qubits · "+(classical==null ? circuit.Count+" operations · Final computational-basis outcomes" : classical.ClassicalBits+" classical bits · Saved measurement outcomes"),Margin=new Thickness(0,6,0,12),TextWrapping=TextWrapping.Wrap});
  var controls=new WrapPanel();top.Children.Add(controls);
  Field(controls,"Shots (1–100,000)",shots);Field(controls,"Seed",seed);controls.Children.Add(run);controls.Children.Add(cancel);controls.Children.Add(save);
  top.Children.Add(new TextBlock {Text=classical==null ? "Bits read left to right: q0, q1, … . Frequencies estimate probabilities; they vary with the seed. Sampling starts from |0…0⟩. Noise, measurements, and resets run on each shot; feedback measures its control wires at that step." : ClassicalDescription(classical),TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,12)});
  // Explicit classical programs contain their own readout operations.
  if(classical==null)top.Children.Add(readout);status.Margin=new Thickness(0,0,0,12);DockPanel.SetDock(status,Dock.Top);root.Children.Add(status);
  root.Children.Add(new Border {Background=WorkspaceTheme.Surface,CornerRadius=new CornerRadius(10),Padding=new Thickness(14),Child=new ScrollViewer {VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Auto,Content=rows}});
  run.Click+=async delegate {
   int shotCount;ulong seedValue;
   if(!Int32.TryParse(shots.Text,NumberStyles.None,CultureInfo.InvariantCulture,out shotCount) || shotCount<1 || shotCount>100000 || !UInt64.TryParse(seed.Text,NumberStyles.None,CultureInfo.InvariantCulture,out seedValue)) {status.Text="Enter 1–100,000 shots and a nonnegative 64-bit integer seed.";return;}
   NumericalSampling.Readout[] model;try {model=readout.Capture(qubits);}catch(ArgumentException error) {status.Text=error.Message;return;}
   run.IsEnabled=false;shots.IsEnabled=false;seed.IsEnabled=false;cancel.IsEnabled=true;save.IsEnabled=false;result=null;rows.Children.Clear();
   readout.IsEnabled=false;cancellation=new CancellationTokenSource();status.Text="Sampling… · Up to five minutes · Cancel is available.";
   try {
    string worker=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"quantum-worker.exe");
    result=classical==null ? await NumericalSampling.Run(worker,qubits,shotCount,seedValue,Enumerable.Range(0,qubits).ToArray(),gates,cancellation.Token,model) : await NumericalSampling.RunClassical(worker,qubits,classical.ClassicalBits,shotCount,seedValue,classical.OutputBits,gates,cancellation.Token,classical.VariableTypes,classical.LoopConditionBudget,classical.NumericTypes);
    resultReadout=model;
    Render();save.IsEnabled=true;
   } catch(OperationCanceledException) {status.Text="Sampling cancelled. Change the settings or run again.";}
   catch(Exception error) {status.Text=error.Message;}
   finally {cancellation.Dispose();cancellation=null;run.IsEnabled=true;shots.IsEnabled=true;seed.IsEnabled=true;readout.IsEnabled=true;cancel.IsEnabled=false;}
  };
  cancel.Click+=delegate {if(cancellation!=null)cancellation.Cancel();};
  Closed+=delegate {if(cancellation!=null)cancellation.Cancel();};
  save.Click+=delegate {
   if(result==null)return;
   var picker=new Microsoft.Win32.SaveFileDialog {Filter="JSON counts and settings (*.json)|*.json|CSV counts and settings (*.csv)|*.csv",DefaultExt=".json",AddExtension=true,FileName="Circuit samples.json",OverwritePrompt=true};
   if(picker.ShowDialog(this)!=true)return;
   try {
    File.WriteAllText(picker.FileName,picker.FilterIndex==2 ? SamplingExport.Csv(result,resultReadout,classical) : SamplingExport.Json(result,resultReadout,classical),new UTF8Encoding(false));status.Text="Saved all "+result.counts.Count+" observed outcomes and captured readout settings.";
   } catch(Exception error) {status.Text="Could not save counts: "+error.Message;}
  };
 }
 internal static string ClassicalDescription(ClassicalCircuit circuit) {
  var names=new List<string>();foreach(var register in circuit.Snapshot().Registers)for(int bit=0;bit<register.Size;bit++)names.Add(register.Name+"["+bit+"]");
  return (circuit.OutputBits.Length==0 ? "No output bits selected. An empty record is shown for each shot." : "Bits read left to right: "+String.Join(", ",circuit.OutputBits.Select(bit=>names[bit]))+".")+" Classical bits start at zero; measurements save to their declared destinations. Conditions read the saved bits. No final measurements are added. Frequencies estimate probabilities and vary with the seed.";
 }
 public async System.Threading.Tasks.Task<NumericalSampling.Result> VerifySampling(string screenshot,bool expectBell=true,ulong seedValue=7,string readoutBits=null,string readoutMatrix=null) {
  if(readoutBits!=null)readout.SetAssignment(readoutBits,readoutMatrix);
  seed.Text=seedValue.ToString(CultureInfo.InvariantCulture);
  run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  if(run.IsEnabled || !cancel.IsEnabled)throw new Exception("Sampling did not enter its running state.");
  var deadline=DateTime.UtcNow.AddSeconds(expectBell ? 30 : 300);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await System.Threading.Tasks.Task.Delay(50);
  if(!run.IsEnabled || result==null || result.shots!=10000 || result.seed!=seedValue.ToString(CultureInfo.InvariantCulture) || result.qubits!=qubits ||
     rows.Children.Count!=Math.Min(128,result.counts.Count) || !save.IsEnabled || cancel.IsEnabled ||
     (expectBell && (result.counts.Count!=2 || !result.counts.ContainsKey("00") || !result.counts.ContainsKey("11"))))
   throw new Exception("Sampling window did not display the expected results: "+status.Text);
  UpdateLayout();
  var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(this);
  var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
  using(var file=File.Create(screenshot))encoder.Save(file);
  if(readoutBits!=null || classical!=null) {
   File.WriteAllText(screenshot+".json",SamplingExport.Json(result,resultReadout,classical));
   File.WriteAllText(screenshot+".csv",SamplingExport.Csv(result,resultReadout,classical));
  }
  return result;
 }
 static void Field(Panel panel,string label,Control input) {
  var field=new StackPanel {Margin=new Thickness(0,0,12,0)};field.Children.Add(new TextBlock {Text=label,Margin=new Thickness(0,0,0,4)});field.Children.Add(input);panel.Children.Add(field);
  System.Windows.Automation.AutomationProperties.SetName(input,label);
 }
 void Render() {
  rows.Children.Clear();
  status.Text=result.shots.ToString("N0")+" shots · "+result.counts.Count+" outcomes · Seed "+result.seed+(result.counts.Count>128 ? " · Showing the 128 most frequent; Save counts exports all." : "");
  if(resultReadout.Length>0)status.Text+=" · Final readout error applied";
  foreach(var item in result.counts.OrderByDescending(pair=>pair.Value).ThenBy(pair=>pair.Key,StringComparer.Ordinal).Take(128)) {
   var line=new Grid {Margin=new Thickness(0,5,0,5)};
   line.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(Math.Max(110,item.Key.Length*12))});line.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(80)});line.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(85)});line.ColumnDefinitions.Add(new ColumnDefinition {MinWidth=80});
   var bits=new TextBlock {Text=item.Key.Length==0 ? "(empty)" : item.Key,FontFamily=new FontFamily("Consolas"),FontSize=18};line.Children.Add(bits);
   var count=new TextBlock {Text=item.Value.ToString("N0"),VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(count,1);line.Children.Add(count);
   var frequency=new TextBlock {Text=((double)item.Value/result.shots).ToString("P2"),VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(frequency,2);line.Children.Add(frequency);
   var bar=new ProgressBar {Minimum=0,Maximum=result.shots,Value=item.Value,Height=8,Foreground=WorkspaceTheme.Accent,Background=WorkspaceTheme.Border,BorderThickness=new Thickness(0)};Grid.SetColumn(bar,3);line.Children.Add(bar);rows.Children.Add(line);
  }
 }
}

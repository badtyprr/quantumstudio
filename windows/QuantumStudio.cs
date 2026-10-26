// GPL-2.0-or-later; see COPYING.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Markup;
using System.Windows.Media;
using System.Web.Script.Serialization;

class QuantumStudio {
 static Window window;
 static TextBox input, output;
 static string copyText;
 static TextBlock status, resultLabel;
 static Button run, cancel;
 static CancellationTokenSource calculationCancellation;
 static ComboBox mode, evaluation, timeAllowance;
 static ListBox history;
 static StateDefinition[] states=new StateDefinition[0];
 static MatrixDeclaration[] matrices=new MatrixDeclaration[0];
 static BasisDeclaration[] bases=new BasisDeclaration[0];
 static void RefreshStates() {Find<Button>("EditStates").Content="States · "+states.Length;Find<Button>("EditMatrices").Content="Matrices · "+matrices.Length;Find<Button>("EditBases").Content="Bases · "+bases.Length;}
 static Window BasisEditor() {return BasisDeclarationEditor.Create(window,bases,delegate(BasisDeclaration[] applied) {bases=applied;RefreshStates();status.Text="Bases updated · Calculate to evaluate; Save session to keep them.";});}
 static Window MatrixEditor() {return MatrixDeclarationEditor.Create(window,matrices,delegate(MatrixDeclaration[] applied) {matrices=applied;RefreshStates();status.Text="Matrix dimensions updated · Calculate to evaluate; Save session to keep them.";});}
 static Window StateEditor() {
  return NamedStateEditor.Create(window,states,delegate(StateDefinition[] applied) {
   states=applied;RefreshStates();
   status.Text="State definitions updated · Calculate to evaluate; Save session to keep them.";
  });
 }
 static ScrollViewer matrixView;
 static Grid matrixCells;
 static TextBlock matrixCaption;
 static StackPanel probabilityView;
 static StackPanel blochView;
 static double blochAngle=Math.PI/4;
 static bool binaryProbabilityLabels;
 public class ExampleEntry {
  public string category {get;set;}
  public string title {get;set;}
  public string description {get;set;}
  public string expression {get;set;}
  public string expected {get;set;}
 }
 static ExampleEntry[] examples;
 static Window ExamplesWindow() {
  var dialog=new Window {Title="Explore quantum examples", Owner=window, Width=740, Height=650, MinWidth=540, MinHeight=430, WindowStartupLocation=WindowStartupLocation.CenterOwner, Background=WorkspaceTheme.Background, FontFamily=new FontFamily("Segoe UI")};
  dialog.Resources=window.Resources;
  var panel=new DockPanel {Margin=new Thickness(24)}; dialog.Content=panel;
  var heading=new TextBlock {Text="Choose an experiment",FontSize=25,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,0,0,16)}; DockPanel.SetDock(heading,Dock.Top); panel.Children.Add(heading);
  var searchLabel=new TextBlock {Text="Search by topic, title, or notation",FontSize=12,Margin=new Thickness(0,0,0,6)}; DockPanel.SetDock(searchLabel,Dock.Top); panel.Children.Add(searchLabel);
  var search=new TextBox {FontSize=16,Padding=new Thickness(10),Margin=new Thickness(0,0,0,16),ToolTip="Search titles, topics, or notation"};
  System.Windows.Automation.AutomationProperties.SetName(search,"Search examples"); DockPanel.SetDock(search,Dock.Top); panel.Children.Add(search);
  var use=new Button {Content="Use selected example →",Padding=new Thickness(18,10,18,10),Margin=new Thickness(0,16,0,0),HorizontalAlignment=HorizontalAlignment.Right}; DockPanel.SetDock(use,Dock.Bottom); panel.Children.Add(use);
  var list=new ListBox {BorderThickness=new Thickness(0),Background=Brushes.Transparent}; ScrollViewer.SetHorizontalScrollBarVisibility(list,ScrollBarVisibility.Disabled); panel.Children.Add(list);
  dialog.Tag=new object[] {search,list,use};
  Action refresh=delegate {
   list.Items.Clear(); string query=search.Text.Trim(); string category="";
   foreach(var example in examples) {
    if((example.category+" "+example.title+" "+example.description+" "+example.expression).IndexOf(query,StringComparison.OrdinalIgnoreCase)<0) continue;
    if(category!=example.category) {category=example.category; list.Items.Add(new ListBoxItem {IsEnabled=false,Content=new TextBlock {Text=category.ToUpperInvariant(),FontSize=11,FontWeight=FontWeights.SemiBold,Margin=new Thickness(4,12,4,5)}});}
    var content=new StackPanel {Margin=new Thickness(6)};
    content.Children.Add(new TextBlock {Text=example.title,FontSize=17,FontWeight=FontWeights.SemiBold});
    content.Children.Add(new TextBlock {Text=example.description,FontSize=13,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,4,0,4)});
    content.Children.Add(new TextBlock {Text=example.expression,FontSize=17,FontFamily=new FontFamily("Cambria Math"),TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Accent});
    list.Items.Add(new ListBoxItem {Content=content,Tag=example,HorizontalContentAlignment=HorizontalAlignment.Stretch});
   }
   if(list.Items.Count==0) list.Items.Add(new ListBoxItem {IsEnabled=false,Content="No matching examples. Try another topic."});
   use.IsEnabled=false;
  };
  Action choose=delegate {var item=list.SelectedItem as ListBoxItem; var example=item==null ? null : item.Tag as ExampleEntry; if(example==null)return; mode.SelectedIndex=0; input.Text=example.expression; status.Text=example.description; dialog.Close(); input.Focus();};
  search.TextChanged+=delegate {refresh();}; list.SelectionChanged+=delegate {var item=list.SelectedItem as ListBoxItem; use.IsEnabled=item!=null && item.Tag is ExampleEntry;};
  use.Click+=delegate {choose();}; list.MouseDoubleClick+=delegate {choose();}; list.KeyDown+=delegate(object sender,KeyEventArgs e) {if(e.Key==Key.Enter){e.Handled=true;choose();}};
  refresh(); dialog.Loaded+=delegate {search.Focus();}; return dialog;
 }
 public class CalculationResult {
  public string text {get;set;}
  public string display_text {get;set;}
  public string copy_text {get;set;}
  public bool approximate {get;set;}
  public int rows {get;set;}
  public int columns {get;set;}
  public string[][] cells {get;set;}
  public double[] probabilities {get;set;}
  public double[] bloch {get;set;}
 }
 static Process active;
 static Task<string[]> runningWorker;
 static string root = AppDomain.CurrentDomain.BaseDirectory;
 static T Find<T>(string name) where T : class { return window.FindName(name) as T; }
 [STAThread] static void Main(string[] args) {
  var app = new Application();
  WorkspaceTheme.Install(app);
  using(var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("MainWindow.xaml")) window = (Window)XamlReader.Load(stream);
  input=Find<TextBox>("Input"); output=Find<TextBox>("Output"); status=Find<TextBlock>("Status"); resultLabel=Find<TextBlock>("ResultLabel");
  run=Find<Button>("Run"); mode=Find<ComboBox>("Mode"); history=Find<ListBox>("History");
  evaluation=Find<ComboBox>("Evaluation");
  timeAllowance=Find<ComboBox>("TimeAllowance");cancel=Find<Button>("Cancel");
  cancel.Click+=delegate {if(calculationCancellation!=null){calculationCancellation.Cancel();cancel.IsEnabled=false;status.Text="Stopping calculation…";}};
  matrixView=Find<ScrollViewer>("MatrixView"); matrixCells=Find<Grid>("MatrixCells"); matrixCaption=Find<TextBlock>("MatrixCaption");
  probabilityView=Find<StackPanel>("ProbabilityView");
  blochView=new StackPanel {Visibility=Visibility.Collapsed,Margin=new Thickness(0,20,0,0)};((Panel)probabilityView.Parent).Children.Add(blochView);
  using(var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("examples.json"))) examples=new JavaScriptSerializer().Deserialize<ExampleEntry[]>(reader.ReadToEnd());
  Find<Button>("BrowseExamples").Click+=delegate {ExamplesWindow().ShowDialog();};
  Find<Button>("EditStates").Click+=delegate {if(run.IsEnabled)StateEditor().ShowDialog();};
  Find<Button>("EditMatrices").Click+=delegate {if(run.IsEnabled)MatrixEditor().ShowDialog();};
  Find<Button>("EditBases").Click+=delegate {if(run.IsEnabled)BasisEditor().ShowDialog();};
  Find<Button>("ComposeCircuit").Click+=delegate {new CircuitComposer(window,delegate(string value) {mode.SelectedIndex=0;input.Text=value;input.Focus();}).ShowDialog();};
  run.Click += async delegate { await Calculate(); };
  input.PreviewKeyDown += async delegate(object sender, KeyEventArgs e) {
   if(e.Key==Key.Enter && (Keyboard.Modifiers==ModifierKeys.None || Keyboard.Modifiers==ModifierKeys.Control)) {
    e.Handled=true;
    if(!e.IsRepeat) await Calculate();
   }
  };
  Find<Button>("Copy").Click += delegate { try { Clipboard.SetText(copyText ?? output.Text); status.Text="Result copied."; } catch(Exception ex) { status.Text=ex.Message; } };
  Find<Button>("Clear").Click += delegate { history.Items.Clear(); };
  Find<Button>("SaveSession").Click+=delegate {
   if(!run.IsEnabled)return;
   var dialog=new Microsoft.Win32.SaveFileDialog {Filter="Quantum Studio session (*.qsession)|*.qsession",DefaultExt=".qsession",AddExtension=true,FileName="quantum-session.qsession"};
   if(dialog.ShowDialog(window)!=true)return;
   try {SessionStore.Save(dialog.FileName,CaptureSession());status.Text="Session saved · "+Path.GetFileName(dialog.FileName);}catch(Exception ex){status.Text=ex.Message;}
  };
  Find<Button>("OpenSession").Click+=delegate {
   if(!run.IsEnabled)return;
   var dialog=new Microsoft.Win32.OpenFileDialog {Filter="Quantum Studio session (*.qsession)|*.qsession",CheckFileExists=true};
   if(dialog.ShowDialog(window)!=true)return;
   try {OpenSession(dialog.FileName);}catch(Exception ex){status.Text=ex.Message;}
  };
  Find<Button>("Guide").Click += delegate { try { Process.Start(Path.Combine(root,"Notation-guide.html")); } catch(Exception ex) { status.Text=ex.Message; } };
  Example("Bell", "CNOT (H ⊗ I) |00⟩");
  Example("Overlap", "⟨+|0⟩");
  Example("Reduced", "ptrace(density((|00⟩ + |11⟩)/sqrt(2)), 1)");
  Example("Gates", "H† H");
  Example("Phase", "<i|Y|i>");
  Example("Grover", "probs((2 density(|+⟩ ⊗ |+⟩) - (I ⊗ I)) CZ (H ⊗ H) |00⟩)");
  Example("Fourier", "QFT(2) |01⟩");
  foreach(string symbol in new [] {"|0⟩", "|1⟩", "|+⟩", "⟨0|", "⊗", "†", "H", "X", "Y", "Z", "π", "√"}) {
   var button=new Button {Content=symbol, Padding=new Thickness(10,6,10,6), FontFamily=new FontFamily("Cambria Math"), ToolTip="Insert "+symbol};
   string text=symbol; button.Click += delegate { input.SelectedText=text; input.CaretIndex += text.Length; input.Focus(); };
   Find<WrapPanel>("Palette").Children.Add(button);
  }
  window.Closed += delegate {
   if(calculationCancellation!=null)calculationCancellation.Cancel();
   // Wait only for background cleanup, never for the UI continuation.
   if(runningWorker!=null)try {runningWorker.GetAwaiter().GetResult();}catch {}
  };
  // Reproducible off-screen render for layout verification; also checks XAML loading.
  if((args.Length==3 || (args.Length==4 && args[3]=="--published-u")) && args[0]=="--qasm-import-test") {
   window.Show();var composer=new CircuitComposer(window,delegate(string value) {});
   try {
    string previous=composer.Expression();
    composer.LoadCircuit(QasmImport.Compile(args[1],args.Length==4));string imported=composer.Expression();
    if(!composer.Undo() || composer.Expression()!=previous || !composer.Redo() || composer.Expression()!=imported)throw new InvalidDataException("Import undo/redo failed.");
    composer.SaveCircuit(args[2]+".qcircuit");composer.OpenCircuit(args[2]+".qcircuit");
    if(composer.Expression()!=imported)throw new InvalidDataException("Import save/open failed.");
    try {composer.LoadCircuit("{\"Version\":1,\"Qubits\":2,\"Steps\":[{\"Gate\":\"unsupported\",\"Wires\":[0]}]}");throw new Exception("Accepted invalid import.");}catch(InvalidDataException){}
    if(composer.Expression()!=imported)throw new InvalidDataException("Invalid import changed circuit.");
    File.WriteAllText(args[2]+".expression",imported);File.WriteAllText(args[2]+".qasm",composer.OpenQasm());
    File.WriteAllText(args[2]+".txt","PASS: bundled compiler import, undo/redo, save/open and invalid-input preservation.");
   }catch(Exception ex){File.WriteAllText(args[2]+".txt",ex.ToString());Environment.ExitCode=1;}
   composer.Close();window.Close();return;
  }
  if(args.Length==2 && args[0]=="--circuit-layout-test") {
   window.Show();var dialog=new CircuitComposer(window,delegate(string value) {});
   try {dialog.VerifyLayout();File.WriteAllText(args[1],"PASS: responsive circuit layout, expanded details, zoom, fit, scrolling, and expression preservation at three window sizes.");}
   catch(Exception ex){File.WriteAllText(args[1],ex.ToString());Environment.ExitCode=1;}
   dialog.Close();window.Close();return;
  }
  if((args.Length==2 || args.Length==3 || (args.Length==4 && (args[3]=="--fit" || args[3]=="--schmidt"))) && args[0]=="--circuit-preview") {
   window.Show(); var dialog=new CircuitComposer(window,delegate(string value) {});
   if(args.Length>=3) dialog.OpenCircuit(args[2]);
   dialog.Show(); dialog.UpdateLayout();
   if(args.Length==4) {if(args[3]=="--fit")dialog.FitWires();else dialog.SelectSchmidtPartition("0");dialog.UpdateLayout();}
   var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)dialog.ActualWidth,(int)dialog.ActualHeight,96,96,PixelFormats.Pbgra32);
   bitmap.Render(dialog); var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder(); encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
   using(var file=File.Create(args[1])) encoder.Save(file); dialog.Close(); window.Close(); return;
  }
  if(args.Length==2 && (args[0]=="--css-circuit-test" || args[0]=="--css-encoder-circuit-test")) {
   window.Show();var composer=new CircuitComposer(window,delegate(string value) {});
   try {if(args[0]=="--css-circuit-test")CssCircuitTests.Run(composer,args[1]);else CssEncoderCircuitTests.Run(composer,args[1]);}catch(Exception ex){File.WriteAllText(args[1]+".txt",ex.ToString());Environment.ExitCode=1;}
   composer.Close();window.Close();return;
  }
  if(args.Length==2 && (args[0]=="--linear-map-preview" || args[0]=="--css-state-preview" || args[0]=="--css-encoder-preview")) {
   window.Show();var composer=new CircuitComposer(window,delegate(string value) {});composer.Show();var dialog=args[0]=="--css-encoder-preview" ? composer.CssEncoderDialog() : args[0]=="--css-state-preview" ? composer.CssStateDialog() : composer.LinearMapDialog();dialog.Show();dialog.UpdateLayout();
   var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)dialog.ActualWidth,(int)dialog.ActualHeight,96,96,PixelFormats.Pbgra32);
   bitmap.Render(dialog);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
   using(var file=File.Create(args[1]))encoder.Save(file);dialog.Close();composer.Close();window.Close();return;
  }
  if(args.Length==2 && args[0]=="--examples-preview") {
   window.Show(); var dialog=ExamplesWindow(); dialog.Show(); dialog.UpdateLayout();
   var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)dialog.ActualWidth,(int)dialog.ActualHeight,96,96,PixelFormats.Pbgra32);
   bitmap.Render(dialog); var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder(); encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
   using(var file=File.Create(args[1])) encoder.Save(file); dialog.Close(); window.Close(); return;
  }
  if(args.Length==2 && (args[0]=="--render" || args[0]=="--render-compact")) {
   if(args[0]=="--render-compact") {window.Width=window.MinWidth;window.Height=window.MinHeight;}
   window.Show(); window.UpdateLayout();
   var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);
   bitmap.Render(window); var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder(); encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
   using(var file=File.Create(args[1])) encoder.Save(file); window.Close(); return;
  }
  if(args.Length==2 && (args[0]=="--probability-preview" || args[0]=="--binary-probability-preview" || args[0]=="--bloch-preview")) {
   window.Height=1050;window.Loaded+=async delegate {
    binaryProbabilityLabels=args[0]=="--binary-probability-preview";
    input.Text=args[0]=="--bloch-preview" ? "bloch(channel(density(|i⟩),amplitude_damping(3/4)))" : binaryProbabilityLabels ? "probs(|001⟩)" : "probs((|00⟩+|11⟩)/sqrt(2))";await Calculate();window.UpdateLayout();
    var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);
    bitmap.Render(window);var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder();encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
    using(var file=File.Create(args[1]))encoder.Save(file);window.Close();
   };
  }
  if(args.Length==2 && args[0]=="--enter-key-test") {
   window.Loaded+=async delegate {
    try {
     mode.SelectedIndex=0;string entered="|⟨101|(H⊗H⊗H)|000⟩|^2";input.Text=entered;input.Focus();
     int previous=history.Items.Count;
     var key=new KeyEventArgs(Keyboard.PrimaryDevice,PresentationSource.FromVisual(input),Environment.TickCount,Key.Enter) {RoutedEvent=Keyboard.PreviewKeyDownEvent};
     input.RaiseEvent(key);
     if(!key.Handled)throw new Exception("Enter was not handled by the expression box.");
     var elapsed=Stopwatch.StartNew();
     while(!run.IsEnabled && elapsed.ElapsedMilliseconds<10000)await Task.Delay(20);
     if(!run.IsEnabled || history.Items.Count!=previous+1 || output.Text!="0.125" || input.Text!=entered)throw new Exception("Enter did not calculate exactly once without inserting a newline.");
     input.Text="";
     var emptyKey=new KeyEventArgs(Keyboard.PrimaryDevice,PresentationSource.FromVisual(input),Environment.TickCount,Key.Enter) {RoutedEvent=Keyboard.PreviewKeyDownEvent};
     input.RaiseEvent(emptyKey);
     if(!emptyKey.Handled || history.Items.Count!=previous+1 || !run.IsEnabled)throw new Exception("Empty Enter changed calculation state.");
     File.WriteAllText(args[1],"PASS: routed Enter calculates the bra-ket probability as 0.125 exactly once without a newline; empty input remains idle.");
    }catch(Exception ex){File.WriteAllText(args[1],ex.ToString());Environment.ExitCode=1;}
    window.Close();
   };
  }
  if(args.Length==2 && args[0]=="--calculation-control-test") {
   window.Loaded+=async delegate {
    try {
     int count=history.Items.Count;
     foreach(int delay in new[]{0,300}) {
      input.Text="norm(vec(expm(logm(QFT(6)))-QFT(6)))";
      var pending=Calculate();
      if(run.IsEnabled || !cancel.IsEnabled || timeAllowance.IsEnabled)throw new Exception("Busy controls are incorrect.");
      await Task.Delay(delay);
      cancel.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
      await pending;
      if(resultLabel.Text!="CANCELLED" || history.Items.Count!=count || active!=null || !run.IsEnabled || cancel.IsEnabled || !timeAllowance.IsEnabled)throw new Exception("Cancellation did not clean up or preserved a partial result.");
     }
     input.Text="norm(vec(expm(logm(QFT(6)))-QFT(6)))";await Calculate(10);
     if(resultLabel.Text!="TIME ALLOWANCE REACHED" || active!=null || history.Items.Count!=count)throw new Exception("Timeout did not clean up.");
     foreach(int selection in new[]{0,1,2,3}) {
      timeAllowance.SelectedIndex=selection;input.Text="H|0>";await Calculate();
      if(resultLabel.Text!="EXACT RESULT" || !run.IsEnabled || cancel.IsEnabled)throw new Exception("Calculation failed after cancellation or timeout.");
     }
     if(history.Items.Count!=count+4)throw new Exception("Successful history entries missing.");
     timeAllowance.SelectedIndex=0;
     File.WriteAllText(args[1],"PASS: immediate and running cancellation, timeout, cleanup, unchanged interrupted history, and successful reuse with all four allowances.");
    } catch(Exception ex) {File.WriteAllText(args[1],ex.ToString());Environment.ExitCode=1;}
    window.Close();
   };
  }
  if(args.Length==3 && args[0]=="--sampling-circuit-test") {
   window.Loaded+=async delegate {
    CircuitComposer composer=null;SamplingWindow sampling=null;
    try {
     composer=new CircuitComposer(window,delegate(string value) {});composer.OpenCircuit(args[1]);
     sampling=new SamplingWindow(window,composer.QubitCount,composer.SamplingGates());sampling.Show();
     var result=await sampling.VerifySampling(args[2]+".png",false,1731);
     File.WriteAllText(args[2]+".json",new JavaScriptSerializer {MaxJsonLength=8000000}.Serialize(result));
     File.WriteAllText(args[2],"PASS: loaded circuit sampled through the actual GUI; all counts saved for independent validation.");
    } catch(Exception ex) {File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(sampling!=null)sampling.Close();if(composer!=null)composer.Close();window.Close();}
   };
  }
  if(args.Length==5 && args[0]=="--sampling-readout-test") {
   window.Loaded+=async delegate {
    CircuitComposer composer=null;SamplingWindow sampling=null;
    try {
     composer=new CircuitComposer(window,delegate(string value) {});composer.OpenCircuit(args[1]);
     sampling=new SamplingWindow(window,composer.QubitCount,composer.SamplingGates());sampling.Show();
     var result=await sampling.VerifySampling(args[4]+".png",false,1731,args[2],args[3]);
     File.WriteAllText(args[4]+".json",new JavaScriptSerializer {MaxJsonLength=8000000}.Serialize(result));
     File.WriteAllText(args[4],"PASS: actual GUI readout controls, worker, result display and export paths completed.");
    } catch(Exception ex) {File.WriteAllText(args[4],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(sampling!=null)sampling.Close();if(composer!=null)composer.Close();window.Close();}
   };
  }
  if(args.Length==3 && args[0]=="--source-files-test") {
   window.Loaded+=async delegate {
    CircuitComposer composer=null;ClassicalProgramWindow editor=null;
    try {
     string folder=Path.GetFullPath(args[1]);Directory.CreateDirectory(folder);
     string entry=Path.Combine(folder,"main.qasm"),helper=Path.Combine(folder,"helper.qasm");
     File.WriteAllText(entry,"OPENQASM 3; include \"stdgates.inc\"; include \"helper.qasm\"; qubit q; flip q;",new System.Text.UTF8Encoding(true));
     File.WriteAllText(helper,"gate flip a { x a; }\n",new System.Text.UTF8Encoding(false));
     composer=new CircuitComposer(window,delegate(string value){});composer.Show();
     await composer.VerifySourceFiles(entry,args[2]+".composer");composer.Close();composer=null;
     File.WriteAllText(helper,"gate flip a { x a; }\n",new System.Text.UTF8Encoding(false));
     editor=new ClassicalProgramWindow(window);editor.Show();
     await editor.VerifySourceFiles(entry,args[2]+".classical");
     File.WriteAllText(args[2],"PASS: both editors check unchanged/changed/missing files; failed reimport preserves document; successful reimport is undoable.");
    } catch(Exception error) {File.WriteAllText(args[2],"FAIL: "+error);Environment.ExitCode=1;}
    finally {if(editor!=null)editor.Close();if(composer!=null)composer.Close();window.Close();}
   };
  }
  if((args.Length==3 || args.Length==4) && args[0]=="--composer-source-qasm-test") {
   window.Loaded+=delegate {
    CircuitComposer composer=null;
    try {
     if(args.Length==4 && args[3]!="modules")throw new InvalidDataException("Unknown source import test mode.");
     composer=new CircuitComposer(window,delegate(string value){});composer.Show();
     composer.VerifySourceImport(args[1],args[2],args.Length==4);
     File.WriteAllText(args[2],"PASS: frozen numerical composer source import, undo/edit/save/reopen and standalone export.");
    } catch(Exception ex) {File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(composer!=null)composer.Close();window.Close();}
   };
  }
  if((args.Length==3 || args.Length==4) && args[0]=="--classical-export-test") {
   window.Loaded+=async delegate {
    ClassicalProgramWindow editor=null;
    try {
     editor=new ClassicalProgramWindow(window);editor.Show();await editor.VerifyExport(args[1],args[2],args.Length==4 && args[3]=="modules");
     File.WriteAllText(args[2],"PASS: edited classical export, frozen compiler validation, file preservation, source/history and save/reopen.");
    } catch(Exception ex) {File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(editor!=null)editor.Close();window.Close();}
   };
  }
  if((args.Length==3 || args.Length==4) && args[0]=="--classical-qasm-test") {
   window.Loaded+=delegate {
    ClassicalProgramWindow editor=null;
    try {
     if(args.Length==4 && args[3]!="modules")throw new InvalidDataException("Unknown source import test mode.");
     editor=new ClassicalProgramWindow(window);editor.Show();editor.VerifyImport(args[1],args[2],args.Length==4);File.WriteAllText(args[2],"PASS: frozen classical OpenQASM import, undo/redo and display.");
    }
    catch(Exception ex) {File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(editor!=null)editor.Close();window.Close();}
   };
  }
  if(args.Length==2 && args[0]=="--classical-editor-test") {
   window.Loaded+=delegate {
    ClassicalProgramWindow editor=null;
    try {editor=new ClassicalProgramWindow(window);editor.Show();editor.VerifyEditing(args[1]+".png");File.WriteAllText(args[1],"PASS: classical editor preserves branches, saved bits, invalid edits and undo/redo.");}
    catch(Exception ex) {File.WriteAllText(args[1],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(editor!=null)editor.Close();window.Close();}
   };
  }
  if(args.Length==3 && args[0]=="--exact-circuit-test") {
   window.Loaded+=async delegate {
    ExactCircuitWindow exact=null;
    try {exact=new ExactCircuitWindow(window,ClassicalCircuit.Load(File.ReadAllText(args[1],Encoding.UTF8)));exact.Show();await exact.Verify(args[2]);File.WriteAllText(args[2],"PASS: exact results, copy/save data and minimum layout.");}
    catch(Exception ex){File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(exact!=null)exact.Close();window.Close();}
   };
  }
  if(args.Length==3 && args[0]=="--classical-sampling-test") {
   window.Loaded+=async delegate {
    SamplingWindow sampling=null;
    try {
     var circuit=ClassicalCircuit.Load(File.ReadAllText(args[1],Encoding.UTF8));
     sampling=new SamplingWindow(window,circuit);sampling.Show();
     var result=await sampling.VerifySampling(args[2]+".png",false);
     File.WriteAllText(args[2]+".json",new JavaScriptSerializer {MaxJsonLength=8000000}.Serialize(result));
     File.WriteAllText(args[2],"PASS: saved classical outputs sampled and displayed through the GUI.");
    } catch(Exception ex) {File.WriteAllText(args[2],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(sampling!=null)sampling.Close();window.Close();}
   };
  }
  if(args.Length==2 && args[0]=="--sampling-test") {
   window.Loaded+=async delegate {
    CircuitComposer composer=null;SamplingWindow sampling=null;
    try {
     composer=new CircuitComposer(window,delegate(string value) {});composer.BellState(0);
     sampling=new SamplingWindow(window,2,composer.SamplingGates());sampling.Show();
     await sampling.VerifySampling(args[1]+".png");
     File.WriteAllText(args[1],"PASS: packaged sampling button, 10000 Bell shots, result rows, control cleanup and rendered window.");
    } catch(Exception ex) {File.WriteAllText(args[1],"FAIL: "+ex);Environment.ExitCode=1;}
    finally {if(sampling!=null)sampling.Close();if(composer!=null)composer.Close();window.Close();}
   };
  }
  if(args.Length==2 && args[0]=="--session-preservation-test") {
   window.Loaded+=delegate {
    try {
     for(int count=0;count<=50;count+=25) {
      history.Items.Clear();states=new[]{new StateDefinition {Name="Bell",Expression="|Phi+>"}};RefreshStates();
      input.Text="draft \u03b8 |Bell>";mode.SelectedIndex=count==25 ? 1 : 0;evaluation.SelectedIndex=count==50 ? 1 : 0;
      for(int k=0;k<count;k++)history.Items.Add(HistoryItem(new SessionEntry {Expression="H|0>",Result="[1;1]/sqrt(2)",Mode=0,Evaluation=k%2,States=SessionStore.CopyStates(states)},false));
      string path=args[1]+"."+count+".qsession";
      CheckInvalidSessions(path,args[1]+"."+count,new JavaScriptSerializer().Serialize(CaptureSession()));
     }
     File.WriteAllText(args[1],"PASS: 18 malformed-session GUI preservation checks across empty, partial and full histories.");
    } catch(Exception ex) {File.WriteAllText(args[1],"FAIL: "+ex);Environment.ExitCode=1;}
    window.Close();
   };
  }
  if(args.Length==2 && args[0]=="--state-editor-test") {
   window.Loaded+=async delegate {
    try {await CheckStateEditor(args[1]+".png");File.WriteAllText(args[1],"PASS: state editor draft isolation, cancel, apply, duplicate rejection, add/remove, ordering and minimum-width layout.");}
    catch(Exception ex){File.WriteAllText(args[1],"FAIL: "+ex);Environment.ExitCode=1;}
    window.Close();
   };
  }
  if(args.Length==2 && args[0]=="--smoke-test") {
   window.Loaded += async delegate {
    try {
    await Calculate();
    bool passed=history.Items.Count==1 && run.IsEnabled && output.Text.Contains("√(2)") && resultLabel.Text=="EXACT RESULT" && matrixCells.Children.Count==4 && matrixView.Visibility==Visibility.Visible;
    window.UpdateLayout();
    var bitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);
    bitmap.Render(window); var encoder=new System.Windows.Media.Imaging.PngBitmapEncoder(); encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
    using(var file=File.Create(args[1])) encoder.Save(file);
    input.Text="\\norm{\\frac{\\ket{0}+\\ket{1}}{\\sqrt{2}}}"; await Calculate();
    passed=passed && output.Text=="1" && history.Items.Count==2;
    input.Text="H |00⟩"; await Calculate();
    passed=passed && run.IsEnabled && resultLabel.Text=="CHECK YOUR EXPRESSION" && history.Items.Count==2;
    mode.SelectedIndex=1; input.Text="1 m to cm"; await Calculate();
    passed=passed && output.Text=="100 cm" && history.Items.Count==3;
    mode.SelectedIndex=0; input.Text="expm([0,1,0;0,0,1;1,0,0])"; await Calculate();
    passed=passed && resultLabel.Text=="APPROXIMATE RESULT" && matrixCells.Children.Count==9 && matrixView.Visibility==Visibility.Visible;
    var exampleDialog=ExamplesWindow(); var controls=(object[])exampleDialog.Tag;
    ((TextBox)controls[0]).Text="Energy loss from an excited qubit";
    var exampleList=(ListBox)controls[1]; passed=passed && exampleList.Items.Count==2;
    exampleList.SelectedIndex=1; ((Button)controls[2]).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    await Calculate(); passed=passed && output.Text=="[0.75; 0.25]" && probabilityView.Visibility==Visibility.Visible;
    var teleportDialog=ExamplesWindow(); var teleportControls=(object[])teleportDialog.Tag;
    ((TextBox)teleportControls[0]).Text="Teleport a phase-sensitive qubit";
    var teleportList=(ListBox)teleportControls[1]; passed=passed && teleportList.Items.Count==2;
    teleportList.SelectedIndex=1; ((Button)teleportControls[2]).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    await Calculate(); passed=passed && output.Text.Replace(" ","")=="[0.5−0.5i;0.5i0.5]";
    input.Text="shift(3)|2⟩_3"; await Calculate(); passed=passed && output.Text=="[1; 0; 0]" && matrixCells.Children.Count==3;
    input.Text="|Y⟩⟩"; await Calculate(); passed=passed && output.Text=="[0; i; −i; 0]" && matrixCells.Children.Count==4;
    input.Text="choi(vector(I/sqrt(2),Z/sqrt(2)))"; await Calculate();
    passed=passed && output.Text.Replace(" ","")=="[1000;0000;0000;0001]" && matrixCells.Children.Count==16;
    input.Text="probs(diffusion(3)phaseoracle(3,[1,6])H^⊗3 |000⟩)";await Calculate();
    passed=passed && output.Text=="[0; 0.5; 0; 0; 0; 0; 0.5; 0]" && matrixCells.Children.Count==8;
    input.Text="probs((H ⊗ H ⊗ I)oracle([0,1,1,0])(H ⊗ H ⊗ I)(|00⟩ ⊗ |−⟩),[0,1])";await Calculate();
    passed=passed && output.Text=="[0; 0; 0; 1]" && matrixCells.Children.Count==4;
    input.Text="modmul(2,5)|011⟩";await Calculate();passed=passed && output.Text=="[0; 1; 0; 0; 0; 0; 0; 0]" && matrixCells.Children.Count==8;
    input.Text="numberop(3)";await Calculate();passed=passed && output.Text.Replace(" ","")=="[000;010;002]" && matrixCells.Children.Count==9;
    input.Text="fdestroy(3,1)|110⟩";await Calculate();passed=passed && output.Text=="[0; 0; 0; 0; −1; 0; 0; 0]" && matrixCells.Children.Count==8;
    input.Text="Jz(1)";await Calculate();passed=passed && matrixCells.Children.Count==9;
    input.Text="norm(Jplus(1)basis(1,3)-sqrt(2)*basis(0,3))";await Calculate();passed=passed && output.Text=="0";
    input.Text=@"norm(\hat{J}_{+}(1)basis(1,3)-sqrt(2)*basis(0,3))";await Calculate();passed=passed && output.Text=="0";
    input.Text=@"\ket{\uparrow\downarrow}";await Calculate();passed=passed && output.Text=="[0; 1; 0; 0]" && matrixCells.Children.Count==4;
    input.Text="norm(|+−⟩-H^⊗2 |01⟩)";await Calculate();passed=passed && output.Text=="0";
    input.Text="⟨+−|X ⊗ X|+−⟩";await Calculate();passed=passed && output.Text=="−1";
    input.Text="negativity(density((|00>+|11>)/sqrt(2))/2+identity(4)/8,0)";await Calculate();passed=passed && output.Text.StartsWith("0.125") && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="lognegativity((|00>+|11>)/sqrt(2),0)";await Calculate();passed=passed && output.Text.StartsWith("1.000") && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="norm(vec(sqrt(X)-SX))";await Calculate();passed=passed && output.Text=="0" && resultLabel.Text=="EXACT RESULT";
    input.Text="norm(vec(√X-SX))";await Calculate();passed=passed && output.Text=="0" && resultLabel.Text=="EXACT RESULT";
    input.Text="2√9+∛8+∜16";await Calculate();passed=passed && output.Text=="10";
    input.Text="norm(vec(X×Y−i⋅Z))";await Calculate();passed=passed && output.Text=="0";
    input.Text="probs(Rx(π∕2)|0⟩)";await Calculate();passed=passed && output.Text=="[0.5; 0.5]";
    input.Text="sqrt(H*S)";await Calculate();passed=passed && resultLabel.Text=="APPROXIMATE RESULT" && matrixView.Visibility==Visibility.Visible;
    input.Text="norm(vec(expm(logm(X))-X))";await Calculate();passed=passed && output.Text=="0" && resultLabel.Text=="EXACT RESULT";
    input.Text="logm(H*S)";await Calculate();passed=passed && resultLabel.Text=="APPROXIMATE RESULT" && matrixView.Visibility==Visibility.Visible;
    input.Text="schmidt_coeffs(3|00>+4i|11>,0)";await Calculate();if(matrixCells.Children.Count!=2 || resultLabel.Text!="APPROXIMATE RESULT" || output.Text!="[0.800000000000; 0.600000000000]")throw new Exception("Schmidt coefficient display failed.");
    input.Text="‖X‖₁";await Calculate();if(output.Text!="2.00000000000" || resultLabel.Text!="APPROXIMATE RESULT")throw new Exception("Indexed trace norm display failed.");
    input.Text=@"\begin{Vmatrix}3&0\\0&4\end{Vmatrix}_{\mathrm{F}}";await Calculate();if(output.Text!="5" || resultLabel.Text!="APPROXIMATE RESULT")throw new Exception("LaTeX matrix norm display failed.");
    input.Text="probs(-reflection(|++>)reflection(|11>)|++>)";await Calculate();if(output.Text!="[0; 0; 0; 1]" || probabilityView.Visibility!=Visibility.Visible || resultLabel.Text!="EXACT RESULT")throw new Exception("Reflection-based Grover result failed.");
    input.Text="entropy(I/2)";await Calculate();passed=passed && output.Text=="1.00000000000" && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="entropy(I,4)";await Calculate();passed=passed && output.Text.StartsWith("0.5") && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="tracedistance(|0>,|1>)";await Calculate();passed=passed && output.Text=="1.00000000000" && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="fidelity(|0>,|+>)";await Calculate();passed=passed && output.Text=="0.500000000000" && resultLabel.Text=="APPROXIMATE RESULT";
    input.Text="probs(channel(density(|i>),amplitude_damping(1,1/4)))";await Calculate();passed=passed && output.Text=="[0.75; 0.25]" && probabilityView.Visibility==Visibility.Visible;
    input.Text="expect(Y,channel(density(|i>),phase_amplitude_damping(1/4,1/2,1/4)))";await Calculate();passed=passed && output.Text=="0.5";
    input.Text="ptm(amplitude_damping(3/4))";await Calculate();passed=passed && matrixCells.Children.Count==16 && resultLabel.Text=="EXACT RESULT";
    input.Text="chi(vector(S))";await Calculate();if(matrixCells.Children.Count!=16 || resultLabel.Text!="EXACT RESULT" || output.Text.Replace(" ","")!="[100i;0000;0000;−i001]")throw new Exception("Complex chi matrix did not render correctly.");
    input.Text="⟪(X+iY)|(X+iY)⟫";await Calculate();if(output.Text!="4")throw new Exception("Grouped operator overlap failed.");
    input.Text="unvec(sprepost(Y,S)vec(X),2)";await Calculate();if(matrixCells.Children.Count!=4 || output.Text.Replace(" ","")!="[−i0;0−1]")throw new Exception("Left/right superoperator evaluation failed.");
    input.Text="unvec(liouvillian(0I,vector(destroy(2)))vec(density(|1>)),2)";await Calculate();if(matrixCells.Children.Count!=4 || output.Text.Replace(" ","")!="[10;0−1]")throw new Exception("Lindblad generator evaluation failed.");
    input.Text="controlled(X,2,\"01\")|010>";await Calculate();if(output.Text!="[0; 0; 0; 1; 0; 0; 0; 0]")throw new Exception("Quoted control pattern failed in the calculator.");
    input.Text="ptm(vector(S))[1;1;0;0]";await Calculate();passed=passed && output.Text=="[1; 0; 1; 0]";
    input.Text="sqrt(2)paulivec(density(|i>))";await Calculate();passed=passed && output.Text=="[1; 0; 1; 0]";
    input.Text="unpaulivec(ptm(amplitude_damping(3/4))paulivec(density(|i>)))";await Calculate();passed=passed && matrixCells.Children.Count==4 && output.Text.Replace(" ","")=="[0.875−0.25i;0.25i0.125]";
    input.Text="probs((|00>+|11>)/sqrt(2))";await Calculate();passed=passed && probabilityView.Visibility==Visibility.Visible;
    var probabilityBars=(StackPanel)((ScrollViewer)probabilityView.Children[2]).Content;
    passed=passed && probabilityBars.Children.Count==4 && ((TextBlock)((Grid)probabilityBars.Children[0]).Children[2]).Text=="50%" && ((TextBlock)((Grid)probabilityBars.Children[1]).Children[2]).Text=="0%";
    string probabilityText=output.Text;int probabilityHistory=history.Items.Count;
    ((ComboBox)((WrapPanel)probabilityView.Children[1]).Children[1]).SelectedIndex=1;
    probabilityBars=(StackPanel)((ScrollViewer)probabilityView.Children[2]).Content;
    if(((TextBlock)((Grid)probabilityBars.Children[3]).Children[0]).Text!="11" || !System.Windows.Automation.AutomationProperties.GetName(probabilityBars.Children[3]).Contains("binary 11") || output.Text!=probabilityText || history.Items.Count!=probabilityHistory || active!=null)throw new Exception("Binary probability labels changed the calculation.");
    input.Text="probs(|000001>)";await Calculate();probabilityBars=(StackPanel)((ScrollViewer)probabilityView.Children[2]).Content;
    if(probabilityBars.Children.Count!=64 || ((TextBlock)((Grid)probabilityBars.Children[1]).Children[0]).Text!="000001" || ((TextBlock)((Grid)probabilityBars.Children[63]).Children[0]).Text!="111111")throw new Exception("Binary outcome padding failed.");
    input.Text="probs(basis(1,3))";await Calculate();
    if(((ComboBox)((WrapPanel)probabilityView.Children[1]).Children[1]).IsEnabled || !binaryProbabilityLabels)throw new Exception("Qudit outcome label fallback failed.");
    input.Text="probs(|001>)";await Calculate();probabilityBars=(StackPanel)((ScrollViewer)probabilityView.Children[2]).Content;
    if(((TextBlock)((Grid)probabilityBars.Children[1]).Children[0]).Text!="001" || ((TextBlock)((Grid)probabilityBars.Children[1]).Children[2]).Text!="100%")throw new Exception("Binary label preference failed.");
    ((ComboBox)((WrapPanel)probabilityView.Children[1]).Children[1]).SelectedIndex=0;
    probabilityBars=(StackPanel)((ScrollViewer)probabilityView.Children[2]).Content;
    if(binaryProbabilityLabels || ((TextBlock)((Grid)probabilityBars.Children[1]).Children[0]).Text!="1")throw new Exception("Decimal outcome labels failed.");
    input.Text="H";await Calculate();passed=passed && probabilityView.Visibility==Visibility.Collapsed;
    input.Text="bloch(|i>)";await Calculate();passed=passed && blochView.Visibility==Visibility.Visible && output.Text=="[0; 1; 0]";
    var sphereLayout=(WrapPanel)blochView.Children[2];var sphereCanvas=(Canvas)sphereLayout.Children[0];
    passed=passed && System.Windows.Automation.AutomationProperties.GetName(sphereCanvas).Contains("y=1") && ((TextBlock)((StackPanel)sphereLayout.Children[1]).Children[3]).Text=="Length  1";
    double initialSphereX=Canvas.GetLeft(sphereCanvas.Children[sphereCanvas.Children.Count-1]);
    var sphereControls=(WrapPanel)((StackPanel)sphereLayout.Children[1]).Children[6];((Button)sphereControls.Children[0]).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    sphereLayout=(WrapPanel)blochView.Children[2];sphereCanvas=(Canvas)sphereLayout.Children[0];
    passed=passed && Math.Abs(Canvas.GetLeft(sphereCanvas.Children[sphereCanvas.Children.Count-1])-initialSphereX)>1 && output.Text=="[0; 1; 0]";
    sphereControls=(WrapPanel)((StackPanel)sphereLayout.Children[1]).Children[6];((Button)sphereControls.Children[2]).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    sphereLayout=(WrapPanel)blochView.Children[2];sphereCanvas=(Canvas)sphereLayout.Children[0];
    passed=passed && Math.Abs(Canvas.GetLeft(sphereCanvas.Children[sphereCanvas.Children.Count-1])-initialSphereX)<1e-10;
    input.Text="bloch(I/2)";await Calculate();passed=passed && blochView.Visibility==Visibility.Visible && output.Text=="[0; 0; 0]";
    sphereLayout=(WrapPanel)blochView.Children[2];sphereCanvas=(Canvas)sphereLayout.Children[0];
    var spherePoint=(System.Windows.Shapes.Ellipse)sphereCanvas.Children[sphereCanvas.Children.Count-1];
    passed=passed && Canvas.GetLeft(spherePoint)==136 && Canvas.GetTop(spherePoint)==116;
    evaluation.SelectedIndex=1;input.Text="bloch(Ry(pi/3)|0>)";await Calculate();passed=passed && blochView.Visibility==Visibility.Visible && resultLabel.Text=="APPROXIMATE RESULT";evaluation.SelectedIndex=0;
    input.Text="H";await Calculate();passed=passed && blochView.Visibility==Visibility.Collapsed;
    input.Text="bloch([1,2;2,1])";await Calculate();passed=passed && blochView.Visibility==Visibility.Collapsed && resultLabel.Text=="CHECK YOUR EXPRESSION";
    input.Text="probs(0|0>)";await Calculate();passed=passed && probabilityView.Visibility==Visibility.Collapsed && resultLabel.Text=="CHECK YOUR EXPRESSION";
    input.Text="⟨0|X²|0⟩";await Calculate();passed=passed && output.Text=="1";
    input.Text=@"\bra{i}\hat{\sigma}_{y}\ket{i}";await Calculate();passed=passed && output.Text=="1";
    input.Text="((X+iY)/2)|1⟩";await Calculate();passed=passed && output.Text=="[1; 0]" && matrixCells.Children.Count==2;
    input.Text=@"\bra{0}\mathbf{X}\mathbf{Y}\ket{0}";await Calculate();passed=passed && output.Text=="i";
    input.Text="permute(|1⟩ ⊗ |0⟩_3,[1,0],[2,3])"; await Calculate(); passed=passed && output.Text=="[0; 1; 0; 0; 0; 0]" && matrixCells.Children.Count==6;
    input.Text="3ptrace(density(SUM(3)(fourier(3) ⊗ identity(3))(|0⟩_3 ⊗ |0⟩_3)),0,[3,3])"; await Calculate();
    passed=passed && output.Text.Replace(" ","")=="[100;010;001]" && matrixCells.Children.Count==9;
    var composer=new CircuitComposer(window,delegate(string value) {});
    string bell=composer.Expression();
    string[] bellLabels={"Φ+","Φ-","Ψ+","Ψ-"};
    for(int bellCase=1;bellCase<=4;bellCase++) {
     int bellIndex=bellCase%4;string beforeBell=composer.Expression();composer.BellState(bellIndex);string bellExpression=composer.Expression();
     input.Text="norm(("+bellExpression+")-|"+bellLabels[bellIndex]+">)";await Calculate();if(output.Text!="0")throw new Exception("Bell preparation phase failed.");
     if(!composer.Undo() || composer.Expression()!=beforeBell || !composer.Redo() || composer.Expression()!=bellExpression)throw new Exception("Bell preset undo/redo failed.");
     string bellPath=args[1]+".bell"+bellIndex+".qcircuit";composer.SaveCircuit(bellPath);composer.OpenCircuit(bellPath);
     if(composer.Expression()!=bellExpression)throw new Exception("Bell save/open changed the circuit.");
     File.WriteAllText(args[1]+".bell"+bellIndex+".qasm",composer.OpenQasm());
     foreach(int badBell in new[]{-1,4}) {bool rejectedBell=false;try {composer.BellState(badBell);}catch(ArgumentOutOfRangeException){rejectedBell=true;}if(!rejectedBell || composer.Expression()!=bellExpression)throw new Exception("Invalid Bell preset changed the circuit.");}
    }

    for(int marked=0;marked<4;marked++) {
     string beforeGrover=composer.Expression();composer.Grover(marked);string groverExpression=composer.Expression();
     input.Text="norm(("+groverExpression+")+basis("+marked+",4))";await Calculate();if(output.Text!="0")throw new Exception("Grover target or global phase failed.");
     input.Text=composer.InspectionExpression(1,0);await Calculate();if(probabilityView.Visibility!=Visibility.Visible)throw new Exception("Grover probability chart failed.");
     if(!composer.Undo() || composer.Expression()!=beforeGrover || !composer.Redo() || composer.Expression()!=groverExpression)throw new Exception("Grover preset undo/redo failed.");
     string groverPath=args[1]+".grover"+marked+".qcircuit";composer.SaveCircuit(groverPath);composer.OpenCircuit(groverPath);
     if(composer.Expression()!=groverExpression)throw new Exception("Grover save/open changed the circuit.");
     File.WriteAllText(args[1]+".grover"+marked+".qasm",composer.OpenQasm());
     bool invalidTarget=false;try {composer.Grover(4);}catch(ArgumentOutOfRangeException){invalidTarget=true;}
     if(!invalidTarget || composer.Expression()!=groverExpression)throw new Exception("Invalid Grover target changed the circuit.");
    }
    for(int secret=0;secret<8;secret++) {
     string bits=Convert.ToString(secret,2).PadLeft(3,'0');string beforeBv=composer.Expression();composer.BernsteinVazirani(bits);string bvExpression=composer.Expression();
     input.Text="norm(("+bvExpression+")-|"+bits+",->)";await Calculate();if(output.Text!="0")throw new Exception("Bernstein–Vazirani hidden string or ancilla phase failed.");
     input.Text="<"+bits+"|"+composer.InspectionExpression(4,"0,1,2");await Calculate();if(output.Text!="1")throw new Exception("Bernstein–Vazirani marginal failed.");
     if(!composer.Undo() || composer.Expression()!=beforeBv || !composer.Redo() || composer.Expression()!=bvExpression)throw new Exception("Bernstein–Vazirani undo/redo failed.");
     string bvPath=args[1]+".bv"+secret+".qcircuit";composer.SaveCircuit(bvPath);composer.OpenCircuit(bvPath);
     if(composer.Expression()!=bvExpression)throw new Exception("Bernstein–Vazirani save/open failed.");
     File.WriteAllText(args[1]+".bv"+secret+".qasm",composer.OpenQasm());
     foreach(string badSecret in new[]{null,"","01","0000","0x1","10 ","α01"}) {bool rejectedBv=false;try {composer.BernsteinVazirani(badSecret);}catch(ArgumentException){rejectedBv=true;}if(!rejectedBv || composer.Expression()!=bvExpression)throw new Exception("Invalid hidden string changed the circuit.");}
    }
    for(int mask=0;mask<512;mask++) {
     string matrix="";for(int r=0;r<3;r++) {if(r>0)matrix+=";";for(int c=0;c<3;c++){if(c>0)matrix+=",";matrix+=((mask>>(3*r+c))&1);}}
     string beforeLinear=composer.Expression();bool rejectedLinear=false;try {composer.LinearMap(matrix);}catch(ArgumentException){rejectedLinear=true;}
     if(rejectedLinear) {if(composer.Expression()!=beforeLinear)throw new Exception("Rejected linear map changed the circuit.");continue;}
     string linearExpression=composer.Expression();
     if(linearExpression!=beforeLinear && (!composer.Undo() || composer.Expression()!=beforeLinear || !composer.Redo() || composer.Expression()!=linearExpression))throw new Exception("Linear map undo/redo failed.");
     File.WriteAllText(args[1]+".linear"+mask+".qasm",composer.OpenQasm());
    }
    var linearRandom=new Random(927);
    for(int wideCase=0;wideCase<8;wideCase++) {
     int[,] a=new int[8,8];for(int r=0;r<8;r++)a[r,r]=1;
     for(int k=0;k<100;k++){int r=linearRandom.Next(8),c=linearRandom.Next(8);if(r!=c)for(int j=0;j<8;j++)a[r,j]^=a[c,j];}
     string matrix="";for(int r=0;r<8;r++){if(r>0)matrix+=";";for(int c=0;c<8;c++){if(c>0)matrix+=",";matrix+=a[r,c];}}
     composer.LinearMap(matrix);string expression8=composer.Expression();
     string widePath=args[1]+".wide"+wideCase;composer.SaveCircuit(widePath+".qcircuit");composer.OpenCircuit(widePath+".qcircuit");
     if(composer.Expression()!=expression8)throw new Exception("Eight-bit map save/open failed.");
     File.WriteAllText(widePath+".qasm",composer.OpenQasm());File.WriteAllText(widePath+".matrix",matrix);
     input.Text="norm(("+expression8+")-|00000000>)";await Calculate();if(output.Text!="0")throw new Exception("Eight-bit synthesized expression failed: "+output.Text);
    }
    composer.LinearMap("[1,0;1,1]");string linearPath=args[1]+".linear.qcircuit";composer.SaveCircuit(linearPath);string savedLinear=composer.Expression();composer.OpenCircuit(linearPath);
    if(composer.Expression()!=savedLinear)throw new Exception("Linear-map save/open failed.");
    foreach(string badMatrix in new[]{null,"","0","1,1;1,1","1,2;0,1","1,,0;0,1","[1,0;0,1","1,0,0;0,1,0"}) {bool rejectedLinear=false;try {composer.LinearMap(badMatrix);}catch(ArgumentException){rejectedLinear=true;}if(!rejectedLinear || composer.Expression()!=savedLinear)throw new Exception("Invalid binary matrix changed the circuit.");}
    for(int secret=0;secret<8;secret++) {
     string bits=Convert.ToString(secret,2).PadLeft(3,'0');string beforeSimon=composer.Expression();composer.Simon(bits);string simonExpression=composer.Expression();
     var expectedSimon=new System.Collections.Generic.List<string>();
     for(int y=0;y<8;y++) {int parity=0;for(int bit=0;bit<3;bit++)parity^=((y & secret)>>bit)&1;expectedSimon.Add(secret==0 ? "1/8" : parity==0 ? "1/4" : "0");}
     input.Text="norm(("+composer.InspectionExpression(4,"0,1,2")+")-["+String.Join(";",expectedSimon.ToArray())+"])";await Calculate();if(output.Text!="0")throw new Exception("Simon marginal violates the hidden-string constraint.");
     if(!composer.Undo() || composer.Expression()!=beforeSimon || !composer.Redo() || composer.Expression()!=simonExpression)throw new Exception("Simon undo/redo failed.");
     string simonPath=args[1]+".simon"+secret+".qcircuit";composer.SaveCircuit(simonPath);composer.OpenCircuit(simonPath);
     if(composer.Expression()!=simonExpression)throw new Exception("Simon save/open failed.");
     File.WriteAllText(args[1]+".simon"+secret+".qasm",composer.OpenQasm());
     foreach(string badSecret in new[]{null,"","01","0000","0x1","10 ","α01"}) {bool rejectedSimon=false;try {composer.Simon(badSecret);}catch(ArgumentException){rejectedSimon=true;}if(!rejectedSimon || composer.Expression()!=simonExpression)throw new Exception("Invalid Simon string changed the circuit.");}
    }
    for(int phaseIndex=0;phaseIndex<8;phaseIndex++) {
     composer.PhaseEstimation(phaseIndex+"*pi/4");
     string estimationExpression=composer.Expression();
     input.Text="norm(("+estimationExpression+")-basis("+(2*phaseIndex+1)+",16))";await Calculate();if(output.Text!="0")throw new Exception("Phase estimation bit order or phase failed: "+phaseIndex);
     input.Text="<"+Convert.ToString(phaseIndex,2).PadLeft(3,'0')+"|"+composer.InspectionExpression(4,"0,1,2");await Calculate();if(output.Text!="1")throw new Exception("Phase estimation marginal output failed.");
     char[] reverseBits=Convert.ToString(phaseIndex,2).PadLeft(3,'0').ToCharArray();Array.Reverse(reverseBits);
     input.Text="<"+new string(reverseBits)+"|"+composer.InspectionExpression(4,"2,1,0");await Calculate();if(output.Text!="1")throw new Exception("Marginal wire-order preservation failed.");
     string estimationPath=args[1]+".qpe"+phaseIndex+".qcircuit";composer.SaveCircuit(estimationPath);composer.OpenCircuit(estimationPath);
     if(composer.Expression()!=estimationExpression)throw new Exception("Phase-estimation save/open changed the circuit.");
     File.WriteAllText(args[1]+".qpe"+phaseIndex+".qasm",composer.OpenQasm());
    }
    string priorEstimation=composer.Expression();composer.PhaseEstimation("pi/8");string halfEstimation=composer.Expression();File.WriteAllText(args[1]+".qpe-half.qasm",composer.OpenQasm());
    if(!composer.Undo() || composer.Expression()!=priorEstimation || !composer.Redo() || composer.Expression()!=halfEstimation)throw new Exception("Phase-estimation preset undo/redo failed.");
    composer.Close();composer=new CircuitComposer(window,delegate(string value) {});

    composer.SelectSchmidtPartition("0");
    input.Text=composer.InspectionExpression(3,"0");await Calculate();
    if(matrixCells.Children.Count!=2 || resultLabel.Text!="APPROXIMATE RESULT" || output.Text!="[0.707106781187; 0.707106781187]")throw new Exception("Bell Schmidt inspection failed.");
    foreach(string invalidPartition in new[]{"", "0,", "0,0", "-1", "2", "0.5", "0,1", "0;1", "H"}) {
     bool partitionRejected=false;try {composer.InspectionExpression(3,invalidPartition);}catch(InvalidDataException){partitionRejected=true;}if(!partitionRejected)throw new Exception("Invalid Schmidt partition accepted: "+invalidPartition);
    }
    var partitionComposer=new CircuitComposer(window,delegate(string value) {});
    string partitionPath=args[1]+".partition.qcircuit";
    File.WriteAllText(partitionPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");partitionComposer.OpenCircuit(partitionPath);
    partitionComposer.AddGate("H","0","");partitionComposer.AddGate("CNOT","0,1","");partitionComposer.AddGate("CNOT","0,2","");
    if(partitionComposer.InspectionExpression(3,"2, 0")!=partitionComposer.InspectionExpression(3,"0,2"))throw new Exception("Partition wire order changed Schmidt inspection.");
    input.Text=partitionComposer.InspectionExpression(3,"2,0");await Calculate();if(output.Text!="[0.707106781187; 0.707106781187]")throw new Exception("Nonadjacent GHZ partition failed.");
    foreach(string mixedOperation in new[]{"Reset","Measure","M0-X","AD"}) {
     File.WriteAllText(partitionPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");partitionComposer.OpenCircuit(partitionPath);
     partitionComposer.AddGate(mixedOperation,mixedOperation=="M0-X" ? "0,1" : "0",mixedOperation=="AD" ? "1/4" : "");
     bool partitionMixedRejected=false;try {partitionComposer.InspectionExpression(3,"0");}catch(InvalidDataException){partitionMixedRejected=true;}if(!partitionMixedRejected)throw new Exception("Density circuit accepted for Schmidt inspection: "+mixedOperation);
    }
    partitionComposer.Close();
    input.Text=composer.InspectionExpression(4,"1");await Calculate();if(output.Text!="[0.5; 0.5]" || probabilityView.Visibility!=Visibility.Visible)throw new Exception("Marginal probability inspection failed.");
    foreach(string invalidMarginal in new[]{"", "0,0", "-1", "2", "0,"}) {
     bool marginalRejected=false;try {composer.InspectionExpression(4,invalidMarginal);}catch(InvalidDataException){marginalRejected=true;}if(!marginalRejected)throw new Exception("Invalid marginal wire list accepted.");
    }
    if(composer.InspectionExpression(0,0)!=bell)throw new Exception("State inspection changed the circuit expression.");
    input.Text=composer.InspectionExpression(1,0);await Calculate();if(output.Text!="[0.5; 0; 0; 0.5]" || probabilityView.Visibility!=Visibility.Visible)throw new Exception("Circuit probability inspection failed.");
    input.Text=composer.InspectionExpression(2,0);await Calculate();if(output.Text!="[0; 0; 0]" || blochView.Visibility!=Visibility.Visible)throw new Exception("Circuit Bloch inspection failed.");
    bool invalidInspection=false;try{composer.InspectionExpression(2,2);}catch(InvalidDataException){invalidInspection=true;}
    if(!invalidInspection || composer.Expression()!=bell)throw new Exception("Invalid inspection altered the circuit.");
    passed=passed && !composer.AddGate("CNOT","0,0","") && composer.Expression()==bell;
    passed=passed && composer.AddGate("S","1","");
    input.Text="norm(("+composer.Expression()+")-(|00⟩+i|11⟩)/sqrt(2))"; await Calculate();
    passed=passed && output.Text=="0";
    passed=passed && composer.AddGate("Rx","0","pi");
    input.Text="norm(("+composer.Expression()+")-(|01⟩-i|10⟩)/sqrt(2))"; await Calculate();
    passed=passed && output.Text=="0";
    string savedExpression=composer.Expression(), circuitPath=args[1]+".qcircuit";
    composer.SaveCircuit(circuitPath); composer.AddGate("X","0",""); composer.OpenCircuit(circuitPath);
    passed=passed && composer.Expression()==savedExpression;
    composer.SaveCircuit(circuitPath); // Exercise atomic replacement of an existing save.
    string validCircuit=File.ReadAllText(circuitPath);
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":2,\"Steps\":[{\"Gate\":\"CNOT\",\"Wires\":[0,0]}]}");
    bool rejected=false; try {composer.OpenCircuit(circuitPath);} catch(InvalidDataException) {rejected=true;}
    passed=passed && rejected && composer.Expression()==savedExpression;
    File.WriteAllText(circuitPath,validCircuit);
    string qasm=composer.OpenQasm();
    passed=passed && qasm.Contains("h q[0];\ncx q[0], q[1];\ns q[1];\nrx(pi) q[0];") && qasm.StartsWith("OPENQASM 3.0;");
    passed=passed && QasmAngle.Translate("1/2")=="(1.0/2.0)" && QasmAngle.Translate("−π/2")=="((-pi)/2.0)";
    File.WriteAllText(args[1]+".qasm",qasm);
    composer.AddGate("Rx","0","sin(pi/3)"); bool refused=false;
    try {composer.OpenQasm();} catch(InvalidDataException){refused=true;} passed=passed && refused;
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    foreach(string name in new[]{"H","X","Y","Z","S","T","Rx","Ry","Rz","P","CNOT","CZ","SWAP","CCX"}) {
     string targets=name=="CCX" ? "2,0,1" : name=="CNOT" || name=="CZ" || name=="SWAP" ? "2,0" : "1";
     passed=passed && composer.AddGate(name,targets,"1/2");
    }
    passed=passed && composer.AddGate("CY","2,0","") && composer.AddGate("CH","2,0","") && composer.AddGate("CCZ","2,0,1","") && composer.AddGate("CSWAP","2,0,1","");
    foreach(string name in new[]{"Sdg","Tdg","SX","SXdg"}) passed=passed && composer.AddGate(name,"1","");
    passed=passed && composer.AddGate("Reset","2","");
    passed=passed && composer.AddGate("Measure","1","");
    File.WriteAllText(args[1]+".all.qasm",composer.OpenQasm());
    string expanded=composer.Expression(); composer.SaveCircuit(circuitPath); composer.OpenCircuit(circuitPath);
    passed=passed && expanded==composer.Expression() && !composer.AddGate("CSWAP","0,1","") && !composer.AddGate("CH","0,1,2","");
    foreach(string name in new[]{"CY","CH","CCZ","CSWAP"}) {
     File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
     composer.AddGate("X","2","");
     if(name=="CCZ" || name=="CSWAP") composer.AddGate("X","0","");
     if(name=="CCZ") composer.AddGate("X","1","");
     passed=passed && composer.AddGate(name,name=="CY" || name=="CH" ? "2,0" : "2,0,1","");
     string expected=name=="CY" ? "i|101⟩" : name=="CH" ? "(|001⟩+|101⟩)/sqrt(2)" : name=="CCZ" ? "-|111⟩" : "|011⟩";
     input.Text="norm(("+composer.Expression()+")-("+expected+"))"; await Calculate(); passed=passed && output.Text=="0";
    }
    File.WriteAllText(circuitPath,validCircuit);
    composer.OpenCircuit(circuitPath); passed=passed && composer.AddGate("Reset","0","");
    input.Text="purity("+composer.Expression()+")"; await Calculate(); passed=passed && output.Text=="0.5";
    passed=passed && composer.AddGate("X","0","");
    input.Text="probs("+composer.Expression()+",0)"; await Calculate(); passed=passed && output.Text=="[0; 1]";
    composer.OpenCircuit(circuitPath); passed=passed && composer.AddGate("Measure","0","");
    input.Text="purity("+composer.Expression()+")"; await Calculate(); passed=passed && output.Text=="0.5";
    passed=passed && composer.AddGate("H","0","");
    input.Text="expect(X ⊗ X,"+composer.Expression()+")"; await Calculate(); passed=passed && output.Text=="0";
    composer.Teleport();
    input.Text="ptrace("+composer.Expression()+",[0,1])"; await Calculate(); passed=passed && output.Text.Replace(" ","")=="[0.5−0.5i;0.5i0.5]";
    composer.SaveCircuit(args[1]+".teleport.qcircuit"); string teleportExpression=composer.Expression();
    composer.OpenCircuit(args[1]+".teleport.qcircuit"); passed=passed && teleportExpression==composer.Expression();
    File.WriteAllText(args[1]+".teleport.qasm",composer.OpenQasm());
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    foreach(string name in new[]{"M0-X","M1-X","M0-Z","M1-Z"}) passed=passed && composer.AddGate(name,"2,0","");
    File.WriteAllText(args[1]+".feedback.qasm",composer.OpenQasm());
    passed=passed && !composer.AddGate("M1-X","0","") && !composer.AddGate("M0-Z","0,0","");
    foreach(string name in new[]{"CP","CRx","CRy","CRz"}) {
     File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
     composer.AddGate("X","2",""); passed=passed && composer.AddGate(name,"2,0","pi");
     string expected=name=="CP" ? "|001⟩" : name=="CRx" ? "-i|101⟩" : name=="CRy" ? "|101⟩" : "-i|001⟩";
     input.Text="norm(("+composer.Expression()+")-("+expected+"))"; await Calculate(); passed=passed && output.Text=="0";
    }
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    foreach(string name in new[]{"CP","CRx","CRy","CRz"}) passed=passed && composer.AddGate(name,"2,0","pi/2");
    string rotations=composer.Expression(); composer.SaveCircuit(circuitPath); composer.OpenCircuit(circuitPath);
    passed=passed && rotations==composer.Expression();
    File.WriteAllText(args[1]+".rotations.qasm",composer.OpenQasm());
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    composer.AddGate("X","2",""); passed=passed && composer.AddGate("iSWAP","2,0","") && !composer.AddGate("iSWAP","0","");
    input.Text="norm(("+composer.Expression()+")-i|100⟩)"; await Calculate(); passed=passed && output.Text=="0";
    string exchange=composer.Expression(); composer.SaveCircuit(circuitPath); composer.OpenCircuit(circuitPath);
    passed=passed && exchange==composer.Expression(); File.WriteAllText(args[1]+".iswap.qasm",composer.OpenQasm());
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    if(composer.AddGate("ECR","0","") || composer.AddGate("ECR","0,0","") || !composer.AddGate("ECR","2,0",""))throw new Exception("ECR wire validation failed.");
    string echoed=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);
    if(echoed!=composer.Expression())throw new Exception("ECR save/open changed the circuit.");
    File.WriteAllText(args[1]+".ecr.qasm",composer.OpenQasm());
    input.Text="norm(("+echoed+")-(|001>-i|101>)/sqrt(2))";await Calculate();if(output.Text!="0")throw new Exception("ECR circuit result mismatch.");
    if(!composer.UpdateGate(0,"ECR","0,2",""))throw new Exception("ECR edit failed.");
    input.Text="norm(("+composer.Expression()+")-(|100>-i|101>)/sqrt(2))";await Calculate();if(output.Text!="0")throw new Exception("ECR reordered wire result mismatch.");
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    passed=passed && !composer.AddGate("fSim","0,2","pi") && !composer.AddGate("fSim","0,2",",pi") && !composer.AddGate("fSim","0,2","pi,0,1");
    passed=passed && composer.AddGate("fSim","2,0","pi/3, pi/4");
    string fsim=composer.Expression(); composer.SaveCircuit(circuitPath); composer.OpenCircuit(circuitPath);passed=passed && fsim==composer.Expression();
    File.WriteAllText(args[1]+".fsim.qasm",composer.OpenQasm());
    input.Text="norm(("+fsim+")-|000⟩)";await Calculate();passed=passed && output.Text=="0";
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}"); composer.OpenCircuit(circuitPath);
    passed=passed && !composer.AddGate("U3","2","pi,0") && !composer.AddGate("U3","2","pi,,0") && !composer.AddGate("U3","0,2","pi,0,0");
    passed=passed && composer.AddGate("U3","2","pi/2, 0, pi");
    input.Text="norm(("+composer.Expression()+")-(|000⟩+|001⟩)/sqrt(2))";await Calculate();passed=passed && output.Text=="0";
    string euler=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);passed=passed && euler==composer.Expression();
    passed=passed && composer.AddGate("U3","0","pi/3, pi, pi/2");
    File.WriteAllText(args[1]+".u3.qasm",composer.OpenQasm());
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
    if(composer.AddGate("R","2","pi") || composer.AddGate("R","0,2","pi,0") || !composer.AddGate("R","2","pi/3,pi/4"))throw new Exception("R parameter validation failed.");
    string equatorial=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);
    if(composer.Expression()!=equatorial)throw new Exception("R save/open changed the circuit.");
    if(!composer.UpdateGate(0,"R","2","pi/2,pi/2"))throw new Exception("R editing failed.");
    input.Text="norm(("+composer.Expression()+")-(|000>+|001>)/sqrt(2))";await Calculate();if(output.Text!="0")throw new Exception("R circuit evaluation failed.");
    if(!composer.UpdateGate(0,"R","2","pi/3,pi/4"))throw new Exception("R editing failed.");
    File.WriteAllText(args[1]+".r.qasm",composer.OpenQasm());
    foreach(string parity in new[]{"XXPlusYY","XXMinusYY"}) {
     File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
     if(composer.AddGate(parity,"0","pi/3,pi/4") || composer.AddGate(parity,"2,0","pi/3") || !composer.AddGate(parity,"2,0","pi/3,pi/4"))throw new Exception("Parity gate validation failed.");
     string parityExpression=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);
     if(composer.Expression()!=parityExpression)throw new Exception("Parity gate save/open changed the circuit.");
     File.WriteAllText(args[1]+"."+parity+".qasm",composer.OpenQasm());
     if(!composer.UpdateGate(0,parity,"2,0","pi,pi/2"))throw new Exception("Parity gate edit failed.");
     input.Text="norm(("+composer.Expression()+")-"+(parity=="XXPlusYY" ? "|000>" : "|101>")+")";await Calculate();if(output.Text!="0")throw new Exception("Parity circuit result failed.");
    }

    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
    if(!passed)throw new Exception("Smoke checks failed before the full-length circuit test.");
    for(int j=0;j<CircuitComposer.MaxSteps;j++)passed=passed && composer.AddGate("H","0","");
    string beforeEdit=composer.Expression();
    passed=passed && composer.SelectStep(0) && !composer.UpdateGate(0,"CNOT","0,0","") && !composer.UpdateGate(0,"U3","0","pi,0");
    passed=passed && !composer.UpdateGate(CircuitComposer.MaxSteps,"X","0","") && !composer.SelectStep(-1) && beforeEdit==composer.Expression();
    passed=passed && composer.UpdateGate(0,"X","0","") && !composer.AddGate("H","0","");
    if(!passed)throw new Exception("Full-length circuit editing failed.");
    string edited=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);passed=passed && edited==composer.Expression();
    input.Text="norm(("+edited+")-(|−⟩ ⊗ |00⟩))";await Calculate();passed=passed && output.Text=="0";
    if(!passed)throw new Exception("Full-length circuit calculation failed: "+output.Text);
    File.WriteAllText(args[1]+".edited.qasm",composer.OpenQasm());
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":2,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
    passed=passed && composer.AddGate("H","0","") && composer.AddGate("S","0","") && composer.AddGate("CNOT","0,1","");
    string beforeMove=composer.Expression();
    passed=passed && !composer.MoveStep(-1,0) && !composer.MoveStep(0,3) && !composer.DeleteStep(3) && beforeMove==composer.Expression();
    passed=passed && composer.SelectStep(1) && composer.MoveStep(1,0);
    input.Text="norm(("+composer.Expression()+")-(|00⟩+|11⟩)/sqrt(2))";await Calculate();passed=passed && output.Text=="0";
    passed=passed && composer.MoveStep(0,1) && beforeMove==composer.Expression();
    passed=passed && composer.DeleteStep(1);
    composer.SaveCircuit(circuitPath);string afterDelete=composer.Expression();composer.OpenCircuit(circuitPath);passed=passed && afterDelete==composer.Expression();
    File.WriteAllText(args[1]+".reordered.qasm",composer.OpenQasm());
    input.Text="norm(("+composer.Expression()+")-(|00⟩+|11⟩)/sqrt(2))";await Calculate();passed=passed && output.Text=="0";
    passed=passed && composer.DeleteStep(0) && composer.DeleteStep(0) && !composer.DeleteStep(0) && !composer.MoveStep(0,0) && composer.Expression()=="|00⟩";
    passed=passed && composer.Undo() && composer.Undo() && composer.Expression()==afterDelete;
    passed=passed && composer.Redo() && composer.Redo() && composer.Expression()=="|00⟩" && !composer.Redo();
    passed=passed && composer.Undo() && !composer.UpdateGate(9,"X","0","") && composer.Redo();
    passed=passed && composer.Undo() && composer.AddGate("X","1","") && !composer.Redo();
    string beforePreset=composer.Expression();composer.Teleport();string preset=composer.Expression();
    passed=passed && composer.Undo() && composer.Expression()==beforePreset && composer.Redo() && composer.Expression()==preset;
    input.Text="ptrace("+composer.Expression()+",[0,1])";await Calculate();passed=passed && output.Text.Replace(" ","")=="[0.5−0.5i;0.5i0.5]";
    composer.OpenCircuit(circuitPath);string openedHistory=composer.Expression();
    passed=passed && composer.Undo() && composer.Expression()==preset && composer.Redo() && composer.Expression()==openedHistory;
    passed=passed && composer.MoveStep(0,1) && composer.Undo() && composer.Expression()==openedHistory && composer.Redo();
    passed=passed && composer.UpdateGate(0,"X","1","") && composer.Undo() && composer.Undo() && composer.Expression()==openedHistory;
    string lockedPath=args[1]+".locked.qcircuit";composer.SaveCircuit(lockedPath);
    string originalLocked=File.ReadAllText(lockedPath);composer.AddGate("X","0","");
    using(var held=new FileStream(lockedPath,FileMode.Open,FileAccess.Read,FileShare.Read)) {
     bool lockRejected=false;try {composer.SaveCircuit(lockedPath);}catch(IOException){lockRejected=true;}
     passed=passed && lockRejected;
    }
    passed=passed && File.ReadAllText(lockedPath)==originalLocked;
    var transientLock=new FileStream(lockedPath,FileMode.Open,FileAccess.Read,FileShare.Read);
    var unlock=Task.Run(delegate {System.Threading.Thread.Sleep(150);transientLock.Dispose();});
    composer.SaveCircuit(lockedPath);await unlock;
    string afterLockedSave=composer.Expression();composer.OpenCircuit(lockedPath);passed=passed && composer.Expression()==afterLockedSave;
    passed=passed && Directory.GetFiles(Path.GetDirectoryName(lockedPath),Path.GetFileName(lockedPath)+".*.tmp").Length==0;
    for(int error=-1;error<3;error++) {
     composer.BitFlip(error);
     string corrected=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);passed=passed && corrected==composer.Expression();
     input.Text="tr((ptrace("+corrected+",[1,2,3,4])-density(|i⟩))^2)";await Calculate();passed=passed && output.Text=="0";
     if(error==1)File.WriteAllText(args[1]+".correction.qasm",composer.OpenQasm());
    }
    passed=passed && !composer.AddGate("M11-X","3,4","") && !composer.AddGate("M00-Z","3,3,0","");
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
    passed=passed && composer.AddGate("X","0","") && composer.AddGate("X","1","") && composer.AddGate("FSWAP","0,1","");
    input.Text="norm(("+composer.Expression()+")+|110⟩)";await Calculate();passed=passed && output.Text=="0";
    string fermionicSwap=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);passed=passed && fermionicSwap==composer.Expression();
    File.WriteAllText(args[1]+".fswap.qasm",composer.OpenQasm());
    foreach(string name in new[]{"Rxx","Ryy","Rzz","Rzx"}) {
     File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
     passed=passed && composer.AddGate(name,"2,0","pi") && !composer.AddGate(name,"0","");
     string expected=name=="Rxx" ? "-i|101⟩" : name=="Ryy" ? "i|101⟩" : name=="Rzz" ? "-i|000⟩" : "-i|100⟩";
     input.Text="norm(("+composer.Expression()+")-("+expected+"))";await Calculate();passed=passed && output.Text=="0";
    }
    File.WriteAllText(circuitPath,"{\"Version\":1,\"Qubits\":3,\"Steps\":[]}");composer.OpenCircuit(circuitPath);
    foreach(string name in new[]{"Rxx","Ryy","Rzz","Rzx"})passed=passed && composer.AddGate(name,"2,0","pi/2");
    string interactions=composer.Expression();composer.SaveCircuit(circuitPath);composer.OpenCircuit(circuitPath);passed=passed && interactions==composer.Expression();
    File.WriteAllText(args[1]+".interactions.qasm",composer.OpenQasm());
    string noisePath=args[1]+".noise.qcircuit";
    string[] noiseNames={"AD","GAD","PD","PAD","Depol","Thermal"};
    string[] noiseParameters={"3/4","3/4,1/4","3/4","1/4,1/2,1/4","1/2","1,1,ln(2),1/4"};
    string[] noiseMatrices={"[7/8,-i/4;i/4,1/8]","[11/16,-i/4;i/4,5/16]","[1/2,-i/4;i/4,1/2]","[9/16,-i/4;i/4,7/16]","[1/2,-i/4;i/4,1/2]","[5/8,-i/4;i/4,3/8]"};
    for(int n=0;n<noiseNames.Length;n++) {
     File.WriteAllText(noisePath,"{\"Version\":1,\"Qubits\":1,\"Steps\":[]}");composer.OpenCircuit(noisePath);
     if(!composer.AddGate("H","0","") || !composer.AddGate("S","0","") || !composer.AddGate(noiseNames[n],"0",noiseParameters[n]))throw new Exception("Could not add noise step: "+noiseNames[n]);
     input.Text="tr(("+composer.Expression()+"-"+noiseMatrices[n]+")^2)";await Calculate();if(output.Text!="0")throw new Exception("Incorrect noise circuit: "+noiseNames[n]+": "+output.Text);
     string noiseExpression=composer.Expression();composer.SaveCircuit(noisePath);composer.OpenCircuit(noisePath);
     if(composer.Expression()!=noiseExpression)throw new Exception("Noise circuit did not round-trip.");
     bool noiseExportRejected=false;try {composer.OpenQasm();}catch(InvalidDataException ex){noiseExportRejected=ex.Message.Contains("noise channels");}
     if(!noiseExportRejected)throw new Exception("Noise export must explicitly reject unsupported channels.");
     if(composer.AddGate(noiseNames[n],"0,1",noiseParameters[n]) || composer.AddGate(noiseNames[n],"0","") || composer.AddGate(noiseNames[n],"0",noiseParameters[n]+",0") || composer.Expression()!=noiseExpression)throw new Exception("Invalid noise edit changed the circuit.");
     if(!composer.AddGate("H","0","") || !composer.AddGate("AD","0","1/2"))throw new Exception("Could not continue a noisy circuit.");
     input.Text="tr("+composer.Expression()+")";await Calculate();if(output.Text!="1")throw new Exception("Gates or subsequent channels lost density-matrix state.");
    }
    foreach(string preparation in new[]{"Reset","Measure","M1-X"}) {
     File.WriteAllText(noisePath,"{\"Version\":1,\"Qubits\":2,\"Steps\":[]}");composer.OpenCircuit(noisePath);
     composer.AddGate("H","0","");composer.AddGate(preparation,preparation=="M1-X" ? "0,1" : "0","");composer.AddGate("Depol","1","1");
     input.Text="tr("+composer.Expression()+")";await Calculate();if(output.Text!="1")throw new Exception("Noise after "+preparation+" failed.");
    }
    File.WriteAllText(noisePath,"{\"Version\":1,\"Qubits\":1,\"Steps\":[]}");composer.OpenCircuit(noisePath);composer.AddGate("X","0","");composer.AddGate("AD","0","1");
    string beforeNoiseEdit=composer.Expression();
    if(!composer.SelectStep(1) || composer.UpdateGate(1,"PAD","0","1/2,0") || composer.Expression()!=beforeNoiseEdit || !composer.UpdateGate(1,"AD","0","1/2"))throw new Exception("Noise parameter editing failed.");
    input.Text="expect(Z,"+composer.Expression()+")";await Calculate();if(output.Text!="0")throw new Exception("Edited damping parameter was not applied.");
    composer.UpdateGate(1,"AD","0","1");
    string beforeNoiseMove=composer.Expression();composer.MoveStep(1,0);
    input.Text="expect(Z,"+composer.Expression()+")";await Calculate();if(output.Text!="−1")throw new Exception("Noise order was not preserved.");
    if(!composer.Undo() || composer.Expression()!=beforeNoiseMove || !composer.Redo())throw new Exception("Noise move undo/redo failed.");
    string validNoise=composer.Expression();
    File.WriteAllText(noisePath,"{\"Version\":1,\"Qubits\":1,\"Steps\":[{\"Gate\":\"PAD\",\"Angle\":\"1/2,0\",\"Wires\":[0]}]}");
    bool malformedNoise=false;try{composer.OpenCircuit(noisePath);}catch(InvalidDataException){malformedNoise=true;}
    if(!malformedNoise || composer.Expression()!=validNoise)throw new Exception("Malformed noise file was not rejected atomically.");
    File.WriteAllText(noisePath,"{\"Version\":1,\"Qubits\":2,\"Steps\":[]}");composer.OpenCircuit(noisePath);
    composer.AddGate("H","0","");composer.AddGate("CNOT","0,1","");composer.AddGate("GAD","1","1/4, 1/10");composer.AddGate("PD","0","1/4");composer.SaveCircuit(noisePath);
    bool mixedSchmidtRejected=false;try {composer.InspectionExpression(3,"0");}catch(InvalidDataException){mixedSchmidtRejected=true;}if(!mixedSchmidtRejected)throw new Exception("Mixed circuit accepted for Schmidt inspection.");
    input.Text=composer.InspectionExpression(4,"1");await Calculate();if(output.Text!="[0.6; 0.4]" || probabilityView.Visibility!=Visibility.Visible)throw new Exception("Noisy marginal probability inspection failed.");
    input.Text=composer.InspectionExpression(2,1);await Calculate();if(output.Text!="[0; 0; 0.2]" || blochView.Visibility!=Visibility.Visible)throw new Exception("Noisy circuit marginal Bloch view failed.");
    File.WriteAllText(circuitPath,validCircuit);
    composer.Close();
    evaluation.SelectedIndex=1; input.Text="U3(pi/3,pi/4,pi/6)"; await Calculate();
    passed=passed && resultLabel.Text=="APPROXIMATE RESULT" && matrixCells.Children.Count==4 && !output.Text.Contains("ℜ");
    var numericEntry=(ListBoxItem)history.Items[0]; evaluation.SelectedIndex=0;
    numericEntry.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left) {RoutedEvent=Control.MouseDoubleClickEvent});
    passed=passed && evaluation.SelectedIndex==1;
    evaluation.SelectedIndex=0; input.Text="sqrt(2)"; await Calculate();
    input.Text="\uFEFFnorm(H\u2009|−⟩)";await Calculate();passed=passed && output.Text=="1";
    mode.SelectedIndex=1;input.Text="\uFEFF  quantum:norm(|->)";await Calculate();passed=passed && output.Text=="1";
    mode.SelectedIndex=0;input.Text="sqrt(2)";await Calculate();
    passed=passed && resultLabel.Text=="EXACT RESULT" && output.Text.Contains("√");
    string sessionPath=args[1]+".qsession";
    var originalSession=CaptureSession();string sessionSnapshot=new JavaScriptSerializer().Serialize(originalSession);
    SessionStore.Save(sessionPath,originalSession);SessionStore.Save(sessionPath,originalSession);
    input.Text="draft changed";mode.SelectedIndex=1;evaluation.SelectedIndex=1;history.Items.Clear();
    OpenSession(sessionPath);
    if(new JavaScriptSerializer().Serialize(CaptureSession())!=sessionSnapshot || resultLabel.Text!="SESSION RESTORED" || active!=null || !run.IsEnabled)throw new Exception("Calculation session did not restore exactly or evaluated automatically.");
    for(int j=0;j<history.Items.Count;j++) {
     var restored=(ListBoxItem)history.Items[j];var record=(SessionEntry)restored.Tag;
     restored.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left) {RoutedEvent=Control.MouseDoubleClickEvent});
     if(input.Text!=record.Expression || mode.SelectedIndex!=record.Mode || evaluation.SelectedIndex!=record.Evaluation)throw new Exception("Restored history lost its expression or modes.");
    }
    OpenSession(sessionPath);string validSessionText=File.ReadAllText(sessionPath);
    CheckInvalidSessions(sessionPath,args[1],sessionSnapshot);
    File.WriteAllText(sessionPath,validSessionText);
    using(var locked=new FileStream(sessionPath,FileMode.Open,FileAccess.Read,FileShare.Read)) {
     bool sessionLockRejected=false;try {SessionStore.Save(sessionPath,originalSession);}catch(IOException){sessionLockRejected=true;}
     if(!sessionLockRejected)throw new Exception("Saving a locked session unexpectedly succeeded.");
    }
    if(File.ReadAllText(sessionPath)!=validSessionText || Directory.GetFiles(Path.GetDirectoryName(sessionPath),Path.GetFileName(sessionPath)+".*.tmp").Length!=0)throw new Exception("Failed session save damaged the original or left temporary files.");
    var badSession=new CalculationSession {Version=1,Expression=new string('x',32001),Mode=0,Evaluation=0,History=new SessionEntry[0]};
    bool tooLongRejected=false;try {SessionStore.Save(sessionPath,badSession);}catch(InvalidDataException){tooLongRejected=true;}
    if(!tooLongRejected || File.ReadAllText(sessionPath)!=validSessionText)throw new Exception("Oversized session draft was not safely rejected.");
    OpenSession(sessionPath);await Calculate();if(output.Text!=originalSession.History[0].Result)throw new Exception("Restored expression did not recompute correctly.");
    await CheckStateEditor(args[1]+".states.png");
    mode.SelectedIndex=0;evaluation.SelectedIndex=0;input.Text="<Bell|after CZ>";await Calculate();
    if(output.Text!="0")throw new Exception("Named-state GUI overlap failed: "+output.Text);
    input.Text="<Bell|Bell>";await Calculate();if(output.Text!="1")throw new Exception("Named-state GUI self overlap failed.");
    var namedHistory=(ListBoxItem)history.Items[0];
    SessionStore.Save(sessionPath,CaptureSession());states[0].Expression="2|0>";
    namedHistory.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,Environment.TickCount,MouseButton.Left) {RoutedEvent=Control.MouseDoubleClickEvent});
    if(states[0].Expression!="|Phi+>")throw new Exception("History did not restore its state definitions.");
    states=new StateDefinition[0];OpenSession(sessionPath);await Calculate();
    if(states.Length!=2 || states[1].Name!="after CZ" || output.Text!="1")throw new Exception("Saved named states did not restore and recalculate.");
    states=new[]{new StateDefinition {Name="psi(alpha)",Expression="cos(alpha)|0>+sin(alpha)|1>"}};RefreshStates();
    input.Text="<psi(0)|psi(pi/2)>";await Calculate();
    if(output.Text!="0")throw new Exception("Parameterized-state GUI overlap failed: "+output.Text);
    SessionStore.Save(sessionPath,CaptureSession());states=new StateDefinition[0];OpenSession(sessionPath);await Calculate();
    if(states.Length!=1 || states[0].Name!="psi(alpha)" || output.Text!="0")throw new Exception("Saved state family did not restore and recalculate.");
    SessionStore.Save(sessionPath,originalSession);OpenSession(sessionPath);
    if(copyText!=null)throw new Exception("Restoring a session retained a stale copied result.");
    mode.SelectedIndex=0;evaluation.SelectedIndex=0;
    foreach(string matrixExpression in new[]{"I","[1+i,2;3,4-i]","basis(0,1)","basis(0,256)"}) {
     input.Text=matrixExpression;await Calculate();string shown=output.Text, copied=copyText;
     if(String.IsNullOrEmpty(copied))throw new Exception("Matrix copy expression is missing.");
     input.Text=copied;await Calculate();
     if(output.Text!=shown || copyText!=copied)throw new Exception("Copying a matrix changed its value or shape.");
    }
    input.Text="H(";await Calculate();
    if(resultLabel.Text!="CHECK YOUR EXPRESSION" || copyText!=null)throw new Exception("A failed calculation retained stale matrix copy text.");
    File.WriteAllText(args[1]+".txt",passed ? "PASS: GUI matrices, TeX, history, errors, unit conversion, example search, circuit calculation, save/open, and invalid-file preservation." : "FAIL: "+output.Text);
    Environment.ExitCode=passed ? 0 : 1; window.Close();
    } catch(Exception ex) {
     File.WriteAllText(args[1]+".txt","FAIL: "+ex.ToString());Environment.ExitCode=1;window.Close();
    }
   };
  }
  app.Run(window);
 }
 static async Task CheckStateEditor(string screenshotPath) {
    states=new StateDefinition[0];
    var stateEditor=StateEditor();stateEditor.Show();
    ((Button)stateEditor.FindName("AddBell")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    var stateGrid=(DataGrid)stateEditor.FindName("Definitions");
    if(stateGrid.Items.Count!=2 || states.Length!=0)throw new Exception("State editor changed the workspace before Apply.");
    ((Button)stateEditor.FindName("Cancel")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(states.Length!=0)throw new Exception("State editor Cancel changed definitions.");
    stateEditor=StateEditor();stateEditor.Show();
    ((Button)stateEditor.FindName("AddBell")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    stateGrid=(DataGrid)stateEditor.FindName("Definitions");
    ((Button)stateEditor.FindName("AddBell")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(stateGrid.Items.Count!=2 || String.IsNullOrEmpty(((TextBlock)stateEditor.FindName("Error")).Text))throw new Exception("Duplicate Bell example was not rejected.");
    stateGrid.SelectedIndex=1;((Button)stateEditor.FindName("MoveUp")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(((StateDefinition)stateGrid.Items[0]).Name!="after CZ")throw new Exception("Move state up failed.");
    ((Button)stateEditor.FindName("MoveDown")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    ((Button)stateEditor.FindName("Add")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    ((Button)stateEditor.FindName("Remove")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(stateGrid.Items.Count!=2)throw new Exception("Add/remove state failed.");
    ((StateDefinition)stateGrid.Items[1]).Name="Bell";
    ((Button)stateEditor.FindName("Apply")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(!stateEditor.IsVisible || states.Length!=0)throw new Exception("Invalid state edits were applied.");
    ((StateDefinition)stateGrid.Items[1]).Name="after CZ";stateGrid.Items.Refresh();
    stateEditor.Width=600;stateEditor.Height=520;stateEditor.UpdateLayout();await Task.Delay(100);stateEditor.UpdateLayout();
    if(stateGrid.Columns[1].ActualWidth<240)throw new Exception("State expression column collapsed at minimum window size.");
    var editorBitmap=new System.Windows.Media.Imaging.RenderTargetBitmap((int)stateEditor.ActualWidth,(int)stateEditor.ActualHeight,96,96,PixelFormats.Pbgra32);editorBitmap.Render(stateEditor);
    var editorEncoder=new System.Windows.Media.Imaging.PngBitmapEncoder();editorEncoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(editorBitmap));using(var editorFile=File.Create(screenshotPath))editorEncoder.Save(editorFile);
    ((Button)stateEditor.FindName("Apply")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    if(stateEditor.IsVisible || states.Length!=2 || Find<Button>("EditStates").Content.ToString()!="States · 2")throw new Exception("State editor Apply failed.");
 }
 static void Example(string name,string expression) { Find<Button>(name).Click += delegate { mode.SelectedIndex=0; input.Text=expression; input.Focus(); input.CaretIndex=input.Text.Length; }; }
 static ListBoxItem HistoryItem(SessionEntry record,bool saved) {
  var item=new ListBoxItem {Content=new TextBlock {Text=(saved ? "Saved · " : "")+record.Expression+"   =   "+record.Result,TextWrapping=TextWrapping.Wrap,FontSize=14,Margin=new Thickness(4,7,4,7)},Tag=record};
  item.MouseDoubleClick+=delegate {states=SessionStore.CopyStates(record.States);matrices=MatrixDeclarations.Copy(record.Matrices);bases=BasisDeclarations.Copy(record.Bases);RefreshStates();input.Text=record.Expression;mode.SelectedIndex=record.Mode;evaluation.SelectedIndex=record.Evaluation;input.Focus();};return item;
 }
 static CalculationSession CaptureSession() {
  var entries=new SessionEntry[history.Items.Count];for(int j=0;j<entries.Length;j++)entries[j]=(SessionEntry)((ListBoxItem)history.Items[j]).Tag;
  var snapshots=new SessionEntry[entries.Length];
  for(int j=0;j<entries.Length;j++)snapshots[j]=new SessionEntry {Expression=entries[j].Expression,Result=entries[j].Result,Mode=entries[j].Mode,Evaluation=entries[j].Evaluation,States=SessionStore.CopyStates(entries[j].States),Matrices=MatrixDeclarations.Copy(entries[j].Matrices),Bases=BasisDeclarations.Copy(entries[j].Bases)};
  return new CalculationSession {Version=5,Expression=input.Text,Mode=mode.SelectedIndex,Evaluation=evaluation.SelectedIndex,History=snapshots,States=SessionStore.CopyStates(states),Matrices=MatrixDeclarations.Copy(matrices),Bases=BasisDeclarations.Copy(bases)};
 }
 static bool SameSnapshotValue(object left,object right) {
  var leftObject=left as System.Collections.Generic.IDictionary<string,object>;var rightObject=right as System.Collections.Generic.IDictionary<string,object>;
  if(leftObject!=null || rightObject!=null) {
   if(leftObject==null || rightObject==null || leftObject.Count!=rightObject.Count)return false;
   foreach(var entry in leftObject) {object value;if(!rightObject.TryGetValue(entry.Key,out value) || !SameSnapshotValue(entry.Value,value))return false;}
   return true;
  }
  var leftArray=left as System.Collections.IList;var rightArray=right as System.Collections.IList;
  if(leftArray!=null || rightArray!=null) {
   if(leftArray==null || rightArray==null || leftArray.Count!=rightArray.Count)return false;
   for(int i=0;i<leftArray.Count;i++)if(!SameSnapshotValue(leftArray[i],rightArray[i]))return false;
   return true;
  }
  return Object.Equals(left,right);
 }
 static bool SameSessionSnapshot(string left,string right) {
  // Serializer reflection order can change after allocation/GC. Object key
  // order is not session state; history, declaration and array order still is.
  var serializer=new JavaScriptSerializer();
  return SameSnapshotValue(serializer.DeserializeObject(left),serializer.DeserializeObject(right));
 }
 static void CheckInvalidSessions(string path,string diagnostics,string expectedSnapshot) {
  const string fixture="{\"Expression\":\"draft\",\"History\":[{\"Result\":\"1\",\"States\":[]},{\"Result\":\"2\",\"States\":[]}]}";
  const string reordered="{\"History\":[{\"States\":[],\"Result\":\"1\"},{\"States\":[],\"Result\":\"2\"}],\"Expression\":\"draft\"}";
  if(!SameSessionSnapshot(fixture,reordered) || SameSessionSnapshot(fixture,reordered.Replace("draft","changed")) ||
     SameSessionSnapshot(fixture,"{\"Expression\":\"draft\",\"History\":[{\"Result\":\"2\",\"States\":[]},{\"Result\":\"1\",\"States\":[]}]}") ||
     SameSessionSnapshot(fixture,"{\"Expression\":\"draft\",\"History\":[]}") ||
     SameSessionSnapshot("{\"States\":null}","{\"States\":[]}"))
   throw new Exception("Session snapshot comparison lost values or array order.");
  var serializer=new JavaScriptSerializer();
  string before=serializer.Serialize(CaptureSession());
  if(!SameSessionSnapshot(before,expectedSnapshot)) {
   File.WriteAllText(diagnostics+".before.json",expectedSnapshot);File.WriteAllText(diagnostics+".after.json",before);
   throw new Exception("Workspace differed before invalid-session attempts.");
  }
  int index=0;
  foreach(string bad in new[]{"{", "null", "{\"Version\":2}", "{\"Version\":1,\"Expression\":\"x\",\"Mode\":7,\"Evaluation\":0,\"History\":[]}", "{\"Version\":1,\"Expression\":\"x\",\"History\":[null]}", new string('x',8*1024*1024+1)}) {
   File.WriteAllText(path,bad);Exception rejected=null;
   try {OpenSession(path);}catch(Exception ex) {rejected=ex;}
   string after=serializer.Serialize(CaptureSession());
   bool unchanged=SameSessionSnapshot(after,before);
   if(rejected==null || !unchanged) {
    File.WriteAllText(diagnostics+".before.json",before);File.WriteAllText(diagnostics+".after.json",after);
    throw new Exception("Invalid-session case "+index+" ("+bad.Length+" characters): rejected="+(rejected!=null)+", workspace unchanged="+unchanged+". Rejection: "+(rejected==null ? "none" : rejected.GetType().Name));
   }
   ++index;
  }
 }
 static void OpenSession(string path) {
  var session=SessionStore.Load(path);
  var restoredStates=SessionStore.CopyStates(session.States);
  var restoredMatrices=MatrixDeclarations.Copy(session.Matrices);
  var restoredBases=BasisDeclarations.Copy(session.Bases);
  var items=new ListBoxItem[session.History.Length];for(int j=0;j<items.Length;j++)items[j]=HistoryItem(session.History[j],true);
  history.Items.Clear();foreach(var item in items)history.Items.Add(item);
  states=restoredStates;matrices=restoredMatrices;bases=restoredBases;
  RefreshStates();
  input.Text=session.Expression;mode.SelectedIndex=session.Mode;evaluation.SelectedIndex=session.Evaluation;
  matrixView.Visibility=Visibility.Collapsed;matrixCaption.Visibility=Visibility.Collapsed;probabilityView.Visibility=Visibility.Collapsed;blochView.Visibility=Visibility.Collapsed;
  copyText=null;output.Visibility=Visibility.Visible;output.Text="Choose Calculate to evaluate the restored expression.";resultLabel.Text="SESSION RESTORED";
  status.Text="Opened "+Path.GetFileName(path)+" · Saved results are snapshots; double-click a history item to reuse it.";
 }
 static void ShowProbabilities(CalculationResult result) {
  probabilityView.Children.Clear();probabilityView.Visibility=Visibility.Collapsed;
  if(result.probabilities==null || result.probabilities.Length<2 || result.probabilities.Length>64)return;
  double total=0;foreach(double p in result.probabilities) {if(Double.IsNaN(p) || Double.IsInfinity(p) || p<0 || p>1)return;total+=p;}
  if(Math.Abs(total-1)>1e-9)return;
  probabilityView.Children.Add(new TextBlock {Text="MEASUREMENT PROBABILITIES",FontSize=11,FontWeight=FontWeights.SemiBold,Foreground=WorkspaceTheme.Muted});
  int count=result.probabilities.Length,bits=0;while((1 << bits)<count)bits++;
  bool powerOfTwo=(1 << bits)==count,binary=binaryProbabilityLabels && powerOfTwo;
  var options=new WrapPanel {Margin=new Thickness(0,5,0,10)};
  options.Children.Add(new TextBlock {Text="Outcome labels",FontSize=12,VerticalAlignment=VerticalAlignment.Center,Margin=new Thickness(0,0,8,0)});
  var labels=new ComboBox {Width=110,Padding=new Thickness(6),IsEnabled=powerOfTwo,ToolTip=powerOfTwo ? "Change how indices are written. Probabilities and outcome order stay the same." : "Binary labels are available for a power-of-two outcome count."};
  labels.Items.Add("Decimal");labels.Items.Add("Binary");labels.SelectedIndex=binary ? 1 : 0;
  System.Windows.Automation.AutomationProperties.SetName(labels,"Probability outcome label format");
  labels.SelectionChanged+=delegate {bool restoreFocus=labels.IsKeyboardFocusWithin;binaryProbabilityLabels=labels.SelectedIndex==1;ShowProbabilities(result);if(restoreFocus)((ComboBox)((WrapPanel)probabilityView.Children[1]).Children[1]).Focus();};
  options.Children.Add(labels);
  options.Children.Add(new TextBlock {Text="Approximate percentages · values above",FontSize=12,VerticalAlignment=VerticalAlignment.Center,Margin=new Thickness(12,0,0,0)});
  probabilityView.Children.Add(options);
  var bars=new StackPanel();
  for(int index=0;index<result.probabilities.Length;index++) {
   double p=result.probabilities[index];var row=new Grid {Margin=new Thickness(0,3,0,3),Height=25};
   row.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(binary ? 78 : 50)});row.ColumnDefinitions.Add(new ColumnDefinition());row.ColumnDefinitions.Add(new ColumnDefinition {Width=new GridLength(75)});
   string outcome=binary ? Convert.ToString(index,2).PadLeft(bits,'0') : index.ToString();
   var label=new TextBlock {Text=outcome,VerticalAlignment=VerticalAlignment.Center,FontFamily=new FontFamily("Consolas")};row.Children.Add(label);
   var fill=new Border {Background=WorkspaceTheme.Accent,CornerRadius=new CornerRadius(6),Height=12,HorizontalAlignment=HorizontalAlignment.Left};
   var track=new Border {Background=WorkspaceTheme.Raised,CornerRadius=new CornerRadius(6),Height=12,VerticalAlignment=VerticalAlignment.Center,Child=fill};
   track.SizeChanged+=delegate {fill.Width=Math.Max(0,track.ActualWidth*p);};Grid.SetColumn(track,1);row.Children.Add(track);
   string percent=p.ToString("0.##%",System.Globalization.CultureInfo.InvariantCulture);
   var value=new TextBlock {Text=percent,HorizontalAlignment=HorizontalAlignment.Right,VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(value,2);row.Children.Add(value);
   string description="Outcome "+index+(binary ? " (binary "+outcome+")" : "");
   System.Windows.Automation.AutomationProperties.SetName(row,description+": "+percent);row.ToolTip=description+": "+p.ToString("G17",System.Globalization.CultureInfo.InvariantCulture);
   bars.Children.Add(row);
  }
  probabilityView.Children.Add(new ScrollViewer {Content=bars,MaxHeight=210,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled});
  probabilityView.Visibility=Visibility.Visible;
 }
 static void ShowBloch(CalculationResult result) {
  blochView.Children.Clear();blochView.Visibility=Visibility.Collapsed;
  if(result.bloch==null || result.bloch.Length!=3)return;
  double lengthSquared=0;foreach(double v in result.bloch) {if(Double.IsNaN(v) || Double.IsInfinity(v))return;lengthSquared+=v*v;}
  if(lengthSquared>1+1e-10)return;
  blochView.Children.Add(new TextBlock {Text="BLOCH SPHERE",FontSize=11,FontWeight=FontWeights.SemiBold,Foreground=WorkspaceTheme.Muted});
  blochView.Children.Add(new TextBlock {Text="Single-qubit state · approximate 3D projection · coordinates above",FontSize=12,Margin=new Thickness(0,5,0,0)});
  var layout=new WrapPanel();blochView.Children.Add(layout);
  var canvas=new Canvas {Width=280,Height=245};layout.Children.Add(canvas);
  var blue=WorkspaceTheme.Accent;var grid=WorkspaceTheme.Border;
  double cosine=Math.Cos(blochAngle),sine=Math.Sin(blochAngle);
  Func<double,double,double,Point> project=(x,y,z)=>new Point(140+90*(cosine*x+sine*y),120+90*((-sine*x+cosine*y)/Math.Sqrt(3)-z*Math.Sqrt(2.0/3)));
  var shell=new System.Windows.Shapes.Ellipse {Width=180,Height=180,Fill=new RadialGradientBrush(WorkspaceTheme.Raised.Color,WorkspaceTheme.Input.Color),Stroke=grid,StrokeThickness=1};Canvas.SetLeft(shell,50);Canvas.SetTop(shell,30);canvas.Children.Add(shell);
  for(int plane=0;plane<3;plane++) {
   var circle=new System.Windows.Shapes.Polyline {Stroke=grid,StrokeThickness=1};
   for(int k=0;k<=72;k++) {double theta=2*Math.PI*k/72,c=Math.Cos(theta),s=Math.Sin(theta);circle.Points.Add(plane==0 ? project(c,s,0) : plane==1 ? project(c,0,s) : project(0,c,s));}
   canvas.Children.Add(circle);
  }
  Action<Point,Point,Brush,double,bool> line=(a,b,color,width,dashed)=>canvas.Children.Add(new System.Windows.Shapes.Line {X1=a.X,Y1=a.Y,X2=b.X,Y2=b.Y,Stroke=color,StrokeThickness=width,StrokeDashArray=dashed ? new DoubleCollection {3,3} : null});
  string[] labels={"+X","+Y","+Z · |0⟩"};
  for(int axis=0;axis<3;axis++) {
   Point a=project(axis==0 ? -1.1 : 0,axis==1 ? -1.1 : 0,axis==2 ? -1.1 : 0),b=project(axis==0 ? 1.1 : 0,axis==1 ? 1.1 : 0,axis==2 ? 1.1 : 0);
   line(a,b,WorkspaceTheme.Muted,1,true);
   var label=new TextBlock {Text=labels[axis],FontSize=12,Foreground=WorkspaceTheme.Muted};Canvas.SetLeft(label,b.X+5);Canvas.SetTop(label,b.Y-10);canvas.Children.Add(label);
  }
  Point origin=project(0,0,0),tip=project(result.bloch[0],result.bloch[1],result.bloch[2]);line(origin,tip,blue,3,false);
  double dx=tip.X-origin.X,dy=tip.Y-origin.Y,projected=Math.Sqrt(dx*dx+dy*dy);
  if(projected>8) {
   double ux=dx/projected,uy=dy/projected;
   var arrow=new System.Windows.Shapes.Polygon {Fill=blue,Points=new PointCollection {tip,new Point(tip.X-10*ux+4*uy,tip.Y-10*uy-4*ux),new Point(tip.X-10*ux-4*uy,tip.Y-10*uy+4*ux)}};canvas.Children.Add(arrow);
  }
  var point=new System.Windows.Shapes.Ellipse {Width=8,Height=8,Fill=blue};Canvas.SetLeft(point,tip.X-4);Canvas.SetTop(point,tip.Y-4);canvas.Children.Add(point);
  var details=new StackPanel {Margin=new Thickness(12,25,0,0),MinWidth=190};layout.Children.Add(details);
  var culture=System.Globalization.CultureInfo.InvariantCulture;
  for(int axis=0;axis<3;axis++)details.Children.Add(new TextBlock {Text="xyz"[axis]+"   "+result.bloch[axis].ToString("0.######",culture),FontFamily=new FontFamily("Consolas"),FontSize=17,Margin=new Thickness(0,4,0,4)});
  double radius=Math.Sqrt(Math.Min(1,lengthSquared));
  details.Children.Add(new TextBlock {Text="Length  "+radius.ToString("0.######",culture),FontSize=13,Margin=new Thickness(0,12,0,4)});
  details.Children.Add(new TextBlock {Text="Purity  "+((1+Math.Min(1,lengthSquared))/2).ToString("0.######",culture),FontSize=13});
  details.Children.Add(new TextBlock {Text="Pure states: length 1\nMaximally mixed: center",FontSize=12,Margin=new Thickness(0,12,0,0)});
  var controls=new WrapPanel {Margin=new Thickness(0,8,0,0)};details.Children.Add(controls);
  var left=new Button {Content="↶",ToolTip="Rotate view left",Padding=new Thickness(8,3,8,3),Margin=new Thickness(0,0,5,0)};
  var right=new Button {Content="↷",ToolTip="Rotate view right",Padding=new Thickness(8,3,8,3),Margin=new Thickness(0,0,5,0)};
  var reset=new Button {Content="Reset view",Padding=new Thickness(8,3,8,3),Margin=new Thickness(0)};
  System.Windows.Automation.AutomationProperties.SetName(left,"Rotate Bloch view left");System.Windows.Automation.AutomationProperties.SetName(right,"Rotate Bloch view right");
  controls.Children.Add(left);controls.Children.Add(right);controls.Children.Add(reset);
  left.Click+=delegate {blochAngle-=Math.PI/8;ShowBloch(result);};right.Click+=delegate {blochAngle+=Math.PI/8;ShowBloch(result);};reset.Click+=delegate {blochAngle=Math.PI/4;ShowBloch(result);};
  System.Windows.Automation.AutomationProperties.SetName(canvas,"Bloch vector x="+result.bloch[0].ToString("G6",culture)+", y="+result.bloch[1].ToString("G6",culture)+", z="+result.bloch[2].ToString("G6",culture));
  blochView.Visibility=Visibility.Visible;
 }
 static void ShowResult(CalculationResult result) {
  ShowProbabilities(result);
  ShowBloch(result);
  output.Text=result.display_text ?? result.text;
  copyText=result.copy_text ?? result.text;
  resultLabel.Text=result.approximate ? "APPROXIMATE RESULT" : "EXACT RESULT";
  matrixCells.Children.Clear(); matrixCells.RowDefinitions.Clear(); matrixCells.ColumnDefinitions.Clear();
  bool matrix=result.rows>0 && result.columns>0 && result.cells!=null && result.cells.Length==result.rows;
  matrixView.Visibility=matrix ? Visibility.Visible : Visibility.Collapsed;
  matrixCaption.Visibility=matrix ? Visibility.Visible : Visibility.Collapsed;
  output.Visibility=matrix ? Visibility.Collapsed : Visibility.Visible;
  if(!matrix) return;
  matrixCaption.Text=result.rows+" × "+result.columns+" matrix";
  for(int c=0;c<result.columns;c++) matrixCells.ColumnDefinitions.Add(new ColumnDefinition {Width=GridLength.Auto});
  for(int r=0;r<result.rows;r++) {
   if(result.cells[r].Length!=result.columns) throw new Exception("The backend returned an incomplete matrix.");
   matrixCells.RowDefinitions.Add(new RowDefinition {Height=GridLength.Auto});
   for(int c=0;c<result.columns;c++) {
    var cell=new TextBox {Text=result.cells[r][c], IsReadOnly=true, Background=Brushes.Transparent, BorderThickness=new Thickness(0), Padding=new Thickness(12,2,12,2), MinWidth=45, FontFamily=new FontFamily("Cambria Math"), FontSize=23, HorizontalContentAlignment=HorizontalAlignment.Center, ToolTip=result.cells[r][c]};
    System.Windows.Automation.AutomationProperties.SetName(cell,"Row "+(r+1)+", column "+(c+1));
    Grid.SetRow(cell,r); Grid.SetColumn(cell,c); matrixCells.Children.Add(cell);
   }
  }
 }
 static async Task Calculate(int? testTimeoutMilliseconds=null) {
  if(!run.IsEnabled || String.IsNullOrWhiteSpace(input.Text)) return;
  string expression=input.Text.Trim();
  if(Encoding.UTF8.GetByteCount(expression)>32000) { status.Text="Please keep expressions below 32 KB."; return; }
  int calculationMode=mode.SelectedIndex, calculationEvaluation=evaluation.SelectedIndex;
  var calculationMatrices=MatrixDeclarations.Copy(matrices);
  var calculationBases=BasisDeclarations.Copy(bases);
  string request;
  try {request=calculationMode==0 ? "quantum:"+MatrixDeclarations.Apply(BasisDeclarations.Apply(expression,calculationBases),calculationMatrices) : expression;}
  catch(Exception ex) {copyText=null;matrixView.Visibility=Visibility.Collapsed;matrixCaption.Visibility=Visibility.Collapsed;probabilityView.Visibility=Visibility.Collapsed;blochView.Visibility=Visibility.Collapsed;output.Visibility=Visibility.Visible;output.Text=ex.Message;resultLabel.Text="CHECK YOUR EXPRESSION";status.Text="Edit the expression or matrix dimensions and try again.";return;}
  var calculationStates=SessionStore.CopyStates(states);
  byte[] requestBytes;
  try {requestBytes=calculationStates.Length==0 ? Encoding.UTF8.GetBytes(request) : SessionStore.StateRequest(calculationStates,request);}
  catch(Exception ex) {status.Text=ex.Message;return;}
  bool chart=calculationMode==0 && System.Text.RegularExpressions.Regex.IsMatch(expression,@"^probs\s*\(");
  bool sphere=calculationMode==0 && System.Text.RegularExpressions.Regex.IsMatch(expression,@"^bloch\s*\(");
  int seconds=new[]{15,60,180,600}[timeAllowance.SelectedIndex];
  int deadline=testTimeoutMilliseconds ?? seconds*1000;
  var cancellation=new CancellationTokenSource();calculationCancellation=cancellation;
  run.IsEnabled=false;cancel.IsEnabled=true;timeAllowance.IsEnabled=false; status.Text="Calculating… · "+seconds+" second allowance"; resultLabel.Text="RESULT";
  Find<Button>("OpenSession").IsEnabled=false;Find<Button>("SaveSession").IsEnabled=false;
  Find<Button>("EditStates").IsEnabled=false;Find<Button>("EditMatrices").IsEnabled=false;Find<Button>("EditBases").IsEnabled=false;
  try {
   runningWorker=Task.Run(async delegate {
    using(var process=new Process()) {
     process.StartInfo=new ProcessStartInfo(Path.Combine(root,"quantum-worker.exe"),(calculationEvaluation==1 ? "--json --approx" : "--json")+(chart ? " --probabilities" : "")+(sphere ? " --bloch" : "")+(calculationStates.Length>0 ? " --states" : "")) { UseShellExecute=false, CreateNoWindow=true, RedirectStandardInput=true, RedirectStandardOutput=true, RedirectStandardError=true, StandardOutputEncoding=Encoding.UTF8, StandardErrorEncoding=Encoding.UTF8, WorkingDirectory=root };
     process.StartInfo.EnvironmentVariables["QALCULATE_DEFINITIONS_DIR"]=Path.Combine(root,"data");
     cancellation.Token.ThrowIfCancellationRequested();
     process.Start(); active=process;
     var elapsed=Stopwatch.StartNew();
     try {
     var stdout=process.StandardOutput.ReadToEndAsync(); var stderr=process.StandardError.ReadToEndAsync();
     process.StandardInput.BaseStream.Write(requestBytes,0,requestBytes.Length); process.StandardInput.Close();
     while(!process.WaitForExit(100)) {
      cancellation.Token.ThrowIfCancellationRequested();
      if(elapsed.ElapsedMilliseconds>=deadline)throw new TimeoutException("Calculation exceeded the time allowance. Choose a longer allowance or simplify the expression.");
     }
     cancellation.Token.ThrowIfCancellationRequested();
     string value=await stdout, errors=await stderr;
     if(process.ExitCode!=0) throw new Exception(String.IsNullOrWhiteSpace(errors) ? "The expression could not be evaluated." : errors.Trim());
     return new [] {value.Trim(),errors.Trim()};
     } finally {
      if(!process.HasExited){process.Kill();process.WaitForExit();}
      active=null;
     }
    }
   });
   string[] response=await runningWorker;
   cancellation.Token.ThrowIfCancellationRequested();
   var result=new JavaScriptSerializer().Deserialize<CalculationResult>(response[0]);
   ShowResult(result);
   status.Text=response[1].Length==0 ? (result.approximate ? "Complete · Approximate arithmetic" : "Complete · Exact arithmetic")+" · Leftmost qubit is subsystem 0" : response[1];
   string preview=result.display_text ?? result.text;
   if(preview.Length>32768){int end=32767;if(Char.IsHighSurrogate(preview[end-1]))end--;preview=preview.Substring(0,end)+"…";}
   var entry=HistoryItem(new SessionEntry {Expression=expression,Result=preview,Mode=calculationMode,Evaluation=calculationEvaluation,States=calculationStates,Matrices=calculationMatrices,Bases=calculationBases},false);
   history.Items.Insert(0,entry); if(history.Items.Count>50) history.Items.RemoveAt(50);
  } catch(OperationCanceledException) {
   blochView.Visibility=Visibility.Collapsed;probabilityView.Visibility=Visibility.Collapsed;matrixView.Visibility=Visibility.Collapsed;matrixCaption.Visibility=Visibility.Collapsed;output.Visibility=Visibility.Visible;
   copyText=null;resultLabel.Text="CANCELLED";output.Text="Calculation cancelled.";status.Text="Stopped · Your expression is ready to edit or run again.";
  } catch(Exception ex) { copyText=null;blochView.Visibility=Visibility.Collapsed;probabilityView.Visibility=Visibility.Collapsed;matrixView.Visibility=Visibility.Collapsed; matrixCaption.Visibility=Visibility.Collapsed; output.Visibility=Visibility.Visible; resultLabel.Text=ex is TimeoutException ? "TIME ALLOWANCE REACHED" : "CHECK YOUR EXPRESSION"; output.Text=ex.Message; status.Text="Calculation stopped. Edit the expression and try again."; }
  finally { active=null;runningWorker=null;calculationCancellation=null;cancellation.Dispose();cancel.IsEnabled=false;timeAllowance.IsEnabled=true; run.IsEnabled=true;Find<Button>("OpenSession").IsEnabled=true;Find<Button>("SaveSession").IsEnabled=true;Find<Button>("EditStates").IsEnabled=true;Find<Button>("EditMatrices").IsEnabled=true;Find<Button>("EditBases").IsEnabled=true; }
 }
}

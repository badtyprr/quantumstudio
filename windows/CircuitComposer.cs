// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using Path = System.IO.Path;

class CircuitComposer : Window {
 public const int MaxSteps=512;
 public const int MaxQubits=25;
 public const int MaxExactQubits=10;
 public class Step { public string Gate, Angle; public int[] Wires; }
 public class CircuitFile { public int Version, Qubits; public Step[] Steps; }
 readonly List<Step> steps=new List<Step>();
 readonly ComboBox qubits=new ComboBox(), gate=new ComboBox();
 readonly TextBox wires=new TextBox {Text="0",Width=95}, angle=new TextBox {Text="pi/2",Width=130};
 readonly TextBlock status=new TextBlock {TextWrapping=TextWrapping.Wrap};
 readonly TextBlock parameterHelp=new TextBlock {FontSize=12,TextWrapping=TextWrapping.Wrap};
 readonly ComboBox resultView=new ComboBox {Width=180};
 readonly TextBlock partitionHelp=new TextBlock {Text="Side A: comma-separated wires, e.g. 0,2. All other wires form side B. Pure circuits only.",TextWrapping=TextWrapping.Wrap,FontSize=12,Visibility=Visibility.Collapsed};
 readonly TextBox resultWire=new TextBox {Text="0",Width=120,IsEnabled=false};
 readonly TextBox expression=new TextBox {IsReadOnly=true,TextWrapping=TextWrapping.Wrap,FontSize=16,MaxHeight=100,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
 readonly Canvas diagram=new Canvas();
 readonly ScrollViewer page=new ScrollViewer {VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled,HorizontalContentAlignment=HorizontalAlignment.Stretch};
 readonly ScrollViewer diagramView=new ScrollViewer {HorizontalScrollBarVisibility=ScrollBarVisibility.Auto,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
 readonly Slider zoom=new Slider {Minimum=0.05,Maximum=1.5,Value=1,Width=105,SmallChange=0.05,LargeChange=0.25,VerticalAlignment=VerticalAlignment.Center};
 readonly TextBlock zoomLabel=new TextBlock {Text="100%",Width=42,VerticalAlignment=VerticalAlignment.Center,TextAlignment=TextAlignment.Right};
 readonly Expander expressionDetails=new Expander {Header="Equivalent expression",Margin=new Thickness(0,4,0,0)};
 readonly Expander helpDetails=new Expander {Header="Measurement and feedback help",Margin=new Thickness(0,4,0,0)};
 Button use;
 readonly Action<string> load;
 readonly Button commit=new Button {Content="Add gate",VerticalAlignment=VerticalAlignment.Bottom,Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};
 readonly Button cancelEdit=new Button {Content="Cancel edit",VerticalAlignment=VerticalAlignment.Bottom,Visibility=Visibility.Collapsed};
 readonly Button earlier=new Button {Content="← Move earlier"}, later=new Button {Content="Move later →"}, deleteStep=new Button {Content="Delete selected"};
 readonly Button undoChange=new Button {Content="Undo"}, redoChange=new Button {Content="Redo"};
 readonly List<string> past=new List<string>(), future=new List<string>();
 string snapshot;
 bool restoring, batch;
 int editing=-1;
 int Count {get{return qubits.SelectedIndex+1;}}
 public int QubitCount {get{return Count;}}
 static readonly Brush blue=WorkspaceTheme.Accent;
 public CircuitComposer(Window owner,Action<string> loadExpression) {
  Owner=owner; load=loadExpression; Resources=owner.Resources; Title="Circuit composer";
  Width=1040; Height=780; MinWidth=800; MinHeight=550; WindowStartupLocation=WindowStartupLocation.CenterOwner;
  Background=WorkspaceTheme.Background; Foreground=WorkspaceTheme.Text; FontFamily=new FontFamily("Segoe UI");
  page.Margin=new Thickness(20);Content=page;
  var root=new Grid();page.Content=root;
  root.RowDefinitions.Add(new RowDefinition {Height=GridLength.Auto});root.RowDefinitions.Add(new RowDefinition());root.RowDefinitions.Add(new RowDefinition {Height=GridLength.Auto});
  var top=new StackPanel();root.Children.Add(top);
  top.Children.Add(new TextBlock {Text="Build a quantum circuit",FontSize=26,FontWeight=FontWeights.SemiBold});
  top.Children.Add(new TextBlock {Text="Start at |0…0⟩. Gates run left to right. Wire 0 is the first tensor factor.",FontSize=13,Margin=new Thickness(0,6,0,8)});
  var inputs=new WrapPanel(); top.Children.Add(inputs);
  for(int n=1;n<=MaxQubits;n++) qubits.Items.Add(n+" qubits"); qubits.SelectedIndex=1; qubits.Width=100;
  foreach(string name in new[]{"H","X","Y","Z","S","T","Sdg","Tdg","SX","SXdg","Rx","Ry","Rz","P","CNOT","CZ","SWAP","CCX","CY","CH","CCZ","CSWAP","Reset","Measure"}) gate.Items.Add(name);
  gate.SelectedIndex=0; gate.Width=100;
  foreach(string name in new[]{"M0-X","M1-X","M0-Z","M1-Z"}) gate.Items.Add(name);
  foreach(string bits in new[]{"00","01","10","11"})foreach(string op in new[]{"X","Z"})gate.Items.Add("M"+bits+"-"+op);
  foreach(string name in new[]{"CP","CRx","CRy","CRz"}) gate.Items.Add(name);
  gate.Items.Add("iSWAP");
  gate.Items.Add("FSWAP");
  gate.Items.Add("ECR");
  gate.Items.Add("fSim");gate.Items.Add("XXPlusYY");gate.Items.Add("XXMinusYY");
  gate.Items.Add("U3");
  gate.Items.Add("GPhase");
  gate.Items.Add("R");
  foreach(string name in new[]{"Rxx","Ryy","Rzz","Rzx"})gate.Items.Add(name);
  foreach(string name in new[]{"AD","GAD","PD","PAD","Depol","Thermal"})gate.Items.Add(name);
  gate.ToolTip="AD/GAD: amplitude damping; PD: phase damping; PAD: combined damping; Depol: depolarization. Measure discards its Z-basis outcome. Noise, Measure, and Reset return density matrices.";
  Input(inputs,"Register",qubits); Input(inputs,"Gate / noise",gate); Input(inputs,"Wires in order",wires); Input(inputs,"Parameters",angle);
  inputs.Children.Add(commit);inputs.Children.Add(cancelEdit);
  var help=new StackPanel {Margin=new Thickness(0,6,0,4)};helpDetails.Content=help;top.Children.Add(helpDetails);
  help.Children.Add(new TextBlock {Text="Measure: Z basis, outcome discarded. Reset: prepare zero. Both return density matrices.",FontSize=12,TextWrapping=TextWrapping.Wrap});
  help.Children.Add(new TextBlock {Text="M1-X: measure the first wire, apply X to the second if the result is 1. M0 and Z variants work likewise.",FontSize=12,TextWrapping=TextWrapping.Wrap});
  top.Children.Add(parameterHelp);UpdateParameterHelp();
  var actions=new WrapPanel {Margin=new Thickness(0,6,0,4)}; top.Children.Add(actions);
  actions.Children.Add(undoChange);actions.Children.Add(redoChange);
  actions.Children.Add(earlier);actions.Children.Add(later);actions.Children.Add(deleteStep);
  var undo=new Button {Content="Remove last"}; var clear=new Button {Content="Clear circuit"}; var bell=new MenuItem {Header="Bell states"};
  actions.Children.Add(undo); actions.Children.Add(clear);
  var teleport=new MenuItem {Header="Teleportation"};teleport.Click+=delegate {Teleport();};
  var correction=new MenuItem {Header="Bit-flip correction"};correction.Click+=delegate {BitFlip(1);};
  var grover=new MenuItem {Header="Grover search"};
  for(int target=0;target<4;target++) {int selected=target;var item=new MenuItem {Header="Mark "+Convert.ToString(target,2).PadLeft(2,'0')};item.Click+=delegate {Grover(selected);};grover.Items.Add(item);}
  var hiddenString=new MenuItem {Header="Bernstein–Vazirani"};
  for(int secret=0;secret<8;secret++) {string bits=Convert.ToString(secret,2).PadLeft(3,'0');var item=new MenuItem {Header="Hidden string "+bits};item.Click+=delegate {BernsteinVazirani(bits);};hiddenString.Items.Add(item);}
  var simon=new MenuItem {Header="Simon’s algorithm"};
  for(int secret=0;secret<8;secret++) {string bits=Convert.ToString(secret,2).PadLeft(3,'0');var item=new MenuItem {Header=secret==0 ? "000 · one-to-one" : "Hidden string "+bits};item.Click+=delegate {Simon(bits);};simon.Items.Add(item);}
  var estimation=new MenuItem {Header="Phase estimation · T gate"};estimation.Click+=delegate {PhaseEstimation("pi/4");};
  var open=new MenuItem {Header="Open circuit…"}; var save=new MenuItem {Header="Save circuit…"};
  var export=new MenuItem {Header="Export OpenQASM…"};
  var import=new MenuItem {Header="Import OpenQASM"};
  var importQiskit=new MenuItem {Header="IBM / Qiskit U convention…"};
  var importPublished=new MenuItem {Header="Published OpenQASM 3 U convention…"};
  import.Items.Add(importQiskit);import.Items.Add(importPublished);
  var bottom=new StackPanel();Grid.SetRow(bottom,2);root.Children.Add(bottom);
  bottom.Children.Add(status);expression.Margin=new Thickness(0,8,0,0);expressionDetails.Content=expression;bottom.Children.Add(expressionDetails);
  var outputOptions=new WrapPanel {Margin=new Thickness(0,8,0,0)};bottom.Children.Add(outputOptions);
  foreach(string option in new[]{"State","Probabilities","Bloch qubit","Schmidt coefficients","Marginal probabilities"})resultView.Items.Add(option);resultView.SelectedIndex=0;
  Input(outputOptions,"Inspect",resultView);
  var partitionLabel=Input(outputOptions,"Wire / side A",resultWire);bottom.Children.Add(partitionHelp);
  resultView.SelectionChanged+=delegate {
   resultWire.IsEnabled=resultView.SelectedIndex>=2;
   partitionLabel.Text=resultView.SelectedIndex==3 ? "Side A wires" : resultView.SelectedIndex==4 ? "Measured wires" : "Bloch wire";
   System.Windows.Automation.AutomationProperties.SetName(resultWire,partitionLabel.Text);
   partitionHelp.Visibility=resultView.SelectedIndex>=3 ? Visibility.Visible : Visibility.Collapsed;
   partitionHelp.Text=resultView.SelectedIndex==4 ? "Comma-separated measured wires, e.g. 0,1,2. Outcomes follow the entered wire order." : "Side A: comma-separated wires, e.g. 0,2. All other wires form side B. Pure circuits only.";
   resultWire.ToolTip=resultView.SelectedIndex==4 ? "A nonempty list of distinct wires, in the desired outcome bit order." : resultView.SelectedIndex==3 ? "A nonempty proper subset, e.g. 0,2. The other wires form side B." : "One zero-based wire index.";
  };
  use=new Button {Content="Load into calculator →",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary,VerticalAlignment=VerticalAlignment.Bottom,Margin=new Thickness(0,0,0,8)};outputOptions.Children.Add(use);
  var sample=new Button {Content="Sample circuit…",VerticalAlignment=VerticalAlignment.Bottom,Margin=new Thickness(8,0,0,8)};outputOptions.Children.Add(sample);
  sample.Click+=delegate {try {new SamplingWindow(this,Count,SamplingGates()).Show();}catch(Exception error) {status.Text=error.Message;}};
  var circuitCard=new Border {Background=WorkspaceTheme.Surface,CornerRadius=new CornerRadius(10),Margin=new Thickness(0,8,0,12),Padding=new Thickness(10)};Grid.SetRow(circuitCard,1);root.Children.Add(circuitCard);
  var preview=new DockPanel();circuitCard.Child=preview;
  var previewHeader=new DockPanel {Margin=new Thickness(0,0,0,8)};DockPanel.SetDock(previewHeader,Dock.Top);preview.Children.Add(previewHeader);
  var viewControls=new StackPanel {Orientation=Orientation.Horizontal};DockPanel.SetDock(viewControls,Dock.Right);previewHeader.Children.Add(viewControls);
  viewControls.Children.Add(zoom);viewControls.Children.Add(zoomLabel);
  var fit=new Button {Content="Fit wires",Padding=new Thickness(10,5,10,5),Margin=new Thickness(10,0,0,0),ToolTip="Fit all wires vertically; use the horizontal scrollbar for long circuits."};viewControls.Children.Add(fit);
  var navigation=new StackPanel {Orientation=Orientation.Horizontal};previewHeader.Children.Add(navigation);
  navigation.Children.Add(new TextBlock {Text="Circuit preview",FontSize=14,FontWeight=FontWeights.SemiBold,VerticalAlignment=VerticalAlignment.Center,Margin=new Thickness(0,0,18,0)});
  var menus=new Menu {Background=Brushes.Transparent,VerticalAlignment=VerticalAlignment.Center,FontSize=14};navigation.Children.Add(menus);
  var files=new MenuItem {Header="_File"};files.Items.Add(open);files.Items.Add(save);files.Items.Add(import);files.Items.Add(export);menus.Items.Add(files);
  var build=new MenuItem {Header="_Build"};var fromMatrix=new MenuItem {Header="From binary matrix…"};fromMatrix.Click+=delegate {LinearMapDialog().ShowDialog();};build.Items.Add(fromMatrix);
  var fromCss=new MenuItem {Header="CSS code state…"};fromCss.Click+=delegate {CssStateDialog().ShowDialog();};build.Items.Add(fromCss);menus.Items.Add(build);
  var cssEncoder=new MenuItem {Header="CSS encoding circuit…"};cssEncoder.Click+=delegate {CssEncoderDialog().ShowDialog();};build.Items.Add(cssEncoder);
  var examples=new MenuItem {Header="_Examples"};examples.Items.Add(bell);examples.Items.Add(teleport);examples.Items.Add(correction);examples.Items.Add(estimation);examples.Items.Add(grover);examples.Items.Add(hiddenString);examples.Items.Add(simon);menus.Items.Add(examples);
  diagramView.Content=diagram;preview.Children.Add(diagramView);
  System.Windows.Automation.AutomationProperties.SetName(zoom,"Circuit zoom");
  zoom.ToolTip="Zoom the diagram from 5% to 150%. This changes only the view.";
  zoom.ValueChanged+=delegate {diagram.LayoutTransform=new ScaleTransform(zoom.Value,zoom.Value);zoomLabel.Text=Math.Round(zoom.Value*100)+"%";};
  fit.Click+=delegate {FitWires();};
  // Keep a usable diagram viewport. On smaller windows the whole editor can
  // scroll, so expanded help and the calculator action remain reachable.
  Action sizePage=delegate {root.Height=Math.Max(page.ActualHeight,top.ActualHeight+bottom.ActualHeight+240);};
  page.SizeChanged+=delegate {sizePage();};top.SizeChanged+=delegate {sizePage();};bottom.SizeChanged+=delegate {sizePage();};
  qubits.SelectionChanged+=delegate {if(restoring)return;editing=-1;steps.Clear(); Refresh();};
  undoChange.Click+=delegate {Undo();};redoChange.Click+=delegate {Redo();};
  gate.SelectionChanged+=delegate {
   string name=(string)gate.SelectedItem;angle.IsEnabled=NeedsAngle(name);UpdateParameterHelp();
   if(editing<0 && Noise(name))angle.Text=name=="Thermal" ? "20, 30, 4, 0" : name=="GAD" ? "1/4, 1/10" : name=="PAD" ? "1/4, 1/4, 0" : "1/4";
   if(editing<0 && name=="R")angle.Text="pi/2, pi/4";
  }; angle.IsEnabled=false;
  commit.Click+=delegate {if(editing<0)AddGate((string)gate.SelectedItem,wires.Text,angle.Text);else UpdateGate(editing,(string)gate.SelectedItem,wires.Text,angle.Text);};
  cancelEdit.Click+=delegate {editing=-1;Refresh();};
  earlier.Click+=delegate {MoveStep(editing,editing-1);};
  later.Click+=delegate {MoveStep(editing,editing+1);};
  deleteStep.Click+=delegate {DeleteStep(editing);};
  undo.Click+=delegate {editing=-1;if(steps.Count>0)steps.RemoveAt(steps.Count-1); Refresh();};
  clear.Click+=delegate {editing=-1;steps.Clear(); Refresh();};
  string[] bellNames={"Φ+ · correlated", "Φ− · phase flipped", "Ψ+ · anticorrelated", "Ψ− · singlet"};
  for(int index=0;index<4;index++) {int selected=index;var item=new MenuItem {Header=bellNames[index]};item.Click+=delegate {BellState(selected);};bell.Items.Add(item);}

  open.Click+=delegate {
   var picker=new Microsoft.Win32.OpenFileDialog {Filter="Quantum Studio circuit (*.qcircuit)|*.qcircuit",CheckFileExists=true};
   if(picker.ShowDialog(this)!=true)return;
   try {OpenCircuit(picker.FileName);status.Text="Opened "+Path.GetFileName(picker.FileName)+".";} catch(Exception ex) {status.Text="Could not open circuit: "+ex.Message;}
  };
  save.Click+=delegate {
   var picker=new Microsoft.Win32.SaveFileDialog {Filter="Quantum Studio circuit (*.qcircuit)|*.qcircuit",DefaultExt=".qcircuit",AddExtension=true,FileName="My circuit.qcircuit",OverwritePrompt=true};
   if(picker.ShowDialog(this)!=true)return;
   try {SaveCircuit(picker.FileName);status.Text="Saved "+Path.GetFileName(picker.FileName)+".";} catch(Exception ex) {status.Text="Could not save circuit: "+ex.Message;}
  };
  Func<bool,System.Threading.Tasks.Task> importProgram=async delegate(bool publishedU) {
   var picker=new Microsoft.Win32.OpenFileDialog {Filter="OpenQASM (*.qasm)|*.qasm",CheckFileExists=true};
   if(picker.ShowDialog(this)!=true)return;
   IsEnabled=false;status.Text="Compiling OpenQASM…";
   try {
    string circuit=await System.Threading.Tasks.Task.Run(()=>QasmImport.Compile(picker.FileName,publishedU));
    LoadCircuit(circuit);
    status.Text="Imported OpenQASM · U uses "+(publishedU ? "the published OpenQASM 3 matrix" : "the IBM/Qiskit matrix")+" · registers follow declaration order · angles are numeric · measurements discard outcomes; inspect probabilities for the distribution.";
   } catch(Exception ex) {status.Text="Could not import: "+ex.Message;}
   finally {IsEnabled=true;}
  };
  importQiskit.Click+=async delegate {await importProgram(false);};
  importPublished.Click+=async delegate {await importProgram(true);};
  export.Click+=delegate {
   try {
    string program=OpenQasm();
    var picker=new Microsoft.Win32.SaveFileDialog {Filter="OpenQASM 3 (*.qasm)|*.qasm",DefaultExt=".qasm",AddExtension=true,FileName="My circuit.qasm",OverwritePrompt=true};
    if(picker.ShowDialog(this)!=true)return;
    File.WriteAllText(picker.FileName,program,new UTF8Encoding(false)); status.Text="Exported OpenQASM 3. Wire q0 maps to q[0]; output bitstring order depends on the consuming tool.";
   } catch(Exception ex) {status.Text="Could not export: "+ex.Message;}
  };
  use.Click+=delegate {
   try {load(InspectionExpression(resultView.SelectedIndex,resultWire.Text));Close();}catch(InvalidDataException ex){status.Text=ex.Message;}
  };
  Bell();
 }
 static TextBlock Input(Panel parent,string label,Control control) {
  var column=new StackPanel {Margin=new Thickness(0,0,14,8)};
  var caption=new TextBlock {Text=label,FontSize=12,Margin=new Thickness(0,0,0,6)};column.Children.Add(caption); control.Padding=new Thickness(8); column.Children.Add(control); parent.Children.Add(column);
  System.Windows.Automation.AutomationProperties.SetName(control,label);return caption;
 }
 public void FitWires() {
  UpdateLayout();zoom.Value=Math.Max(zoom.Minimum,Math.Min(1,(diagramView.ViewportHeight-2)/diagram.Height));UpdateLayout();
  // Increasing zoom can reveal a horizontal scrollbar and reduce height.
  if(diagram.Height*zoom.Value>diagramView.ViewportHeight-2) {
   zoom.Value=Math.Max(zoom.Minimum,Math.Min(zoom.Value,(diagramView.ViewportHeight-2)/diagram.Height));UpdateLayout();
  }
  diagramView.ScrollToTop();
 }
 public void VerifyLayout() {
  string original=Snapshot();Show();
  foreach(int count in new[]{3,MaxQubits}) {
   var layoutSteps=new List<Step> {new Step {Gate="H",Angle="",Wires=new[]{0}},new Step {Gate="ECR",Angle="",Wires=new[]{count-1,0}}};
   for(int step=2;step<MaxSteps;++step)layoutSteps.Add(new Step {Gate="Rz",Angle="pi/4",Wires=new[]{step%count}});
   LoadCircuit(new JavaScriptSerializer().Serialize(new CircuitFile {Version=1,Qubits=count,Steps=layoutSteps.ToArray()}));string expected=Expression();
   foreach(var size in new[]{new Size(1040,780),new Size(800,550),new Size(1360,960)}) {
    Width=size.Width;Height=size.Height;
    foreach(int inspection in new[]{0,3,4}) foreach(bool expanded in new[]{false,true}) {
     resultView.SelectedIndex=inspection;
     if(expanded)SelectStep(0);else {editing=-1;Refresh();}
     helpDetails.IsExpanded=expanded;expressionDetails.IsExpanded=expanded;zoom.Value=1;page.ScrollToTop();UpdateLayout();
     Point editAction=commit.TranslatePoint(new Point(),page);
     if(editAction.Y<0 || editAction.Y+commit.ActualHeight>page.ViewportHeight+1 || editAction.X+commit.ActualWidth>page.ViewportWidth+1)throw new InvalidDataException("Gate editing action is unreachable at "+size+".");
     if(diagramView.ViewportHeight<140 || diagramView.ViewportWidth<500)throw new InvalidDataException("Circuit viewport is unusable at "+size+".");
     if(inspection==0 && count==3 && size.Width==1040 && !expanded && diagramView.ViewportHeight<diagram.Height)throw new InvalidDataException("Default layout clips a three-wire circuit.");
     zoom.Value=0.25;UpdateLayout();FitWires();
     if(diagram.Height*zoom.Value>diagramView.ViewportHeight+1)throw new InvalidDataException("Fit wires left a wire outside the viewport.");
     zoom.Value=1.5;UpdateLayout();
     if(diagramView.ExtentWidth<diagram.Width*1.5-1)throw new InvalidDataException("Zoomed diagram cannot be scrolled fully.");
     page.ScrollToBottom();UpdateLayout();Point action=use.TranslatePoint(new Point(),page);
     if(action.Y<0 || action.Y+use.ActualHeight>page.ViewportHeight+1)throw new InvalidDataException("Calculator action is unreachable at "+size+".");
     if(Expression()!=expected)throw new InvalidDataException("Changing the circuit view changed its expression.");
    }
   }
  }
  Restore(original);resultView.SelectedIndex=0;Width=1040;Height=780;helpDetails.IsExpanded=false;expressionDetails.IsExpanded=false;zoom.Value=1;page.ScrollToTop();UpdateLayout();
 }
 static bool ControlledAngle(string name) {return name=="CP" || name=="CRx" || name=="CRy" || name=="CRz";}
 static bool ParityRotation(string name) {return name=="XXPlusYY" || name=="XXMinusYY";}
 static bool Interaction(string name) {return name=="Rxx" || name=="Ryy" || name=="Rzz" || name=="Rzx";}
 static bool Noise(string name) {return name=="AD" || name=="GAD" || name=="PD" || name=="PAD" || name=="Depol" || name=="Thermal";}
 void UpdateParameterHelp() {
  string name=(string)gate.SelectedItem;
  parameterHelp.Text=name=="GPhase" ? "GPhase multiplies the entire state by exp(iθ). Choose any one wire; its choice does not change the result." : name=="AD" ? "AD · amplitude damping: probability p in [0,1]. Relaxes toward |0⟩." : name=="GAD" ? "GAD · generalized amplitude damping: p, equilibrium excited population. Both in [0,1]." : name=="PD" ? "PD · phase damping: p in [0,1]. Coherence is multiplied by √(1−p)." : name=="PAD" ? "PAD · combined damping: amplitude, phase, excited population. Each in [0,1]; amplitude + phase ≤ 1." : name=="Depol" ? "Depol · depolarizing λ in [0,4/3]. λ=1 completely mixes the selected qubit." : "Angles in radians: XXPlusYY/XXMinusYY take θ, β; fSim takes θ, φ; U3 takes θ, φ, λ. Separate parameters with commas.";
  if(name=="Thermal")parameterHelp.Text="Thermal · T1, T2, elapsed time, excited population. Use consistent time units; T2 ≤ 2T1.";
  if(name=="R")parameterHelp.Text="R · rotation angle θ, axis angle φ in the XY plane. Both in radians, separated by a comma.";
  if(Noise(name))parameterHelp.Text+=" Noise returns a density matrix; save as .qcircuit (OpenQASM export is unavailable).";
  angle.ToolTip=parameterHelp.Text;
 }
 static bool NeedsAngle(string name) {return name=="GPhase" || ParityRotation(name) || Noise(name) || Interaction(name) || name=="R" || name=="U3" || name=="fSim" || ControlledAngle(name) || name=="Rx" || name=="Ry" || name=="Rz" || name=="P";}
 static string[] GateAngles(string name,string value) {
  var parts=new List<string>(); int depth=0, start=0;
  for(int j=0;j<value.Length;j++) {
   if(value[j]=='(')depth++; else if(value[j]==')')depth--;
   if(depth<0)throw new InvalidDataException("Unbalanced angle parentheses.");
   if(value[j]==',' && depth==0){parts.Add(value.Substring(start,j-start).Trim());start=j+1;}
  }
  parts.Add(value.Substring(start).Trim());
  int count=name=="Thermal" ? 4 : name=="U3" || name=="PAD" ? 3 : ParityRotation(name) || name=="R" || name=="fSim" || name=="GAD" ? 2 : 1;
  if(depth!=0 || parts.Count!=count || parts.Exists(String.IsNullOrWhiteSpace))throw new InvalidDataException(name+" needs "+count+" parameter expressions, separated by commas, with balanced parentheses.");
  return parts.ToArray();
 }
 static bool Feedback(string name) {return name!=null && (name=="M0-X" || name=="M1-X" || name=="M0-Z" || name=="M1-Z" || name=="M00-X" || name=="M01-X" || name=="M10-X" || name=="M11-X" || name=="M00-Z" || name=="M01-Z" || name=="M10-Z" || name=="M11-Z");}
 static string FeedbackBits(string name) {return name.Substring(1,name.IndexOf('-')-1);}
 static char FeedbackGate(string name) {return name[name.Length-1];}
 static int WireCount(string name) {return Feedback(name) ? FeedbackBits(name).Length+1 : name=="CCX" || name=="CCZ" || name=="CSWAP" ? 3 : ParityRotation(name) || Interaction(name) || name=="ECR" || name=="FSWAP" || name=="fSim" || ControlledAngle(name) || name=="CNOT" || name=="CZ" || name=="CY" || name=="CH" || name=="SWAP" || name=="iSWAP" ? 2 : 1;}
 static void PauliRotation(StringBuilder result,string axes,string theta,int[] wires) {
  string a="q["+wires[0]+"]", b="q["+wires[1]+"]";
  for(int k=0;k<2;k++) {
   string wire=k==0 ? a : b;
   if(axes[k]=='x')result.Append("h "+wire+";\n");
   if(axes[k]=='y')result.Append("rx(pi/2.0) "+wire+";\n");
  }
  result.Append("cx "+a+", "+b+";\nrz("+theta+") "+b+";\ncx "+a+", "+b+";\n");
  for(int k=0;k<2;k++) {
   string wire=k==0 ? a : b;
   if(axes[k]=='x')result.Append("h "+wire+";\n");
   if(axes[k]=='y')result.Append("rx(-pi/2.0) "+wire+";\n");
  }
 }
 public string OpenQasm() {
  foreach(var step in steps)if(Noise(step.Gate))throw new InvalidDataException("OpenQASM export does not support noise channels ("+step.Gate+"). Save this circuit as .qcircuit to preserve its noise operations.");
  var result=new StringBuilder("OPENQASM 3.0;\ninclude \"stdgates.inc\";\n// Composer wire q0 maps to q[0]. Gates retain their original order.\nqubit["+Count+"] q;\nreset q;\n");
  int classical=0;
  foreach(var step in steps) {
   if(step.Gate=="GPhase") {result.Append("gphase("+QasmAngle.Translate(step.Angle)+");\n");continue;}
   if(Interaction(step.Gate)) {PauliRotation(result,step.Gate.Substring(1),QasmAngle.Translate(step.Angle),step.Wires);continue;}
   if(step.Gate=="U3") {
    string[] angles=Array.ConvertAll(GateAngles(step.Gate,step.Angle),QasmAngle.Translate); string wire="q["+step.Wires[0]+"]";
    result.Append("p("+angles[2]+") "+wire+";\nry("+angles[0]+") "+wire+";\np("+angles[1]+") "+wire+";\n");continue;
   }
   if(step.Gate=="R") {
    string[] angles=Array.ConvertAll(GateAngles(step.Gate,step.Angle),QasmAngle.Translate);string wire="q["+step.Wires[0]+"]";
    result.Append("rz(-("+angles[1]+")) "+wire+";\nrx("+angles[0]+") "+wire+";\nrz("+angles[1]+") "+wire+";\n");continue;
   }
   if(ParityRotation(step.Gate)) {
    string[] angles=Array.ConvertAll(GateAngles(step.Gate,step.Angle),QasmAngle.Translate);
    bool plus=step.Gate=="XXPlusYY";string wire="q["+step.Wires[plus ? 0 : 1]+"]", beta="("+angles[1]+")", half="("+angles[0]+")/2.0";
    result.Append("rz("+(plus ? beta : "-"+beta)+") "+wire+";\n");
    PauliRotation(result,"xx",half,step.Wires);PauliRotation(result,"yy",plus ? half : "-("+half+")",step.Wires);
    result.Append("rz("+(plus ? "-"+beta : beta)+") "+wire+";\n");continue;
   }
   if(step.Gate=="fSim") {
    string[] angles=GateAngles(step.Gate,step.Angle); string theta=QasmAngle.Translate(angles[0]), phi=QasmAngle.Translate(angles[1]);
    string a="q["+step.Wires[0]+"]", b="q["+step.Wires[1]+"]";
    // Commuting XX and YY rotations, followed by the negative controlled phase.
    PauliRotation(result,"xx",theta,step.Wires);PauliRotation(result,"yy",theta,step.Wires);
    result.Append("cp(-("+phi+")) "+a+", "+b+";\n"); continue;
   }
   if(step.Gate=="ECR") {
    string a="q["+step.Wires[0]+"]", b="q["+step.Wires[1]+"]";
    // Preserve the matrix's global phase, including for future controlled use.
    result.Append("gphase(-pi/4.0);\ns "+a+";\nsx "+b+";\ncx "+a+", "+b+";\nx "+a+";\n");continue;
   }
   if(step.Gate=="FSWAP") {
    string a="q["+step.Wires[0]+"]", b="q["+step.Wires[1]+"]";
    result.Append("swap "+a+", "+b+";\ncz "+a+", "+b+";\n");continue;
   }
   if(step.Gate=="iSWAP") {
    string a="q["+step.Wires[0]+"]", b="q["+step.Wires[1]+"]";
    result.Append("swap "+a+", "+b+";\ns "+a+";\ns "+b+";\ncz "+a+", "+b+";\n"); continue;
   }
   if(Feedback(step.Gate)) {
    string bits=FeedbackBits(step.Gate);var conditions=new List<string>();
    for(int k=0;k<bits.Length;k++) {
     string bit="m"+(classical++);
     result.Append("bit "+bit+";\n"+bit+" = measure q["+step.Wires[k]+"];\n");conditions.Add(bit+" == "+bits[k]);
    }
    result.Append("if ("+String.Join(" && ",conditions)+") {\n  "+Char.ToLowerInvariant(FeedbackGate(step.Gate))+" q["+step.Wires[bits.Length]+"];\n}\n");
    continue;
   }
   string name=step.Gate=="CNOT" ? "cx" : step.Gate=="CCZ" ? "ctrl(2) @ z" : step.Gate=="SXdg" ? "inv @ sx" : step.Gate.ToLowerInvariant();
   result.Append(name); if(NeedsAngle(step.Gate))result.Append("("+QasmAngle.Translate(step.Angle)+")");
   result.Append(" "); result.Append(String.Join(", ",Array.ConvertAll(step.Wires,n=>"q["+n+"]"))); result.Append(";\n");
  } return result.ToString();
 }
 public void SaveCircuit(string path) {
  string text=new JavaScriptSerializer().Serialize(new CircuitFile {Version=1,Qubits=Count,Steps=steps.ToArray()});
  string temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
  try {
   File.WriteAllText(temporary,text,new UTF8Encoding(false));
   for(int attempt=0;;attempt++) {
    try {if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);break;}
    catch(IOException ex) {
     int code=ex.HResult & 0xffff;
     if((code!=32 && code!=33 && code!=1175) || attempt>=5)throw;
     // Antivirus/indexing readers can briefly deny replacement. Keep the
     // original file intact; never fall back to truncating it in place.
     System.Threading.Thread.Sleep(200);
    }
   }
  } finally {if(File.Exists(temporary))File.Delete(temporary);}
 }
 string Snapshot() {return new JavaScriptSerializer().Serialize(new CircuitFile {Version=1,Qubits=Count,Steps=steps.ToArray()});}
 void Restore(string text) {
  var file=new JavaScriptSerializer().Deserialize<CircuitFile>(text);
  restoring=true;
  try {editing=-1;qubits.SelectedIndex=file.Qubits-1;steps.Clear();steps.AddRange(file.Steps);gate.SelectedIndex=0;wires.Text="0";angle.Text="pi/2";snapshot=text;Refresh();}
  finally {restoring=false;}
 }
 public bool Undo() {
  if(past.Count==0)return false;
  string previous=past[past.Count-1];past.RemoveAt(past.Count-1);future.Add(snapshot);Restore(previous);return true;
 }
 public bool Redo() {
  if(future.Count==0)return false;
  string next=future[future.Count-1];future.RemoveAt(future.Count-1);past.Add(snapshot);Restore(next);return true;
 }
 public void OpenCircuit(string path) {
  LoadCircuit(Encoding.UTF8.GetString(BoundedUtf8File.Read(path,262144,"Circuit")));
 }
 public void LoadCircuit(string text) {
  if(text==null || text.Length>262144)throw new InvalidDataException("Circuit data is too large.");
  var file=new JavaScriptSerializer().Deserialize<CircuitFile>(text);
  if(file==null || file.Version!=1 || file.Qubits<1 || file.Qubits>MaxQubits || file.Steps==null || file.Steps.Length>MaxSteps) throw new InvalidDataException("Expected a version 1 circuit with 1–25 qubits and at most 512 steps.");
  // Validate the entire document before changing any controls or circuit state.
  foreach(var step in file.Steps) {
   if(step==null || step.Gate==null || !gate.Items.Contains(step.Gate) || step.Wires==null) throw new InvalidDataException("Unknown gate or missing wire list.");
   int required=WireCount(step.Gate);
   if(step.Wires.Length!=required) throw new InvalidDataException("Incorrect number of wires for "+step.Gate+".");
   var seen=new HashSet<int>();
   foreach(int wire in step.Wires) if(wire<0 || wire>=file.Qubits || !seen.Add(wire)) throw new InvalidDataException("Wire indices must be distinct and inside the register.");
   if(NeedsAngle(step.Gate) && (String.IsNullOrWhiteSpace(step.Angle) || step.Angle.Length>200)) throw new InvalidDataException("Missing or excessive parameter expression.");
   step.Angle=NeedsAngle(step.Gate) ? step.Angle.Trim() : "";
   if(ParityRotation(step.Gate) || step.Gate=="R" || step.Gate=="fSim" || step.Gate=="U3" || Noise(step.Gate))GateAngles(step.Gate,step.Angle);
  }
  batch=true;
  try {editing=-1;qubits.SelectedIndex=file.Qubits-1;steps.Clear();steps.AddRange(file.Steps);}
  finally {batch=false;}
  Refresh();
 }
 public bool AddGate(string name,string selectedWires,string parameter) {
  return WriteGate(-1,name,selectedWires,parameter);
 }
 public bool UpdateGate(int index,string name,string selectedWires,string parameter) {
  if(index<0 || index>=steps.Count){status.Text="Select an existing step to update.";return false;}
  return WriteGate(index,name,selectedWires,parameter);
 }
 public bool SelectStep(int index) {
  if(index<0 || index>=steps.Count)return false;
  editing=index;var step=steps[index];gate.SelectedItem=step.Gate;
  wires.Text=String.Join(",",Array.ConvertAll(step.Wires,n=>n.ToString()));angle.Text=step.Angle;Refresh();return true;
 }
 public bool MoveStep(int index,int destination) {
  if(index<0 || index>=steps.Count || destination<0 || destination>=steps.Count)return false;
  var step=steps[index];steps.RemoveAt(index);steps.Insert(destination,step);
  if(editing==index)editing=destination;
  else if(index<editing && destination>=editing)editing--;
  else if(index>editing && destination<=editing)editing++;
  Refresh();return true;
 }
 public bool DeleteStep(int index) {
  if(index<0 || index>=steps.Count)return false;
  steps.RemoveAt(index);
  if(editing==index)editing=-1;else if(editing>index)editing--;
  Refresh();return true;
 }
 bool WriteGate(int index,string name,string selectedWires,string parameter) {
  int required=WireCount(name);
  if(!gate.Items.Contains(name)) {status.Text="Choose a supported gate."; return false;}
  if(index<0 && steps.Count>=MaxSteps) {status.Text="This composer supports up to 512 gate steps."; return false;}
  string[] parts=selectedWires.Split(','); var targets=new int[parts.Length]; var seen=new HashSet<int>();
  if(parts.Length!=required) {status.Text=name+" needs "+required+" wire indices, separated by commas. Controls come first."; return false;}
  for(int k=0;k<parts.Length;k++) if(!Int32.TryParse(parts[k].Trim(),out targets[k]) || targets[k]<0 || targets[k]>=Count || !seen.Add(targets[k])) {status.Text="Wire indices must be distinct integers from 0 to "+(Count-1)+"."; return false;}
  if(NeedsAngle(name) && (String.IsNullOrWhiteSpace(parameter) || parameter.Length>200)) {status.Text="Enter parameter expressions of 1–200 characters."; return false;}
  if(ParityRotation(name) || name=="R" || name=="fSim" || name=="U3" || Noise(name))try {GateAngles(name,parameter);} catch(InvalidDataException ex){status.Text=ex.Message;return false;}
  var replacement=new Step {Gate=name,Angle=NeedsAngle(name) ? parameter.Trim() : "",Wires=targets};
  if(index<0)steps.Add(replacement);else steps[index]=replacement;
  editing=-1;Refresh(); return true;
 }
 void Bell() {BellState(0);}
 public void BellState(int index) {
  if(index<0 || index>3)throw new ArgumentOutOfRangeException("index");
  batch=true;
  try {
   qubits.SelectedIndex=1;steps.Clear();AddGate("H","0","");AddGate("CNOT","0,1","");
   if(index>=2)AddGate("X","1","");
   if((index&1)!=0)AddGate("Z","0","");
  } finally {batch=false;}
  Refresh();resultView.SelectedIndex=0;
  status.Text=new[]{"Φ+ = (|00⟩ + |11⟩)/√2", "Φ− = (|00⟩ − |11⟩)/√2", "Ψ+ = (|01⟩ + |10⟩)/√2", "Ψ− = (|01⟩ − |10⟩)/√2 · singlet"}[index]+". First bit is q0. Inspect State to see the relative phase.";
 }
 public void Teleport() {
  batch=true;
  try {
  qubits.SelectedIndex=2; steps.Clear();
  AddGate("H","0",""); AddGate("S","0",""); AddGate("H","1",""); AddGate("CNOT","1,2","");
  AddGate("CNOT","0,1",""); AddGate("H","0",""); AddGate("M1-X","1,2",""); AddGate("M1-Z","0,2","");
  } finally {batch=false;}
  Refresh();
  status.Text="Teleport |i⟩ from q0 to q2. Trace out q0 and q1 to inspect Bob's recovered qubit.";
 }
 public void Grover(int target) {
  if(target<0 || target>3)throw new ArgumentOutOfRangeException("target");
  batch=true;
  try {
   qubits.SelectedIndex=1;steps.Clear();AddGate("H","0","");AddGate("H","1","");
   // Conjugate CZ with X on zero bits to mark exactly the requested basis state.
   for(int wire=0;wire<2;wire++)if((target & (1 << (1-wire)))==0)AddGate("X",wire.ToString(),"");
   AddGate("CZ","0,1","");
   for(int wire=0;wire<2;wire++)if((target & (1 << (1-wire)))==0)AddGate("X",wire.ToString(),"");
   for(int wire=0;wire<2;wire++)AddGate("H",wire.ToString(),"");
   for(int wire=0;wire<2;wire++)AddGate("X",wire.ToString(),"");
   AddGate("CZ","0,1","");
   for(int wire=0;wire<2;wire++)AddGate("X",wire.ToString(),"");
   for(int wire=0;wire<2;wire++)AddGate("H",wire.ToString(),"");
  } finally {batch=false;}
  Refresh();resultView.SelectedIndex=1;
  status.Text="One Grover iteration marks "+Convert.ToString(target,2).PadLeft(2,'0')+" and gives 100% ideal probability. This gate decomposition produces −|target⟩; its global phase is preserved.";
 }
 public void BernsteinVazirani(string secret) {
  if(secret==null || secret.Length!=3 || secret.Trim('0','1').Length!=0)throw new ArgumentException("Choose a three-bit hidden string.");
  batch=true;
  try {
   qubits.SelectedIndex=3;steps.Clear();AddGate("X","3","");
   for(int wire=0;wire<4;wire++)AddGate("H",wire.ToString(),"");
   // One query to f(x)=s·x mod 2, decomposed into its controlled-NOT gates.
   for(int wire=0;wire<3;wire++)if(secret[wire]=='1')AddGate("CNOT",wire+",3","");
   for(int wire=0;wire<3;wire++)AddGate("H",wire.ToString(),"");
  } finally {batch=false;}
  Refresh();resultView.SelectedIndex=4;resultWire.Text="0,1,2";
  status.Text="Bernstein–Vazirani: one oracle query recovers "+secret+" on q0q1q2. q3 remains |−⟩. The visible CNOTs implement f(x) = s·x mod 2 for this chosen string.";
 }
 static List<int[]> CssChecks(string text,ref int width) {
  if(String.IsNullOrWhiteSpace(text) || text.Length>4096)throw new ArgumentException("Enter binary check rows, or [] for no checks of that type.");
  text=text.Trim();var result=new List<int[]>();if(text=="[]")return result;
  if(text.StartsWith("[") || text.EndsWith("]")) {
   if(!text.StartsWith("[") || !text.EndsWith("]"))throw new ArgumentException("Close both matrix brackets.");
   text=text.Substring(1,text.Length-2).Trim();
  }
  foreach(string row in text.Replace("\r","").Replace("\n",";").Split(';')) {
   string[] values=row.Contains(",") ? row.Split(',') : row.Split(new[]{' ','\t'},StringSplitOptions.RemoveEmptyEntries);
   if(width==0)width=values.Length;
   if(width<1 || width>8 || values.Length!=width)throw new ArgumentException("All check rows must have the same 1–8 columns, one per qubit.");
   var bits=new int[width];for(int c=0;c<width;c++) {
    string value=values[c].Trim();if(value!="0" && value!="1")throw new ArgumentException("Check entries must be 0 or 1.");bits[c]=value=="1" ? 1 : 0;
   }
   result.Add(bits);if(result.Count>32)throw new ArgumentException("Use at most 32 total check rows.");
  }
  return result;
 }
 public void CssState(string xText,string zText,string representative) {
  int n=0;var xs=CssChecks(xText,ref n);var zs=CssChecks(zText,ref n);
  if(n==0 || xs.Count+zs.Count>32)throw new ArgumentException("Specify 1–32 total check rows.");
  if(representative==null)throw new ArgumentException("Enter one binary representative bit per qubit.");
  representative=representative.Trim();
  if(representative.Length!=n || representative.Trim('0','1').Length!=0)throw new ArgumentException("Enter exactly "+n+" representative bits, with q0 first.");
  foreach(var x in xs)foreach(var z in zs) {
   int parity=0;for(int c=0;c<n;c++)parity^=x[c]&z[c];
   if(parity!=0)throw new ArgumentException("X and Z checks must commute: Hx Hzᵀ must be zero over GF(2).");
  }
  foreach(var z in zs) {
   int parity=0;for(int c=0;c<n;c++)parity^=z[c]&(representative[c]-'0');
   if(parity!=0)throw new ArgumentException("The representative must satisfy every Z parity check.");
  }
  var pivots=new List<int>();int rank=0;
  for(int column=0;column<n && rank<xs.Count;column++) {
   int pivot=rank;while(pivot<xs.Count && xs[pivot][column]==0)pivot++;
   if(pivot==xs.Count)continue;
   var swap=xs[rank];xs[rank]=xs[pivot];xs[pivot]=swap;
   for(int r=0;r<xs.Count;r++)if(r!=rank && xs[r][column]!=0)for(int c=0;c<n;c++)xs[r][c]^=xs[rank][c];
   pivots.Add(column);rank++;
  }
  var synthesized=new List<Step>();
  for(int r=0;r<rank;r++)synthesized.Add(new Step {Gate="H",Angle="",Wires=new[]{pivots[r]}});
  // RREF pivot columns form an identity matrix. Nonpivot bits are XORs of
  // independent Hadamard-prepared pivot bits, yielding the uniform row space.
  for(int r=0;r<rank;r++)for(int c=0;c<n;c++)if(c!=pivots[r] && xs[r][c]!=0)synthesized.Add(new Step {Gate="CNOT",Angle="",Wires=new[]{pivots[r],c}});
  for(int c=0;c<n;c++)if(representative[c]=='1')synthesized.Add(new Step {Gate="X",Angle="",Wires=new[]{c}});
  if(synthesized.Count>MaxSteps)throw new ArgumentException("The prepared circuit exceeds the step limit.");
  batch=true;try {editing=-1;qubits.SelectedIndex=n-1;steps.Clear();steps.AddRange(synthesized);}finally {batch=false;}
  Refresh();resultView.SelectedIndex=0;
  status.Text="Prepared CSS coset state · "+n+" qubits · "+rank+" independent X checks · "+steps.Count+" H/CNOT/X steps. This prepares the selected state from |0…0⟩.";
 }
 public Window CssStateDialog() {
  var dialog=new Window {Owner=this,Title="Prepare a CSS code state",Width=650,Height=680,MinWidth=460,MinHeight=480,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=Background,FontFamily=FontFamily,Resources=Resources};
  var panel=new StackPanel {Margin=new Thickness(22)};dialog.Content=new ScrollViewer {Content=panel,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  panel.Children.Add(new TextBlock {Text="From check matrices to a circuit",FontSize=23,FontWeight=FontWeights.SemiBold});
  panel.Children.Add(new TextBlock {Text="Prepare a uniform CSS coset state with H, CNOT and X gates. Columns are q0, q1, …; use 1–8 columns and at most 32 total rows. Separate rows with new lines or semicolons. Use [] for no checks of one type.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,12)});
  string h="1, 1, 1, 1, 0, 0, 0\n1, 1, 0, 0, 1, 1, 0\n1, 0, 1, 0, 1, 0, 1";
  var x=new TextBox {Text=h,AcceptsReturn=true,Height=100,FontFamily=new FontFamily("Consolas"),FontSize=16,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  var z=new TextBox {Text=h,AcceptsReturn=true,Height=100,FontFamily=new FontFamily("Consolas"),FontSize=16,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  var u=new TextBox {Text="0000000",FontFamily=new FontFamily("Consolas"),FontSize=17};
  Input(panel,"X checks (Hx)",x);Input(panel,"Z checks (Hz)",z);Input(panel,"Representative bits",u);
  panel.Children.Add(new TextBlock {Text="The defaults prepare Steane logical |0⟩. Use 0000111 for logical |1⟩. A representative must satisfy the Z checks; equivalent representatives can prepare the same state.",TextWrapping=TextWrapping.Wrap,FontSize=12,Margin=new Thickness(0,0,0,8)});
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Error};panel.Children.Add(error);
  var actions=new StackPanel {Orientation=Orientation.Horizontal,Margin=new Thickness(0,10,0,0)};panel.Children.Add(actions);
  var build=new Button {Content="Build preparation circuit",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};var cancel=new Button {Content="Cancel",IsCancel=true};actions.Children.Add(build);actions.Children.Add(cancel);
  build.Click+=delegate {try {CssState(x.Text,z.Text,u.Text);dialog.DialogResult=true;}catch(ArgumentException ex){error.Text=ex.Message;}};
  return dialog;
 }
 static int BinaryParity(int value) {int parity=0;while(value!=0){parity^=1;value&=value-1;}return parity;}
 static bool ExtendBinarySpan(List<int> span,bool[] present,int word) {
  if(present[word])return false;int count=span.Count;
  for(int j=0;j<count;j++){int next=span[j]^word;present[next]=true;span.Add(next);}return true;
 }
 public int CssEncoder(string xText,string zText,bool append) {
  int n=0;var xs=CssChecks(xText,ref n);var zs=CssChecks(zText,ref n);
  if(n==0 || xs.Count+zs.Count>32)throw new ArgumentException("Specify 1–32 total check rows.");
  var xmasks=new List<int>();var zmasks=new List<int>();
  foreach(var row in xs){int mask=0;foreach(int bit in row)mask=(mask<<1)|bit;xmasks.Add(mask);}
  foreach(var row in zs){int mask=0;foreach(int bit in row)mask=(mask<<1)|bit;zmasks.Add(mask);}
  foreach(int x in xmasks)foreach(int z in zmasks)if(BinaryParity(x&z)!=0)throw new ArgumentException("X and Z checks must commute: Hx Hzᵀ must be zero over GF(2).");
  var span=new List<int>{0};var present=new bool[1<<n];present[0]=true;var xbasis=new List<int>();var logical=new List<int>();
  foreach(int mask in xmasks)if(ExtendBinarySpan(span,present,mask))xbasis.Add(mask);
  for(int word=1;word<(1<<n);word++) {
   if(present[word])continue;bool allowed=true;foreach(int z in zmasks)if(BinaryParity(word&z)!=0){allowed=false;break;}
   if(allowed){logical.Add(word);ExtendBinarySpan(span,present,word);}
  }
  int k=logical.Count;
  if(append && (k==0 || Count!=k))throw new ArgumentException("Appending requires a current circuit with exactly "+k+" logical qubits. Build a new encoder instead when k=0.");
  // Logical words match css_encoder; editor input wires are most significant first.
  var columns=new List<int>();for(int j=k-1;j>=0;j--)columns.Add(logical[j]);columns.AddRange(xbasis);
  for(int bit=0;bit<n;bit++)if(ExtendBinarySpan(span,present,1<<bit))columns.Add(1<<bit);
  if(columns.Count!=n)throw new InvalidOperationException("Could not complete the CSS encoding basis.");
  var map=new int[n,n];for(int r=0;r<n;r++)for(int c=0;c<n;c++)map[r,c]=(columns[c]>>(n-1-r))&1;
  var synthesized=new List<Step>();
  if(append)foreach(var step in steps)synthesized.Add(new Step {Gate=step.Gate,Angle=step.Angle,Wires=(int[])step.Wires.Clone()});
  for(int j=0;j<xbasis.Count;j++)synthesized.Add(new Step {Gate="H",Angle="",Wires=new[]{k+j}});
  synthesized.AddRange(LinearSteps(map,n));
  if(synthesized.Count>MaxSteps)throw new ArgumentException("The encoder and existing steps exceed the 512-step circuit limit.");
  batch=true;try {editing=-1;qubits.SelectedIndex=n-1;steps.Clear();steps.AddRange(synthesized);}finally {batch=false;}
  Refresh();resultView.SelectedIndex=0;
  status.Text="CSS encoder · "+k+" logical qubits → "+n+" physical qubits. Logical inputs occupy the first "+k+" wires; remaining inputs are zero ancillas. "+(append ? "Previous preparation is preserved." : "Insert logical preparation before these gates to change the encoded state.");
  return k;
 }
 public Window CssEncoderDialog() {
  var dialog=new Window {Owner=this,Title="Build a CSS encoding circuit",Width=650,Height=670,MinWidth=460,MinHeight=480,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=Background,FontFamily=FontFamily,Resources=Resources};
  var panel=new StackPanel {Margin=new Thickness(22)};dialog.Content=new ScrollViewer {Content=panel,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  panel.Children.Add(new TextBlock {Text="Encode logical amplitudes",FontSize=25,FontWeight=FontWeights.SemiBold});
  panel.Children.Add(new TextBlock {Text="Build an H/CNOT/SWAP encoder from compatible X and Z checks. The first k wires carry the logical input; the remaining wires start at zero. The logical basis matches css_encoder(Hx,Hz).",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,12)});
  string h="1, 1, 1, 1, 0, 0, 0\n1, 1, 0, 0, 1, 1, 0\n1, 0, 1, 0, 1, 0, 1";
  var x=new TextBox {Text=h,AcceptsReturn=true,Height=100,FontFamily=new FontFamily("Consolas"),FontSize=16,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  var z=new TextBox {Text=h,AcceptsReturn=true,Height=100,FontFamily=new FontFamily("Consolas"),FontSize=16,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  Input(panel,"X checks (Hx)",x);Input(panel,"Z checks (Hz)",z);
  var append=new CheckBox {Content="Append to my current logical-input circuit",Margin=new Thickness(0,4,0,10)};panel.Children.Add(append);
  panel.Children.Add(new TextBlock {Text="The defaults encode one logical qubit into the seven-qubit Steane code. To encode |i⟩, first prepare a one-qubit circuit with H then S and select Append. Use [] for an absent check type. Limits: 1–8 physical qubits, 32 check rows, 512 total gate steps.",TextWrapping=TextWrapping.Wrap,FontSize=12});
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Error,Margin=new Thickness(0,8,0,0)};panel.Children.Add(error);
  var actions=new StackPanel {Orientation=Orientation.Horizontal,Margin=new Thickness(0,12,0,0)};panel.Children.Add(actions);
  var build=new Button {Content="Build encoding circuit",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};var cancel=new Button {Content="Cancel",IsCancel=true};actions.Children.Add(build);actions.Children.Add(cancel);
  build.Click+=delegate {try {CssEncoder(x.Text,z.Text,append.IsChecked==true);dialog.DialogResult=true;}catch(ArgumentException ex){error.Text=ex.Message;}};
  return dialog;
 }
 static List<Step> LinearSteps(int[,] a,int n) {
  var synthesized=new List<Step>();
  for(int c=0;c<n;c++) {
   int pivot=c;while(pivot<n && a[pivot,c]==0)pivot++;
   if(pivot==n)throw new ArgumentException("This binary map is singular and cannot be a reversible quantum gate.");
   if(pivot!=c) {for(int j=0;j<n;j++){int v=a[c,j];a[c,j]=a[pivot,j];a[pivot,j]=v;}synthesized.Add(new Step {Gate="SWAP",Angle="",Wires=new[]{c,pivot}});}
   for(int r=0;r<n;r++)if(r!=c && a[r,c]!=0) {for(int j=0;j<n;j++)a[r,j]^=a[c,j];synthesized.Add(new Step {Gate="CNOT",Angle="",Wires=new[]{c,r}});}
  }
  synthesized.Reverse();return synthesized;
 }
 public void LinearMap(string text) {
  if(String.IsNullOrWhiteSpace(text) || text.Length>4096)throw new ArgumentException("Enter a square binary matrix with 1–8 rows.");
  text=text.Trim();
  if(text.StartsWith("[") && text.EndsWith("]"))text=text.Substring(1,text.Length-2).Trim();
  string[] rows=text.Replace("\r","").Replace("\n",";").Split(';');int n=rows.Length;
  if(n<1 || n>8)throw new ArgumentException("Use 1–8 rows, separated by semicolons or new lines.");
  int[,] a=new int[n,n];
  for(int r=0;r<n;r++) {
   string[] values=rows[r].Contains(",") ? rows[r].Split(',') : rows[r].Split(new[]{' ','\t'},StringSplitOptions.RemoveEmptyEntries);
   if(values.Length!=n)throw new ArgumentException("The binary matrix must be square.");
   for(int c=0;c<n;c++) {string value=values[c].Trim();if(value!="0" && value!="1")throw new ArgumentException("Every matrix entry must be 0 or 1.");a[r,c]=value=="1" ? 1 : 0;}
  }
  // Elimination gives E_t ... E_1 A=I. Execute the self-inverse operations
  // in reverse order to implement A, with row indices as output wires.
  var synthesized=LinearSteps(a,n);
  if(synthesized.Count>MaxSteps)throw new ArgumentException("The synthesized circuit exceeds the step limit.");
  batch=true;try {editing=-1;qubits.SelectedIndex=n-1;steps.Clear();steps.AddRange(synthesized);}finally {batch=false;}
  Refresh();resultView.SelectedIndex=0;
  status.Text="Built "+n+"-qubit binary map with "+steps.Count+" CNOT/SWAP steps. Rows are output bits; columns are input bits. Prepare an input before these gates to explore its action.";
 }
 public Window LinearMapDialog() {
  var dialog=new Window {Owner=this,Title="Build from binary matrix",Width=560,Height=510,MinWidth=440,MinHeight=350,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=Background,FontFamily=FontFamily,Resources=Resources};
  var panel=new StackPanel {Margin=new Thickness(22)};dialog.Content=new ScrollViewer {Content=panel,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  panel.Children.Add(new TextBlock {Text="A binary map, as a circuit",FontSize=23,FontWeight=FontWeights.SemiBold});
  panel.Children.Add(new TextBlock {Text="Enter an invertible 1–8 bit matrix. Rows are output bits and columns are input bits, with q0 first. Separate rows with new lines or semicolons.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,12)});
  var input=new TextBox {Text="1, 0\n1, 1",AcceptsReturn=true,Height=150,FontFamily=new FontFamily("Consolas"),FontSize=17,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};panel.Children.Add(input);
  System.Windows.Automation.AutomationProperties.SetName(input,"Binary matrix");
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Error,Margin=new Thickness(0,8,0,8)};panel.Children.Add(error);
  var actions=new StackPanel {Orientation=Orientation.Horizontal};panel.Children.Add(actions);
  var build=new Button {Content="Build circuit",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};var cancel=new Button {Content="Cancel",IsCancel=true};actions.Children.Add(build);actions.Children.Add(cancel);
  build.Click+=delegate {try {LinearMap(input.Text);dialog.DialogResult=true;}catch(ArgumentException ex){error.Text=ex.Message;}};
  return dialog;
 }
 public void Simon(string secret) {
  if(secret==null || secret.Length!=3 || secret.Trim('0','1').Length!=0)throw new ArgumentException("Choose a three-bit hidden string.");
  int pivot=secret.IndexOf('1');batch=true;
  try {
   qubits.SelectedIndex=5;steps.Clear();
   for(int wire=0;wire<3;wire++)AddGate("H",wire.ToString(),"");
   // Reversible query |x,z> -> |x,z XOR f(x)> with f(x)=x XOR x_p*s.
   // For s=000, use f(x)=x. Inputs are q0..q2; outputs are q3..q5.
   for(int wire=0;wire<3;wire++)AddGate("CNOT",wire+","+(wire+3),"");
   if(pivot>=0)for(int wire=0;wire<3;wire++)if(secret[wire]=='1')AddGate("CNOT",pivot+","+(wire+3),"");
   for(int wire=0;wire<3;wire++)AddGate("H",wire.ToString(),"");
  } finally {batch=false;}
  Refresh();resultView.SelectedIndex=4;resultWire.Text="0,1,2";
  status.Text=pivot<0 ? "Simon: the one-to-one oracle gives all eight input outcomes with probability 1/8. Hidden string: 000." : "Simon: the four outcomes y with y·"+secret+" = 0 mod 2 each have probability 1/4. Repeated measurements supply equations for the hidden string; one sample does not determine it.";
 }
 public void PhaseEstimation(string phase) {
  if(String.IsNullOrWhiteSpace(phase) || phase.Length>180)throw new ArgumentException("Enter a phase angle of at most 180 characters.");
  QasmAngle.Translate(phase);
  batch=true;
  try {
   qubits.SelectedIndex=3;steps.Clear();AddGate("X","3","");
   for(int wire=0;wire<3;wire++)AddGate("H",wire.ToString(),"");
   for(int wire=0;wire<3;wire++)AddGate("CP",wire+",3","("+phase+")*"+(1 << (2-wire)));
   // Inverse QFT, reversed from the positive-phase, leftmost-first QFT.
   AddGate("SWAP","0,2","");AddGate("H","2","");
   AddGate("CP","2,1","-pi/2");AddGate("H","1","");
   AddGate("CP","2,0","-pi/4");AddGate("CP","1,0","-pi/2");AddGate("H","0","");
  } finally {batch=false;}
  Refresh();resultView.SelectedIndex=4;resultWire.Text="0,1,2";
  status.Text="Estimate P("+phase+") on |1⟩. Read q0q1q2 as k: phase ≈ k/8 turns. q3 stays |1⟩. The T-gate preset gives 001 (1/8).";
 }
 public void BitFlip(int errorWire) {
  if(errorWire < -1 || errorWire>2)throw new ArgumentOutOfRangeException("errorWire");
  batch=true;
  try {
   qubits.SelectedIndex=4;steps.Clear();AddGate("H","0","");AddGate("S","0","");
   AddGate("CNOT","0,1","");AddGate("CNOT","0,2","");
   if(errorWire>=0)AddGate("X",errorWire.ToString(),"");
   AddGate("CNOT","0,3","");AddGate("CNOT","1,3","");AddGate("CNOT","1,4","");AddGate("CNOT","2,4","");
   AddGate("M10-X","3,4,0","");AddGate("M11-X","3,4,1","");AddGate("M01-X","3,4,2","");
   AddGate("CNOT","0,2","");AddGate("CNOT","0,1","");
  } finally {batch=false;}
  Refresh();status.Text="Correct one bit flip and decode |i⟩ on q0. Trace out [1,2,3,4]. Phase errors are not corrected.";
 }
 public void SelectSchmidtPartition(string wires) {resultView.SelectedIndex=3;resultWire.Text=wires;}
 public string InspectionExpression(int view,int wire) {return InspectionExpression(view,wire.ToString());}
 public string InspectionExpression(int view,string wires) {
  if(Count>MaxExactQubits)throw new InvalidDataException("Use Sample circuit for registers above 10 qubits. Exact state and density-matrix inspection supports up to 10 qubits.");
  if(view<0 || view>4)throw new InvalidDataException("Choose State, Probabilities, Bloch qubit, Schmidt coefficients, or Marginal probabilities.");
  if(view==3 || view==4) {
   var selected=new HashSet<int>();var ordered=new List<int>();
   foreach(string part in (wires ?? "").Split(',')) {
    int wire;if(!Int32.TryParse(part.Trim(),out wire) || wire<0 || wire>=Count)throw new InvalidDataException("Enter comma-separated wire indices between 0 and "+(Count-1)+".");
    if(!selected.Add(wire))throw new InvalidDataException("Each selected wire must appear once.");ordered.Add(wire);
   }
   if(view==4)return "probs("+Expression()+",["+String.Join(",",ordered)+"])";
   if(selected.Count==Count)throw new InvalidDataException("Leave at least one wire in side B. Schmidt inspection needs two nonempty sides.");
   foreach(var step in steps)if(Noise(step.Gate) || Feedback(step.Gate) || step.Gate=="Reset" || step.Gate=="Measure")throw new InvalidDataException("Schmidt coefficients need a pure state vector. This circuit produces a density matrix; use State, Probabilities, or Bloch qubit instead.");
   ordered.Sort();return "schmidt_coeffs("+Expression()+",["+String.Join(",",ordered)+"])";
  }
  int index=0;
  if(view==2 && (!Int32.TryParse(wires,out index) || index<0 || index>=Count))throw new InvalidDataException("Bloch wire must be an integer between 0 and "+(Count-1)+".");
  string value=Expression();return view==0 ? value : view==1 ? "probs("+value+")" : "bloch("+value+","+index+")";
 }
 public string Expression() {
  string value="|"+new string('0',Count)+"⟩";
  bool mixed=false,initial=true,requiresDensity=false;
  var transformations=steps.Count>64 ? new List<string>() : null;
  string placeholder="qstate_0";
  if(transformations!=null) {
   // Keep a user-supplied angle symbol free, including braced TeX subscripts.
   var parameterText=new StringBuilder();
   foreach(var step in steps)foreach(char ch in step.Angle ?? "")if(!Char.IsWhiteSpace(ch) && ch!='{' && ch!='}' && ch!='\\')parameterText.Append(ch);
   string parameters=parameterText.ToString();
   for(int suffix=1;parameters.Contains(placeholder);++suffix)placeholder="qstate_"+suffix;
  }
  for(int position=0;position<steps.Count;position++) {
   var step=steps[position];
   // The composer starts in the all-zero ket. Leading resets leave it unchanged.
   // Defer their density conversion through linear gates, but retain the output type.
   if(initial && step.Gate=="Reset") {requiresDensity=true;continue;}
   initial=false;
   // Consecutive resets, or computational-basis measurements, commute and are idempotent.
   // Group only the calculation; preserve the editable steps and exported program.
   if((step.Gate=="Measure" || step.Gate=="Reset") && position+1<steps.Count && steps[position+1].Gate==step.Gate) {
    var measured=new List<int>(step.Wires);
    while(position+1<steps.Count && steps[position+1].Gate==step.Gate)
     foreach(int wire in steps[++position].Wires)if(!measured.Contains(wire))measured.Add(wire);
    step=new Step {Gate=step.Gate,Angle="",Wires=measured.ToArray()};
   }
   if(transformations!=null)value=placeholder;
   if(Feedback(step.Gate)) {
    string bits=FeedbackBits(step.Gate),measured=bits.Length==1 ? step.Wires[0].ToString() : "["+step.Wires[0]+","+step.Wires[1]+"]";
    value="feedforward("+value+","+measured+","+Convert.ToInt32(bits,2)+","+FeedbackGate(step.Gate)+","+step.Wires[bits.Length]+")";mixed=true;if(transformations!=null)transformations.Add(value);continue;
   }
   if(Noise(step.Gate)) {
    if(!mixed)value="density("+value+")";
    value="channel("+value+","+ChannelExpression(step)+","+step.Wires[0]+")";mixed=true;if(transformations!=null)transformations.Add(value);continue;
   }
   string op=GateExpression(step);
   string indices=String.Join(",",Array.ConvertAll(step.Wires,n=>n.ToString()));
   value=step.Gate=="Reset" ? "reset("+value+",["+indices+"])" : step.Gate=="Measure" ? "dephase("+value+",["+indices+"])" : "apply("+op+","+value+",["+indices+"])";
   if(step.Gate=="Reset" || step.Gate=="Measure")mixed=true;
   if(transformations!=null)transformations.Add(value);
  }
  string result=transformations==null || transformations.Count==0 ? value : "sequence(["+String.Join(",",transformations)+"],|"+new string('0',Count)+"⟩,"+placeholder+")";
  return requiresDensity && !mixed ? "density("+result+")" : result;
 }
 static string ChannelExpression(Step step) {
  string constructor=step.Gate=="AD" || step.Gate=="GAD" ? "amplitude_damping" : step.Gate=="PD" ? "phase_damping" : step.Gate=="PAD" ? "phase_amplitude_damping" : step.Gate=="Thermal" ? "thermal_relaxation" : "depolarizing";
  return constructor+"("+step.Angle+")";
 }
 static string GateExpression(Step step) {
  return step.Gate=="GPhase" ? "(exp(i*("+step.Angle+"))*I)" : step.Gate+(NeedsAngle(step.Gate) ? "("+step.Angle+")" : "");
 }
 public List<NumericalSampling.Gate> SamplingGates() {
  var result=new List<NumericalSampling.Gate>();bool measured=false,dynamic=false;
  foreach(var step in steps) {
   if(step.Gate=="Measure")measured=true;
   else if(measured || step.Gate=="Reset" || Feedback(step.Gate) || Noise(step.Gate))dynamic=true;
  }
  foreach(var step in steps) {
   // Terminal measurements can use the faster single-state sampler.
   if(step.Gate=="Measure" && !dynamic)continue;
   if(Noise(step.Gate)) {
    result.Add(new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Channel,Expression=ChannelExpression(step),Wires=(int[])step.Wires.Clone()});
    continue;
   }
   if(step.Gate=="Measure" || step.Gate=="Reset") {
    result.Add(new NumericalSampling.Gate {Kind=step.Gate=="Measure" ? NumericalSampling.Operation.Measure : NumericalSampling.Operation.Reset,Wires=(int[])step.Wires.Clone()});
   } else if(Feedback(step.Gate)) {
    // Editor feedback measures now, as feedforward() does in exact evaluation.
    // Store each result before applying the condition to preserve correlations.
    string bits=FeedbackBits(step.Gate);ulong mask=0,value=0;
    for(int k=0;k<bits.Length;k++) {
     int wire=step.Wires[k];mask|=1UL<<wire;if(bits[k]=='1')value|=1UL<<wire;
     result.Add(new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{wire}});
    }
    result.Add(new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Conditional,Mask=mask,Value=value,Expression=FeedbackGate(step.Gate).ToString(),Wires=new[]{step.Wires[bits.Length]}});
   } else result.Add(new NumericalSampling.Gate {Expression=GateExpression(step),Wires=(int[])step.Wires.Clone()});
  }
  return result;
 }
 void Line(double x1,double y1,double x2,double y2,Brush color,double width,bool dashed=false) {diagram.Children.Add(new Line {X1=x1,Y1=y1,X2=x2,Y2=y2,Stroke=color,StrokeThickness=width,StrokeDashArray=dashed ? new DoubleCollection {3,2} : null});}
 void Label(string text,double x,double y,double width) {var label=new TextBlock {Text=text,Width=width,TextAlignment=TextAlignment.Center,FontSize=14,TextTrimming=TextTrimming.CharacterEllipsis,ToolTip=text}; Canvas.SetLeft(label,x); Canvas.SetTop(label,y); diagram.Children.Add(label);}
 void Refresh() {
  if(!restoring && !batch) {
   string current=Snapshot();
   if(snapshot!=current) {
    if(snapshot!=null) {past.Add(snapshot);if(past.Count>100)past.RemoveAt(0);}
    future.Clear();snapshot=current;
   }
  }
  use.IsEnabled=Count<=MaxExactQubits;
  use.ToolTip=Count>MaxExactQubits ? "Use Sample circuit for this register. Exact state and density-matrix inspection is limited to 10 qubits." : null;
  undoChange.IsEnabled=past.Count>0;redoChange.IsEnabled=future.Count>0;
  expression.Text=Expression(); status.Text=editing<0 ? steps.Count+" gate steps · Select a numbered step to edit it · Changing register size starts a new circuit" : "Editing step "+(editing+1)+" · Update gate to apply changes, or Cancel edit to keep the original";
  if(Count>MaxExactQubits)status.Text+=" · Numerical sampling only · 25-qubit states use 512 MiB plus sampling memory";
  commit.Content=editing<0 ? "Add gate" : "Update gate";cancelEdit.Visibility=editing<0 ? Visibility.Collapsed : Visibility.Visible;
  earlier.IsEnabled=editing>0;later.IsEnabled=editing>=0 && editing<steps.Count-1;deleteStep.IsEnabled=editing>=0;
  diagram.Children.Clear(); diagram.Width=Math.Max(750,100+steps.Count*90); diagram.Height=28+Count*65;
  if(editing>=0) {
   var highlight=new Border {Width=86,Height=diagram.Height-25,Background=WorkspaceTheme.Selection,CornerRadius=new CornerRadius(8)};
   Canvas.SetLeft(highlight,67+editing*90);Canvas.SetTop(highlight,25);diagram.Children.Add(highlight);
  }
  for(int q=0;q<Count;q++) {double y=45+65*q; Label("q"+q+"  |0⟩",0,y-12,75); Line(78,y,diagram.Width-15,y,WorkspaceTheme.Border,1);}
  for(int j=0;j<steps.Count;j++) {
   var step=steps[j]; double x=110+j*90; int low=step.Wires[0], high=low;
   int stepIndex=j;
   var select=new Button {Content=(j+1)+" · "+step.Gate,Width=84,Height=24,Padding=new Thickness(2),Margin=new Thickness(0),FontSize=11,ToolTip="Edit step "+(j+1)};
   System.Windows.Automation.AutomationProperties.SetName(select,"Edit step "+(j+1)+", "+step.Gate);
   Canvas.SetLeft(select,x-42);Canvas.SetTop(select,1);select.Click+=delegate {SelectStep(stepIndex);};diagram.Children.Add(select);
   foreach(int wire in step.Wires){low=Math.Min(low,wire);high=Math.Max(high,wire);}
   if(step.Wires.Length>1) Line(x,45+65*low,x,45+65*high,blue,2,Feedback(step.Gate));
   for(int k=0;k<step.Wires.Length;k++) {
    double y=45+65*step.Wires[k];
    if(Noise(step.Gate)) {
     double noiseWidth=step.Gate=="Thermal" ? 70 : 54;
     var noiseBox=new Border {Width=noiseWidth,Height=32,Background=WorkspaceTheme.WarningSurface,BorderBrush=WorkspaceTheme.Warning,BorderThickness=new Thickness(2),CornerRadius=new CornerRadius(5),ToolTip="Noise channel: "+step.Gate};
     Canvas.SetLeft(noiseBox,x-noiseWidth/2);Canvas.SetTop(noiseBox,y-16);diagram.Children.Add(noiseBox);Label(step.Gate,x-noiseWidth/2+1,y-10,noiseWidth-2);continue;
    }
    if(step.Gate=="ECR") {
     var echoBox=new Border {Width=64,Height=32,Background=WorkspaceTheme.Surface,BorderBrush=blue,BorderThickness=new Thickness(2),CornerRadius=new CornerRadius(5),ToolTip="ECR operand "+k+" (ordered wire "+step.Wires[k]+")"};
     Canvas.SetLeft(echoBox,x-32);Canvas.SetTop(echoBox,y-16);diagram.Children.Add(echoBox);Label("ECR "+k,x-31,y-10,62);continue;
    }
    if(ParityRotation(step.Gate) || step.Gate=="fSim" || Interaction(step.Gate)) {
     var pairBox=new Border {Width=52,Height=32,Background=WorkspaceTheme.Surface,BorderBrush=blue,BorderThickness=new Thickness(2),CornerRadius=new CornerRadius(5)};
     Canvas.SetLeft(pairBox,x-26);Canvas.SetTop(pairBox,y-16);diagram.Children.Add(pairBox);Label(ParityRotation(step.Gate) ? (step.Gate=="XXPlusYY" ? "XY+" : "XY−")+k : step.Gate=="fSim" ? "fSim" : Char.ToUpperInvariant(step.Gate[k+1]).ToString(),x-25,y-10,50);continue;
    }
    if(Feedback(step.Gate)) {
     var feedbackBox=new Border {Width=48,Height=32,Background=WorkspaceTheme.Surface,BorderBrush=blue,BorderThickness=new Thickness(2),CornerRadius=new CornerRadius(5)};
     Canvas.SetLeft(feedbackBox,x-24);Canvas.SetTop(feedbackBox,y-16);diagram.Children.Add(feedbackBox);
     Label(k<step.Wires.Length-1 ? "M" : FeedbackGate(step.Gate)+"|"+FeedbackBits(step.Gate),x-23,y-10,46); continue;
    }
    if(step.Gate=="SWAP" || step.Gate=="iSWAP" || step.Gate=="FSWAP" || (step.Gate=="CSWAP" && k>0)) {Line(x-8,y-8,x+8,y+8,blue,2);Line(x-8,y+8,x+8,y-8,blue,2);if(step.Gate=="iSWAP" || step.Gate=="FSWAP")Label(step.Gate=="FSWAP" ? "f" : "i",x+10,y-18,16);}
    else if(step.Wires.Length>1 && (k<step.Wires.Length-1 || step.Gate=="CZ" || step.Gate=="CCZ")) {var dot=new Ellipse {Width=10,Height=10,Fill=blue}; Canvas.SetLeft(dot,x-5);Canvas.SetTop(dot,y-5);diagram.Children.Add(dot);}
    else {var box=new Border {Width=42,Height=32,Background=WorkspaceTheme.Surface,BorderBrush=blue,BorderThickness=new Thickness(2),CornerRadius=new CornerRadius(5)}; Canvas.SetLeft(box,x-21);Canvas.SetTop(box,y-16);diagram.Children.Add(box); Label(ControlledAngle(step.Gate) ? step.Gate.Substring(1) : step.Gate=="Measure" ? "M" : step.Gate=="Reset" ? "|0⟩" : step.Gate=="CY" ? "Y" : step.Gate=="CH" ? "H" : step.Wires.Length>1 ? "X" : step.Gate,x-20,y-10,40);}
   }
   if(NeedsAngle(step.Gate)) Label(step.Angle,x-40,45+65*high+20,80);
  }
 }
}

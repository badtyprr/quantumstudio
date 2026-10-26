// GPL-2.0-or-later; see COPYING.
using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

static class BasisDeclarationEditor {
 public static Window Create(Window owner,BasisDeclaration[] initial,Action<BasisDeclaration[]> applyBasis) {
  var dialog=new Window {Title="Orthonormal bases · QuantumStudio",Owner=owner,Width=1000,Height=600,MinWidth=760,MinHeight=540,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=WorkspaceTheme.Background,FontFamily=new FontFamily("Segoe UI")};
  dialog.Resources=owner.Resources;NameScope.SetNameScope(dialog,new NameScope());
  var draft=new System.Collections.ObjectModel.ObservableCollection<BasisDeclaration>(BasisDeclarations.Copy(initial));
  var panel=new DockPanel {Margin=new Thickness(24)};dialog.Content=panel;
  var heading=new TextBlock {Text="Declare orthonormal bases",FontSize=25,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,0,0,8)};DockPanel.SetDock(heading,Dock.Top);panel.Children.Add(heading);
  var help=new TextBlock {Text="Named bases: enter labels such as red, blue; their count is the dimension. Indexed families: enter a family such as b and a positive integer dimension such as n, then use |b(j)⟩ with integer 0 ≤ j < n. Each label or family belongs to one workspace basis. Different bases keep unknown overlaps.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,0,0,16),Foreground=WorkspaceTheme.Muted};DockPanel.SetDock(help,Dock.Top);panel.Children.Add(help);
  var actions=new WrapPanel();DockPanel.SetDock(actions,Dock.Top);panel.Children.Add(actions);
  var add=new Button {Content="Add named basis"};var family=new Button {Content="Add indexed family"};var remove=new Button {Content="Remove"};actions.Children.Add(add);actions.Children.Add(family);actions.Children.Add(remove);
  var footer=new StackPanel {Margin=new Thickness(0,14,0,0)};DockPanel.SetDock(footer,Dock.Bottom);panel.Children.Add(footer);
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Error};footer.Children.Add(error);
  footer.Children.Add(new TextBlock {Text="Calculate validates symbolic dimensions and indices. Save session preserves bases and each history entry’s declarations.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,8)});
  var buttons=new StackPanel {Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right};footer.Children.Add(buttons);
  var cancel=new Button {Content="Cancel",IsCancel=true};var apply=new Button {Content="Apply bases",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};buttons.Children.Add(cancel);buttons.Children.Add(apply);
  var grid=new DataGrid {ItemsSource=draft,AutoGenerateColumns=false,CanUserAddRows=false,CanUserDeleteRows=false,CanUserSortColumns=false,SelectionMode=DataGridSelectionMode.Single,HeadersVisibility=DataGridHeadersVisibility.Column,MinRowHeight=40,Background=WorkspaceTheme.Surface,BorderBrush=WorkspaceTheme.Border};
  string[] fields={"Name","Kind","Labels","Family","Dimension"};string[] headers={"Basis name","Kind","Named labels","Family","Dimension"};
  for(int k=0;k<fields.Length;k++)grid.Columns.Add(new DataGridTextColumn {Header=headers[k],MinWidth=k==2 ? 180 : 110,Width=new DataGridLength(k==2 ? 2 : 1,DataGridLengthUnitType.Star),IsReadOnly=k==1,Binding=new System.Windows.Data.Binding(fields[k]) {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged}});
  System.Windows.Automation.AutomationProperties.SetName(grid,"Orthonormal basis declarations");panel.Children.Add(grid);
  Action commit=delegate {if(!grid.CommitEdit(DataGridEditingUnit.Cell,true) || !grid.CommitEdit(DataGridEditingUnit.Row,true))throw new InvalidOperationException("Finish the current edit before applying bases.");};
  Action refresh=delegate {remove.IsEnabled=grid.SelectedIndex>=0;add.IsEnabled=family.IsEnabled=draft.Count<BasisDeclarations.MaximumCount;};
  Action<bool> insert=delegate(bool indexed) {commit();if(draft.Count>=BasisDeclarations.MaximumCount)return;int suffix=1;while(System.Linq.Enumerable.Any(draft,d=>d.Name=="Basis_"+suffix || d.Family=="b_"+suffix))suffix++;var item=new BasisDeclaration {Name="Basis_"+suffix,Kind=BasisDeclarations.Kinds[indexed ? 1 : 0],Labels=indexed ? "" : "red_"+suffix+", blue_"+suffix,Family=indexed ? "b_"+suffix : "",Dimension=indexed ? "n" : ""};draft.Add(item);grid.SelectedItem=item;grid.ScrollIntoView(item);refresh();};
  add.Click+=delegate {try {insert(false);}catch(Exception ex){error.Text=ex.Message;}};
  family.Click+=delegate {try {insert(true);}catch(Exception ex){error.Text=ex.Message;}};
  remove.Click+=delegate {try {commit();if(grid.SelectedIndex>=0)draft.RemoveAt(grid.SelectedIndex);refresh();}catch(Exception ex){error.Text=ex.Message;}};
  grid.SelectionChanged+=delegate {refresh();};cancel.Click+=delegate {dialog.Close();};
  apply.Click+=delegate {try {commit();applyBasis(BasisDeclarations.Copy(System.Linq.Enumerable.ToArray(draft)));dialog.Close();}catch(Exception ex){error.Text=ex.Message;}};
  dialog.RegisterName("Definitions",grid);dialog.RegisterName("Add",add);dialog.RegisterName("AddFamily",family);dialog.RegisterName("Remove",remove);dialog.RegisterName("Apply",apply);dialog.RegisterName("Cancel",cancel);dialog.RegisterName("Error",error);refresh();return dialog;
 }
}

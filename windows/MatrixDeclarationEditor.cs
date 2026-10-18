// GPL-2.0-or-later; see COPYING.
using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

// The editor owns a private draft. Only a successful Apply publishes a copy.
static class MatrixDeclarationEditor {
 public static Window Create(Window owner,MatrixDeclaration[] initial,Action<MatrixDeclaration[]> applyMatrices) {
  var dialog=new Window {Title="Matrix dimensions · Quantum Studio",Owner=owner,Width=780,Height=560,MinWidth=600,MinHeight=520,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=WorkspaceTheme.Background,FontFamily=new FontFamily("Segoe UI")};
  dialog.Resources=owner.Resources;
  NameScope.SetNameScope(dialog,new NameScope());
  var draft=new System.Collections.ObjectModel.ObservableCollection<MatrixDeclaration>(MatrixDeclarations.Copy(initial));
  var panel=new DockPanel {Margin=new Thickness(24)};dialog.Content=panel;
  var heading=new TextBlock {Text="Declare your matrices",FontSize=25,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,0,0,8)};DockPanel.SetDock(heading,Dock.Top);panel.Children.Add(heading);
  var help=new TextBlock {Text="Give each matrix a symbol and its number of rows and columns. Use numbers or symbols such as n. Then write Tr(A) or A*B naturally. Dimensions apply in Quantum notation; Calculate checks their mathematical validity.",TextWrapping=TextWrapping.Wrap,FontSize=14,Foreground=WorkspaceTheme.Muted,Margin=new Thickness(0,0,0,16)};DockPanel.SetDock(help,Dock.Top);panel.Children.Add(help);
  var actions=new WrapPanel();DockPanel.SetDock(actions,Dock.Top);panel.Children.Add(actions);
  var add=new Button {Content="Add matrix"};var pair=new Button {Content="Add A and B"};var remove=new Button {Content="Remove"};var up=new Button {Content="Move up"};var down=new Button {Content="Move down"};
  foreach(var button in new[]{add,pair,remove,up,down})actions.Children.Add(button);
  var footer=new StackPanel {Margin=new Thickness(0,14,0,0)};DockPanel.SetDock(footer,Dock.Bottom);panel.Children.Add(footer);
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=WorkspaceTheme.Error,Margin=new Thickness(0,0,0,8)};footer.Children.Add(error);
  var note=new TextBlock {Text="Save session keeps these dimensions and the dimensions used by each history entry.",TextWrapping=TextWrapping.Wrap,FontSize=12,Margin=new Thickness(0,0,0,10)};footer.Children.Add(note);
  var buttons=new StackPanel {Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right};footer.Children.Add(buttons);
  var cancelEdit=new Button {Content="Cancel",IsCancel=true};var apply=new Button {Content="Apply matrices",Background=WorkspaceTheme.Primary,Foreground=WorkspaceTheme.OnPrimary};buttons.Children.Add(cancelEdit);buttons.Children.Add(apply);
  var grid=new DataGrid {ItemsSource=draft,AutoGenerateColumns=false,CanUserAddRows=false,CanUserDeleteRows=false,CanUserSortColumns=false,CanUserReorderColumns=false,SelectionMode=DataGridSelectionMode.Single,HeadersVisibility=DataGridHeadersVisibility.Column,RowHeaderWidth=0,MinRowHeight=40,FontSize=14,Background=WorkspaceTheme.Surface,BorderBrush=WorkspaceTheme.Border,GridLinesVisibility=DataGridGridLinesVisibility.Horizontal,HorizontalGridLinesBrush=WorkspaceTheme.Border};
  var editingStyle=new Style(typeof(TextBox),(Style)Application.Current.FindResource(typeof(TextBox)));editingStyle.Setters.Add(new Setter(TextBox.PaddingProperty,new Thickness(6)));editingStyle.Setters.Add(new Setter(TextBox.FontSizeProperty,14.0));
  var displayStyle=new Style(typeof(TextBlock),(Style)Application.Current.FindResource(typeof(TextBlock)));displayStyle.Setters.Add(new Setter(TextBlock.MarginProperty,new Thickness(6)));displayStyle.Setters.Add(new Setter(TextBlock.TextWrappingProperty,TextWrapping.Wrap));
  grid.Columns.Add(new DataGridTextColumn {Header="Matrix symbol",MinWidth=130,Width=new DataGridLength(160),Binding=new System.Windows.Data.Binding("Name") {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged},EditingElementStyle=editingStyle,ElementStyle=displayStyle});
  grid.Columns.Add(new DataGridTextColumn {Header="Rows",MinWidth=130,Width=new DataGridLength(1,DataGridLengthUnitType.Star),Binding=new System.Windows.Data.Binding("Rows") {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged},EditingElementStyle=editingStyle,ElementStyle=displayStyle});
  grid.Columns.Add(new DataGridTextColumn {Header="Columns",MinWidth=130,Width=new DataGridLength(1,DataGridLengthUnitType.Star),Binding=new System.Windows.Data.Binding("Columns") {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged},EditingElementStyle=editingStyle,ElementStyle=displayStyle});
  System.Windows.Automation.AutomationProperties.SetName(grid,"Matrix dimension declarations");panel.Children.Add(grid);
  Action commit=delegate {grid.CommitEdit(DataGridEditingUnit.Cell,true);grid.CommitEdit(DataGridEditingUnit.Row,true);};
  Action refresh=delegate {int index=grid.SelectedIndex;remove.IsEnabled=index>=0;up.IsEnabled=index>0;down.IsEnabled=index>=0 && index<draft.Count-1;add.IsEnabled=draft.Count<MatrixDeclarations.MaximumCount;pair.IsEnabled=draft.Count<=MatrixDeclarations.MaximumCount-2;};
  grid.SelectionChanged+=delegate {refresh();};
  grid.CellEditEnding+=delegate {error.Text="";};
  add.Click+=delegate {commit();if(draft.Count>=MatrixDeclarations.MaximumCount)return;int suffix=1;while(System.Linq.Enumerable.Any(draft,s=>s.Name=="M"+suffix))suffix++;var state=new MatrixDeclaration {Name="M"+suffix,Rows="n",Columns="n"};draft.Add(state);grid.SelectedItem=state;grid.ScrollIntoView(state);error.Text="";refresh();};
  pair.Click+=delegate {commit();if(draft.Count>MatrixDeclarations.MaximumCount-2)return;if(System.Linq.Enumerable.Any(draft,s=>s.Name=="A" || s.Name=="B")){error.Text="A or B already exists. Edit that declaration or choose another name.";return;}draft.Add(new MatrixDeclaration {Name="A",Rows="n",Columns="n"});draft.Add(new MatrixDeclaration {Name="B",Rows="n",Columns="n"});grid.SelectedIndex=draft.Count-1;grid.ScrollIntoView(grid.SelectedItem);error.Text="";refresh();};
  remove.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>=0)draft.RemoveAt(index);refresh();};
  up.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>0){draft.Move(index,index-1);grid.SelectedIndex=index-1;}refresh();};
  down.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>=0 && index<draft.Count-1){draft.Move(index,index+1);grid.SelectedIndex=index+1;}refresh();};
  cancelEdit.Click+=delegate {dialog.Close();};
  apply.Click+=delegate {try {commit();var proposed=System.Linq.Enumerable.ToArray(draft);applyMatrices(MatrixDeclarations.Copy(proposed));dialog.Close();}catch(Exception ex){error.Text=ex.Message;}};
  dialog.RegisterName("Definitions",grid);dialog.RegisterName("AddPair",pair);dialog.RegisterName("Apply",apply);dialog.RegisterName("Cancel",cancelEdit);dialog.RegisterName("Error",error);dialog.RegisterName("Add",add);dialog.RegisterName("Remove",remove);dialog.RegisterName("MoveUp",up);dialog.RegisterName("MoveDown",down);refresh();return dialog;
 }
}

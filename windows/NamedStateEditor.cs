// GPL-2.0-or-later; see COPYING.
using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

// The editor owns a private draft. Only a successful Apply publishes a copy.
static class NamedStateEditor {
 public static Window Create(Window owner,StateDefinition[] initial,Action<StateDefinition[]> applyStates) {
  var dialog=new Window {Title="Named states · Quantum Studio",Owner=owner,Width=780,Height=560,MinWidth=600,MinHeight=520,WindowStartupLocation=WindowStartupLocation.CenterOwner,Background=new SolidColorBrush(Color.FromRgb(245,246,250)),FontFamily=new FontFamily("Segoe UI")};
  dialog.Resources=owner.Resources;
  NameScope.SetNameScope(dialog,new NameScope());
  var draft=new System.Collections.ObjectModel.ObservableCollection<StateDefinition>(SessionStore.CopyStates(initial));
  var panel=new DockPanel {Margin=new Thickness(24)};dialog.Content=panel;
  var heading=new TextBlock {Text="Give your states a name",FontSize=25,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,0,0,8)};DockPanel.SetDock(heading,Dock.Top);panel.Children.Add(heading);
  var help=new TextBlock {Text="Use names in bras and kets: <Bell|after CZ>. Definitions use quantum notation and may reference states above them. Calculation checks the vectors; states are not automatically normalized.",TextWrapping=TextWrapping.Wrap,FontSize=14,Foreground=new SolidColorBrush(Color.FromRgb(90,105,130)),Margin=new Thickness(0,0,0,16)};DockPanel.SetDock(help,Dock.Top);panel.Children.Add(help);
  var actions=new WrapPanel();DockPanel.SetDock(actions,Dock.Top);panel.Children.Add(actions);
  var add=new Button {Content="Add state"};var bell=new Button {Content="Add Bell example"};var remove=new Button {Content="Remove"};var up=new Button {Content="Move up"};var down=new Button {Content="Move down"};
  foreach(var button in new[]{add,bell,remove,up,down})actions.Children.Add(button);
  var footer=new StackPanel {Margin=new Thickness(0,14,0,0)};DockPanel.SetDock(footer,Dock.Bottom);panel.Children.Add(footer);
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap,Foreground=Brushes.Firebrick,Margin=new Thickness(0,0,0,8)};footer.Children.Add(error);
  var note=new TextBlock {Text="Save session keeps these definitions and the definitions used by each history entry.",TextWrapping=TextWrapping.Wrap,FontSize=12,Margin=new Thickness(0,0,0,10)};footer.Children.Add(note);
  var buttons=new StackPanel {Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right};footer.Children.Add(buttons);
  var cancelEdit=new Button {Content="Cancel",IsCancel=true};var apply=new Button {Content="Apply states",Background=new SolidColorBrush(Color.FromRgb(55,94,232)),Foreground=Brushes.White};buttons.Children.Add(cancelEdit);buttons.Children.Add(apply);
  var grid=new DataGrid {ItemsSource=draft,AutoGenerateColumns=false,CanUserAddRows=false,CanUserDeleteRows=false,CanUserSortColumns=false,CanUserReorderColumns=false,SelectionMode=DataGridSelectionMode.Single,HeadersVisibility=DataGridHeadersVisibility.Column,RowHeaderWidth=0,MinRowHeight=40,FontSize=14,Background=Brushes.White,BorderBrush=new SolidColorBrush(Color.FromRgb(221,226,238)),GridLinesVisibility=DataGridGridLinesVisibility.Horizontal,HorizontalGridLinesBrush=new SolidColorBrush(Color.FromRgb(235,239,246))};
  var editingStyle=new Style(typeof(TextBox));editingStyle.Setters.Add(new Setter(TextBox.PaddingProperty,new Thickness(6)));editingStyle.Setters.Add(new Setter(TextBox.FontSizeProperty,14.0));
  var displayStyle=new Style(typeof(TextBlock));displayStyle.Setters.Add(new Setter(TextBlock.MarginProperty,new Thickness(6)));displayStyle.Setters.Add(new Setter(TextBlock.TextWrappingProperty,TextWrapping.Wrap));
  grid.Columns.Add(new DataGridTextColumn {Header="State name",MinWidth=130,Width=new DataGridLength(160),Binding=new System.Windows.Data.Binding("Name") {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged},EditingElementStyle=editingStyle,ElementStyle=displayStyle});
  grid.Columns.Add(new DataGridTextColumn {Header="Defining expression",MinWidth=240,Width=new DataGridLength(1,DataGridLengthUnitType.Star),Binding=new System.Windows.Data.Binding("Expression") {UpdateSourceTrigger=System.Windows.Data.UpdateSourceTrigger.PropertyChanged},EditingElementStyle=editingStyle,ElementStyle=displayStyle});
  System.Windows.Automation.AutomationProperties.SetName(grid,"Named state definitions");panel.Children.Add(grid);
  Action commit=delegate {grid.CommitEdit(DataGridEditingUnit.Cell,true);grid.CommitEdit(DataGridEditingUnit.Row,true);};
  Action refresh=delegate {int index=grid.SelectedIndex;remove.IsEnabled=index>=0;up.IsEnabled=index>0;down.IsEnabled=index>=0 && index<draft.Count-1;add.IsEnabled=draft.Count<SessionStore.MaximumStates;bell.IsEnabled=draft.Count<=SessionStore.MaximumStates-2;};
  grid.SelectionChanged+=delegate {refresh();};
  grid.CellEditEnding+=delegate {error.Text="";};
  add.Click+=delegate {commit();if(draft.Count>=SessionStore.MaximumStates)return;int suffix=1;while(System.Linq.Enumerable.Any(draft,s=>s.Name=="state"+suffix))suffix++;var state=new StateDefinition {Name="state"+suffix,Expression="|0>"};draft.Add(state);grid.SelectedItem=state;grid.ScrollIntoView(state);error.Text="";refresh();};
  bell.Click+=delegate {commit();if(draft.Count>SessionStore.MaximumStates-2)return;if(System.Linq.Enumerable.Any(draft,s=>s.Name=="Bell" || s.Name=="after CZ")){error.Text="Bell or after CZ already exists. Edit that definition or choose another name.";return;}draft.Add(new StateDefinition {Name="Bell",Expression="|Phi+>"});draft.Add(new StateDefinition {Name="after CZ",Expression="CZ|Bell>"});grid.SelectedIndex=draft.Count-1;grid.ScrollIntoView(grid.SelectedItem);error.Text="";refresh();};
  remove.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>=0)draft.RemoveAt(index);refresh();};
  up.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>0){draft.Move(index,index-1);grid.SelectedIndex=index-1;}refresh();};
  down.Click+=delegate {commit();int index=grid.SelectedIndex;if(index>=0 && index<draft.Count-1){draft.Move(index,index+1);grid.SelectedIndex=index+1;}refresh();};
  cancelEdit.Click+=delegate {dialog.Close();};
  apply.Click+=delegate {try {commit();var proposed=System.Linq.Enumerable.ToArray(draft);applyStates(SessionStore.CopyStates(proposed));dialog.Close();}catch(Exception ex){error.Text=ex.Message;}};
  dialog.RegisterName("Definitions",grid);dialog.RegisterName("AddBell",bell);dialog.RegisterName("Apply",apply);dialog.RegisterName("Cancel",cancelEdit);dialog.RegisterName("Error",error);dialog.RegisterName("Add",add);dialog.RegisterName("Remove",remove);dialog.RegisterName("MoveUp",up);dialog.RegisterName("MoveDown",down);refresh();return dialog;
 }
}

#!/usr/bin/env python

try:
    import os
    import commands
    import sys
    import string    
    import gettext
    from gi.repository import Gio, Gtk
    from gi.repository import GdkPixbuf 
    import gconf
    import json
    from user import home
except Exception, detail:
    print detail
    sys.exit(1)


# i18n
gettext.install("cinnamon-settings", "/usr/share/cinnamon/locale")

# i18n for menu item
menuName = _("Desktop Settings")
menuGenericName = _("Desktop Configuration Tool")
menuComment = _("Fine-tune desktop settings")
                                  
class SidePage:
    def __init__(self, name, icon, content_box):        
        self.name = name
        self.icon = icon
        self.content_box = content_box
        self.widgets = []
        
    def add_widget(self, widget):
        self.widgets.append(widget)
        
    def build(self):
        # Clear all the widgets from the content box
        widgets = self.content_box.get_children()
        for widget in widgets:
            self.content_box.remove(widget)
        
        # Add our own widgets
        for widget in self.widgets:
            self.content_box.pack_start(widget, False, False, 2)            
            self.content_box.show_all()
                      
class ThemeViewSidePage (SidePage):
    def __init__(self, name, icon, content_box):   
        SidePage.__init__(self, name, icon, content_box)        
        self.icons = []
                  
    def build(self):
        # Clear all the widgets from the content box
        widgets = self.content_box.get_children()
        for widget in widgets:
            self.content_box.remove(widget)
        
        # Find the current theme name
        self.settings = Gio.Settings.new("org.cinnamon.theme")
        self.current_theme = self.settings.get_string("name")
        
        # Add our own widgets
        scrolledWindow = Gtk.ScrolledWindow()                
        
        iconView = Gtk.IconView();        
        self.model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
                 
        img = GdkPixbuf.Pixbuf.new_from_file_at_size( "/usr/share/cinnamon/theme/thumbnail.png", 64, 64 )

        self.active_theme_iter = self.model.append(["Cinnamon", img])
                     
        self.load_themes_in('/usr/share/themes')
        self.load_themes_in('%s/.themes' % home)
        
        iconView.set_text_column(0)
        iconView.set_pixbuf_column(1)
        iconView.set_model(self.model)    
        if (self.active_theme_iter is not None):
            iconView.select_path(self.model.get_path(self.active_theme_iter))
        iconView.connect("selection_changed", self.apply_theme )
        scrolledWindow.add(iconView)
        self.content_box.add(scrolledWindow)
        self.content_box.show_all()
    
    def load_themes_in(self, directory):
        if os.path.exists(directory) and os.path.isdir(directory):
            themes = os.listdir(directory)
            themes.sort()
            for theme in themes:
                if os.path.exists("%s/%s/cinnamon/cinnamon.css" % (directory, theme)):
                    if os.path.exists("%s/%s/cinnamon/thumbnail.png" % (directory, theme)):
                        img = GdkPixbuf.Pixbuf.new_from_file_at_size( "%s/%s/cinnamon/thumbnail.png" % (directory, theme), 64, 64 )
                    else:
                        img = GdkPixbuf.Pixbuf.new_from_file_at_size( "/usr/share/cinnamon/theme/thumbnail-generic.png", 64, 64 )
                    theme_iter = self.model.append([theme, img])
                    if theme==self.current_theme:
                        self.active_theme_iter = theme_iter
        
    def apply_theme(self, iconView):
        selected_items = iconView.get_selected_items()
        if len(selected_items) > 0:
            path = selected_items[0];                  
            iterator = self.model.get_iter(path)
            theme_name = self.model.get_value(iterator, 0)
            if theme_name == "Cinnamon":
                theme_name = ""            
            self.settings.set_string("name", theme_name)
            
class ExtensionViewSidePage (SidePage):
    def __init__(self, name, icon, content_box):   
        SidePage.__init__(self, name, icon, content_box)        
        self.icons = []
                  
    def build(self):
        # Clear all the widgets from the content box
        widgets = self.content_box.get_children()
        for widget in widgets:
            self.content_box.remove(widget)
        
        scrolledWindow = Gtk.ScrolledWindow()    
        treeview = Gtk.TreeView()
                
        cr = Gtk.CellRendererToggle()
        cr.connect("toggled", self.toggled, treeview)
        column1 = Gtk.TreeViewColumn(_("Enable"), cr)
        column1.set_cell_data_func(cr, self.celldatafunction_checkbox)
        column1.set_sort_column_id(4)
        column1.set_resizable(True)

        column2 = Gtk.TreeViewColumn(_("UUID"), Gtk.CellRendererText(), text=0)
        column2.set_sort_column_id(1)
        column2.set_resizable(True)

        column3 = Gtk.TreeViewColumn(_("Name"), Gtk.CellRendererText(), text=1)
        column3.set_sort_column_id(2)
        column3.set_resizable(True)

        column4 = Gtk.TreeViewColumn(_("Description"), Gtk.CellRendererText(), text=2)
        column4.set_sort_column_id(3)
        column4.set_resizable(True)
        
        treeview.append_column(column1)
        treeview.append_column(column2)
        treeview.append_column(column3)
        treeview.append_column(column4)
        treeview.set_headers_clickable(True)
        treeview.set_reorderable(False)
            
        self.model = Gtk.TreeStore(str, str, str, bool)
        #self.model.set_sort_column_id( 1, Gtk.SORT_ASCENDING )
        treeview.set_model(self.model)
                                
        # Find the enabled extensions
        self.settings = Gio.Settings.new("org.cinnamon")
        self.enabled_extensions = self.settings.get_strv("enabled-extensions")
                         
        self.load_extensions_in('/usr/share/cinnamon/extensions')                                                                          
        self.load_extensions_in('%s/.local/share/cinnamon/extensions' % home)
        
        scrolledWindow.add(treeview)                                       
        self.content_box.add(scrolledWindow)
        self.content_box.show_all()   
        
    def load_extensions_in(self, directory):
        if os.path.exists(directory) and os.path.isdir(directory):
            extensions = os.listdir(directory)
            extensions.sort()
            for extension in extensions:            
                if os.path.exists("%s/%s/metadata.json" % (directory, extension)):
                    json_data=open("%s/%s/metadata.json" % (directory, extension)).read()
                    data = json.loads(json_data)  
                    extension_uuid = data["uuid"]
                    extension_name = data["name"]                
                    extension_description = data["description"]
                    iter = self.model.insert_before(None, None)
                    self.model.set_value(iter, 0, extension_uuid)                
                    self.model.set_value(iter, 1, extension_name)
                    self.model.set_value(iter, 2, extension_description)
                    self.model.set_value(iter, 3, (extension_uuid in self.enabled_extensions))
        
    def toggled(self, renderer, path, treeview):        
        iter = self.model.get_iter(path)
        if (iter != None):
            uuid = self.model.get_value(iter, 0)
            checked = self.model.get_value(iter, 3)
            if (checked):
                self.model.set_value(iter, 3, False)
                self.enabled_extensions.remove(uuid)
            else:
                self.model.set_value(iter, 3, True) 
                self.enabled_extensions.append(uuid)
            
            self.settings.set_strv("enabled-extensions", self.enabled_extensions)
                
    def celldatafunction_checkbox(self, column, cell, model, iter, data=None):
        cell.set_property("activatable", True)
        checked = model.get_value(iter, 3)
        if (checked):
            cell.set_property("active", True)
        else:
            cell.set_property("active", False)

class GConfCheckButton(Gtk.CheckButton):    
    def __init__(self, label, key):        
        self.key = key
        super(GConfCheckButton, self).__init__(label)       
        self.settings = gconf.client_get_default()
        self.set_active(self.settings.get_bool(self.key))
        self.settings.notify_add(self.key, self.on_my_setting_changed)
        self.connect('toggled', self.on_my_value_changed)            
    
    def on_my_setting_changed(self, client, cnxn_id, entry):
        value = entry.value.get_bool()
        self.set_active(value)
        
    def on_my_value_changed(self, widget):
        self.settings.set_bool(self.key, self.get_active())

            
class GSettingsCheckButton(Gtk.CheckButton):    
    def __init__(self, label, schema, key):        
        self.key = key
        super(GSettingsCheckButton, self).__init__(label)
        self.settings = Gio.Settings.new(schema)        
        self.set_active(self.settings.get_boolean(self.key))
        self.settings.connect("changed::"+self.key, self.on_my_setting_changed)
        self.connect('toggled', self.on_my_value_changed)            
    
    def on_my_setting_changed(self, settings, key):
        self.set_active(self.settings.get_boolean(self.key))
        
    def on_my_value_changed(self, widget):
        self.settings.set_boolean(self.key, self.get_active())

class GSettingsEntry(Gtk.HBox):    
    def __init__(self, label, schema, key):        
        self.key = key
        super(GSettingsEntry, self).__init__()
        self.label = Gtk.Label(label)
        self.content_widget = Gtk.Entry()
        self.add(self.label)
        self.add(self.content_widget)     
        self.settings = Gio.Settings.new(schema)        
        self.content_widget.set_text(self.settings.get_string(self.key))
        self.settings.connect("changed::"+self.key, self.on_my_setting_changed)
        self.content_widget.connect('changed', self.on_my_value_changed)            
    
    def on_my_setting_changed(self, settings, key):
        self.content_widget.set_text(self.settings.get_string(self.key))
        
    def on_my_value_changed(self, widget):
        self.settings.set_string(self.key, self.content_widget.get_text())
        
class MainWindow:
  
    # Change pages
    def side_view_nav(self, side_view):
        selected_items = side_view.get_selected_items()
        if len(selected_items) > 0:
            path = selected_items[0];            
            iterator = self.store.get_iter(path)
            print self.store.get_value(iterator, 0)
            self.store.get_value(iterator,2).build()
            
    ''' Create the UI '''
    def __init__(self):        
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file("/usr/lib/cinnamon-settings/cinnamon-settings.ui")
        self.window = self.builder.get_object("main_window")
        self.side_view = self.builder.get_object("side_view")
        self.content_box = self.builder.get_object("content_box")
        self.button_cancel = self.builder.get_object("button_cancel")
        
        self.window.connect("destroy", Gtk.main_quit)

        self.sidePages = []
                               
                       
        sidePage = SidePage(_("Panel"), "panel.svg", self.content_box)
        self.sidePages.append(sidePage);
        sidePage.add_widget(GSettingsEntry(_("Menu text"), "org.cinnamon", "menu-text")) 
        sidePage.add_widget(GSettingsCheckButton(_("Auto-hide panel"), "org.cinnamon", "panel-autohide")) 
        
        sidePage = SidePage(_("Calendar"), "clock.svg", self.content_box)
        self.sidePages.append(sidePage);        
        sidePage.add_widget(GSettingsCheckButton(_("Show week dates in calendar"), "org.cinnamon.calendar", "show-weekdate"))         
        sidePage.add_widget(GSettingsEntry(_("Date format for the panel"), "org.cinnamon.calendar", "date-format"))                                 
        sidePage.add_widget(GSettingsEntry(_("Date format inside the date applet"), "org.cinnamon.calendar", "date-format-full"))                                 
        sidePage.add_widget(Gtk.LinkButton.new_with_label("http://www.foragoodstrftime.com/", _("Generate your own date formats"))) 
        
        sidePage = SidePage(_("Overview"), "overview.svg", self.content_box)
        self.sidePages.append(sidePage);
        sidePage.add_widget(GSettingsCheckButton(_("Overview icon visible"), "org.cinnamon", "overview-corner-visible")) 
        sidePage.add_widget(GSettingsCheckButton(_("Overview hot corner enabled"), "org.cinnamon", "overview-corner-hover")) 
        
        sidePage = ThemeViewSidePage(_("Themes"), "themes.svg", self.content_box)
        self.sidePages.append(sidePage);
        
        sidePage = ExtensionViewSidePage(_("Extensions"), "extensions.svg", self.content_box)
        self.sidePages.append(sidePage);
        
        #sidePage = SidePage(_("Terminal"), "terminal", self.content_box)
        #self.sidePages.append(sidePage);
        #sidePage.add_widget(GConfCheckButton(_("Show fortune cookies"), "/desktop/linuxmint/terminal/show_fortunes"))
        
                                
        # create the backing store for the side nav-view.                    
        theme = Gtk.IconTheme.get_default()
        self.store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, object)
        for sidePage in self.sidePages:
            img = GdkPixbuf.Pixbuf.new_from_file_at_size( "/usr/lib/cinnamon-settings/data/icons/%s" % sidePage.icon, 48, 48)
            self.store.append([sidePage.name, img, sidePage])     
                      
        # set up the side view - navigation.
        self.side_view.set_text_column(0)
        self.side_view.set_pixbuf_column(1)
        self.side_view.set_model(self.store)
        #path = self.side_view.get_path_at_pos(0,0)
        #self.side_view.select_path(path)
        self.side_view.connect("selection_changed", self.side_view_nav )

        # set up larger components.
        self.window.set_title(_("Desktop Settings"))
        self.window.connect("destroy", Gtk.main_quit)
        self.button_cancel.connect("clicked", Gtk.main_quit)                                    
        self.window.show()
                
                
if __name__ == "__main__":
    MainWindow()
    Gtk.main()

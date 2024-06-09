import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from classes.upnp_interface import UPnPinterface

class MainWindow(Gtk.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(600, 400)
        self.set_title("Simple UPNP")
        
        self.box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.inputRow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.labelRow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=17)
        self.gridBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.box1.set_halign(Gtk.Align.END)
        
        self.labelRow.set_margin_top(5)

        self.add(self.box1)

        self.box1.pack_start(self.gridBox, True, True, 0)
        self.box1.pack_start(self.labelRow, True, True, 0)
        self.box1.pack_start(self.inputRow, True, True, 0)

        self.createPortMapperMenu()
        self.createUPnPMappingList()
    
    def createUPnPMappingList(self):
        self.liststore = Gtk.ListStore(str, str, int, int, bool, bool)
        mappings = upnp.get_port_mappings()
        if type(mappings) == dict:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to find port mappings.\nReturned {mappings['code']} {mappings['error']}"
            )
            dialog.run()
            dialog.destroy()
        else:
            for mapping in mappings:
                self.liststore.append([mapping['NewProtocol'],f"{mapping['NewInternalClient']}:{mapping['NewInternalPort']}", int(mapping['NewExternalPort']), int(mapping['NewLeaseDuration']), False, False])

        treeview = Gtk.TreeView(model=self.liststore)

        renderer_text = Gtk.CellRendererText()
        column_protocol = Gtk.TreeViewColumn("Protocol", renderer_text, text=0)
        treeview.append_column(column_protocol)

        renderer_mapping = Gtk.CellRendererText()
        column_mapping = Gtk.TreeViewColumn("Mapping", renderer_mapping, text=1)
        treeview.append_column(column_mapping)

        renderer_external_port = Gtk.CellRendererSpin()
        column_external_port = Gtk.TreeViewColumn("External Port", renderer_external_port, text=2)
        treeview.append_column(column_external_port)

        renderer_lease_duration = Gtk.CellRendererSpin()
        column_lease_duration = Gtk.TreeViewColumn("Lease Duration", renderer_lease_duration, text=3)
        treeview.append_column(column_lease_duration)

        renderer_renew = Gtk.CellRendererToggle()
        renderer_renew.connect("toggled", self.on_renew_toggled)

        column_renew = Gtk.TreeViewColumn("Renew", renderer_renew, active=4)
        treeview.append_column(column_renew)

        renderer_remove = Gtk.CellRendererToggle()
        renderer_remove.connect("toggled", self.on_remove_toggled)

        column_remove = Gtk.TreeViewColumn("Remove", renderer_remove, active=5)
        treeview.append_column(column_remove)

        self.refreshButton = Gtk.Button(label="Refresh")
        self.removeButton = Gtk.Button(label="Remove selected")

        self.refreshButton.connect('clicked', self.refreshMappingsList)
        self.removeButton.connect('clicked', self.removePort)

        self.gridBox.pack_start(treeview, False, False, 0)
        self.gridBox.pack_start(self.refreshButton, False, False, 0)
        self.gridBox.pack_start(self.removeButton, False, False, 0)

    def on_renew_toggled(self, widget, path):
        self.liststore[path][4] = not self.liststore[path][4]
    def on_remove_toggled(self, widget, path):
        self.liststore[path][5] = not self.liststore[path][5]
    
    def createPortMapperMenu(self):
        self.internalPortBox = Gtk.Entry(text="12345")
        self.externalPortBox = Gtk.Entry(text="12345")
        ip = upnp.get_local_ip()
        self.internalIPBox = Gtk.Entry(text=ip)
        self.leaseDurationBox = Gtk.Entry(text="0")
        self.descriptionBox = Gtk.Entry(text="Server")
        self.button1 = Gtk.RadioButton.new_with_label_from_widget(None, "TCP")

        self.button2 = Gtk.RadioButton.new_from_widget(self.button1)
        self.button2.set_label("UDP")

        self.submitButton = Gtk.Button(label="Submit")

        self.button1.set_active(True)

        self.submitButton.connect('clicked', self.addPort)

        self.interalIPLabel = Gtk.Label()
        self.interalIPLabel.set_text("IP Address")
        self.externalPortLabel = Gtk.Label()
        self.externalPortLabel.set_text("External Port")
        self.internalPortLabel = Gtk.Label()
        self.internalPortLabel.set_text("Internal Port")
        self.leaseDurationLabel = Gtk.Label()
        self.leaseDurationLabel.set_text("Lease Duration")
        self.descriptionLabel = Gtk.Label()
        self.descriptionLabel.set_text("Description")
        self.protocolLabel = Gtk.Label()
        self.protocolLabel.set_text("Protocol")

        self.labelRow.pack_start(self.interalIPLabel, False, False, 0)
        self.labelRow.pack_start(self.externalPortLabel, False, False, 0)
        self.labelRow.pack_start(self.internalPortLabel, False, False, 0)
        self.labelRow.pack_start(self.leaseDurationLabel, False, False, 0)
        self.labelRow.pack_start(self.descriptionLabel, False, False, 0)
        self.labelRow.pack_start(self.protocolLabel, False, False, 0)

        self.radioBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.radioBox.pack_start(self.button1, False, False, 0)
        self.radioBox.pack_start(self.button2, False, False, 0)
        self.inputRow.pack_start(self.internalIPBox, False, False, 0)
        self.inputRow.pack_start(self.internalPortBox, False, False, 0)
        self.inputRow.pack_start(self.externalPortBox, False, False, 0)
        self.inputRow.pack_start(self.leaseDurationBox, False, False, 0)
        self.inputRow.pack_start(self.descriptionBox, False, False, 0)
        self.inputRow.pack_start(self.radioBox, False, False, 0)
        self.inputRow.pack_start(self.submitButton, False, False, 0)


    def addPort(self, button):
        protocol = "TCP" if self.button1.get_active() else "UDP"
        response = upnp.add_port_mapping(self.internalIPBox.get_text(), 
                         int(self.externalPortBox.get_text()), 
                         int(self.internalPortBox.get_text()), 
                         protocol, 
                         self.descriptionBox.get_text(), 
                         int(self.leaseDurationBox.get_text()))
        if response['code'] == 0:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=f"Port mapping added successfully."
            )
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to add port mapping.\nReturned {response['code']} {response['error']}"
            )
            dialog.run()
            dialog.destroy()
    
    def removePort(self, button):
        iter = self.liststore.get_iter_first()
        while iter is not None:
            port, protocol, remove = self.liststore.get(iter, 2, 0, 5)
            iter = self.liststore.iter_next(iter)
            if not(remove):
                continue
            response = upnp.remove_port_mapping(port, protocol)
            if response['code'] == 0:
                dialog = Gtk.MessageDialog(
                    transient_for=None,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Port mapping removed successfully."
                )
                dialog.run()
                dialog.destroy()
            else:
                dialog = Gtk.MessageDialog(
                    transient_for=None,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Failed to remove port mapping.\nReturned {response['code']} {response['error']}"
                )
                dialog.run()
                dialog.destroy()
                break
            
    
    def refreshMappingsList(self, button):
        mappings = upnp.get_port_mappings()
        self.liststore.clear()
        if type(mappings) == dict:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to find port mappings.\nReturned {mappings['code']} {mappings['error']}"
            )
            dialog.run()
            dialog.destroy()
        else:
            for mapping in mappings:
                self.liststore.append([mapping['NewProtocol'],f"{mapping['NewInternalClient']}:{mapping['NewInternalPort']}", int(mapping['NewExternalPort']), int(mapping['NewLeaseDuration']), False, False])

upnp = UPnPinterface({'location':'','control_url':'','renewals':''})

win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
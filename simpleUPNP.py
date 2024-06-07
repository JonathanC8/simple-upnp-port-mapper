import requests
from xml.etree import ElementTree
import socket
import gi
import sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import netifaces


def discover_upnp_devices():
    # M-Search message body
    MS = \
        'M-SEARCH * HTTP/1.1\r\n' \
        'HOST:239.255.255.250:1900\r\n' \
        'ST:upnp:rootdevice\r\n' \
        'MX:2\r\n' \
        'MAN:"ssdp:discover"\r\n' \
        '\r\n'
    
    # Set up a UDP socket for multicast
    SOC = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    SOC.settimeout(2)
    
    # Send M-Search message to multicast address for UPNP
    SOC.sendto(MS.encode('utf-8'), ('239.255.255.250', 1900) )
    
    #listen and capture returned responses
    gateway_info = {}
    try:
        while True:
            data, addr = SOC.recvfrom(8192)
            #print (addr," ", data.decode('utf-8'))
            lines = data.decode("utf-8").strip().split('\n')

            # Loop through each line and parse key-value pairs
            for line in lines:
                if ":" in line:
                    # Split each line at the first occurrence of ":"
                    key, value = line.split(":", 1)
                    # Remove leading and trailing whitespaces from key and value
                    key = key.strip()
                    value = value.strip()
                    # Add key-value pair to the dictionary
                    gateway_info[key] = value
    except socket.timeout:
            pass
    return gateway_info

def get_control_url(location):
    headers = {"Content-Type": "application/xml"}
    response = requests.get(location, headers=headers)
    xml_data = response.text
    control_url = None

    root = ElementTree.fromstring(xml_data)
    services = root.findall('.//{urn:schemas-upnp-org:device-1-0}serviceList/{urn:schemas-upnp-org:device-1-0}service')
    if not services:
        print("No service elements found in the XML data.")
        return None

    for service in services:
        service_type = service.find('{urn:schemas-upnp-org:device-1-0}serviceType').text
        if "WANIPConnection" in service_type or "WANPPPConnection" in service_type:
            control_url = service.find('{urn:schemas-upnp-org:device-1-0}controlURL').text
            break

    return control_url

def remove_port_mapping(external_port, protocol="TCP"):
    # Replace these values with your router's control URL
    control_url = "http://192.168.1.1:45766/ctl/IPConn"

    headers = {
        "Content-Type": "text/xml",
        "SOAPAction": '"urn:schemas-upnp-org:service:WANIPConnection:1#DeletePortMapping"'
    }

    body = f"""<?xml version="1.0"?>
    <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
    s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
            <u:DeletePortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">
                <NewRemoteHost></NewRemoteHost>
                <NewExternalPort>{external_port}</NewExternalPort>
                <NewProtocol>{protocol}</NewProtocol>
            </u:DeletePortMapping>
        </s:Body>
    </s:Envelope>"""

    response = requests.post(control_url, headers=headers, data=body)

    if response.status_code == 200:
        print("Port mapping removed successfully.")
    else:
        print("Failed to remove port mapping.")
        print(response.text)

def add_port_mapping(internal_client, external_port, internal_port, protocol, description, leaseDuration):
    upnp_gateway = discover_upnp_devices()
    try:
        location = upnp_gateway['LOCATION']  # Change this to your router's description URL
        control_url = get_control_url(location)
    except Exception as e:
        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Failed to add port mapping, could not find IGD device."
        )
        dialog.run()
        dialog.destroy()
        return None

    if control_url:
        headers = {
            "Content-Type": "text/xml",
            "SOAPAction": '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"'
        }

        body = f"""<?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
        s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <s:Body>
                <u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">
                    <NewRemoteHost></NewRemoteHost>
                    <NewExternalPort>{external_port}</NewExternalPort>
                    <NewProtocol>{protocol}</NewProtocol>
                    <NewInternalPort>{internal_port}</NewInternalPort>
                    <NewInternalClient>{internal_client}</NewInternalClient>
                    <NewEnabled>1</NewEnabled>
                    <NewPortMappingDescription>{description}</NewPortMappingDescription>
                    <NewLeaseDuration>{leaseDuration}</NewLeaseDuration>
                </u:AddPortMapping>
            </s:Body>
        </s:Envelope>"""

        response = requests.post(f"http://192.168.1.1:45766{control_url}", headers=headers, data=body)
        
        if response.status_code == 200:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to add port mapping.\n{response.text}"
            )
            dialog.run()
            dialog.destroy()
            print("Port mapping added successfully.\n", response.text)
        else:
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Failed to add port mapping.\n{response.text}"
            )
            dialog.run()
            dialog.destroy()
            print("Failed to add port mapping.\n",response.text)

class MainWindow(Gtk.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(600, 400)
        self.set_title("MyApp")
        
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

        self.internalPortBox = Gtk.Entry(text="12345")
        self.externalPortBox = Gtk.Entry(text="12345")
        self.internalIPBox = Gtk.Entry(text=(netifaces.ifaddresses(netifaces.interfaces()[2])[2][0]['addr']))
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

        self.radioBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.radioBox.pack_start(self.button1, False, False, 0)
        self.radioBox.pack_start(self.button2, False, False, 0)

        self.labelRow.pack_start(self.interalIPLabel, False, False, 0)
        self.labelRow.pack_start(self.externalPortLabel, False, False, 0)
        self.labelRow.pack_start(self.internalPortLabel, False, False, 0)
        self.labelRow.pack_start(self.leaseDurationLabel, False, False, 0)
        self.labelRow.pack_start(self.descriptionLabel, False, False, 0)
        self.labelRow.pack_start(self.protocolLabel, False, False, 0)        

        self.inputRow.pack_start(self.internalIPBox, False, False, 0)
        self.inputRow.pack_start(self.internalPortBox, False, False, 0)
        self.inputRow.pack_start(self.externalPortBox, False, False, 0)
        self.inputRow.pack_start(self.leaseDurationBox, False, False, 0)
        self.inputRow.pack_start(self.descriptionBox, False, False, 0)
        self.inputRow.pack_start(self.radioBox, False, False, 0)
        self.inputRow.pack_start(self.submitButton, False, False, 0)
    
    def addPort(self, button):
        protocol = "TCP" if self.button1.get_active() else "UDP"
        add_port_mapping(self.internalIPBox.get_text(), 
                         int(self.externalPortBox.get_text()), 
                         int(self.internalPortBox.get_text()), 
                         protocol, 
                         self.descriptionBox.get_text(), 
                         int(self.leaseDurationBox.get_text()))

win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
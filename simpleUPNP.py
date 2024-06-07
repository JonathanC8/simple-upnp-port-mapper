import requests
from xml.etree import ElementTree
import socket
import gi
import sys
gi.require_version("Gtk", "4.0")
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
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
    location = upnp_gateway['LOCATION']  # Change this to your router's description URL
    control_url = get_control_url(location)

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
            print("Port mapping added successfully.\n", response.text)
        else:
            print("Failed to add port mapping.\n",response.text)

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here
        self.set_default_size(600, 400)
        self.set_title("MyApp")
        self.box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.inputRow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.labelRow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        self.gridBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.box1.set_halign(Gtk.Align.END)
        
        self.labelRow.set_margin_top(5)

        #self.button.connect('clicked', self.hello)

        self.set_child(self.box1)  # Horizontal box to window
        self.box1.append(self.gridBox)
        self.box1.append(self.labelRow)
        self.box1.append(self.inputRow)  # And another one, empty for now


        self.internalPortBox = Gtk.Entry(text="12345")
        self.externalPortBox = Gtk.Entry(text="12345")
        self.internalIPBox = Gtk.Entry(text=(netifaces.ifaddresses(netifaces.interfaces()[2])[2][0]['addr']))
        self.leaseDurationBox = Gtk.Entry(text="0")
        self.descriptionBox = Gtk.Entry(text="Server")
        self.radioButton1 = Gtk.CheckButton(label="TCP")
        self.radioButton2 = Gtk.CheckButton(label="UDP")
        self.radioButton2.set_group(self.radioButton1)
        self.submitButton = Gtk.Button(label="Submit")

        self.radioButton1.set_active(True)

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
        self.radioBox.append(self.radioButton1)
        self.radioBox.append(self.radioButton2)

        self.labelRow.append(self.interalIPLabel)
        self.labelRow.append(self.externalPortLabel)
        self.labelRow.append(self.internalPortLabel)
        self.labelRow.append(self.leaseDurationLabel)
        self.labelRow.append(self.descriptionLabel)
        self.labelRow.append(self.protocolLabel)        

        self.inputRow.append(self.internalIPBox)
        self.inputRow.append(self.internalPortBox)
        self.inputRow.append(self.externalPortBox)
        self.inputRow.append(self.leaseDurationBox)
        self.inputRow.append(self.descriptionBox)
        self.inputRow.append(self.radioBox)
        self.inputRow.append(self.submitButton)
    
    def addPort(window, button):
        protocol = "TCP"
        if window.radioButton1.get_active():
            protocol = "TCP"
        else:
            protocol = "UDP"
        add_port_mapping(window.internalIPBox.get_text(), int(window.externalPortBox.get_text()), int(window.internalPortBox.get_text()), protocol, window.descriptionBox.get_text(), int(window.leaseDurationBox.get_text()))

        

class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
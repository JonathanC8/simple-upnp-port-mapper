import requests
from xml.etree import ElementTree 
import socket
import sys
import netifaces

class UPnPinterface:

    def __init__(self, data):

        #self.control_url = data['control_url']
        #self.location = data['location']
        self.renewals = data['renewals']
    
    def get_local_ip(self):
        try:
            return netifaces.ifaddresses(netifaces.gateways()['default'][netifaces.AF_INET][1])[2][0]['addr']
        except:
            return "192.168.1.100"

    def parse_port_mappings(self, xml_string):
        root = ElementTree.fromstring(xml_string)
        namespace = {'s': 'http://schemas.xmlsoap.org/soap/envelope/'}
        body = root.find('s:Body', namespace)
        response = body.find('*')
        result = {}
        for child in response:
            result[child.tag.replace('{http://schemas.xmlsoap.org/soap/envelope/}', '')] = child.text
        return result


    def discover_upnp_devices(self):
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

    def get_control_url(self, location):
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
    

    def get_port_mappings(self):
        upnp_gateway = self.discover_upnp_devices()
        try:
            self.location = upnp_gateway['LOCATION']  # Change this to your router's description URL
            self.control_url = self.get_control_url(self.location)
        except Exception as e:
            print(f"Failed to find IGD device.\n {e}")
            return {
                'code':1,
                'error':f"Failed to find IGD device: {e}"
            }

        headers = {'Content-Type': 'text/xml; charset="utf-8"',
                   'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#GetGenericPortMappingEntry"'}
        mappings = []
        count = 0
        while True:
            body = f"""<?xml version="1.0"?>
                <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
                s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                <s:Body>
                <u:GetGenericPortMappingEntry xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">
                <NewPortMappingIndex>{count}</NewPortMappingIndex>
                </u:GetGenericPortMappingEntry>
                </s:Body>
                </s:Envelope>"""
            count+=1
            response = requests.post(f"{self.location.split('/')[0]}//{self.location.split('/')[2]}{self.control_url}", headers=headers, data=body)
            if response.status_code != 200:
                break
            mappings.append(self.parse_port_mappings(response.text))

        return mappings

    def remove_port_mapping(self, external_port, protocol):
        upnp_gateway = self.discover_upnp_devices()
        try:
            self.location = upnp_gateway['LOCATION']  # Change this to your router's description URL
            self.control_url = self.get_control_url(self.location)
        except Exception as e:
            print(f"Failed to find IGD device.\n {e}")
            return {
                'code':1,
                'error':f"Failed to find IGD device: {e}"
            }

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

        response = requests.post(f"{self.location.split('/')[0]}//{self.location.split('/')[2]}{self.control_url}", headers=headers, data=body)

        if response.status_code == 200:
            print("Port mapping removed successfully.\n",response.text)
            return {
                'code':0,
                'error':response.text
            }
        else:
            print("Failed to remove port mapping.\n",response.text)
            return {
                'code':2,
                'error':response.text
            }

    def add_port_mapping(self, internal_client, external_port, internal_port, protocol, description, leaseDuration):
        upnp_gateway = self.discover_upnp_devices()
        try:
            self.location = upnp_gateway['LOCATION']  # Change this to your router's description URL
            self.control_url = self.get_control_url(self.location)
        except Exception as e:
            print(f"Failed to find IGD device.\n {e}")
            return {
                'code':1,
                'error':f"Failed to find IGD device: {e}"
            }

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

        response = requests.post(f"{self.location.split('/')[0]}//{self.location.split('/')[2]}{self.control_url}", headers=headers, data=body)

        if response.status_code == 200:
            print("Port mapping added successfully.\n", response.text)
            return {
                'code':0,
                'error':response.text
            }

        else:
            print("Failed to add port mapping.\n",response.text)
            return {
                'code':2,
                'error':response.text
            }
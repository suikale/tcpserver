#!/usr/bin/env python
# Simple TCP server for receiving Yeelight commands and using them to do different things
# https://www.yeelight.com/download/Yeelight_Inter-Operation_Spec.pdf
# examples of incoming JSON RPC
# {"id": 1, "method": "set_power", "params": ["on", "smooth", 300]}
# {"id": 2, "method": "set_ct_abx", "params": [1700, "smooth", 300]}
# {"id": 3, "method": "toggle", "params": []}
# written (mostly :D) by suikal, ty ukot

import socket
import smbus 

class TcpServer():
    def __init__(self):
        self.TCP_IP = '192.168.1.105'        # Pi IP
        self.TCP_PORT = 55443                # Yeelight bulbs use port 55443 so it cant be changed
        self.BUFFER_SIZE = 64                # 64 isn't enough
        self.I2CADDR = 0x0a                  # 433MHz transmitter address
        self.toggle = True
        self.socket = self.init_socket()

        # Hash tables for power functions. Currently "set_power" "on/off" will control socket 1, and "toggle" toggles socket 2
        self.set_power_map = {
                "on": "a",
                "off": "b"
        }

        self.toggle_map = {
                True: "c",
                False: "d"
        }

    # TCP socket inits straight from manpages
    def init_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.TCP_IP, self.TCP_PORT))
        s.listen(1)

        return s

    # Writes cmd to i2c address where it is processed by ATTiny-powered rf transmitter
    def write(self, cmd):
        bus = smbus.SMBus(1)
        bus.write_byte_data(self.I2CADDR, ord(cmd),0)

    # Decides what to do with parsed json
    def parse_cmd(self, method, param,  numparam, unparsed):
        if method == 'toggle':
            toggle = self.toggle_map[self.toggle]
            self.toggle = not self.toggle

            return toggle

        elif method == 'set_power':
            return self.set_power_map[param]

        return unparsed
        

    # This parses the data from json
    def json_parse(self, unparsed):
        data = unparsed.split('"')[1::2]   # split json from every other quotation mark, in other words picks words between quotes
        numdata = unparsed.split(' ')      # split json for numbers
        method = data[2]                   # method (toggle, set_power etc)
        param = data[4]                    # additional parameter for method (on/off etc)
        cmd_id = numdata[1][:-1]           # id for result message
        numparam = numdata[5][1:-1]        # additional numeric parameter for method

        return method, param, numparam, cmd_id, unparsed
   
    # Yeelight software requires result message in this format:
    # {"id": 1, "result": ["ok"]} 
    def result_cmd(self, cmd_id):
        result = '{"id": '+cmd_id+', "result": ["ok"]}'

        return result

    def run(self):
        # Main loop that picks JSON RPC data from LAN
        while True:
            conn, addr = self.socket.accept()
            json = conn.recv(self.BUFFER_SIZE)
            
            if not json: break
            
            method, param, numparam, cmd_id, unparsed = self.json_parse(json) # send json to parser
            result = self.result_cmd(cmd_id)
            print(result)
            conn.send(result)                                       # return a result message
            conn.close()                                            # 
            cmd = self.parse_cmd(method, param, numparam, unparsed) # send parsed data to next function
            if cmd == unparsed:                                     #
                print unparsed                                      # print unrecognised messages to stdout
            else:                                                   #
                self.write(cmd)                                     # finally this does the thing

if __name__ == "__main__":
    TcpServer().run()

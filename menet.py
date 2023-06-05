# -*- coding: utf-8 -*-
"""
Created on Sat Jun  3 09:03:54 2023

@author: linft
"""
import argparse
import threading
import socket
import subprocess
import sys

__app_name__ = 'menet'
__version__ = '0.1.0'

app_description = '''
A featured networking utility which
reads and writes data across network connections,
using the TCP/IP protocol.
'''

parser = argparse.ArgumentParser(prog=f'{__app_name__}.py',
                                 description=app_description)

parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')

parser.add_argument('-t', '--target', type=str,
                    default='0.0.0.0',
                    help="- Set the server's hostname or IP address")

parser.add_argument('-p', '--port', type=int,
                    default=1024,
                    help="- Set port to listen on (non-privileged ports are > 1023)")

parser.add_argument('-l', '--listen', action='store_true',
                    help="- Listen on [host]:[port] for incoming connections")

parser.add_argument('-c', '--command', action='store_true',
                    help="- Initialize a command shell")

parser.add_argument('-e', '--execute', type=str,
                    help="- Execute the given [file_name] upon receiving a connection")

parser.add_argument('-u', '--upload', type=str,
                    help="- Upload a file and write to [destination] upon receiving connection")

args = parser.parse_args()

def _sender(socket, data):
    try:
        socket.send(str.encode(data))
    except:
        socket.send(data)

def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # connect to target host
        client.connect((args.target, args.port))
        print(f'Client:: connecting to {args.target} on {args.port}')
        
        # send data
        if len(buffer):
            _sender(client, buffer)
        
        # wait for data back
        while True:
            recv_len = 1    
            response = b''
            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data
                
                if recv_len < 4096:
                    break
            print(response.decode())
            
            # wait for more input
            buffer = input()
            buffer += '\n'
            
            # send it off
            _sender(client, buffer)
    except:
        print('[*] Exception! Exiting.')
        # tear down the connection
        client.close()

def server_loop():
    # (default) the server listens on all interfaces
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((args.target, args.port))
    print(f'Server:: listening at {args.target} on {args.port}')
    server.listen(5)
    
    while True:
        client_socket, addr = server.accept()
        
        # spin off a thread to handle new client
        print(f'Server:: connecting to {client_socket} at {addr}')
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def run_command(command):
    # trim the newline
    print(f'running cmd: {command}')
    command = command.rstrip()
    
    # run the command and get the output back
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        print(f'output: {output}')
    except:
        output = 'Failed to execute command.\r\n'
    return output

def client_handler(client_socket):
    # 1. Check for upload
    if args.upload is not None:
        # read in all of the bytes and write to destination
        file_buffer = b''
        
        # keep reading data until none is available
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                file_buffer += data
            except Exception as err:
                print(f'Server:: Unexpected error {err}')
                sys.Exit(0)
        
        # try to write these bytes out
        try:
            with open(args.upload, 'wb') as file:
                file.write(file_buffer)
            _sender(client_socket, f'Successfully saved file to {args.upload}\r\n')
        except:
            _sender(client_socket, f'Failed to save file to {args.upload}\r\n')
    
    # 2. Check for command execution
    if args.execute is not None:
        output = run_command(args.execute)
        _sender(client_socket, output)
    
    # 3. Go into another loop if a command shell was requested
    if args.command:
        while True:
            # show a simple prompt
            _sender(client_socket, '<menet:#> ')
            
            # receiving until a linefeed (enter-key) is sent
            cmd_buffer = b''
            while b'\n' not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)
            
            # send back the command output
            response = run_command(cmd_buffer.decode())
            
            # send back the response
            _sender(client_socket, response)

def main():
    # Listen as a server, or just send data from stding?
    if args.listen:
        server_loop()
    
    if not args.listen:
        # read in the buffer from the commandline
        # this will block, so send CTRL-D if not sending input to stdin
        buffer = input()
        
        # send data off
        client_sender(buffer)

print(args)

main()




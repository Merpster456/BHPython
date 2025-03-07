#! /usr/bin/python

"""
Author: Ryan Quirk
Email: ryan.quirk6@protonmail.ch

Desc: This is a pythonic NetCat alternative.
For scenarios where NetCat is unreachable but
python is available

"""

import sys
import socket as s
import getopt
import threading
import subprocess
import traceback

# Global Variables
listen      = False
command     = False
upload      = False
execute     = ""
target      = ""
upload_dest = ""
port        = 0

def usage():
    print("BHP PyCat Net Tool")
    print("")
    print("Usage: pycat.py -t target_host -p port")
    print("-l --listen              - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command             - initialize a command shell")
    print("-u --upload=destination  - upon receiving connection upload a file and write to [destination]")
    print("")
    print("")
    print("Examples: ")
    print("pycat.py -t 192.168.0.1 -p 5555 -l -c")
    print("pycat.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("pycat.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./pycat.py -t 192.168.11.12 -p 135")
    sys.exit(0)

def client_sender(buffer):

    client = s.socket(s.AF_INET, s.SOCK_STREAM)

    try:
        # connect to target host
        client.connect((target, port))

        if len(buffer):
            client.send(bytes(buffer, "utf-8"))

        while True:

            # now wait for data back
            recv_len = 1
            response = ""

            while recv_len:
                data     = client.recv(4096).decode("utf-8")
                recv_len = len(data)
                response+= data

                if recv_len < 4096:
                    break

            #print(response, )

            buffer = input(response, )
            buffer += "\n"

            # send it off
            client.send(bytes(buffer, "utf-8"))

    except Exception as err:

        print("\n[*] Exception! Exiting.")

        #print(err)
        #print(traceback.format_exc())
        # Close connection
        client.close()


def client_handler(client_socket):
    global upload
    global execute
    global command

    # check for upload
    if len(upload_dest):

        # read in all of the bytes and write to our dest
        file_buffer = ""

        #keep reading data until none is available
        while True:
            data = client_socket.recv(1024)

            if not data:
                break
            else:
                file_buffer += data

        # take bytes and try to write them
        try:
            file_descriptor = open(upload_dest, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            # Acknowledge that we wrote the file out
            client_socket.send(bytes(f"Successfully saved file to {upload_dest}\r\n", "utf-8"))
        except:
            client_socket.send(bytes(f"Failed to save file to {upload_dest}\r\n", "utf-8"))

    # check for command execution
    if len(execute):

        # run the command
        output = run_command(execute)
        client_socket.send(output)

    # Go to another loop if commandshell was requested
    if command:

        while True:
            # Show a simple prompt
            client_socket.send(bytes("[PyC@]:$ ", "utf-8"))

            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode("utf-8")

                # send back the command output
                response = run_command(cmd_buffer)
                client_socket.send(response)

def server_loop():
    global target

    # if no target is defined, we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"

    # Initialize server
    server = s.socket(s.AF_INET, s.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)
    print(f"[*] Listening on {target}:{port}")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"[*] Client connected from {addr[0]}:{addr[1]}")

            # spin off a thread to handle our new client
            client_thread = threading.Thread(target=client_handler, args=(client_socket,))
            client_thread.start()
    except:
        print("[!] Exception! Exiting...")
        server.close()


def run_command(command):

    # trim newline
    command = command.rstrip()

    # run the command and get the output back
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = bytes("Failed to execute command.\r\n", "utf-8")

    return output


def main():
    global listen
    global port
    global execute
    global command
    global upload_dest
    global target

    if not len(sys.argv[1:]):
        usage()

    # Read Commandline Options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu", ["help", "listen",
                                                                "execute", "target", "port", "command", "upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--l"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--commandshell"):
            command = True
        elif o in ("-u", "--upload"):
            upload_dest = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

    # Listen or just send data from stdin?
    if not listen and len(target) and port > 0:

        # Read in the buffer from the commandline this will block, so
        # send CTRL-D if not sending input to stdin
        buffer = sys.stdin.read()

        # Send data off
        client_sender(buffer)

    # Listen and potentially upload things, execute commands, and drop a shell
    if listen:
        server_loop()

main()

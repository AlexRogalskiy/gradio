import subprocess
import requests
import zipfile
import io
import sys
import os
import socket
from psutil import process_iter, AccessDenied
from signal import SIGTERM  # or SIGKILL
import signal
import http.server
import socketserver
import threading

INITIAL_PORT_VALUE = 7860
TRY_NUM_PORTS = 100
LOCALHOST_NAME = 'localhost'
LOCALHOST_PREFIX = 'localhost:'
NGROK_TUNNELS_API_URL = "http://localhost:4040/api/tunnels"  # TODO(this should be captured from output)
NGROK_TUNNELS_API_URL2 = "http://localhost:4041/api/tunnels"  # TODO(this should be captured from output)

NGROK_ZIP_URLS = {
    "linux": "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip",
    "darwin": "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip",
    "win32": "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip",
}


def get_ports_in_use(start, stop):
    ports_in_use = []
    for port in range(start, stop):
        try:
            s = socket.socket()  # create a socket object
            s.bind((LOCALHOST_NAME, port))  # Bind to the port
            s.close()
        except OSError:
            ports_in_use.append(port)
    return ports_in_use
    # ports_in_use = []
    # try:
    #     for proc in process_iter():
    #         for conns in proc.connections(kind='inet'):
    #             ports_in_use.append(conns.laddr.port)
    # except AccessDenied:
    #     pass  # TODO(abidlabs): somehow find a way to handle this issue?
    # return ports_in_use


def serve_files_in_background(port, directory_to_serve=None):
    def handler(*args):
        return http.server.SimpleHTTPRequestHandler(*args, directory=directory_to_serve)

    server = socketserver.ThreadingTCPServer(('localhost', port), handler)
    # Ensures that Ctrl-C cleanly kills all spawned threads
    server.daemon_threads = True
    # Quicker rebinding
    server.allow_reuse_address = True

    # A custom signal handle to allow us to Ctrl-C out of the process
    def signal_handler(signal, frame):
        print('Exiting http server (Ctrl+C pressed)')
        try:
            if (server):
                server.server_close()
        finally:
            sys.exit(0)

    # Install the keyboard interrupt handler
    signal.signal(signal.SIGINT, signal_handler)

    # Now loop forever
    def serve_forever():
        try:
            while True:
                sys.stdout.flush()
                server.serve_forever()
        except KeyboardInterrupt:
            pass

    thread = threading.Thread(target=serve_forever)
    thread.start()


def start_simple_server(directory_to_serve=None):
    # TODO(abidlabs): increment port number until free port is found
    ports_in_use = get_ports_in_use(start=INITIAL_PORT_VALUE, stop=INITIAL_PORT_VALUE + TRY_NUM_PORTS)
    for i in range(TRY_NUM_PORTS):
        if not((INITIAL_PORT_VALUE + i) in ports_in_use):
            break
    else:
        raise OSError("All ports from {} to {} are in use. Please close a port.".format(
            INITIAL_PORT_VALUE, INITIAL_PORT_VALUE + TRY_NUM_PORTS))
    serve_files_in_background(INITIAL_PORT_VALUE + i, directory_to_serve)
    # if directory_to_serve is None:
    #     subprocess.Popen(['python', '-m', 'http.server', str(INITIAL_PORT_VALUE + i)])
    # else:
    #     cmd = ' '.join(['python', '-m', 'http.server', '-d', directory_to_serve, str(INITIAL_PORT_VALUE + i)])
    #     subprocess.Popen(cmd, shell=True)  # Doesn't seem to work if list is passed for some reason.
    return INITIAL_PORT_VALUE + i


def download_ngrok():
    try:
        zip_file_url = NGROK_ZIP_URLS[sys.platform]
    except KeyError:
        print("Sorry, we don't currently support your operating system, please leave us a note on GitHub, and we'll look into it!")
        return

    r = requests.get(zip_file_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall()


def setup_ngrok(local_port, api_url=NGROK_TUNNELS_API_URL):
    if not(os.path.isfile('ngrok.exe')):
        download_ngrok()
    subprocess.Popen(['ngrok', 'http', str(local_port)])
    r = requests.get(api_url)
    for tunnel in r.json()['tunnels']:
        if LOCALHOST_PREFIX + str(local_port) in tunnel['config']['addr']:
            return tunnel['public_url']
    raise RuntimeError("Not able to retrieve ngrok public URL")


def kill_processes(process_ids):
    for proc in process_iter():
        try:
            for conns in proc.connections(kind='inet'):
                if conns.laddr.port in process_ids:
                        proc.send_signal(SIGTERM)  # or SIGKILL
        except AccessDenied:
            print("Unable to kill processes, please kill manually.")



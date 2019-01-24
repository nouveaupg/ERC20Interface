import socket
import json
import time


class GethInterface:
    def __init__(self, request_data, config_data, logger=None):
        if type(request_data) is not str:
            self.request_data = json.dumps(request_data)
        else:
            self.request_data = request_data
        self.config = config_data
        self.logger = logger

    def setup_socket(self):
        new_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        new_socket.connect(self.config['ipc_address'])
        new_socket.settimeout(2)
        return new_socket

    def log_info(self, message):
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

    def log_error(self, message):
        if self.logger:
            self.logger.error(message)
        else:
            print(message)

    def send(self):
        _socket = self.setup_socket()
        _socket.sendall(self.request_data.encode())
        response_raw = ""
        for _ in range(self.config['max_rpc_tries']):
            while True:
                try:
                    response_raw += _socket.recv(4096).decode()
                except socket.timeout:
                    self.log_error("Geth IPC socket timeout.")
                    # wait 2 seconds before hammering the IO system some more
                    time.sleep(2)
                    break
            if response_raw == "":
                # retry if we didn't get a response
                self.log_info("Geth IPC socket no response, retrying...")
                _socket.close()
                _socket = self.setup_socket()
            else:
                break
        return response_raw

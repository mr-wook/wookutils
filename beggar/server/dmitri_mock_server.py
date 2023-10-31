#!/bin/env python3

if True:
    import json
    import logging
    import os
    import re
    import socket
    import sys


class Server:
    SERVICE_NAME = "d-mitri-mock-server"
    LOG_FORMAT = '%(levelname)s %(asctime)s %(message)s'
    LOGGERS = { logging.INFO: logging.info, logging.DEBUG: logging.debug,
                logging.WARNING: logging.warning, logging.ERROR: logging.error,
                logging.CRITICAL: logging.critical, logging.FATAL: logging.fatal }
    def __init__(self, where = '127.0.0.1', port = 6867):
        logging.basicConfig(filename='dmitri_server_mock.log', filemode='w',
                            level=logging.DEBUG, format=BasicClient.LOG_FORMAT)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(where, port)
        self._socket.listen(5) # backlog of 5 before rejecting;
        self.log(f"Started, Mock server listening on port {port}...")

    def log(self, msg, level = logging.info):
        if level not in Server.LOGGERS:
            return logging.debug(msg)
        logger = Server.LOGGERS(level)
        return logger(msg)

    def _exit(self, tokens):
        # unbind/close self._socket, self._client_socket if set
        self._socket.close()
        self.log("Exiting Server")
        sys.exit(0)

    def _project(self, tokens):
        self.log(f"Project Message: {' '.join(tokens)}")
        self.respond(self._client_socket, f"project message received")
        return

    def wait(self, bufsize = 1024):
        services = dict(exit=self._exit, project=self._project)
        while True:
            self._client_socket, self._addr = self._socket.accept()
            self.log(f"Connection established with {self._addr}")
            try:
                while True:
                    data = self._client_socket.recv(bufsize).decode('utf-8')
                    if not data:
                        self.log("No data, Connection closed by the client.")
                        break
                    self.log(f"Received: {data}")
                    tokens = re.split(r'\s+', data)
                    service_name = services[tokens[0]].lower()
                    if service_name not in services:
                        self.log(f"Unrecognized service name {service_name}")
                        self.respond(self._client_socket, f"Unrecognized request {tokens[0].lower()}")
                        continue
                    # self.respond(self._client_socket, f"Ack: {data}")
                    response_fn = services[service_name]
                    response_fn(tokens)
            finally:
                self._client_socket.close()


    def respond(self, client, msg):
         # Send a response back to the client
        response = f"{msg}"
        try:
            client.sendall(response.encode('utf-8'))
        except Exception as e:
            self.log(f"Response failed: {str(e)}")
            return False
        return True

if __name__ == "__main__":
    server = Server()
    rc = server.wait()
    if rc:
        sys.exit(0)
    sys.exit(1)



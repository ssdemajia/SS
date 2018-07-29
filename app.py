import socket
import errno
import sys
import wsgiref

class WSGIServer:
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 2

    def __init__(self, server_address):
        listen_socket = socket.socket(self.address_family, self.socket_type)
        self.listen_socket = listen_socket
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        listen_socket.bind(server_address)
        listen_socket.listen(self.request_queue_size)
        host, port = listen_socket.getsockname()
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        self.headers_set = []

    def set_app(self, application):
        self.application = application

    def serve_forever(self):
        listen_socket = self.listen_socket
        while True:
            try:
                self.client_connection, client_address = listen_socket.accept()
                self.handle_one_request()
            except IOError as e:
                code, msg = e.args
                if code == errno.EINTR:
                    continue
                else:
                    raise

    def handle_one_request(self):
        self.request_data = request_data = self.client_connection.recv(1024)
        print('---request length{length}\n'.format(length=len(self.request_data)))
        if len(self.request_data) == 0:
            self.finish_response(self.request_data)
            return
        print(''.join('<{line}\n'.format(line=line) for line in request_data.splitlines()))
        self.parse_request(request_data)

        env = self.get_environ()
        result = self.application(env, self.start_response)
        self.finish_response(result)

    def parse_request(self, text):
        request_line = text.splitlines()[0].decode('ascii')
        request_line = request_line.rstrip('\r\n')
        (self.request_method, self.path, self.request_version) = request_line.split()

    def get_environ(self):
        env = dict()
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = self.request_data
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        env['REQUEST_METHOD'] = self.request_method
        env['PATH_INFO'] = self.path
        env['SERVER_NAME'] = self.server_name
        env['SERVER_PORT'] = str(self.server_port)
        return env

    def start_response(self, status, response_headers, exc_info=None):
        server_headers = [
            ('Date', 'Tue, 31 Mar 2015 12:54:48 GMT'),
            ('Server', 'WSGIServer 0.2')
        ]
        self.headers_set = [status, response_headers + server_headers]

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            # response += '\r\n'
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            response = response.encode('ascii')
            for data in result:
                response += data
            print(''.join('> {line}\n'.format(line=line) for line in response.decode('utf-8').splitlines()))
            self.client_connection.sendall(response)
        finally:
            self.client_connection.close()

    def __del__(self):
        self.listen_socket.close()


def make_server(server_address, application):
    server = WSGIServer(server_address)
    server.set_app(application)
    return server


if __name__ == '__main__':
    # flasky = __import__('flasky')
    # app = flasky.app
    ss = __import__('ss')
    app = ss.app
    httpd = make_server(('127.0.0.1', 9001), app)
    httpd.serve_forever()
#!/usr/bin/env python3

"""
Yandex Transport Monitor proxy service, automates getting data from Yandex.Transport using Selenium Webdriver and
Chromium browser.
"""

# NOTE: This project uses camelCase for function names. While PEP8 recommends using snake_case for these,
#       the project in fact implements the "quasi-API" for Yandex Masstransit, where names are in camelCase,
#       for example, get_stop_info. Correct naming for this function according to PEP8 would be get_stop_info.
#       Thus, the desision to use camelCase was made. In fact, there are a bunch of python projects which use
#       camelCase, like Robot Operating System.
#       I also personally find camelCase more pretier than the snake_case.

__author__ = "Yury D."
__credits__ = ["Yury D.", "Pavel Lutskov", "Yury Alexeev"]
__license__ = "MIT"
__version__ = "0.0.13-alpha"
__maintainer__ = "Yury D."
__email__ = "SoulGate@yandex.ru"
__status__ = "Alpha"

import time
import sys
import json
import signal
import socket
import re
import threading
from collections import deque
from collections import defaultdict
import argparse
import setproctitle
from yandex_transport_core import YandexTransportCore, Logger

# -------------------------------------------------------------------------------------------------------------------- #


def chunks(arr, n):
    """
    Helper function to slice array into smaller size chunks.
    Is used in "send_message".
    :param arr: an array
    :param n: size of a chunk
    :return: array of n-sized chunks
    """
    for i in range(0, len(arr), n):
        # Create an index range for l of n items:
        yield arr[i:i+n]


class ListenerThread(threading.Thread):
    """
    Listener thread class, will listen to incoming queries.
    """
    def __init__(self, conn, addr, app):
        super().__init__()
        self.app = app
        self.conn = conn
        self.addr = addr

    def run(self):
        self.app.log.info("Connection established : " + str(self.addr))

        while self.app.is_running:
            self.conn.settimeout(5)
            try:
                data = self.conn.recvfrom(4096)
            except socket.timeout:
                continue

            if data != (b'', None):
                string = data[0].decode("utf-8")
                lines = string.splitlines()
                for line in lines:
                    query = line.strip()
                    self.app.log.debug("Received : " + str(query))

                    if query == 'getCurrentQueue':
                        self.app.process_get_current_queue(self.conn)

                    elif query.startswith('getStopInfo?'):
                        self.app.process_get_stop_info(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfo?'):
                        self.app.process_get_vehicles_info(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfoWithRegion?'):
                        self.app.process_get_vehicles_info_with_region(query, self.addr, self.conn)

                    elif query.startswith('getRouteInfo?'):
                        self.app.process_get_route_info(query, self.addr, self.conn)

                    elif query.startswith('getLayerRegions?'):
                        self.app.process_get_route_info(query, self.addr, self.conn)

                    elif query.startswith('getAllInfo?'):
                        self.app.process_get_all_info(query, self.addr, self.conn)

                    elif query.startswith('getEcho?'):
                        self.app.process_echo(query, self.addr, self.conn)

                    else:
                        self.app.process_unknown_query(self.conn)
            else:
                self.app.log.info("Connection terminated : " + str(self.addr))
                break

        self.conn.shutdown(socket.SHUT_RDWR)
        self.app.log.debug("Thread for connection ( " + str(self.addr) + " ) terminated")
        del self.app.listeners[self.addr]
# -------------------------------------------------------------------------------------------------------------------- #


class ExecutorThread(threading.Thread):
    """
    Executor thread, single thread to pick and execute queries from Query Queue.
    """
    def __init__(self, app):
        super().__init__()
        self.app = app

        # Flag to check if exeturoe thread is running.
        # In case it fails - program should terminate / Executor Thread should restart.
        # Let's stick with "terminate" scenario for now

        # Time to wait between queries
        self.wait_time = self.app.query_delay
        # Time to wait between watch updates
        self.watch_wait_time = 5

    def send_message(self, message, addr, conn, log_tag=None):
        """
        Send a message to the server
        :param message: message to send
        :param addr: address (from socket bind/accept)
        :param conn: connection
        :param log_tag: tag which will append to log message
        :return: nothing
        """
        if log_tag is not None:
            log_tag_text = " (" + log_tag + ")"
        else:
            log_tag_text = ""
        try:
            send_msg = bytes(str(message) + '\n' + '\0', 'utf-8')

            self.app.log.debug("Writing to " + self.app.network_log_file + " "
                               "(" + str(len(send_msg)) + " bytes) ")
            if self.app.network_log_enabled:
                f = open(self.app.network_log_file, 'ab')
                f.write(bytes(str(len(send_msg))+'\n', 'utf-8'))
                f.write(send_msg)
                f.write(bytes('\n\n', 'utf-8'))
                f.close()

            self.app.log.debug("Sending response " +
                               "(" + str(len(send_msg)) + " bytes) "
                               "to " + str(addr) + log_tag_text)

            # It seems data needs to be sent in chunks, JSON objects with size of several kilobytes
            # effectively break "sending in one piece" strategy.
            buffer_size = 4096
            for chunk in chunks(send_msg, buffer_size):
                bytes_send = conn.send(chunk)
                if bytes_send != len(chunk):
                    self.app.log.error("Sent " + str(bytes_send) + "out of " + str(len(chunk)) + "bytes!")

        except socket.error as e:
            self.app.log.error("Failed to send data to " + str(addr))
            self.app.log.error("Exception (send_message):" + str(e))

    def execute_get_info(self, query):
        """
        Execute general get... query.
        :param query: internal 'query' dictionary
        :return: result as JSON
        """
        if query['type'] == 'getStopInfo':
            data, error = self.app.core.get_stop_info(url=query['body'])
        elif query['type'] == 'getRouteInfo':
            data, error = self.app.core.get_route_info(url=query['body'])
        elif query['type'] == 'getVehiclesInfo':
            data, error = self.app.core.get_vehicles_info(url=query['body'])
        elif query['type'] == 'getVehiclesInfoWithRegion':
            data, error = self.app.core.get_vehicles_info_with_region(url=query['body'])
        elif query['type'] == 'getLayerRegions':
            data, error = self.app.core.get_layer_regions(url=query['body'])
        elif query['type'] == 'getAllInfo':
            data, error = self.app.core.get_all_info(url=query['body'])
        else:
            return

        payload = []
        if error == YandexTransportCore.RESULT_OK:
            for entry in data:
                if 'data' in entry:
                    result = {'id': query['id'],
                              'method': entry['method'],
                              'error': self.app.RESULT_OK,
                              'message': 'OK',
                              'expect_more_data': True,
                              'data': entry['data']}
                    payload.append(result)
                else:
                    result = {'id': query['id'],
                              'method': entry['method'],
                              'error': self.app.RESULT_NO_DATA,
                              'message': 'No data',
                              'expect_more_data': True,
                              }
                    payload.append(result)
        elif error == YandexTransportCore.RESULT_GET_ERROR:
            result = {'id': query['id'],
                      'method': query['type'],
                      'error': self.app.RESULT_GET_ERROR,
                      'message': 'Error getting requested URL',
                      'expect_more_data': False}
            payload.append(result)

        if payload:                                   # Same as "if len(payload) > 0:"
            payload[-1]['expect_more_data'] = False
        else:
            result = {'id': query['id'],
                      'method': query['type'],
                      'error': self.app.RESULT_NO_YANDEX_DATA,
                      'message': 'No Yandex Masstransit API data received for method ' + query['type'] +
                                 ' from URL "' + query['body'] + '"',
                      'expect_more_data': False}
            payload.append(result)

        for entry in payload:
            self.send_message(json.dumps(entry), query['addr'], query['conn'], log_tag=entry['method'])

    def execute_get_echo(self, query):
        """
        Execute "getEcho" command.
        :param query: internal query structure
        :return: None
        """
        result = {'id': query['id'],
                  'method': query['type'],
                  'error': self.app.RESULT_OK,
                  'message': 'OK',
                  'expect_more_data': False,
                  'data': query['body']}
        result_json = json.dumps(result)
        self.send_message(result_json, query['addr'], query['conn'], log_tag='getEcho')

    def execute_get_stop_info(self, query):
        """
        Execute get_stop_info query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getStopInfo" + " query:"
                           " ID=" + str(query['id']) +
                           " Body=" + str(query['body']))
        self.execute_get_info(query)

    def execute_get_route_info(self, query):
        """
        Execute get_route_info query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getRouteInfo" + " query:"
                           " ID=" + str(query['id']) +
                           " URL=" + str(query['body']))
        self.execute_get_info(query)

    def execute_get_vehicles_info(self, query):
        """
        Execute get_vehicles_info query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getVehiclesInfo" + " query:"
                           " ID=" + str(query['id']) +
                           " URL=" + str(query['body']))
        self.execute_get_info(query)

    def execute_get_vehicles_info_with_region(self, query):
        """
        Execute get_vehicles_info_with_region query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getVehiclesInfoWithRegion" + " query:"
                           " ID=" + str(query['id']) +
                           " URL=" + str(query['body']))
        self.execute_get_info(query)

    def execute_get_layer_regions(self, query):
        """
        Execute get_layer_regions query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getLayersRegion" + " query:"
                           " ID=" + str(query['id']) +
                           " URL=" + str(query['body']))
        self.execute_get_info(query)

    def execute_get_all_info(self, query):
        """
        Execute get_all_info query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getAllInfo" + " query:" +
                           " ID=" + str(query['id']) +
                           " URL=" + str(query['body']))
        self.execute_get_info(query)

    def execute_query(self, query):
        """
        Execute query from the Query Queue
        :param query: query inner structure {'id', 'type', 'body'}
        :return: None
        """
        if query['type'] == 'getEcho':
            self.execute_get_echo(query)
            return
        if query['type'] == 'getStopInfo':
            self.execute_get_stop_info(query)
            return
        if query['type'] == 'getRouteInfo':
            self.execute_get_route_info(query)
            return
        if query['type'] == 'getVehiclesInfo':
            self.execute_get_vehicles_info(query)
            return
        if query['type'] == 'getVehiclesInfoWithRegion':
            self.execute_get_vehicles_info_with_region(query)
            return
        if query['type'] == 'getLayerRegions':
            self.execute_get_layer_regions(query)
            return
        if query['type'] == 'getAllInfo':
            self.execute_get_all_info(query)
            return

    def perform_query_extraction_and_execution(self):
        """
        Extract and execute query from Query Queue
        :return: None
        """
        # Default "discard" query
        query = None

        # Get the query from Query Queue
        self.app.queue_lock.acquire()
        query_len = len(self.app.query_queue)
        if query_len > 0:
            query = self.app.query_queue[0]
        self.app.queue_lock.release()

        # Executing the query
        if query is not None:
            self.execute_query(query)

        # Removing executed query from the Query Queue
        self.app.queue_lock.acquire()
        if query_len > 0:
            self.app.query_queue.popleft()
        self.app.queue_lock.release()

    def run(self):
        self.app.log.debug("Executor thread started, wait time between queries is "+str(self.wait_time)+" secs.")
        while self.app.is_running:
            # Extracting and executing extraction and execution of query from Query Queue
            self.perform_query_extraction_and_execution()

            # Waiting for some time before next query is extracted and executed
            for _ in range(0, self.wait_time):
                if self.app.is_running:
                    time.sleep(1)
                else:
                    break
        self.app.log.debug("Executor thread stopped.")
# -------------------------------------------------------------------------------------------------------------------- #


class Application:
    """
    Main application class
    """
    # Error codes
    RESULT_OK = 0
    RESULT_NO_DATA = 1
    RESULT_GET_ERROR = 2
    RESULT_NO_YANDEX_DATA = 3

    RESULT_SOCKET_BIND_FAILED = 1

    def __init__(self):
        setproctitle.setproctitle('transport_proxy')

        self.is_running = True  # If set to false, the server will begin to terminate itself

        # Listen address
        self.host = '0.0.0.0'
        # Listen port
        self.port = 25555

        # Delay between queries, in secs.
        self.query_delay = 5

        # Yandex Transport API Core
        self.core = None

        # Executor thread
        self.executor_thread = None

        # List of clients currently connected to the server
        self.listeners = defaultdict()

        # Logger
        self.log = Logger(Logger.INFO)

        # Debug: Write EVERYTHING this thing sends via network to a file.
        self.network_log_enabled = False
        self.network_log_file = 'ytproxy-network.log'

        # Queue lock
        self.queue_lock = threading.Lock()

        # Will turn on with "Watch" command, and prevent any further queries to be added to Queue
        self.watch_lock = False

        # Last Query ID, will increment with each query added to the Queue
        self.query_id = 0

        # Server will run in single thread, the deque is to store incoming queries.
        self.query_queue = deque()

    def sigint_handler(self, _signal, _time):
        """
        SIGINT signal handler
        :param _signal: signal
        :param _time: time
        :return: nothing
        """
        self.log.info("SIGINT received! Terminating the program...")
        self.watch_lock = False
        self.is_running = False
        self.log.info("Waiting for threads to terminate...")
        copy_listeners = self.listeners.copy()
        # pylint: disable = W0612
        for key, listener in copy_listeners.items():
            listener.join()
        # pylint: enable = W0612
        if self.executor_thread is not None:
            self.executor_thread.join()

    def listen(self):
        """
        Start listening to incoming connections. Each new accepted connection will create a new ListenerThread.
        :return: nothing
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)
        self.log.debug("Binding socket...")
        try:
            sock.bind((self.host, self.port))
        except socket.error as e:
            self.log.error("Exception (listen): " + str(e))
            return self.RESULT_SOCKET_BIND_FAILED

        self.log.info("Listening for incoming connections.")
        self.log.info("Host: " + str(self.host) + " , Port: " + str(self.port))
        sock.listen(1)

        while self.is_running:
            # Checking if Executor Thread is dead.
            if not self.executor_thread.isAlive():
                self.log.error("Executor thread is dead. Terminating the program.")
                self.is_running = False
                break

            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue


            listener_thread = ListenerThread(conn, addr, self)
            self.listeners[addr] = listener_thread
            listener_thread.start()

        sock.shutdown(socket.SHUT_RDWR)

        return self.RESULT_OK

    def get_current_connections(self):
        """
        Get current connections
        :return: JSON containing list of current connections
                 {"ip_address": "string", "port": "integer"}
                   ip_address - IP address of the client
                   port       - port of the client
        """
        data = []
        # pylint: disable = W0612
        for key, value in self.listeners.items():
            entry = {"ip_address" : key[0], "port" : key[1]}
            data.append(entry)
        # pylint: enable = W0612
        json_data = json.dumps(data)

        return json_data

    def get_current_queue(self):
        """
        Get current Query Queue.
        :return: JSON containing list of elements in Query Queue
                 {"type": "string", "id": "string", "query": "string"}
                   type  - type of query (get_stop_info, get_vehicles_info etc.)
                   id    - ID of query, string value, passed from the client.
                   query - actual query string
        """
        data = []

        self.queue_lock.acquire()
        for entry in self.query_queue:
            entry = {'type': entry['type'], 'id': entry['id'], 'query': entry['body']}
            data.append(entry)
        self.queue_lock.release()

        json_data = json.dumps(data)

        return json_data

    def handle_watch_lock(self, conn):
        """
        Send a message back to the client if new query arrived while WatchLock is engaged.
        Was supposed to use with watch... methods, abandoned for now until and if watch... methods
        are re-implemented again.
        :param conn: connection
        :return: nothing
        """
        if self.watch_lock:
            response = {"id": self.query_id,
                        "response": "ERROR",
                        "message": "Watch task is planned, no queries accepted until cancelled!",
                       }
            response_json = json.dumps(response)
            conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    @staticmethod
    def split_query(query):
        """
        Get ID from getXXXInfo?id=?YYYY?... requests
        :param query: the query
        :return: query_type, the id value from the query, body of the query
        """
        result = re.match(r'(.*?)\?id=(.*?)\?(.*)', query)
        query_type = ''
        query_id = ''
        query_body = ''
        if result is not None:
            query_type, query_id, query_body = result.group(1), result.group(2), result.group(3)
        return query_type, query_id, query_body

    def process_get_info(self, query, addr, conn, set_watch_lock=False):
        """
        Process the getXXXInfo?id=?YYYY?... requests
        :param query:
        :param addr:
        :param conn:
        :param set_watch_lock:
        :return:
        """
        if self.watch_lock:
            self.handle_watch_lock(conn)
        else:
            if set_watch_lock:
                self.watch_lock = True

            query_type, query_id, query_body = self.split_query(query)

            self.queue_lock.acquire()
            self.query_queue.append({'type': query_type,
                                     'id': query_id,
                                     'body': query_body,
                                     'addr': addr,
                                     'conn': conn}
                                   )
            queue_position = len(self.query_queue) - 1
            self.queue_lock.release()

            response = {'id': query_id,
                        'response': 'OK',
                        'queue_position': queue_position}
            response_json = json.dumps(response)
            conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def process_get_stop_info(self, query, addr, conn):
        """Process get_stop_info query """
        self.process_get_info(query, addr, conn)

    def process_get_vehicles_info(self, query, addr, conn):
        """Process geVehiclesInfo query """
        self.process_get_info(query, addr, conn)

    def process_get_vehicles_info_with_region(self, query, addr, conn):
        """Process get_vehicles_info_with_region query """
        self.process_get_info(query, addr, conn)

    def process_get_route_info(self, query, addr, conn):
        """Process get_route_info query """
        self.process_get_info(query, addr, conn)

    def process_get_layer_regions(self, query, addr, conn):
        """Process get_layer_regions query """
        self.process_get_info(query, addr, conn)

    def process_get_all_info(self, query, addr, conn):
        """Process get_all_info query """
        self.process_get_info(query, addr, conn)

    def process_echo(self, query, addr, conn):
        """Process getEcho query"""
        # If blocked by Watch Lock
        if self.watch_lock:
            self.handle_watch_lock(conn)
        else:
            self.process_get_info(query, addr, conn)

    def process_get_current_queue(self, conn):
        """Process get_current_queue"""
        current_queue = self.get_current_queue()
        queue_json = json.loads(current_queue)
        response_json = json.dumps(queue_json)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def process_unknown_query(self, conn):
        """Process unknown query"""
        response = {"response": "ERROR", "message": "Unknown query"}
        response_json = json.dumps(response)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def parse_arguments(self):
        """
        Parse CLI arguments
        :return: nothing
        """
        parser = argparse.ArgumentParser(description="Yandex Transport Proxy - a proxy-server which will "
                                                     "capture Yandex Transport/Mastransit API responses.\n"
                                                     "Requires Chromium browser and Selenium Webdriver.\n"
                                                     "Use 'YandexTransportWebdriverAPI-Python' "
                                                     "(https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python)\n"
                                                     "in conjunction with this server.",
                                         formatter_class=argparse.RawTextHelpFormatter,
                                        )

        parser.add_argument("-v", "--version", action="store_true", default=False,
                            help="show version info")
        parser.add_argument("--host", default=self.host,
                            help="host to listen on, default is " + str(self.host))
        parser.add_argument("--port", default=self.port,
                            help="port to listen on, default is " + str(self.port))
        parser.add_argument("--verbose", default=self.log.verbose,
                            help=
                            "log verbose level, possible values:\r" +
                            "   0 : no debug\n" +
                            "   1 : error messages only\n" +
                            "   2 : errors and warnings\n" +
                            "   3 : errors, warnings and info\n" +
                            "   4 : full debug\n" +
                            "default is " + str(self.log.verbose))
        parser.add_argument("--delay", default=self.query_delay,
                            help="delay between execution of queries, in seconds, default is " +
                            str(self.query_delay) + " secs.\n"
                            "Use this to lower the load on Yandex Maps " +
                            "and avoid possible ban for\n"
                            "too many queries in short amount of time.")

        args = parser.parse_args()
        if args.version:
            print(__version__)
            sys.exit(0)

        self.host = str(args.host)
        self.port = int(args.port)
        self.log.verbose = int(args.verbose)
        self.query_delay = int(args.delay)

    def run(self):
        """
        Run the application
        :return: exit code
        """

        # Parsing the arguments
        self.parse_arguments()

        # Starting the main program
        self.log.info("YTPS - Yandex Transport Proxy Server - starting up...")

        # Signal handler
        signal.signal(signal.SIGINT, self.sigint_handler)

        # Starting query executor thread
        self.executor_thread = ExecutorThread(self)
        self.executor_thread.start()

        # Calling Yandex Transport API Core
        self.core = YandexTransportCore()
        self.log.info("Starting ChromeDriver...")
        self.core.start_webdriver()
        self.log.info("ChromeDriver started successfully!")

        # Start the process of listening and accepting incoming connections.
        result = self.listen()
        if result == self.RESULT_SOCKET_BIND_FAILED:
            self.log.error("Failed to bind socket.")


        self.core.stop_webdriver()

        # Stopping the server executor and listener threads.
        self.is_running = False

        for _, listener in self.listeners.items():
            listener.join()

        if self.executor_thread is not None:
            self.executor_thread.join()
        self.log.info("YTPS - Yandex Transport Proxy Server - terminated!")

# -------------------------------------------------------------------------------------------------------------------- #
#pylint: disable = C0103
if __name__ == '__main__':
    application = Application()
    application.run()
    sys.exit(0)

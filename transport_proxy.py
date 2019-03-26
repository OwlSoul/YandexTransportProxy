#!/usr/bin/env python3

"""
Yandex Transport Monitor proxy service, automates getting data from Yandex.Transport using Selenium Webdriver and
Chromium browser.
"""

# NOTE: This project uses camelCase for function names. While PEP8 recommends using snake_case for these,
#       the project in fact implements the "quasi-API" for Yandex Masstransit, where names are in camelCase,
#       for example, getStopInfo. Correct naming for this function according to PEP8 would be get_stop_info.
#       Thus, the desision to use camelCase was made. In fact, there are a bunch of python projects which use
#       camelCase, like Robot Operating System.
#       I also personally find camelCase more pretier than the snake_case.

# Project follows PascalCase for module naming, but snake_case for final executable.
# Maybe a better idea is to use executable an sh script instead.
# pylint: disable=C0103
# pylint: enable=C0103

__author__ = "Yury D."
__credits__ = ["Yury D.", "Pavel Lutskov", "Yury Alexeev"]
__license__ = "MIT"
__version__ = "2.0.0-beta"
__maintainer__ = "Yury D."
__email__ = "SoulGate@yandex.ru"
__status__ = "Beta"

import time
import sys
import json
import signal
import socket
import re
import threading
from collections import deque
from collections import defaultdict
import setproctitle
from YandexTransportCore import YandexTransportCore, Logger

# -------------------------------------------------------------------------------------------------------------------- #

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
                        self.app.processGetCurrentQueue(self.conn)

                    elif query.startswith('getStopInfo?'):
                        self.app.processGetStopInfo(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfo?'):
                        self.app.processGetVehiclesInfo(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfoWithRegion?'):
                        self.app.processGetVehiclesInfoWithRegion(query, self.addr, self.conn)

                    elif query.startswith('getRouteInfo?'):
                        self.app.processGetRouteInfo(query, self.addr, self.conn)

                    elif query.startswith('getAllInfo?'):
                        self.app.processGetAllInfo(query, self.addr, self.conn)

                    elif query.startswith('getEcho?'):
                        self.app.processEcho(query, self.addr, self.conn)

                    else:
                        self.app.processUnknownQuery(self.conn)
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
        self.wait_time = 5
        # Time to wait between watch updates
        self.watch_wait_time = 5

    def sendMessage(self, message, addr, conn, log_tag=None):
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
            self.app.log.debug("Sending response to " + str(addr) + log_tag_text)
            conn.send(bytes(str(message) + '\n' + '\0', 'utf-8'))
        except socket.error as e:
            self.app.log.error("Failed to send data to " + str(addr))
            self.app.log.error("Exception ocurred:" + str(e))

    def executeGetInfo(self, query):
        """
        Execute general get... query.
        :param query: internal 'query' dictionary
        :return: result as JSON
        """
        if query['type'] == 'getStopInfo':
            data, error = self.app.core.getStopInfo(url=query['body'])
        elif query['type'] == 'getRouteInfo':
            data, error = self.app.core.getRouteInfo(url=query['body'])
        elif query['type'] == 'getVehiclesInfo':
            data, error = self.app.core.getVehiclesInfo(url=query['body'])
        elif query['type'] == 'getVehiclesInfoWithRegion':
            data, error = self.app.core.getVehiclesInfoWithRegion(url=query['body'])
        elif query['type'] == 'getAllInfo':
            data, error = self.app.core.getAllInfo(url=query['body'])
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
                      'message': 'No Yandex Masstransit API data received for method ' + query['type'] + \
                                 ' from URL "' + query['body'] + '"',
                      'expect_more_data': False}
            payload.append(result)

        for entry in payload:
            self.sendMessage(json.dumps(entry), query['addr'], query['conn'], log_tag=entry['method'])

    def executeGetEcho(self, query):
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
        self.sendMessage(result_json, query['addr'], query['conn'], log_tag='getEcho')

    def executeGetStopInfo(self, query):
        """
        Execute getStopInfo query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getStopInfo" + " query:"
                              " ID=" + str(query['id']) +
                              " Body=" + str(query['body']))
        self.executeGetInfo(query)

    def executeGetRouteInfo(self, query):
        """
        Execute getRouteInfo query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getRouteInfo" + " query:"
                              " ID=" + str(query['id']) +
                              " URL=" + str(query['body']))
        self.executeGetInfo(query)

    def executeGetVehiclesInfo(self, query):
        """
        Execute getVehiclesInfo query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getVehiclesInfo" + " query:"
                              " ID=" + str(query['id']) +
                              " URL=" + str(query['body']))
        self.executeGetInfo(query)

    def executeGetVehiclesInfoWithRegion(self, query):
        """
        Execute getVehiclesInfoWithRegion query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getVehiclesInfoWithRegion" + " query:"
                              " ID=" + str(query['id']) +
                              " URL=" + str(query['body']))
        self.executeGetInfo(query)

    def executeGetAllInfo(self, query):
        """
        Execute getAllInfo query
        :param query: internal query structure
        :return: nothing
        """
        self.app.log.debug("Executing " + "getAllInfo" + " query:" +
                              " ID=" + str(query['id']) +
                              " URL=" + str(query['body']))
        self.executeGetInfo(query)

    def executeQuery(self, query):
        """
        Execute query from the Query Queue
        :param query: query inner structure {'id', 'type', 'body'}
        :return: None
        """
        if query['type'] == 'getEcho':
            self.executeGetEcho(query)
            return
        if query['type'] == 'getStopInfo':
            self.executeGetStopInfo(query)
            return
        if query['type'] == 'getRouteInfo':
            self.executeGetRouteInfo(query)
            return
        if query['type'] == 'getVehiclesInfo':
            self.executeGetVehiclesInfo(query)
            return
        if query['type'] == 'getVehiclesInfoWithRegion':
            self.executeGetVehiclesInfoWithRegion(query)
            return
        if query['type'] == 'getAllInfo':
            self.executeGetAllInfo(query)
            return

    def performQueryExtractionAndExecution(self):
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
            self.executeQuery(query)

        # Removing executed query from the Query Queue
        self.app.queue_lock.acquire()
        if query_len > 0:
            self.app.query_queue.popleft()
        self.app.queue_lock.release()

    def run(self):
        self.app.log.debug("Executor thread started, wait time between queries is "+str(self.wait_time)+" secs.")
        while self.app.is_running:
            # Extracting and executing extraction and execution of query from Query Queue
            self.performQueryExtractionAndExecution()

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

    def __init__(self):
        setproctitle.setproctitle('transport_proxy')

        self.is_running = True  # If set to false, the server will begin to terminate itself

        # Listen address
        self.host = '0.0.0.0'
        # Listen port
        self.port = 25555

        # Executor thread
        self.executor_thread = None

        # List of clients currently connected to the server
        self.listeners = defaultdict()

        # Logger
        self.log = Logger(Logger.DEBUG)

        # Queue lock
        self.queue_lock = threading.Lock()

        # Will turn on with "Watch" command, and prevent any further queries to be added to Queue
        self.watch_lock = False

        # Last Query ID, will increment with each query added to the Queue
        self.query_id = 0

        # Server will run in single thread, the deque is to store incoming queries.
        self.query_queue = deque()

    def sigintHandler(self, _signal, _time):
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
        except socket.error:
            return 1

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

        return 0

    def getCurrentConnections(self):
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

    def getCurrentQueue(self):
        """
        Get current Query Queue.
        :return: JSON containing list of elements in Query Queue
                 {"type": "string", "id": "string", "query": "string"}
                   type  - type of query (getStopInfo, getVehiclesInfo etc.)
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

    def handleWatchLock(self, conn):
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
    def splitQuery(query):
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

    def processGetInfo(self, query, addr, conn, set_watch_lock=False):
        """
        Process the getXXXInfo?id=?YYYY?... requests
        :param query:
        :param addr:
        :param conn:
        :param set_watch_lock:
        :return:
        """
        if self.watch_lock:
            self.handleWatchLock(conn)
        else:
            if set_watch_lock:
                self.watch_lock = True

            query_type, query_id, query_body = self.splitQuery(query)

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

    def processGetStopInfo(self, query, addr, conn):
        """Process getStopInfo query """
        self.processGetInfo(query, addr, conn)

    def processGetVehiclesInfo(self, query, addr, conn):
        """Process geVehiclesInfo query """
        self.processGetInfo(query, addr, conn)

    def processGetVehiclesInfoWithRegion(self, query, addr, conn):
        """Process getVehiclesInfoWithRegion query """
        self.processGetInfo(query, addr, conn)

    def processGetRouteInfo(self, query, addr, conn):
        """Process getRouteInfo query """
        self.processGetInfo(query, addr, conn)

    def processGetAllInfo(self, query, addr, conn):
        """Process getAllInfo query """
        self.processGetInfo(query, addr, conn)

    def processEcho(self, query, addr, conn):
        """Process getEcho query"""
        # If blocked by Watch Lock
        if self.watch_lock:
            self.handleWatchLock(conn)
        else:
            self.processGetInfo(query, addr, conn)

    def processGetCurrentQueue(self, conn):
        """Process getCurrentQueue"""
        current_queue = self.getCurrentQueue()
        queue_json = json.loads(current_queue)
        response_json = json.dumps(queue_json)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def processUnknownQuery(self, conn):
        """Process unknown query"""
        response = {"response": "ERROR", "message": "Unknown query"}
        response_json = json.dumps(response)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def run(self):
        """
        Run the application
        :return: exit code
        """

        self.log.info("YTPS - Yandex Transport Proxy Server - starting up...")

        signal.signal(signal.SIGINT, self.sigintHandler)

        # Starting query executor thread
        self.executor_thread = ExecutorThread(self)
        self.executor_thread.start()

        # Calling Yandex Transport API Core
        core = YandexTransportCore()
        self.log.info("Starting ChromeDriver...")
        core.startWebdriver()
        self.log.info("ChromeDriver started successfully!")

        # Start the process of listening and accepting incoming connections.
        self.listen()

        core.stopWebdriver()

        self.log.info("YTPS - Yandex Transport Proxy Server - terminated!")

# -------------------------------------------------------------------------------------------------------------------- #
if __name__ == '__main__':
    application = Application()
    application.run()
    sys.exit(0)

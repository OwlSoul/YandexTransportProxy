#!/usr/bin/env python3

"""
Yandex Transport Monitor proxy service, automates getting data from Yandex.Transport using Selenium
"""

import time
import sys
import json
import signal
import socket
import datetime
import re
import threading
import setproctitle
from collections import deque
from collections import defaultdict
from Logger import Logger
from YandexTransportCore import YandexTransportCore

# -------------------------------------------------------------------------------------------------------------------- #

class ListenerThread(threading.Thread):
    def __init__(self, conn, addr, app):
        super().__init__()
        self.conn = conn
        self.addr = addr

    def run(self):
        app.logger.info("Connection established : " + str(self.addr))

        while app.is_running:
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
                    app.logger.debug("Received : " + str(query))

                    if query == 'getCurrentQueue':
                        app.processGetCurrentQueue(self.conn)

                    elif query.startswith('getStopInfo?'):
                        app.processGetStopInfo(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfo?'):
                        app.processGetVehiclesInfo(query, self.addr, self.conn)

                    elif query.startswith('getVehiclesInfoWithRegion?'):
                        app.processGetVehiclesInfoWithRegion(query, self.addr, self.conn)

                    elif query.startswith('getRouteInfo?'):
                        app.processGetRouteInfo(query, self.addr, self.conn)

                    elif query.startswith('getAllInfo?'):
                        app.processGetAllInfo(query, self.addr, self.conn)

                    elif query.startswith('getEcho?'):
                        app.processEcho(query, self.addr, self.conn)

                    elif query.startswith('watchVehiclesInfo?'):
                        app.processWatchVehiclesInfo(query, self.addr, self.conn)

                    elif query == "cancelWatch":
                        app.processCancelWatch(query, self.addr, self.conn)

                    else:
                        app.processUnknownQuery(self.conn)
            else:
                app.logger.info("Connection terminated : " + str(self.addr))
                break

        self.conn.shutdown(socket.SHUT_RDWR)
        app.logger.debug("Thread for connection ( " + str(self.addr) + " ) terminated")
        del app.listeners[self.addr]
# -------------------------------------------------------------------------------------------------------------------- #


class ExecutorThread(threading.Thread):
    def __init__(self, app):
        super().__init__()

        # Time to wait between queries
        self.wait_time = 5
        # Time to wait between watch updates
        self.watch_wait_time = 5

    def send_message(self, message, addr, conn, log_tag=''):
        if len(log_tag) > 0:
            log_tag_text = " (" + log_tag + ")"
        else:
            log_tag_text = ""
        try:
            app.logger.debug("Sending response to " + str(addr) + log_tag_text)
            conn.send(bytes(str(message) + '\n' + '\0', 'utf-8'))
        except Exception as e:
            app.logger.error("Failed to send data to " + str(addr))

    def _executeGetInfo(self, query):
            if query['type'] == 'getStopInfo':
                data, error = app.core.getStopInfo(url=query['body'])
            elif query['type'] == 'getRouteInfo':
                data, error = app.core.getRouteInfo(url=query['body'])
            elif query['type'] == 'getVehiclesInfo':
                data, error = app.core.getVehiclesInfo(url=query['body'])
            elif query['type'] == 'getVehiclesInfoWithRegion':
                data, error = app.core.getVehiclesInfoWithRegion(url=query['body'])
            elif query['type'] == 'watchVehiclesInfo':
                data, error = app.core.getVehiclesInfo(url=query['body'])
            elif query['type'] == 'getAllInfo':
                data, error = app.core.getAllInfo(url=query['body'])
            else:
                return

            payload = []
            if error == YandexTransportCore.RESULT_OK:
                for entry in data:
                    if 'data' in entry:
                        result = {'id': query['id'],
                                  'method': entry['method'],
                                  'error': 'OK',
                                  'expect_more_data': True,
                                  'data': entry['data']}
                        payload.append(result)
                    else:
                        result = {'id': query['id'],
                                  'method': entry['method'],
                                  'error': 'No data',
                                  'expect_more_data': True,
                                  }
                        payload.append(result)

            if len(payload) > 0:
                payload[-1]['expect_more_data'] = False

            for entry in payload:
                self.send_message(json.dumps(entry), query['addr'], query['conn'], log_tag=entry['method'])

    def executeGetEcho(self, query):
        """
        Execute "getEcho" command.
        :param query: internal query structure
        :return: None
        """
        result = {'id': query['id'],
                  'method': query['type'],
                  'error': 'OK',
                  'expect_more_data': False,
                  'data': query['body']}
        result_json = json.dumps(result)
        self.send_message(result_json, query['addr'], query['conn'], log_tag='getEcho')

    def executeGetStopInfo(self, query):
        app.logger.debug("Executing " + "getStopInfo" + " query:"
                         " ID=" + str(query['id']) +
                         " Body=" + str(query['body']))
        self._executeGetInfo(query)

    def executeGetRouteInfo(self, query):
        app.logger.debug("Executing " + "getRouteInfo" + " query:"
                         " ID=" + str(query['id']) +
                         " URL=" + str(query['body']))
        self._executeGetInfo(query)

    def executeGetVehiclesInfo(self, query):
        app.logger.debug("Executing " + "getVehiclesInfo" + " query:"
                         " ID=" + str(query['id']) +
                         " URL=" + str(query['body']))
        self._executeGetInfo(query)

    def executeGetVehiclesInfoWithRegion(self, query):
        app.logger.debug("Executing " + "getVehiclesInfoWithRegion" + " query:"
                         " ID=" + str(query['id']) +
                         " URL=" + str(query['body']))
        self._executeGetInfo(query)

    def executeGetAllInfo(self, query):
        app.logger.debug("Executing " + "getAllInfo" + " query:" +
                         " ID=" + str(query['id']) +
                         " URL=" + str(query['body']))
        self._executeGetInfo(query)

    def executeWatchVehiclesInfo(self, query):
        app.logger.debug("Executing " + "watchVehiclesInfo" + " query:" +
                         " ID=" + str(query['id']) +
                         " URL=" + str(query['body']))
        self._executeGetInfo(query)

        while app.watch_lock:
            for i in range(0, self.watch_wait_time):
                time.sleep(1)

            app.core.network_json = app.core.getChromiumNetworkingData()


    def executeQuery(self, query):
        """
        Execute query from the Query Queue
        :param query: query inner structure
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
        if query['type'] == 'watchVehiclesInfo':
            self.executeWatchVehiclesInfo(query)
            return

    def performQueryExtractionAndExecution(self):
        """
        Extract and execute query from Query Queue
        :return: None
        """
        # Default "discard" query
        query = None

        # Get the query from Query Queue
        app.queue_lock.acquire()
        query_len = len(app.query_queue)
        if query_len > 0:
            query = app.query_queue[0]
        app.queue_lock.release()

        # Executing the query
        if query is not None:
            self.executeQuery(query)

        # Removing executed query from the Query Queue
        app.queue_lock.acquire()
        if query_len > 0:
            app.query_queue.popleft()
        app.queue_lock.release()

    def run(self):
        app.logger.debug("Executor thread started, wait time between queries is "+str(self.wait_time)+" secs.")
        while app.is_running:
            # Extracting and executing extraction and execution of query from Query Queue
            self.performQueryExtractionAndExecution()

            # Waiting for some time before next query is extracted and executed
            for i in range(0, self.wait_time):
                if app.is_running:
                    time.sleep(1)
                else:
                    break
        app.logger.debug("Executor thread stopped.")
# -------------------------------------------------------------------------------------------------------------------- #


class Application:
    """
    Main application class
    """
    def __init__(self):
        setproctitle.setproctitle('transport_proxy')
        "If set to false, the server will begin to terminate itself"
        self.is_running = True

        # Listen address
        self.host = '0.0.0.0'
        # Listen port
        self.port = 25555

        # List of clients currently connected to the server
        self.listeners = defaultdict()

        # Logger
        self.logger = Logger(Logger.DEBUG)

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
        self.logger.info("SIGINT received! Terminating the program...")
        self.watch_lock = False
        self.is_running = False
        self.logger.info("Waiting for threads to terminate...")
        copy_listeners = self.listeners.copy()
        for key, listener in copy_listeners.items():
            listener.join()
        if self.executor_thread is not None:
            self.executor_thread.join()

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)
        self.logger.debug("Binding socket...")
        try:
            sock.bind((self.host, self.port))
        except socket.error:
            return 1

        self.logger.info("Listening for incoming connections.")
        self.logger.info("Host: " + str(self.host) + " , Port: " + str(self.port))
        sock.listen(1)

        while self.is_running:
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
        data = []
        for key, value in self.listeners.items():
            entry = {"ip_address" : key[0], "port" : key[1]}
            data.append(entry)
        json_data = json.dumps(data)

        return json_data

    def getCurrentQueue(self):
        data = []

        self.queue_lock.acquire()
        for entry in self.query_queue:
            entry = {'type': entry['type'], 'id': entry['id'], 'query': entry['body']}
            data.append(entry)
        self.queue_lock.release()

        json_data = json.dumps(data)

        return json_data

    def handleWatchLock(self, conn):
        if app.watch_lock:
            response = {"id": self.query_id,
                        "response": "ERROR",
                        "message": "Watch task is planned, no queries accepted until cancelled!",
            }
            response_json = json.dumps(response)
            conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def split_query(self, query):
        """
        Get ID from getXXXInfo?id=?YYYY?... requests
        :param query: the query
        :return: query_type, the id value from the query, body of the query
        """
        result = re.match("(.*?)\?id=(.*?)\?(.*)", query)
        query_type = ''
        query_id = ''
        query_body=''
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
        if app.watch_lock:
            self.handleWatchLock(conn)
        else:
            if set_watch_lock:
                self.watch_lock = True

            query_type, query_id, query_body = self.split_query(query)

            self.queue_lock.acquire()
            app.query_queue.append({'type': query_type,
                                    'id': query_id,
                                    'body': query_body,
                                    'addr': addr,
                                    'conn': conn}
                                   )
            queue_position = len(app.query_queue) - 1
            self.queue_lock.release()

            response = {'id': query_id,
                        'response': 'OK',
                        'queue_position': queue_position}
            response_json = json.dumps(response)
            conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def processGetStopInfo(self, query, addr, conn):
        self.processGetInfo(query, addr, conn)

    def processGetVehiclesInfo(self, query, addr, conn):
        self.processGetInfo(query, addr, conn)

    def processGetVehiclesInfoWithRegion(self, query, addr, conn):
        self.processGetInfo(query, addr, conn)

    def processGetRouteInfo(self, query, addr, conn):
        self.processGetInfo(query, addr, conn)

    def processGetAllInfo(self, query, addr, conn):
        self.processGetInfo(query, addr, conn)

    def processWatchVehiclesInfo(self, query, addr, conn):
        app.logger.info("Watch event (watchVehiclesInfo) requested!")
        app.logger.warning("All subsequent queries are blocked until watch query is cancelled!")
        # Add watch event to Query Queue
        self.processGetInfo(query, addr, conn, set_watch_lock=True)

    def processCancelWatch(self, query, addr, conn):
        app.logger.info("Watch task cancelled, resuming normal operations")
        app.watch_lock = False
        response = {"response": "OK", "message": "Watch task cancelled."}
        response_json = json.dumps(response)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def processEcho(self, query, addr, conn):
        # If blocked by Watch Lock
        if app.watch_lock:
            self.handleWatchLock(conn)
        else:
            self.processGetInfo(query, addr, conn)

    def processGetCurrentQueue(self, conn):
        """
        Processing of "getCurrentQueue" request.
        :param conn: connection to send info back
        :return: None
        """
        current_queue = app.getCurrentQueue()
        queue_json = json.loads(current_queue)
        response_json = json.dumps(queue_json)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def processUnknownQuery(self, conn):
        response = {"response": "ERROR", "message": "Unknown query"}
        response_json = json.dumps(response)
        conn.send(bytes(response_json + '\n' + '\0', 'utf-8'))

    def run(self):
        """
        Run the application
        :return: exit code
        """

        self.logger.info("YTPS - Yandex Transport Proxy Server - starting up...")

        signal.signal(signal.SIGINT, self.sigint_handler)

        # Starting query executor thread
        self.executor_thread = ExecutorThread(self)
        self.executor_thread.start()

        self.core = YandexTransportCore()
        self.logger.info("Starting ChromeDriver...")
        self.core.startWebdriver()
        self.logger.info("ChromeDriver started successfully!")

        # Getting stop info example
        """
        res = core.getStopInfo(url="https://yandex.ru/maps/213/moscow/?"
                                   "ll=37.579537,C55.821644&"
                                   "masstransit[stopId]=stop__9639753&"
                                   "mode=stop&"
                                   "z=16")
        # Printing the output
        print(json.dumps(res, sort_keys=True, indent=4, separators=(',', ': ')))
        time.sleep(5)

        # Getting vehicles info example
        res = core.getVehiclesInfo(url="https://yandex.ru/maps/213/moscow/?"
                                       "ll=37.589633%2C55.835559&"
                                       "masstransit[routeId]=213_56_trolleybus_mosgortrans&"
                                       "masstransit[stopId]=stop__9639753&"
                                       "masstransit[threadId]=213A_56_trolleybus_mosgortrans&"
                                       "mode=stop&"
                                       "z=14")
        # Printing the output
        print(json.dumps(res, sort_keys=True, indent=4, separators=(',', ': ')))
        """
        self.listen()

        self.core.stopWebdriver()

        self.logger.info("YTPS - Yandex Transport Proxy Server - terminated!")

# -------------------------------------------------------------------------------------------------------------------- #
if __name__ == '__main__':
    app = Application()
    app.run()
    sys.exit(0)
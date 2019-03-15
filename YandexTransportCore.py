"""
Yandex Transport Core module

This is the core module of Yandex Transport Hack API.
It uses Selenium with ChromeDriver and gets Yandex Transport API JSON responses.
"""

import re
import io
import json
from selenium import webdriver
from bs4 import BeautifulSoup


class YandexTransportCore:
    # Error codes
    RESULT_OK = 0
    RESULT_WEBDRIVER_NOT_RUNNING = 1
    RESULT_NO_LAST_QUERY = 2
    RESULT_NETWORK_PARSE_ERROR = 3
    RESULT_JSON_PARSE_ERROR = 4

    def __init__(self):
        self.driver = None

        # Count of network queries executed so far, the idea is to restart the browser if it's too big.
        self.network_queries_count = 0

        # ChromeDriver location. They changed it a lot, by the way.
        self.chrome_driver_location = "/usr/bin/chromedriver"

    def startWebdriver(self):
        """
        Start Chromium webdriver
        :return: nothing
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--incognito")
        self.driver = webdriver.Chrome(self.chrome_driver_location, chrome_options=options)

    def stopWebdriver(self):
        """
        Stop Chromium webdriver
        :return: nothing
        """
        self.driver.quit()

    # ----                               MASTER FUNCTION TO GET YANDEX API DATA                                   ---- #

    def _getYandexJSON(self, url, api_method):
        """
        Universal method to get Yandex JSON results.
        :param url: initial url, get it by clicking on the route or stop
        :param api_method: basically a string to find, like "maps/api/masstransit/getStopInfo"
        :return: huge json data, error code
        """
        if self.driver is None:
            return None, self.RESULT_WEBDRIVER_NOT_RUNNING
        self.driver.get(url)

        # Script to get Network data from Developer tools, huge thanks to this link:
        # https://stackoverflow.com/questions/20401264/how-to-access-network-panel-on-google-chrome-developer-tools-with-selenium
        script = "var performance = window.performance || window.mozPerformance || window.msPerformance || " \
                 "window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network;"
        data = self.driver.execute_script(script)

        # They output network data in "kinda-JSON" with single quites instead of double ones.
        network_json = str(data).replace("'", '"')

        # Loading Network Data to JSON
        try:
            network_data = json.loads(network_json, encoding='utf-8')
        except Exception as e:
            print(e)
            return self.RESULT_NETWORK_PARSE_ERROR, None

        # Getting the last executed API query
        last_query = None
        url_reached = False

        self.network_queries_count = 0
        for entry in network_data:
            self.network_queries_count += 1
            if not url_reached:
                if entry['name'] == url:
                    url_reached = True
                    continue
            else:
                res = re.match(".*" + api_method + ".*", str(entry['name']))
                if res is not None:
                    last_query = entry['name']

        # Getting last API query results from cache by executing it again in the browser
        if last_query != None:
            self.driver.get(last_query)
        else:
            return None, self.RESULT_NO_LAST_QUERY

        # Writing getStopInfo results to memory
        output_stream = io.StringIO()
        output_stream.write(self.driver.page_source)
        output_stream.seek(0)

        # Getting getStopInfo results to JSON
        soup = BeautifulSoup(output_stream, 'lxml', from_encoding='utf-8')
        body = soup.find('body').string.encode('utf-8')
        try:
            result_json = json.loads(body, encoding='utf-8')
        except Exception as e:
            print(e)
            return self.RESULT_JSON_PARSE_ERROR, None

        return result_json, self.RESULT_OK

    # ----                                   SHORTCUTS TO USED APIs                                               ---- #

    def getStopInfo(self, url):
        """
        Getting Yandex masstransit getStopInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: huge json data, error code
        """
        return self._getYandexJSON(url, api_method="maps/api/masstransit/getStopInfo")

    def getVehiclesInfo(self, url):
        """
        Getting Yandex masstransit getVehiclesInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: huge json data, error code
        """
        return self._getYandexJSON(url, api_method="maps/api/masstransit/getVehiclesInfo")

    def getRouteInfo(self, url):
        """
        Getting Yandex masstransit getRouteInfo JSON results
        :param url:
        :return:
        """
        return self._getYandexJSON(url, api_method="maps/api/masstransit/getRouteInfo")


if __name__ == '__main__':
    print("Hi! This module is not supposed to run on its own.")

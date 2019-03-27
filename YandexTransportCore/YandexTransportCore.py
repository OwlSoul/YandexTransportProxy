"""
Yandex Transport Core module

This is the core module of Yandex Transport Hack API.
It uses Selenium with ChromeDriver and gets Yandex Transport API JSON responses.
"""

# NOTE: This project uses camelCase for function names. While PEP8 recommends using snake_case for these,
#       the project in fact implements the "quasi-API" for Yandex Masstransit, where names are in camelCase,
#       for example, getStopInfo. Correct naming for this function according to PEP8 would be get_stop_info.
#       Thus, the desision to use camelCase was made. In fact, there are a bunch of python projects which use
#       camelCase, like Robot Operating System.
#       I also personally find camelCase more pretier than the snake_case.

import re
import io
import json
import selenium
from selenium import webdriver
from bs4 import BeautifulSoup


class YandexTransportCore:
    """
    YandexTransportCore class, implements core functions of access to Yandex Transport/Masstransit API
    """
    # Error codes
    RESULT_OK = 0
    RESULT_WEBDRIVER_NOT_RUNNING = 1
    RESULT_NO_LAST_QUERY = 2
    RESULT_NETWORK_PARSE_ERROR = 3
    RESULT_JSON_PARSE_ERROR = 4
    RESULT_GET_ERROR = 5

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
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--incognito")
        # These two are basically needed for Chromium to run inside docker container.
        chrome_options.add_argument('--no-sandbox')
        # Next line causes selenium error WebDriverException: Message: chrome not reachable" inside Docker container.
        # Transport Proxy seems to work without it, --no-sandbox only is enough.
        # Left here as s reminder
        # chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(self.chrome_driver_location, options=chrome_options)

    def stopWebdriver(self):
        """
        Stop Chromium webdriver
        :return: nothing
        """
        self.driver.quit()

    @staticmethod
    def yandexAPItoLocalAPI(method):
        """
        Converts Yandex API to local API,
        :param method: method, like "maps/api/masstransit/getVehiclesInfo"
        :return: local API, like to "getVehiclesInfo"
        """
        if method == "maps/api/masstransit/getStopInfo":
            return 'getStopInfo'
        if method == "maps/api/masstransit/getRouteInfo":
            return 'getRouteInfo'
        if method == "maps/api/masstransit/getVehiclesInfo":
            return 'getVehiclesInfo'
        if method == "maps/api/masstransit/getVehiclesInfoWithRegion":
            return 'getVehiclesInfoWithRegion'
        return method

    def getChromiumNetworkingData(self):
        """
        Gets "Network" data from Developer tools of Chromium Browser
        :return: JSON containing data from "Network" tab
        """
        # Script to get Network data from Developer tools, huge thanks to this link:
        # https://stackoverflow.com/questions/20401264/how-to-access-network-panel-on-google-chrome-developer-tools-with-selenium
        script = "var performance = window.performance || window.mozPerformance || window.msPerformance || " \
                 "window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network;"
        data = self.driver.execute_script(script)

        # They output network data in "kinda-JSON" with single quites instead of double ones.
        result_json = str(data).replace("'", '"')

        return result_json

    # ----                               MASTER FUNCTION TO GET YANDEX API DATA                                   ---- #

    def getYandexJSON(self, url, api_method):
        """
        Universal method to get Yandex JSON results.
        :param url: initial url, get it by clicking on the route or stop
        :param api_method: tuple of strings to find,
               like ("maps/api/masstransit/getRouteInfo","maps/api/masstransit/getVehiclesInfo")
        :return: array of huge json data, error code
        """
        result_list = []

        if self.driver is None:
            return result_list, self.RESULT_WEBDRIVER_NOT_RUNNING
        try:
            self.driver.get(url)
        except selenium.common.exceptions.WebDriverException as e:
            print(e)
            return None, self.RESULT_GET_ERROR

        network_json = self.getChromiumNetworkingData()

        # Loading Network Data to JSON
        try:
            network_data = json.loads(network_json, encoding='utf-8')
        except ValueError as e:
            print(e)
            return result_list, self.RESULT_NETWORK_PARSE_ERROR

        url_reached = False
        last_query = []

        self.network_queries_count = 0
        for entry in network_data:
            self.network_queries_count += 1
            if not url_reached:
                if entry['name'] == url:
                    url_reached = True
                    continue
            else:
                for method in api_method:
                    res = re.match(".*" + method + ".*", str(entry['name']))
                    if res is not None:
                        last_query.append({"url": entry['name'], "method": method})

        # Getting last API query results from cache by executing it again in the browser
        if last_query:                    # Same meaning as in "if len(last_query) > 0:"
            for query in last_query:
                # Getting the webpage based on URL
                try:
                    self.driver.get(query['url'])
                except selenium.common.exceptions.WebDriverException as e:
                    print("Your favourite error message: THIS SHOULD NOT HAPPEN!")
                    print(e)
                    return None, self.RESULT_GET_ERROR

                # Writing getStopInfo results to memory
                output_stream = io.StringIO()
                output_stream.write(self.driver.page_source)
                output_stream.seek(0)

                # Getting getStopInfo results to JSON
                soup = BeautifulSoup(output_stream, 'lxml', from_encoding='utf-8')
                body = soup.find('body')
                if body is not None:
                    body_string = body.string.encode('utf-8')
                    try:
                        returned_json = json.loads(body_string, encoding='utf-8')
                        data = {"url": query['url'],
                                "method": self.yandexAPItoLocalAPI(query['method']),
                                "error": "OK",
                                "data": returned_json}
                    except ValueError as e:
                        data = {"url": query['url'],
                                "method": self.yandexAPItoLocalAPI(query['method']),
                                "error": "Failed to parse JSON"}
                else:
                    data = {"url": query['url'],
                            "method": self.yandexAPItoLocalAPI(query['method']),
                            "error": "Failed to parse body of the response"}

                result_list.append(data)

        else:
            return result_list, self.RESULT_NO_LAST_QUERY

        return result_list, self.RESULT_OK

    # ----                                   SHORTCUTS TO USED APIs                                               ---- #

    def getStopInfo(self, url):
        """
        Getting Yandex masstransit getStopInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self.getYandexJSON(url, api_method=("maps/api/masstransit/getStopInfo",))

    def getVehiclesInfo(self, url):
        """
        Getting Yandex masstransit getVehiclesInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self.getYandexJSON(url, api_method=("maps/api/masstransit/getVehiclesInfo",))

    def getVehiclesInfoWithRegion(self, url):
        """
        Getting Yandex masstransit getVehiclesInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self.getYandexJSON(url, api_method=("maps/api/masstransit/getVehiclesInfoWithRegion",))

    def getRouteInfo(self, url):
        """
        Getting Yandex masstransit getRouteInfo JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self.getYandexJSON(url, api_method=("maps/api/masstransit/getRouteInfo",))

    def getAllInfo(self, url):
        """
        Getting basically all Yandex Masstransit API JSON results related to requested URL
        :param url:
        :return:
        """
        return self.getYandexJSON(url, api_method=("maps/api/masstransit/getRouteInfo",
                                                   "maps/api/masstransit/getStopInfo",
                                                   "maps/api/masstransit/getVehiclesInfo",
                                                   "maps/api/masstransit/getVehiclesInfoWithRegion"))


if __name__ == '__main__':
    print("Hi! This module is not supposed to run on its own.")

"""
Yandex Transport Core module

This is the core module of Yandex Transport Hack API.
It uses Selenium with ChromeDriver and gets Yandex Transport API JSON responses.
"""

# NOTE: This project uses camelCase for function names. While PEP8 recommends using snake_case for these,
#       the project in fact implements the "quasi-API" for Yandex Masstransit, where names are in camelCase,
#       for example, get_stop_info. Correct naming for this function according to PEP8 would be get_stop_info.
#       Thus, the desision to use camelCase was made. In fact, there are a bunch of python projects which use
#       camelCase, like Robot Operating System.
#       I also personally find camelCase more prettier than the snake_case.

import ast
import re
import time
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

    def start_webdriver(self):
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

    def stop_webdriver(self):
        """
        Stop Chromium Webdriver
        :return: nothing
        """
        self.driver.quit()

    def restart_webdriver(self):
        """
        Restart Chromium Webdriver. Good idea to do this sometimes, like Garbage Collection.
        :return: nothing
        """
        self.stop_webdriver()
        self.start_webdriver()

    @staticmethod
    def yandex_api_to_local_api(method):
        """
        Converts Yandex API to local API,
        :param method: method, like "maps/api/masstransit/getVehciclesInfo"
        :return: local API, like to "getVehiclesInfo"
        """
        if method == "maps/api/masstransit/getStopInfo":
            return 'getStopInfo'
        if method == "maps/api/masstransit/getRouteInfo":
            return 'getRouteInfo'
        if method == "maps/api/masstransit/getLine":
            return 'getLine'
        if method == "maps/api/masstransit/getVehiclesInfo":
            return 'getVehiclesInfo'
        if method == "maps/api/masstransit/getVehiclesInfoWithRegion":
            return 'getVehiclesInfoWithRegion'
        if method == "maps/api/masstransit/getLayerRegions":
            return 'getLayerRegions'

        return method

    def get_chromium_networking_data(self):
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
        # We used this thing before, which was unreliable in the end
        # result_json = str(data).replace("'", '"')
        # Now we're just using this thing, which is probably VERY dangerous, but we don't care =)
        parsed_data = eval(str(data))

        return parsed_data

    # ----                               MASTER FUNCTION TO GET YANDEX API DATA                                   ---- #

    def _get_yandex_json(self, url, api_method):
        """
        Universal method to get Yandex JSON results.
        :param url: initial url, get it by clicking on the route or stop
        :param api_method: tuple of strings to find,
               like ("maps/api/masstransit/get_route_info","maps/api/masstransit/get_vehicles_info")
        :return: array of huge json data, error code
        """

        print("API Method:", api_method)
        print("URL", url)

        result_list = []

        if self.driver is None:
            return result_list, self.RESULT_WEBDRIVER_NOT_RUNNING
        try:
            self.driver.get(url)
        except selenium.common.exceptions.WebDriverException as e:
            print("Selenium exception (_get_yandex_json):", e)
            return None, self.RESULT_GET_ERROR

        # OK, now Yandex is not supplying us with getStopInfo here, how about we wait for a bit (dirty hack)
        print("Sleeping 30 seconds, dirty hack to get getStopInfo appear")
        time.sleep(30)        

        network_data = self.get_chromium_networking_data()
        print(network_data)

        # Loading Network Data to JSON
        #try:
        #    network_data = json.loads(network_json, encoding='utf-8')
        #except ValueError as e:
        #    print("JSON Exception (_get_yandex_json):", e)
        #    return result_list, self.RESULT_NETWORK_PARSE_ERROR

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
                    print("Selenium exception (_get_yandex_json):", e)
                    return None, self.RESULT_GET_ERROR

                # Writing get_stop_info results to memory
                output_stream = io.StringIO()
                output_stream.write(self.driver.page_source)
                output_stream.seek(0)

                # Getting get_stop_info results to JSON
                soup = BeautifulSoup(output_stream, 'lxml', from_encoding='utf-8')
                body = soup.find('body')
                if body is not None:
                    body_string = body.string.encode('utf-8')
                    try:
                        returned_json = json.loads(body_string, encoding='utf-8')
                        data = {"url": query['url'],
                                "method": self.yandex_api_to_local_api(query['method']),
                                "error": "OK",
                                "data": returned_json}
                    except ValueError as e:
                        data = {"url": query['url'],
                                "method": self.yandex_api_to_local_api(query['method']),
                                "error": "Failed to parse JSON"}
                else:
                    data = {"url": query['url'],
                            "method": self.yandex_api_to_local_api(query['method']),
                            "error": "Failed to parse body of the response"}

                result_list.append(data)

        else:
            return result_list, self.RESULT_NO_LAST_QUERY

        return result_list, self.RESULT_OK

    # ----                                   SHORTCUTS TO USED APIs                                               ---- #

    def get_stop_info(self, url):
        """
        Getting Yandex masstransit get_stop_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getStopInfo",))

    def get_vehicles_info(self, url):
        """
        Getting Yandex masstransit get_vehicles_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getVehiclesInfo",))

    def get_vehicles_info_with_region(self, url):
        """
        Getting Yandex masstransit get_vehicles_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getVehiclesInfoWithRegion",))

    def get_route_info(self, url):
        """
        Getting Yandex masstransit get_route_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getRouteInfo",))

    def get_line(self, url):
        """
        Getting Yandex masstransit get_line JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getLine",))

    def get_layer_regions(self, url):
        """
        No idea what this thing does
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getLayerRegions",))

    def get_all_info(self, url):
        """
        Getting basically all Yandex Masstransit API JSON results related to requested URL
        :param url:
        :return:
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getRouteInfo",
                                                      "maps/api/masstransit/getLine",
                                                      "maps/api/masstransit/getStopInfo",
                                                      "maps/api/masstransit/getVehiclesInfo",
                                                      "maps/api/masstransit/getVehiclesInfoWithRegion",
                                                      "maps/api/masstransit/getLayerRegions")
                                     )


if __name__ == '__main__':
    print("Hi! This module is not supposed to run on its own.")

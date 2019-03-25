"""
Yandex Transport Core unit tests.

NOTE: These are Unit Tests, they should test function behaviour based on input data only, and should NOT
      rely on current state of Yandex API. These tests are executed once during "build" stage.
      Do not use Live Data from Yandex MassTransit here, only saved one. Live Data is tested in
      Integration Tests/Continuous Monitoring tests.
"""

import pytest
import random
import selenium
import time
import json
from YandexTransportCore import YandexTransportCore

# STOP URL's
# Probably replace this to "ConstructURL" in the future to increase randomness.
# Template: {'name': '', 'url': ''}
stop_urls = [{'name': 'Сходненская улица', 'url': 'https://yandex.ru/maps/213/moscow/?ll=37.439156%2C55.841917&masstransit%5BstopId%5D=stop__9640231&mode=stop&z=17'},
             {'name': 'Метро Марьино (южная)', 'url':'https://yandex.ru/maps/213/moscow/?ll=37.744465%2C55.650011&masstransit%5BstopId%5D=stop__9647488&mode=stop&z=17'},
             {'name': 'Улица Столетова', 'url': 'https://yandex.ru/maps/213/moscow/?ll=37.504978%2C55.703850&masstransit%5BstopId%5D=stop__9646267&mode=stop&z=17'},
             {'name': '3-я Рощинская улица', 'url': 'https://yandex.ru/maps/213/moscow/?ll=37.610832%2C55.707313&masstransit%5BstopId%5D=stop__9646344&mode=stop&z=18'},
             {'name': 'Метро Бауманская', 'url': 'https://yandex.ru/maps/213/moscow/?ll=37.678664%2C55.772171&masstransit%5BstopId%5D=stop__9643291&mode=stop&z=19'},
             {'name': 'Метро Войковская', 'url': 'https://yandex.ru/maps/213/moscow/?ll=37.498648%2C55.818952&masstransit%5BstopId%5D=stop__9649585&mode=stop&z=17'}]

# NOTE: It's a good idea to wait random time between queries so to be very sure Yandex will not ban this.
#       Stress tests to check Yandex patience limits with no delays are considered only, from dedicated IP address.
def wait_random_time():
    '''
    Wait random time between queries.
    :return:
    '''
    time.sleep(random.randint(15, 45))

# ---------------------------------------------      warm-up        -------------------------------------------------- #

def test_initial():
    """
    Most basic test to ensure pytest DEFINITELY works
    """
    assert True == True

# ---------------------------------------------   startWebdriver    -------------------------------------------------- #
def test_startWebdriver_invalid_webdriver_location():
    """
    Start ChromeDriver with invalid webdriver location supplied.
    Should raise selenium.common.exceptions.WebDriverException

    """
    core = YandexTransportCore()
    core.chrome_driver_location = '/opt/usr/bin/this-dir-does-not-exist'
    with pytest.raises(selenium.common.exceptions.WebDriverException):
        result = core.startWebdriver()


# ------------------------------------------   yandexAPIToLocalAPI    ------------------------------------------------ #
def test_yandexAPIToLocalAPI():
    """
    Test Yandex API to Local API conversions.
    """
    assert YandexTransportCore.yandexAPItoLocalAPI('maps/api/masstransit/getStopInfo') == 'getStopInfo'
    assert YandexTransportCore.yandexAPItoLocalAPI('maps/api/masstransit/getRouteInfo') == 'getRouteInfo'
    assert YandexTransportCore.yandexAPItoLocalAPI('maps/api/masstransit/getVehiclesInfo') == 'getVehiclesInfo'
    assert YandexTransportCore.yandexAPItoLocalAPI('maps/api/masstransit/getVehiclesInfoWithRegion') == \
           'getVehiclesInfoWithRegion'
    # Unknown API method, should return the input
    assert YandexTransportCore.yandexAPItoLocalAPI('maps/api/masstransit/getNonexistent') == \
                                                   'maps/api/masstransit/getNonexistent'


# ------------------------------------------   getChromiumNetworkingData    ------------------------------------------ #
def test_getChromiumNetworkingData():
    """
    Test getting Chromium Networking Data.
    Basically this will test "Stack Overflow" script to get Networking Data from Chromium, it is expected for this
    test to fail if something will change in Chromium later regarding this functionality.

    The test picks random URL from stop_urlsst, performs "GET" operation, then checks if actual data was returned and will
    try to wind the URL query.
    """
    core = YandexTransportCore()
    core.startWebdriver()
    url = stop_urls[random.randint(0, len(stop_urls) - 1)]
    print("Stop name:", url['url'])
    core.driver.get(url['url'])
    # Getting Chromium Network Data
    data = json.loads(core.getChromiumNetworkingData())
    found_input_url = False
    for entry in data:
        if entry['name'] == url['url']:
            found_input_url = True
            break

    # Wait random amount of time
    assert found_input_url
    wait_random_time()

# ------------------------------------------------- _getYandexJSON --------------------------------------------------- #
def test_getYandexJSON():
    """
    Test "_getYandexJSON" function, should not break no matter what is supplied.
    :return:
    """
    core = YandexTransportCore()
    core.startWebdriver()

    # Fist test, None url, existing method
    url = None
    method = "maps/api/masstransit/getRouteInfo"
    result, error = core._getYandexJSON(url, method)
    assert (result is None) and (error == YandexTransportCore.RESULT_GET_ERROR)

    # Fist test, url is gibberish, existing method
    url = 'abrabgarilsitlsdxyb4396t6'
    method = "maps/api/masstransit/getRouteInfo"
    result, error = core._getYandexJSON(url, method)
    assert (result is None) and (error == YandexTransportCore.RESULT_GET_ERROR)

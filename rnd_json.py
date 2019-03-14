#!/usr/bin/env python3

# Trying to get original JSON

import selenium
from selenium import webdriver
import time
import re
import json
import os
from bs4 import BeautifulSoup

options = webdriver.ChromeOptions()

#print("Running chromium...")
driver_location = "/usr/bin/chromedriver"
url = "https://yandex.ru/maps/213/moscow/?ll=37.579537,C55.821644&masstransit[stopId]=stop__9639753&mode=stop&z=16"
driver = webdriver.Chrome(driver_location, chrome_options=options)
driver.get(url)
# Script to execute, thanks to this link:
# https://stackoverflow.com/questions/20401264/how-to-access-network-panel-on-google-chrome-developer-tools-with-selenium
script = "var performance = window.performance || window.mozPerformance || window.msPerformance || " \
         "window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network;"
data = driver.execute_script(script)
jdata = str(data).replace("'",'"')
json_data = json.loads(jdata)
#print(json.dumps(json_data, sort_keys=True, indent=4, separators=(',', ': ')))
#res = re.match("'name':'https://yandex\.ru/maps/api/masstransit/getStopInfo.*?'", str(data))
#print(data)
#res = re.match(".*getStopInfo(.*?)'", str(data))
#print(res)
last_json_query = None
for entry in json_data:
    res = re.match(".*maps/api/masstransit/getStopInfo.*", str(entry['name']))
    if res is not None:
        last_json_query=entry['name']
#Now executing the last getStopInfo query, taking it from browser's cache!
driver.get(last_json_query)

# --------------------------------------------------- #
# TODO: Think about writing directly to the variable!
with open('output.tmp', 'w', encoding='utf-8') as file:
    file.write(driver.page_source)
file.close()

file = open('output.tmp', 'r', encoding='utf-8')
soup = BeautifulSoup(file, 'lxml', from_encoding='utf-8')
file.close()
os.remove('output.tmp')
# --------------------------------------------------- #

body = soup.find('body')
# Yeah, baby! There's an original JSON from Yandex.Transport API!
orig_json = json.loads(str(body.string))
print(json.dumps(orig_json, sort_keys=True, indent=4, separators=(',', ': ')))

time.sleep(10)
driver.quit()
#print("Finished!")
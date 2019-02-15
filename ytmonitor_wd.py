#!/usr/bin/env python3

# Yandex Transport Monitor - WebDriver Version
#  Very, very, very, very ,very dirty hack thing.
#
#  Uses Selenium web automation tool to scan for public transport.
#  Exceptionally heavy, or maybe not so heavy if used in headless mode.
#
# Workflow pipeline:
#  1. Get the page source code via Selenium Automation + WebDriver
#  2. Parse the page.
#  3  Save contents to the database.
#  4. Delete the page source code
#  5. Wait (1 minute is enough).
#  6. Repeat.

import time
import datetime
import signal
import selenium
from selenium import webdriver
import sys
import uuid
from ytm_pageparser import YTMPageParser
import os
import setproctitle

class Application:
    driver = None

    def __init__(self):

        setproctitle.setproctitle("ytmonitor_wd")

        self.is_running = True

        #self._chrome_driver_location = '/home/astreinw/Apps/ChromeDriver/chromedriver'
        #self._chrome_driver_location = '/usr/bin/chromedriver'
        self._chrome_driver_location = '/usr/sbin/chromedriver'
        self._savefile = 'page-'+str(uuid.uuid4())+".html"

        self._url = "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.493989%2C55.932101&masstransit%5BstopId%5D=stop__9898970&mode=stop&z=16.05"
        self._station_id = "stop__9898970"

        signal.signal(signal.SIGINT, self.sigint_handler)

    def sigint_handler(self, signal, time):
        print("SIGINT received! Graceful termination is in progress...")
        self.is_running = False
        if self.driver is not None:
            self.driver.quit()
        os.remove(self._savefile)
        print("Program terminated.")
        sys.exit(0)

    def run(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")

            print("Running Chrome in headless mode...")
            driver = webdriver.Chrome(self._chrome_driver_location, chrome_options=options)
            while self.is_running:
                time_now = datetime.datetime.now()
                print("Timestamp:", time_now)

                driver.get(self._url)

                with open(self._savefile, 'w', encoding="utf-8") as file:
                    file.write(driver.page_source)
                file.close()

                # Parse the page
                parser = YTMPageParser(self._savefile)
                result = parser.parse()
                for line in result:
                    print(line)
                print("")

                # Write to database
                parser.write_to_database(self._station_id, time_now, parser.data)

                time.sleep(60)
            driver.quit()
            os.remove(self._savefile)
            print("Program terminated.")
            sys.exit(0)
        except selenium.common.exceptions.WebDriverException as e:
            print("Exception:", str(e))
            sys.exit(1)


if __name__=='__main__':
    app = Application()
    app.run()

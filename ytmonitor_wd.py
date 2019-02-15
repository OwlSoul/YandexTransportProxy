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
from selenium import webdriver
import sys

class Application:
    _chrome_driver_location = '/home/astreinw/Apps/ChromeDriver/chromedriver'

    def __init__(self):
        self.is_running = True
        signal.signal(signal.SIGINT, self.sigint_handler)

    def sigint_handler(self, signal, time):
        print("SIGINT received! Graceful termination is in progress...")
        self.is_running = False

    def run(self):
        driver = webdriver.Chrome(self._chrome_driver_location)
        while self.is_running:
            time_now = datetime.datetime.now()
            print(time_now)

            driver.get('https://yandex.ru/maps/214/dolgoprudniy/?ll=37.493989%2C55.932101&masstransit%5BstopId%5D=stop__9898970&mode=stop&z=16.05')
            filename='saves/'+'page-'+str(time_now)+'.html'
            with open(filename, 'w') as file:
                file.write(driver.page_source)
            file.close()
            time.sleep(30)
            #driver.quit()
            time.sleep(30)
        driver.quit()
        print("Program terminated.")
        sys.exit(0)


if __name__=='__main__':
    app = Application()
    app.run()

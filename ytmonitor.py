#!/usr/bin/env python3

# This script prints a bus schedule(essentially how many time left till bus will arrive)
# for particular stop_id.

import pycurl
import io
import re

class Application:
    def __init__(self):
        pass

    def run(self):
        print('YT Monitor')
        # First cUrl: curl -L yandex.ru/maps -c cookies.txt
        # Goal: To get csrfToken, save cookies
        #
        # -c - save cookies
        # -b - get cookies
        buffer = io.BytesIO()
        cUrl = pycurl.Curl()
        cUrl.setopt(pycurl.URL, 'https://yandex.ru/maps')
        cUrl.setopt(pycurl.WRITEFUNCTION, buffer.write)
        cUrl.setopt(pycurl.FOLLOWLOCATION, True)
        cUrl.setopt(pycurl.COOKIEJAR, "cookies.txt")
        cUrl.perform()
        cUrl.close()

        print("Data obtained:")
        print(str(buffer.getvalue()))


if __name__=="__main__":
    app = Application()
    app.run()
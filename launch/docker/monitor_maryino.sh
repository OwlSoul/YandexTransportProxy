#!/bin/bash

IMAGE="ytmonitor:latest"

docker run -it --privileged $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 1 \
--url "https://yandex.ru/maps/213/moscow/?ll=37.744365%2C55.649835&masstransit%5BstopId%5D=stop__9647488&mode=stop&sll=39.497656%2C43.958431&sspn=0.291481%2C0.128713&text=%D0%BC%D0%B0%D1%80%D1%8C%D0%B8%D0%BD%D0%BE%20%D0%BC%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&z=17" \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once
'

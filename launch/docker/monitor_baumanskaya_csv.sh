#!/bin/bash

IMAGE="ytmonitor:latest"

docker run -it --privileged $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 4 \
--station_id "Бауманская" \
--url "https://yandex.ru/maps/213/moscow/?ll=37.679037%2C55.772087&masstransit%5BstopId%5D=stop__9643291&mode=stop&z=19" \
--out_mode csv \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once
'

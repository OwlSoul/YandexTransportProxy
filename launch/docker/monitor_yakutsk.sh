#!/bin/bash

# This is the test of Yakutsk bus (or whatever) station.
# Ad for 2019, shound return NOTHING.

IMAGE="ytmonitor:latest"

docker run -it --rm --privileged $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 4 \
--station_id "Якутск, Школа №7" \
--url "https://yandex.ru/maps/74/yakutsk/?ll=129.725800%2C62.037399&mode=poi&poi%5Bpoint%5D=129.728085%2C62.036624&poi%5Buri%5D=ymapsbm1%3A%2F%2Forg%3Foid%3D179807288972&sll=37.586616%2C55.802258&sspn=0.036435%2C0.012545&text=%D1%8F%D0%BA%D1%83%D1%82%D1%81%D0%BA&z=16" \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once \
--save_to_database \
--db_host "10.10.7.1" \
--db_port 5432 \
--db_name "ytmonitor" \
--db_username "ytmonitor" \
--db_password "password" \
'

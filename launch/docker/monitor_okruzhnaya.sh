#!/bin/bash

IMAGE="ytmonitor:1.0.3"

docker run -it --privileged $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 4 \
--url "https://yandex.ru/maps/213/moscow/?ll=37.573801%2C55.848008&masstransit%5BstopId%5D=stop__10182565&mode=stop&z=18" \
--chrome_driver_location "/usr/sbin/chromedriver" \
--wait_time 60 \
--save_to_database \
--db_host "172.17.0.1" \
--db_port 5432 \
--db_name "ytmonitor" \
--db_username "ytmonitor" \
--db_password "password"'

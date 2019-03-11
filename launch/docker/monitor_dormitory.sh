#!/bin/bash

IMAGE="ytmonitor:latest"

docker run -it --privileged --restart always $IMAGE \
su ytmonitor -c \
'python3 /home/ytmonitor/ytm_wd \
--verbose 4 \
--url "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.495068%2C55.935872&masstransit%5BstopId%5D=stop__9682838&mode=stop&z=16" \
--chrome_driver_location "/usr/sbin/chromedriver" \
--wait_time 60 \
--save_to_database \
--db_host "10.10.7.1" \
--db_port 5432 \
--db_name "ytmonitor" \
--db_username "ytmonitor" \
--db_password "password"'

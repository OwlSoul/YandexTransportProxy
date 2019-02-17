#!/bin/bash

python3 ../ytm_wd \
--verbose 4 \
--url "https://yandex.ru/maps/213/moscow/?ll=37.678948%2C55.772062&masstransit%5BstopId%5D=stop__9643291&mode=stop&z=19" \
--chrome_driver_location "/usr/sbin/chromedriver" \
--wait_time 60 \
--run_once \
--save_to_database \
--db_host "localhost" \
--db_port 5432 \
--db_name "ytmonitor" \
--db_username "ytmonitor" \
--db_password "password"

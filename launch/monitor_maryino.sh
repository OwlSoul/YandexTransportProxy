#!/bin/bash

python3 ../ytm_wd \
--verbose 4 \
--url "https://yandex.ru/maps/213/moscow/?ll=37.745433%2C55.649827&masstransit%5BstopId%5D=stop__9647488&mode=stop&z=17" \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once \
--save_to_database \
--db_host "localhost" \
--db_port 5432 \
--db_name "ytmonitor" \
--db_username "ytmonitor" \
--db_password "password"

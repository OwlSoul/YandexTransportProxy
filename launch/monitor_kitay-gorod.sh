#!/bin/bash

python3 ../ytm_wd \
--verbose 1 \
--station_id "КИТАЙ ГОРОД" \
--url "https://yandex.ru/maps/213/moscow/?ll=37.634676%2C55.754150&masstransit%5BstopId%5D=stop__10187976&mode=stop&z=19" \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once \
--out_mode "plain" \

#!/bin/bash

python3 ../ytm_wd \
--verbose 4 \
--out_mode "csv" \
--url "https://yandex.ru/maps/213/moscow/?ll=37.573801%2C55.848008&masstransit%5BstopId%5D=stop__10182565&mode=stop&z=18" \
--chrome_driver_location "/usr/lib/chromium-browser/chromedriver" \
--wait_time 60 \
--run_once \

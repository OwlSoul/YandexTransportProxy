#!/bin/bash

python3 ../ytm_wd \
--verbose 4 \
--url "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.490358%2C55.930217&masstransit%5BstopId%5D=stop__9898970&mode=stop&z=17" \
--chrome_driver_location "/usr/sbin/chromedriver" \
--wait_time 60 \
--run_once \

#!/usr/bin/env python3

from YandexTransportCore import YandexTransportCore

core = YandexTransportCore()
core.startWebdriver()
data, error = core.getAllInfo(url="https://yandex.ru/maps/213/moscow/?"
                                  "ll=37.589633%2C55.835559&"
                                  "masstransit[routeId]=213_56_trolleybus_mosgortrans&"
                                  "masstransit[stopId]=stop__9639753&"
                                  "masstransit[threadId]=213A_56_trolleybus_mosgortrans&"
                                  "mode=stop&"
                                  "z=14")
for line in data:
    print(line)
    print("")
core.stopWebdriver()
exit()
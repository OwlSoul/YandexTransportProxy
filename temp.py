def getStopLiveInfo(self, stop_data):
    """
    Get a live info for the stop, like in classic version. Suitable for passing to stop indicators or whatever.
    :param stop_data: JSO
    :return: list of routes
    """
    routes_list = []
    if 'data' in stop_data[0]:
        if 'properties' in stop_data[0]['data']:
            if 'StopMetaData' in stop_data[0]['data']['properties']:
                if 'Transport' in stop_data[0]['data']['properties']['StopMetaData']:
                    for record in stop_data[0]['data']['properties']['StopMetaData']['Transport']:
                        record_dic = {}
                        # Route name
                        if 'name' in record:
                            record_dic['name'] = record['name']
                        # Route type
                        if 'type' in record:
                            record_dic['type'] = record['type']
                        # Route frequency
                        if 'BriefSchedule' in record:
                            if 'Frequency' in record['BriefSchedule']:
                                if 'value' in record['BriefSchedule']['Frequency']:
                                    record_dic['frequency'] = int(record['BriefSchedule']['Frequency']['value']) // 60
                        # Append to result
                        routes_list.append(record_dic)

    return routes_list


def getVehiclesCount(self, vehicles_data):
    """
    Counts vehicles on the route
    :param vehicles_data: JSON from getVehiclesInfo
    :return:
    """
    vehicles_count = 0
    if 'data' in vehicles_data[0]:
        for record in vehicles_data[0]['data']:
            # Basically it's just size of vehicles_data[0]['data'], but just to be sure.
            if 'VehicleMetaData' in record['properties']:
                vehicles_count += 1

    return vehicles_count


# ----                                     DATA PARSING FUNCTIONS                                             ---- #

def getStopRoutesList(self, stop_data):
    """
    Get a list of routes passing through this stop
    :param stop_data: JSON from getStopInfo
    :return: list of dictionaries, each consisting of id, lineId, name and type
    """
    routes_list = []
    if 'data' in stop_data[0]:
        if 'properties' in stop_data[0]['data']:
            if 'StopMetaData' in stop_data[0]['data']['properties']:
                if 'Transport' in stop_data[0]['data']['properties']['StopMetaData']:
                    for record in stop_data[0]['data']['properties']['StopMetaData']['Transport']:
                        record_dic = {}
                        if 'id' in record:
                            record_dic['id'] = record['id']
                        if 'lineId' in record:
                            record_dic['lineId'] = record['lineId']
                        if 'name' in record:
                            record_dic['name'] = record['name']
                        if 'type' in record:
                            record_dic['type'] = record['type']
                        routes_list.append(record_dic)

    return routes_list


# data = open("outdata/route_368.json").read()
# res = json.loads(data)
# url = "https://yandex.ru/maps/213/moscow/?ll=37.482033%2C55.851181&masstransit%5BrouteId%5D=213_6_trolleybus_mosgortrans&masstransit%5BstopId%5D=stop__9649585&masstransit%5BthreadId%5D=213A_6_trolleybus_mosgortrans&mode=stop&z=14"
# url = "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.493664%2C55.926349&masstransit%5BrouteId%5D=2037268552&masstransit%5BstopId%5D=stop__9680286&masstransit%5BthreadId%5D=2037276854&mode=stop&z=16"

# res = self.getVehiclesInfo(url)
# print(res)
# print(json.dumps(res, sort_keys=True, indent=4, separators=(',', ': ')))
# veh_cnt = self.getVehiclesCount(res)
# print("Vehicles count =", veh_cnt)

data = open("outdata/dormitory.json").read()
res = json.loads(data)
routes = self.getStopLiveInfo(res)
for route in routes:
    print(route)
    print()
# print(json.dumps(res, sort_keys=True, indent=4, separators=(',', ': ')))
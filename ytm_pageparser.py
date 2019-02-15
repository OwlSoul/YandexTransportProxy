#!/usr/bin/env python3

from bs4 import BeautifulSoup
import re
import psycopg2
import datetime

class PageParser:

    # Filename to parse
    _filename=''

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    # Data returned by parser, tuple of CSV-formatted string
    _data=()

    @property
    def data(self):
        return self._data

    def __init__(self):
        pass

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        """Parse the file, will return tuple of tuples containing the result, and will
           also save the result to data variable (as tuple of tuples)

           Result format:
           (sequence_number,transit_route,transit_type,transit_frequency,prognosis,prognosis_more)

           Currently only up to two prognosis values are available.
           If prognosis data is available, usually no "transit_frequency" data is present.
        """
        f = open(parser.filename, "r")

        soup=BeautifulSoup(f, "lxml")

        cnt = 1
        rows = soup.find_all("div", {"class": "masstransit-stop-panel-view__row"})
        for row in rows:
            # Transit number
            query = row.find('a', {"class": "masstransit-stop-panel-view__vehicle-name"})
            if query is not None:
                transit_number = query.string.replace(u'\xa0', u' ')
            else:
                transit_number = ""

            # Transit type
            query = row.find("div", {"class": "masstransit-icon"})
            result = re.match(r'.*_type_([^ ]+) *.*', str(query))
            transit_type = result.group(1)

            # Bus frequency
            query = row.find("span", {"class": "masstransit-prognoses-view__frequency-time-value"})
            if query is not None:
                transit_frequency = query.string.replace(u'\xa0', u' ')
            else:
                transit_frequency = ""

            # Transit prognosis
            query = row.find_all("span", {"class": "prognosis-value"})
            transit_prognosis = ""
            transit_prognosis_more = ""
            if query is not None:
                line_cnt = 0
                for line in query:
                    if line_cnt==0:
                        transit_prognosis = line.string.replace(u'\xa0', u' ')
                    else:
                        transit_prognosis_more += line.string.replace(u'\xa0', u' ')+"/"
                    line_cnt += 1

                if line_cnt > 1:
                    transit_prognosis_more = transit_prognosis_more[:-1]

            # Saving the result
            #dataline = str(cnt)+"," + \
            #           transit_number + "," + \
            #           transit_type+"," + \
            #           transit_frequency + "," + \
            #           transit_prognosis
            #self._data = self._data_csv + (dataline,)
            datatuple = (str(cnt), transit_number, transit_type, transit_frequency,
                         transit_prognosis, transit_prognosis_more)
            self._data = self._data + (datatuple,)

            cnt = cnt + 1

        f.close()
        return self._data

    def write_to_database(self, station_id, timestamp, data):
        """Write data to PostgreSQL database."""

        # 1. Connect to database
        try:
            conn = psycopg2.connect(host="127.0.0.1",
                                    database="ytmonitor",
                                    user="ytmonitor",
                                    password="password",
                                    connect_timeout=5)
        except psycopg2.OperationalError as e:
            print("ERROR: " + str(datetime.datetime.now()) +
                  " Unable to connect to database (data_init_from_db)")
            print("ERROR: " + str(datetime.datetime.now()) + " " + str(e))
            return 1
        else:
            if conn is not None:
                cur = conn.cursor()

                # 2. Write data

                query = "INSERT INTO " + \
                        "transit(stop_id, stamp, route, type, " + \
                        "frequency, prognosis, prognosis_more) " + \
                        "VALUES "

                for line in data:
                    subquery = "(" + \
                        "'" + station_id + "'" + ", " + \
                        "TIMESTAMP " + "'" + str(timestamp) + "'" + ", " + \
                        "'" + str(line[1]) + "'" + ", " + \
                        "'" + str(line[2]) + "'" + ", " + \
                        "'" + str(line[3]) + "'" + ", " + \
                        "'" + str(line[4]) + "'" + ", " + \
                        "'" + str(line[5]) + "'" + \
                        ")";
                    query = query + subquery + ", "

                query = query[:-2]+";"
                print(query)

                cur.execute(query)

                """   cur.execute("INSERT INTO "
                                            "transit(stop_id, stamp, route, type, "
                                            "frequency, prognosis, prognosis_more)"
                                            "VALUES "
                                            "("+
                                            "'" + str(station_id) + "'" + ", " +
                                            "TIMESTAMPTZ '"+str(timestamp)+"', "+
                                            "'666'"+", "+
                                            "'test_bus'"+", "+
                                            "'66 мин.'"+", "+
                                            "'12 мин.'"+", "+
                                            "'77 мин.'"+" )")"""


                conn.commit()
                # 3. Disconnect from database
                cur.close()
                conn.close()


if __name__=='__main__':
    parser=PageParser('saves/page-2019-02-14 17:49:45.097074.html')
    parser.parse()
    for line in parser.data:
        print(line)
    timestamp = datetime.datetime.now()
    parser.write_to_database("station_test", timestamp, parser.data)

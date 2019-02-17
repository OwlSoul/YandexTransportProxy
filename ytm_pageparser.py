#!/usr/bin/env python3

"""
Yandex Transport Monitor page parser
"""

import datetime
import re
import psycopg2
from bs4 import BeautifulSoup

class YTMPageParser:
    """
    Yandex Transport Monitor page parser class.
    """

    def __init__(self, filename):
        self.filename = ""
        self.data = ()

        self.db_host = "localhost"
        self.db_port = "5432"
        self.db_name = "ytmonitor"
        self.db_username = "ytmonitor"
        self.db_password = "password"
        self.filename = filename

    def set_database(self,
                     db_host="localhost",
                     db_port="5432",
                     db_name="ytmonitor",
                     db_username="ytmonitor",
                     db_password="password"):
        """
        Set PostgreSQL database settings.
        :param db_host: PostgreSQL database host
        :param db_port: PostgreSQL database port
        :param db_name: PostgreSQL database name
        :param db_username: PostgreSQL database username
        :param db_password: PostgreSQL database password
        :return:
        """
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_username = db_username
        self.db_password = db_password


    def parse(self):
        """Parse the file, will return tuple of tuples containing the result, and will
           also save the result to data variable (as tuple of tuples)

           Result format:
           (sequence_number,transit_route,transit_type,transit_frequency,prognosis,prognosis_more)

           Currently only up to two prognosis values are available.
           If prognosis data is available, usually no "transit_frequency" data is present.
        """
        file = open(self.filename, "r", encoding="utf-8")

        soup = BeautifulSoup(file, "lxml", from_encoding="utf-8")

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
                    if line_cnt == 0:
                        transit_prognosis = line.string.replace(u'\xa0', u' ')
                    else:
                        transit_prognosis_more += line.string.replace(u'\xa0', u' ')+"/"
                    line_cnt += 1

                if line_cnt > 1:
                    transit_prognosis_more = transit_prognosis_more[:-1]

            # Saving the result
            datatuple = (str(cnt), transit_number, transit_type, transit_frequency,
                         transit_prognosis, transit_prognosis_more)
            self.data = self.data + (datatuple,)

            cnt = cnt + 1

        file.close()
        return self.data

    def write_to_database(self, station_id, timestamp, data):
        """Write data to PostgreSQL database."""

        # 1. Connect to database
        try:
            conn = psycopg2.connect(host=self.db_host,
                                    port=self.db_port,
                                    database=self.db_name,
                                    user=self.db_username,
                                    password=self.db_password,
                                    connect_timeout=10)
        # pylint: disable=C0103
        except psycopg2.OperationalError as e:
            print("ERROR: " + str(datetime.datetime.now()) +
                  " Unable to connect to database (data_init_from_db)")
            print("ERROR: " + str(datetime.datetime.now()) + " " + str(e))
            return 1
        # pylint: enable=C0103
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
                        ")"
                    query = query + subquery + ", "

                query = query[:-2]+";"

                cur.execute(query)
                conn.commit()

                # 3. Disconnect from database
                cur.close()
                conn.close()
        return 0


if __name__ == '__main__':
    print("Do not run this on its own!")

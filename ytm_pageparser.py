#!/usr/bin/env python3

"""
Yandex Transport Monitor page parser
"""

# String Quotation Policy
# The string quotation policy is as follows:
#  - Strings which are visible to end user should be double-quoted (print, log).
#  - Strings which are "internal", such as values, dictionary keys etc. are single-quoted.
#  - Do not mix single-quoted and double-quoted strings in one statement.
#  - Since SQL queries usually contain single-quotes, it's better to put the whole query
#    in double quotes.

import datetime
import re
import psycopg2
from bs4 import BeautifulSoup

class YTMPageParser:
    """
    Yandex Transport Monitor page parser class.
    """

    def __init__(self, filename):
        self.filename = ''
        self.data = ()

        self.db_host = 'localhost'
        self.db_port = '5432'
        self.db_name = 'ytmonitor'
        self.db_username = 'ytmonitor'
        self.db_password = 'password'
        self.filename = filename

    def set_database(self,
                     db_host='localhost',
                     db_port='5432',
                     db_name='ytmonitor',
                     db_username='ytmonitor',
                     db_password='password'):
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
        file = open(self.filename, 'r', encoding='utf-8')

        soup = BeautifulSoup(file, 'lxml', from_encoding='utf-8')

        cnt = 1
        rows = soup.find_all('div', {'class': 'masstransit-stop-panel-view__vehicle-row'})
        for row in rows:
            # Getting transit route number
            query = row.find('div', {'class': 'masstransit-stop-panel-view__vehicle-name'})
            if query is not None:
                transit_number = query.string.replace(u'\xa0', u' ')
            else:
                transit_number = ''

            # Getting transit type
            query = row.find('div', {'class': 'masstransit-stop-panel-view__vehicle-type'})
            if query is not None:
                transit_type = query.string.replace(u'\xa0', u' ')
            else:
                transit_type = ''
            #query = row.find('div', {'class': 'masstransit-icon'})
            #result = re.match(r'.*_type_([^ ]+) *.*', str(query))
            #transit_type = result.group(1)

            # Bus frequency
            query = row.find('span', {'class': 'masstransit-prognoses-view__frequency-time-value'})
            if query is not None:
                transit_frequency = query.string.replace(u'\xa0', u' ')
            else:
                transit_frequency = ''
            # Recalculate to minutes
            query = transit_frequency.split(u' ')
            if len(query) >= 2:
                value = int(query[0])
                units = query[1]
                if units=='ч':
                    transit_frequency = str(value*60)
                else:
                    transit_frequency = str(value)

            # Transit prognosis
            query = row.find('span', {'class': 'masstransit-prognoses-view__less-hour'})
            transit_prognosis = ''
            transit_prognosis_more = ''
            if query is not None:
                data = query.string.replace(u'\xa0', u' ')
                # Things were so much easier before...
                # Splitting prognosis and prognosis_more
                data = data.replace(u',', u'').split(u' ')
                units = data[-1]
                prognosis = data[0]
                prognosis_more = data[1:-1]
                # Converting to output format
                transit_prognosis = str(prognosis)
                for i in range(0, len(prognosis_more)-1):
                    transit_prognosis_more += str(prognosis_more[i])+', '
                # Adding the last element
                if len(prognosis_more) >= 1:
                    transit_prognosis_more += str(prognosis_more[-1])

            # Amazing new things!
            # Expected exact times of next departures!
            query = row.find('span', {'class': 'masstransit-prognoses-view__more-hour'})
            transit_departures = ''
            if query is not None:
                transit_departures = query.string.replace(u'\xa0', u' ')

            # Saving the result
            data_tuple = (str(cnt), transit_number, transit_type, transit_frequency,
                          transit_prognosis, transit_prognosis_more, transit_departures)
            self.data = self.data + (data_tuple,)

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
                  " Unable to connect to database (method: write_to_database)")
            print("ERROR: " + str(datetime.datetime.now()) + " " + str(e))
            return 1
        # pylint: enable=C0103
        else:
            if conn is not None:
                cur = conn.cursor()

                # 2. Write data

                query = "INSERT INTO " + \
                        "transit(stop_id, stamp, route, type, " + \
                        "frequency, prognosis, prognosis_more," \
                        "departures) " + \
                        "VALUES "

                for line in data:
                    subquery = "(" + \
                        "'" + station_id + "'" + ", " + \
                        "TIMESTAMP " + "'" + str(timestamp) + "'" + ", " + \
                        "'" + str(line[1]) + "'" + ", " + \
                        "'" + str(line[2]) + "'" + ", " + \
                        "'" + str(line[3]) + "'" + ", " + \
                        "'" + str(line[4]) + "'" + ", " + \
                        "'" + str(line[5]) + "'" + ", " + \
                        "'" + str(line[6]) + "'" + \
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

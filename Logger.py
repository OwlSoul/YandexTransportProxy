import sys
import datetime

class Logger:
    # Logging levels
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4

    def __init__(self, log_level):
        self.verbose = log_level

    def log(self, log_level, text):
        """
        Log data to stderr
        :param log_level: log level, see Application.LOG_SOMETHING constants.
        :param text: text to print
        :return: nothing
        """
        timestamp = '['+str(datetime.datetime.now())+']'
        if log_level == self.ERROR:
            if self.verbose >= self.ERROR:
                print("ERROR :", timestamp, ":", str(text), file=sys.stderr)
                return

        if log_level == self.WARNING:
            if self.verbose >= self.WARNING:
                print("WARN  :", timestamp, ":", str(text), file=sys.stderr)
                return

        if log_level == self.INFO:
            if self.verbose >= self.INFO:
                print("INFO  :", timestamp, ":", str(text), file=sys.stderr)
                return

        if log_level == self.DEBUG:
            if self.verbose >= self.DEBUG:
                print("DEBUG :", timestamp, ":", str(text), file=sys.stderr)
                return

    def error(self, text):
        self.log(self.ERROR, text)

    def warning(self, text):
        self.log(self.WARNING, text)

    def info(self, text):
        self.log(self.INFO, text)

    def debug(self, text):
        self.log(self.DEBUG, text)
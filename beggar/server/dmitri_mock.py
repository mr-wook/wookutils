#!/bin/env python3

if True:
    import logging


# This is heinous
LOG_FORMAT = '%(levelname)s %(asctime)s %(message)s'
logging.basicConfig(filename='dmitri_script_mock.log', filemode='w',
                    level=logging.DEBUG, format=BasicClient.LOG_FORMAT)

# Should these be in separate message module?
class GetMessage:
    def __init__(self, message_type = "project"):
        self._message_type = message_type


class Message:
    @staticmethod
    def message():
        pass

# Export to a class, try each flavor
class BasicClient:

    LOGGERS = { logging.INFO: logging.info, logging.DEBUG: logging.debug,
                logging.WARNING: logging.warning, logging.ERROR: logging.error,
                logging.CRITICAL: logging.critical, logging.FATAL: logging.fatal }

    def Log(self, msg, level = logging.INFO):
        if level not in BasicClient.LOGGERS:
            return logging.debug(msg)
        lgr = BasicClient.LOGGERS(level)
        return lgr(msg)

import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


#
# import os.path
# import logging
# import traceback
#
# from logging import DEBUG, WARNING, ERROR, INFO


# class Logger(object):
#     show_source_location = True
#
#     # Formats the message as needed and calls the correct logging method
#     # to actually handle it
#     def _raw_log(self, logfn, message, exc_info):
#         cname = ''
#         loc = ''
#         fn = ''
#         tb = traceback.extract_stack()
#         if len(tb) > 2:
#             if self.show_source_location:
#                 loc = '(%s:%d):' % (os.path.basename(tb[-3][0]), tb[-3][1])
#             fn = tb[-3][2]
#             if fn != '<module>':
#                 if self.__class__.__name__ != Logger.__name__:
#                     fn = self.__class__.__name__ + '.' + fn
#                 fn += '()'
#
#         logfn(loc + cname + fn + ': ' + message, exc_info=exc_info)
#
#     def info(self, message, exc_info=False):
#         """
#         Log a info-level message. If exc_info is True, if an exception
#         was caught, show the exception information (message and stack trace).
#         """
#         self._raw_log(logging.info, message, exc_info)
#
#     def debug(self, message, exc_info=False):
#         """
#         Log a debug-level message. If exc_info is True, if an exception
#         was caught, show the exception information (message and stack trace).
#         """
#         self._raw_log(logging.debug, message, exc_info)
#
#     def warning(self, message, exc_info=False):
#         """
#         Log a warning-level message. If exc_info is True, if an exception
#         was caught, show the exception information (message and stack trace).
#         """
#         self._raw_log(logging.warning, message, exc_info)
#
#     def error(self, message, exc_info=False):
#         """
#         Log an error-level message. If exc_info is True, if an exception
#         was caught, show the exception information (message and stack trace).
#         """
#         self._raw_log(logging.error, message, exc_info)
#
#     @staticmethod
#     def basicConfig(level=DEBUG):
#         """
#         Apply a basic logging configuration which outputs the log to the
#         console (stderr). Optionally, the minimum log level can be set, one
#         of DEBUG, WARNING, ERROR (or any of the levels from the logging
#         module). If not set, DEBUG log level is used as minimum.
#         """
#         logging.basicConfig(level=level,
#             format='%(asctime)s %(levelname)s: %(message)s '
#     '[in %(pathname)s:%(lineno)d]',
#             datefmt='%Y-%m-%d %H:%M:%S')
#
# logger = Logger()
#
# if __name__ == '__main__':
#     # Run the code from examples
#     import doctest
#     doctest.testmod()
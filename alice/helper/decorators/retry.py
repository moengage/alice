import sys
import time
from functools import wraps
import logging

class Retry(object):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def __init__(self, exceptions_to_catch, max_retries=2, default_value=None, after=0):
        self.max_retries = max_retries
        self.default_value = default_value
        self.exceptions_to_catch = exceptions_to_catch if exceptions_to_catch else Exception
        self.after = float(after)


    def __call__(self, func):
        @wraps(func)
        def retries(*args, **kwargs):
            return_value = self.default_value
            for i in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except self.exceptions_to_catch:
                    if i == self.max_retries - 1 and self.default_value is None:
                        raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                    time.sleep(self.after)
                    #self.logger.info(task=func.__name__, message="retrying function")
                    # logger.debug(task=func.__name__, message="retrying function",
                    #                retry_cause=CommonUtils.view_traceback())
            return return_value

        return retries

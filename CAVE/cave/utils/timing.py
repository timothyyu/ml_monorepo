from functools import wraps
from time import time
import logging


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        logger = logging.getLogger("cave.timer")
        ts = time()
        result = f(*args, **kw)
        te = time()
        # logger.debug('func:%r args:[%r, %r] took: %2.4f sec' % \
        logger.debug('func:%r took: %2.4f sec' % (f.__name__, te-ts))
        return result
    return wrap

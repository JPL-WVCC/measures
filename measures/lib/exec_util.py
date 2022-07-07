#!/usr/bin/env python
import os, sys, logging, traceback
from subprocess import check_call


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


def exec_wrapper(func):
    """Execution wrapper to dump alternate errors and tracebacks."""

    def wrapper(*args, **kwargs):
        try: status = func(*args, **kwargs)
        except Exception as e:
            with open('_alt_error.txt', 'w') as f:
                f.write("%s\n" % str(e))
            with open('_alt_traceback.txt', 'w') as f:
                f.write("%s\n" % traceback.format_exc())
            raise
        sys.exit(status)

    return wrapper


def call_noerr(cmd, logr=logger):
    """Run command and warn if exit status is not 0."""

    try: check_call(cmd, shell=True)
    except Exception as e:
        logr.warn("Got exception running {}: {}".format(cmd, str(e)))
        logr.warn("Traceback: {}".format(traceback.format_exc()))

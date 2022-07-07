#!/usr/bin/env python
import os, json, logging, traceback

from os_util import norm_path


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class JobContextError(Exception):
    """Exception class for JobContext class."""
    pass


class JobContext(object):
    """Job context class."""

    def __init__(self, file):
        """Construct JobContext instance."""

        logger.info("file: {}".format(file))
        self._file = file
        with open(self._file) as f:
            self._ctx = json.load(f)

    @property
    def file(self):
        return self._file

    @property
    def ctx(self):
        return self._ctx

    def get(self, key):
        try:
            return self._ctx[key]
        except KeyError as e:
            raise(JobContextError("Context '{}' doesn't exist in {}.".format(key, self._file)))


class DockerParamsError(Exception):
    """Exception class for DockerParams class."""
    pass


class DockerParams(object):
    """Job context class."""

    def __init__(self, file):
        """Construct DockerParams instance."""

        logger.info("file: {}".format(file))
        self._file = file
        with open(self._file) as f:
            self._params = json.load(f)

    @property
    def file(self):
        return self._file

    @property
    def params(self):
        return self._params

    def get(self, key):
        try:
            return self._params[key]
        except KeyError as e:
            raise(DockerParamsError("Docker params '{}' doesn't exist in {}.".format(key, self._file)))

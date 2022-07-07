#!/usr/bin/env python
import os, yaml, logging, traceback

from os_util import norm_path


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class YamlConfError(Exception):
    """Exception class for YamlConf class."""
    pass


class YamlConf(object):
    """YAML configuration class."""

    def __init__(self, file):
        """Construct YamlConf instance."""

        logger.info("file: {}".format(file))
        self._file = file
        with open(self._file) as f:
            self._cfg = yaml.load(f)

    @property
    def file(self):
        return self._file

    @property
    def cfg(self):
        return self._cfg

    def get(self, key):
        try:
            return self._cfg[key]
        except KeyError as e:
            raise(YamlConfError("Configuration '{}' doesn't exist in {}.".format(key, self._file)))


class DatasetVersionConf(YamlConf):
    """Dataset version YAML configuration class."""

    def __init__(self, file=None):
        "Construct DatasetVersionConf instance."""

        if file is None:
            file = norm_path(os.path.join(os.path.dirname(__file__), "..", "..",
                                          "conf", "dataset_version.yaml"))
        super(DatasetVersionConf, self).__init__(file)

   
class SettingsConf(YamlConf):
    """Settings YAML configuration class."""

    def __init__(self, file=None):
        "Construct SettingsConf instance."""

        if file is None:
            file = norm_path(os.path.join(os.path.dirname(__file__), "..", "..",
                                          "conf", "settings.yaml"))
        super(SettingsConf, self).__init__(file)

   
class RunConfig(object):
    """PGE run configuration class."""

    def __init__(self, pge_name, full_pathname, input_filepath, 
                 command_line_params, tmpl=None):
        "Construct RunConfig instance."""

        self._pge_name = pge_name
        self._full_pathname = full_pathname
        self._input_filepath = input_filepath
        self._command_line_params = command_line_params
        if tmpl is None:
            tmpl = norm_path(os.path.join(os.path.dirname(__file__), "..", "..",
                                          "conf", "RunConfig.xml.tmpl"))
        with open(tmpl) as f:
            self._tmpl = f.read()

    def dump(self, output_file):
        """Dump RunConfig to file."""

        rc = self._tmpl.format(PGEName=self._pge_name,
                               FullPathname=self._full_pathname,
                               InputFilePath=self._input_filepath,
                               CommandLineParameters="".join(["<element>{}</element>".format(i) for i in self._command_line_params]))
        with open(output_file, 'w') as f:
            f.write("{}\n".format(rc))

   
if __name__ == "__main__":
    y = DatasetVersionConf()
    cfg = y.cfg
    logger.info("{}".format(cfg))
    logger.info("test")
    cfg['asdf'] = 'test'
    logger.info("{}".format(y.cfg))
    logger.info("{}".format(y.file))
    logger.info("{}".format(y.get('test')))

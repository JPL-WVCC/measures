#!/usr/bin/env python 
"""
Copy CERES data file to S3.
"""

import os, re, json, yaml, logging, traceback, argparse, shutil
from datetime import datetime
from subprocess import check_call
from ftplib import FTP
from urlparse import urlparse

from hysds_commons.job_utils import submit_mozart_job
from hysds.celery import app

from measures.lib.conf_util import DatasetVersionConf, SettingsConf
from measures.lib.exec_util import exec_wrapper, call_noerr
from measures.lib.ctx_util import JobContext


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


BASE_PATH = os.path.dirname(__file__)


@exec_wrapper
def main(id, nc_file):
    """Main."""

    # get configs
    logger.info("called main()")
    ds_cfg = DatasetVersionConf().cfg
    logger.info("ds_cfg: {}".format(json.dumps(ds_cfg, indent=2)))
    cfg = SettingsConf().cfg
    logger.info("cfg: {}".format(json.dumps(cfg, indent=2)))

    # get context
    jc = JobContext('_context.json')
    ctx = jc.ctx
    logger.info("ctx: {}".format(json.dumps(ctx, indent=2)))

    call_noerr("gdal-config --version", logger)
    check_call("gdal-config --version", shell=True)
    #raise(RuntimeError("Failed to get this"))

    # create versioned dataset ID
    ds_version = ds_cfg['CERES_VERSION']
    ds_id = id
    logger.info("ds_id: {}".format(ds_id))

    # get cwd
    cwd = os.getcwd()

    # create dataset directory
    ds_dir = os.path.join(cwd, ds_id)
    os.makedirs(ds_dir, 0755)

    # move file
    ds_nc = os.path.join(ds_dir, "{}.nc".format(ds_id))
    shutil.move(nc_file, ds_nc)

    # get start date and end date
    match = re.search(r'_(\d{4})(\d{2})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})(\d{2})$', id)
    if not match:
        raise RuntimeError("Failed to parse start and end date from id: %s" % id)
    start_yr, start_mo, start_dt, start_hr, end_yr, end_mo, end_dt, end_hr = map(int, match.groups())
    start_min, start_sec = 0, 0
    end_min, end_sec = 59, 59
    start_dt = datetime(start_yr, start_mo, start_dt, start_hr, start_min, start_sec)
    end_dt = datetime(end_yr, end_mo, end_dt, end_hr, end_min, end_sec)

    # enter dataset dir and create dataset/met json files
    os.chdir(ds_dir)
    met_file = os.path.join(ds_dir, "{}.met.json".format(ds_id))
    ds_file = os.path.join(ds_dir, "{}.dataset.json".format(ds_id))
    if ctx['prod_met'] is not None:
        with open(met_file, 'w') as f:
            json.dump(ctx['prod_met'], f, indent=2, sort_keys=True)
    ds_info = {
        "version": ds_version,    
        "creation_timestamp": datetime.utcnow().isoformat('T'),
        "starttime": start_dt.isoformat('T'),
        "endtime": end_dt.isoformat('T'),
        "location": {
            "type": "polygon",
            "coordinates": [
                [
                    [ -180., -90. ],
                    [ -180., 90. ],
                    [ 180., 90. ],
                    [ 180., -90. ],
                    [ -180., -90. ],
                ]
            ]
        }
    }
    with open(ds_file, 'w') as f:
        json.dump(ds_info, f, indent=2, sort_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", help="CERES ID")
    parser.add_argument("nc_file", help="netcdf file")
    args = parser.parse_args()
    main(args.id, args.nc_file)

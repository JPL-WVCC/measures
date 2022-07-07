#!/usr/bin/env python 
"""
Parse email for CERES datasets staged and submit ingest jobs.
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


def submit_job(id, nc_url, nc_file, md=None, job_version='master'):
    """Submit job for CERES ingest."""

    job_spec = "job-ingest-ceres:{}".format(job_version)
    job_name = "%s-%s" % (job_spec, id)
    job_name = job_name.lstrip('job-')

    #Setup input arguments here
    rule = {
        "rule_name": "ingest-ceres",
        "queue": "factotum-job_worker-large",
        "priority": 0,
        "kwargs": '{}'
    }
    params = [
        {   
            "name": "id",
            "from": "value",
            "value": id,
        },
        {   
            "name": "raw_url",
            "from": "value",
            "value": nc_url,
        },
        {   
            "name": "raw_file",
            "from": "value",
            "value": nc_file,
        },
        {   
            "name": "prod_met",
            "from": "value",
            "value": md,
        }
    ]
    logger.info("submitting ingest-ceres job for %s" % id)
    logger.info("job_spec: {}".format(job_spec))
    logger.info("job_name: {}".format(job_name))
    logger.info("md: {}".format(json.dumps(md, indent=2)))
    submit_mozart_job({}, rule,
        hysdsio={"id": "internal-temporary-wiring",
                 "params": params,
                 "job-specification": job_spec},
        job_name=job_name)


@exec_wrapper
def main():
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

    # get email body
    email_body = ctx['email_body']

    # extract ftp dir
    match = re.search(r'(ftp://.*)\.', email_body)
    if not match:
        logger.error("Failed to find ftp url in body: %s" % email_body)
        raise RuntimeError("Failed to find ftp url in body: %s" % email_body)
    ftp_url = match.group(1)
    logger.info("ftp_url: %s" % ftp_url)

    # parse url
    url_comps = urlparse(ftp_url)
    logger.info("url_comps: %s" % str(url_comps))

    # build list of urls of netcdf files
    ftp = FTP(url_comps.netloc)
    ftp.login()
    ftp.set_pasv(True)
    dir_listings = ftp.nlst(url_comps.path)
    nc_urls = []
    logger.info("dir_listings: %s" % dir_listings)
    for dir_listing in dir_listings:
        file_listings = ftp.nlst(dir_listing)
        logger.info("file_listings: %s" % file_listings)
        for file in file_listings:
            if not re.search(r'\.nc$', file):
                logger.info("Skipping %s." % file)
                continue
            nc_url = 'ftp://%s%s' % (url_comps.netloc, os.path.normpath(file))
            #local_path = os.path.basename(file)
            #logger.info("Starting download of %s to %s." % (file, local_path))
            #ftp.retrbinary('RETR %s' % file, open(local_path, 'wb').write)
            #logger.info("Finished downloading %s to %s." % (file, local_path))
            nc_urls.append(nc_url)
    ftp.quit()
    logger.info("nc_urls: %s" % nc_urls)

    # submit jobs
    for nc_url in nc_urls:
        nc_file = os.path.basename(nc_url)
        id = os.path.splitext(nc_file)[0]
        submit_job(id, nc_url, nc_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    main()

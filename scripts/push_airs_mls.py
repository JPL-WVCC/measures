#!/usr/bin/env python 
"""
Query for AIRS-MLS matchup and joined files and submit conversion jobs.
"""

import os, re, json, yaml, logging, traceback, argparse, shutil
import boto3, botocore
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


def submit_job(mat_url, joined_url, job_version='master'):
    """Submit job for AIRS-MLS conversion."""

    job_spec = "job-convert_airs_mls:{}".format(job_version)
    job_name = "%s-%s" % (job_spec, os.path.basename(mat_url))
    job_name = job_name.lstrip('job-')

    #Setup input arguments here
    rule = {
        "rule_name": "convert_airs_mls",
        "queue": "msas-job_worker-large",
        "priority": 0,
        "kwargs": '{}'
    }
    params = [
        {   
            "name": "mat_url",
            "from": "value",
            "value": mat_url,
        },
        {   
            "name": "mat_file",
            "from": "value",
            "value": os.path.basename(mat_url),
        },
        {   
            "name": "joined_url",
            "from": "value",
            "value": joined_url,
        },
        {   
            "name": "joined_file",
            "from": "value",
            "value": os.path.basename(joined_url),
        }
    ]
    logger.info("submitting convert_airs_mls job for %s and %s" % (mat_url, joined_url))
    logger.info("job_spec: {}".format(job_spec))
    logger.info("job_name: {}".format(job_name))
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

    # submit jobs for each mat file
    bucket_name = "wvcc-atrain-product-bucket"
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix="airs_mls/ind/").page_size(100):
        mat_url = "s3://s3.amazonaws.com:80/%s/%s" % (bucket_name, obj.key)
        joined_url = mat_url.replace('/ind/', '/joined/').replace('.mat', '_joined.mat')
        submit_job(mat_url, joined_url)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    main()

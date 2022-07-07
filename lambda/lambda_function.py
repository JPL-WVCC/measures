from __future__ import print_function

import os, sys, re, json, base64, requests, boto3
from utils import submit_job

print ('Loading function')


def lambda_handler(event, context):
    '''
    This lambda handler calls submit_job with the job type info
    and product id from the sns message
    '''

    print("Got event of type: %s" % type(event))
    print("Got event: %s" % json.dumps(event))
    print("Got context: %s"% context)
    
    # parse sns message
    msg = json.loads(event["Records"][0]["Sns"]["Message"])
    print("Message: %s" % json.dumps(msg))

    # parse base64 content
    content = base64.b64decode(msg['content'])
    print("Content: %s" % content)

    #return content
    
    #submit mozart jobs to parse incoming email
    job_type = os.environ['JOB_TYPE'] # "INGEST_L0A_LR_RAW"
    job_release = os.environ['JOB_RELEASE'] # "gman-dev"
    job_spec = "job-%s:%s" % (job_type, job_release)
    job_params = {
        "email_body": content
    }
    queue = "factotum-job_worker-small"
    tags = ["incoming-ceres"]

    # submit mozart job
    submit_job(job_spec, job_params, queue, tags)

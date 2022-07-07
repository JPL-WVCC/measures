from __future__ import print_function

import os, json, requests


# get mozart rest api url from environ
# should be something like this http://<mozart pvt ip>:8888
# or https://<mozart pvt ip>/mozart
if 'MOZART_URL' not in os.environ:
    raise RuntimeError("Need to specify MOZART_URL in environment.")
MOZART_URL = os.environ['MOZART_URL']
JOB_SUBMIT_URL = '%s/api/v0.1/job/submit' % MOZART_URL


def submit_job(job_spec, job_params, queue, tags=[], priority=0):
    """Submit job to mozart via REST API."""
    
    # setup params
    params = {
        'queue': queue,
        'priority': priority,
        'tags': json.dumps(tags),
        'type': job_spec,
        'params': json.dumps(job_params),
    }
    
    # submit job
    print("Job params: %s" % json.dumps(params))
    req = requests.post(JOB_SUBMIT_URL, data=params, verify=False)
    print("Request code: %s"% req.status_code)
    print("Result: %s"% req.json())
    if req.status_code != 200:
        req.raise_for_status()
    result = req.json()
    if 'result' in result.keys() and 'success' in result.keys():
        if result['success'] is True:
            job_id = result['result']
            print('submitted job: %s job_id: %s' % (job_spec, job_id))
        else:
            print('job not submitted successfully: %s' % result)
            raise Exception('job not submitted successfully: %s' % result)
    else:
        raise Exception('job not submitted successfully: %s' % result)
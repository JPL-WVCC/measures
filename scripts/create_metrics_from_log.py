#!/usr/bin/env python
import os, sys, json, re

from measures import app


METRICS_RE = re.compile(r'^METRICS\s+.*?\s+payload:(.*?):(.+)$')


def main():
    # metrics log and json
    metrics_log_file = sys.argv[1]
    metrics_json_file = sys.argv[2]

    # make sure log file exists
    if not os.path.exists(metrics_log_file):
        raise(RuntimeError("Failed to find %s." % metrics_log_file))
   
    # open json file
    metrics_json = {}
    with open(metrics_log_file) as f:
        for i in f:
            match = METRICS_RE.search(i)
            if match:
                k, payload = match.groups()
                metrics_json.setdefault(k, []).append(json.loads(payload))            

    # dump metrics
    with open(metrics_json_file, 'w') as f:
        json.dump(metrics_json, f, indent=2)


if __name__ == "__main__":
    main()

#!/bin/bash

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 1 ]; then
  airs_dap_url=$1
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run matchup
$HOME/verdi/ops/measures/scripts/generate_airs_cloudsat_matchup.py $airs_dap_url 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_cloudsat_matchup.py." 1>&2
  exit 1
fi

# create metrics json
if [ -f "pge_metrics.log" ]; then
  $HOME/verdi/ops/measures/scripts/create_metrics_from_log.py pge_metrics.log pge_metrics.json 1>&2
  if [ "$?" -ne 0 ]; then
    echo "Failed to run create_metrics_from_log.py." 1>&2
    exit 1
  fi
fi

# print product
product_dir=`ls -d ./index-airs.aqua_cloudsat-v?.?-????.??.??.???`
echo $product_dir

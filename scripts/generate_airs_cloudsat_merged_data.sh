#!/bin/bash

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 2 ]; then
  matchup_file=$1
  varlist_json_file=$2
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run matchup
$HOME/verdi/ops/measures/scripts/generate_airs_cloudsat_merged_data.py $matchup_file $varlist_json_file 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_cloudsat_merged_data.py." 1>&2
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
product_dir=`ls -d ./matched-airs.aqua_cloudsat-v?.?-????.??.??.???`
echo $product_dir

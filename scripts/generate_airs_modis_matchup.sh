#!/bin/bash

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 1 ]; then
  hdf_file=$1
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run product generation
$HOME/verdi/ops/measures/scripts/generate_airs_modis_matchup.py $hdf_file $varlist_json_file 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_modis_matchup.py." 1>&2
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
product_dir=`ls -d ./index-airs.aqua_modis.aqua-v?.?-????.??.??.????`
echo $product_dir

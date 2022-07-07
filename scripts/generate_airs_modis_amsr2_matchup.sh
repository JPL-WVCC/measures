#!/bin/bash

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 3 ]; then
  amsr2_file=$1
  airs_modis_file=$2
  airs_modis_met=$3
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run product generation
$HOME/verdi/ops/measures/scripts/generate_airs_modis_amsr2_matchup.py \
  --map_global --amsr2_file=${amsr2_file} --airs_modis_file=${airs_modis_file} \
  --airs_modis_met=${airs_modis_met} 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_modis_amsr2_matchup.py." 1>&2
  exit 1
fi

# create metrics json
#if [ -f "pge_metrics.log" ]; then
#  $HOME/verdi/ops/measures/scripts/create_metrics_from_log.py pge_metrics.log pge_metrics.json 1>&2
#  if [ "$?" -ne 0 ]; then
#    echo "Failed to run create_metrics_from_log.py." 1>&2
#    exit 1
#  fi
#fi

# print product
#product_dir=`ls -d ./index-airs.aqua_modis.aqua-v?.?-????.??.??.????`
#echo $product_dir

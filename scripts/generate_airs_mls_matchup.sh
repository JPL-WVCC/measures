#!/bin/bash

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 2 ]; then
  mat_file=$1
  joined_file=$2
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run product generation
$HOME/verdi/ops/measures/scripts/generate_airs_mls_matchup.py $mat_file $joined_file 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_mls_matchup.py." 1>&2
  exit 1
fi

# print product
product_dir=`ls -d ./index-airs.aqua_mls.aura-v?.?-????.??.??`
echo $product_dir

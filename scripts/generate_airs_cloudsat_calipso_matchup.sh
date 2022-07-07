#!/bin/bash
# Usage:
# rm -rf index-airs.aqua_cloudsat-v4.0-2006.12.25.001; ./generate_airs_cloudsat_calipso_matchup.sh ~/verdi/ops/measures/scripts/index-airs.aqua_cloudsat-v4.0-2006.12.25.001.nc4 http://cvo.hysds.net:8080/opendap/caliop.calipso/333mCLay

# source environment
source $HOME/verdi/bin/activate

# create task
if [ "$#" -eq 2 ]; then
  airs_cloudsat_file=$1
  calipso_dap_url_base=$2
else
  echo "Invalid number of arguments ($#): $*" 1>&2
  exit 1
fi

# run matchup
$HOME/verdi/ops/measures/scripts/generate_airs_cloudsat_calipso_matchup.py \
  $airs_cloudsat_file $calipso_dap_url_base 1>&2
if [ "$?" -ne 0 ]; then
  echo "Failed to run generate_airs_cloudsat_calipso_matchup.py." 1>&2
  exit 1
fi

# print product
product_dir=`ls -d ./index-airs.aqua_cloudsat_caliop.calipso-v?.?-????.??.??.???`
echo $product_dir

#!/bin/bash
BASE_PATH=$(dirname "${BASH_SOURCE}")
BASE_PATH=$(cd "${BASE_PATH}"; pwd)

# source PGE env
export MSAS_HOME=$(dirname "${BASE_PATH}")
#source $MSAS_HOME/msas.sh
#export COMMONS_HOME=$MSAS_HOME/commons
export PYTHONPATH=$BASE_PATH:$MSAS_HOME:$PYTHONPATH
export PATH=$BASE_PATH:$PATH
#export PGE=$(basename "${BASE_PATH}")

# source environment
source $HOME/verdi/bin/activate

echo "##########################################" 1>&2
echo -n "Running push_airs_mls.py: " 1>&2
date 1>&2
$BASE_PATH/push_airs_mls.py $* > push_airs_mls.log 2>&1
STATUS=$?
echo -n "Finished running push_airs_mls.py: " 1>&2
date 1>&2
if [ $STATUS -ne 0 ]; then
  echo "Failed to run push_airs_mls.py." 1>&2
  cat push_airs_mls.log 1>&2
  echo "{}"
  exit $STATUS
fi

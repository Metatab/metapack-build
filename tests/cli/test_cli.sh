#!/bin/bash

set -e

# http://tldp.org/LDP/abs/html/debugging.html
#######################################################################
assert ()                 #  If condition false,
{                         #+ exit from script
                          #+ with appropriate error message.
  E_PARAM_ERR=98
  E_ASSERT_FAILED=99


  if [ -z "$2" ]          #  Not enough parameters passed
  then                    #+ to assert() function.
    return $E_PARAM_ERR   #  No damage done.
  fi

  lineno=$2

  if [ ! $1 ]
  then
    echo "Assertion failed:  \"$1\""
    echo "File \"$0\", line $lineno"    # Give name of file and line number.
    exit $E_ASSERT_FAILED
  # else
  #   return
  #   and continue executing the script.
  fi
} # Insert a similar assert() function into a script you need to debug.


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR

rm -rf _test && mkdir _test && cd _test

##
## example.com-dataset-2019-ca-test
##

# Create and set title
mp new -o example.com -d dataset -t 2019 -s CA -v test

assert "-d example.com-dataset-2019-ca-test" $LINENO

cd example.com-dataset-2019-ca-test

assert "'$(mp info)' = 'example.com-dataset-2019-ca-test-1'" $LINENO

mp edit change Root.Title 'Dataset Title'

mp edit add Resources.Root.Datafile 'http://public.source.civicknowledge.com/example.com/sources/test_data.zip#unicode-latin1.csv&encoding=latin1' \
    -aName=unicode-latin1 \
    -a'Description=Unicode names file, convered to latin1'


# Update version number
mp edit change Root.Version '2'

mp update -n

assert "'$(mp info)' = 'example.com-dataset-2019-ca-test-2'" $LINENO

# Check schema
mp update -s
mp update -A

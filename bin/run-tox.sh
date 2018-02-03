set -ex

SCRIPT_PATH=$( cd $(dirname $0) ; pwd -P)
SRC_PATH=$( cd $(dirname $(dirname $0 )) ; pwd -P )

if [ -d $SRC_PATH/output ]; then
    rm -rf $SRC_PATH/output
fi
if [ -d $SRC_PATH/docs/_build ]; then
    rm -rf $SRC_PATH/docs/_build
fi

mkdir -p $SRC_PATH/docs/_build
chmod 777 $SRC_PATH/docs/_build

mkdir -p $SRC_PATH/output
chmod 777 $SRC_PATH/output


docker run --rm -v $SRC_PATH:/src brewtils:test

#!/bin/bash

xhost +localhost
xhost +192.168.64.1

docker run -ti -e DISPLAY=host.docker.internal:0 -e LSST_DDS_PARTITION_PREFIX=test -v /tmp/.X11-unix:/tmp/.X11-unix:rw lsstts/develop-env:develop $*

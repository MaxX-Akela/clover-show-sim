#!/bin/bash
SRC=/px4
if [ -f "$SRC/etc/init.d-posix/rcS" ]; then
    echo modern
elif [ -f "$SRC/ROMFS/px4fmu_common/mixers/quad_w.main.mix" ]; then
    echo 1.8
else
    echo none
fi

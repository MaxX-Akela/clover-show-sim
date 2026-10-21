#!/bin/bash
set -eu
: "${DRONE_ID:?}"
SRC=/px4
RUN=/run/px4-etc
SIM_RC="$SRC/etc/init.d-posix/px4-rc.simulator"

[ -x "$SRC/bin/px4" ] && [ -f "$SIM_RC" ] || { echo "ОШИБКА: в $SRC нет сборки PX4 SITL (bin/px4, etc/init.d-posix)"; exit 1; }

if grep -q simulator_mavlink "$SIM_RC"; then
    BRANCH=1.14
elif grep -qE 'simulator start' "$SIM_RC"; then
    BRANCH=1.13
else
    echo "ОШИБКА: не удалось определить ветку PX4 по $SIM_RC"; exit 1
fi
echo "PX4 ветка: $BRANCH"

rm -rf "$RUN"
cp -a "$SRC/etc" "$RUN"
cp "/opt/clover-show/airframes/$BRANCH/4500_clover" "$RUN/init.d-posix/airframes/4500_clover"

mkdir -p /px4data
cd /px4data
export PX4_SIM_MODEL=clover
export PX4_ESTIMATOR=ekf2
export PX4_SIM_HOST_ADDR=127.0.0.1
export CLOVER_SHOW_SYS_ID="$DRONE_ID"
exec "$SRC/bin/px4" -d "$RUN" -s etc/init.d-posix/rcS -i 0

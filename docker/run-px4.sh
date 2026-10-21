#!/bin/bash
set -eu
: "${DRONE_ID:?}"
SRC=/px4
RUN=/run/px4-etc
AIRFRAMES=/opt/clover-show/airframes

mkdir -p /px4data
cd /px4data

if [ "$(/opt/clover-show/px4-branch.sh)" = 1.8 ]; then
    [ -x "$SRC/bin/px4" ] || { echo "ОШИБКА: в $SRC нет bin/px4"; exit 1; }
    echo "PX4 ветка: 1.8"
    CMDS=/run/px4-cmds
    {
        echo "uorb start"
        echo "param load"
        echo "dataman start"
        if [ ! -s rootfs/eeprom/parameters ]; then
            cat "$AIRFRAMES/1.8/defaults"
            echo "param save"
        fi
        echo "param set MAV_SYS_ID $DRONE_ID"
        cat "$AIRFRAMES/1.8/modules"
    } > "$CMDS"
    exec "$SRC/bin/px4" -d "$SRC" "$CMDS"
fi

SIM_RC="$SRC/etc/init.d-posix/px4-rc.simulator"
MAVLINKSIM="$SRC/etc/init.d-posix/px4-rc.mavlinksim"

[ -x "$SRC/bin/px4" ] && [ -f "$SIM_RC" ] || { echo "ОШИБКА: в $SRC нет сборки PX4 SITL (bin/px4, etc/init.d-posix)"; exit 1; }

SIM_TEXT="$(cat "$SIM_RC")"
[ -f "$MAVLINKSIM" ] && SIM_TEXT+="$(cat "$MAVLINKSIM")"

if grep -q simulator_mavlink <<<"$SIM_TEXT"; then
    BRANCH=1.14
elif grep -qE 'simulator start' <<<"$SIM_TEXT"; then
    BRANCH=1.13
else
    echo "ОШИБКА: не удалось определить ветку PX4 по $SIM_RC"; exit 1
fi
echo "PX4 ветка: $BRANCH"

rm -rf "$RUN"
cp -a "$SRC/etc" "$RUN"
cp "$AIRFRAMES/$BRANCH/4500_clover" "$RUN/init.d-posix/airframes/4500_clover"

export PX4_SIM_MODEL=clover
export PX4_ESTIMATOR=ekf2
export PX4_SIM_HOST_ADDR=127.0.0.1
export CLOVER_SHOW_SYS_ID="$DRONE_ID"
exec "$SRC/bin/px4" -d "$RUN" -s etc/init.d-posix/rcS -i 0

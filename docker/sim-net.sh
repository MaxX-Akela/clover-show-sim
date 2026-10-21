#!/bin/bash
set -u
: "${DRONE_ID:?}" "${CLOVER_SHOW_HOST:?}"
SIM_PORT=$((4560 + DRONE_ID - 1))
socat TCP-LISTEN:4560,bind=127.0.0.1,reuseaddr,fork "TCP:${CLOVER_SHOW_HOST}:${SIM_PORT},retry=240,interval=0.5" &
python3 /opt/clover-show/bridge/gcs_relay.py "${CLOVER_SHOW_HOST}" &
trap 'kill $(jobs -p) 2>/dev/null' EXIT TERM INT
wait -n

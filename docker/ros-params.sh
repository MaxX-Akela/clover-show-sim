#!/bin/bash
for _ in $(seq 60); do
    rosparam set use_sim_time true 2>/dev/null && exit 0
    sleep 1
done
echo "roscore не отвечает" >&2
exit 1

#!/bin/bash
for svc in clover clever-show; do
    if [ -e "/state/enabled/$svc" ]; then
        supervisorctl start "$svc"
    fi
done

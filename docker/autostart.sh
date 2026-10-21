#!/bin/bash
# Запускает сервисы, включённые флагами в /state/enabled (clover — по умолчанию, clever-show — только если включил участник).
for svc in clover clever-show; do
    if [ -e "/state/enabled/$svc" ]; then
        supervisorctl start "$svc"
    fi
done

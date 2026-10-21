#!/bin/bash
set -u
HERE="$(dirname "$(readlink -f "$0")")"
CLI="$HERE/../bin/clover-px4"

choice=$(whiptail --title "Версия PX4" --menu "Какую версию PX4 использовать для всех дронов?" 16 72 3 \
    "1.13.3" "как в Clover VM (рекомендуется)" \
    "1.15.4" "новее, другие параметры (control allocation)" \
    "custom" "своя сборка (путь к build/px4_sitl_default)" 3>&1 1>&2 2>&3) || exit 1

if [ "$choice" = custom ]; then
    path=$(whiptail --inputbox "Путь к каталогу build/px4_sitl_default" 10 72 "$HOME/PX4-Autopilot/build/px4_sitl_default" 3>&1 1>&2 2>&3) || exit 1
    choice="$path"
fi

"$CLI" use "$choice"

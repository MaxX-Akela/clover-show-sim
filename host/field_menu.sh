#!/bin/bash
set -u
CLI="$(dirname "$(readlink -f "$0")")/../bin/clover-field"
items=()
while read -r mark name rest; do
    [ "$mark" = "*" ] || { rest="$name $rest"; name="$mark"; }
    items+=("$name" "$rest")
done < <("$CLI" list)
[ ${#items[@]} -gt 0 ] || { echo "Нет полей"; exit 1; }
choice=$(whiptail --title "Поле ArUco" --menu "Поле применится при следующем запуске симуляции" 16 76 6 "${items[@]}" 3>&1 1>&2 2>&3) || exit 1
"$CLI" use "$choice"

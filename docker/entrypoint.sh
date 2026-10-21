#!/bin/bash
set -eu
: "${DRONE_ID:?}"

HOST_UID=${HOST_UID:-1000}
HOST_GID=${HOST_GID:-1000}
groupmod -o -g "$HOST_GID" pi
usermod -o -u "$HOST_UID" -g "$HOST_GID" pi

seed() {
    if [ -d "$2" ] && [ -z "$(ls -A "$2" 2>/dev/null)" ]; then
        cp -a "$1/." "$2/"
        chown -R pi:pi "$2"
    fi
}
seed /opt/seed/launch /home/pi/catkin_ws/src/clover/clover/launch
seed /opt/seed/map /home/pi/catkin_ws/src/clover/aruco_pose/map
seed /opt/seed/clever-show /home/pi/clever-show

mkdir -p /state /px4data /var/log/clover-show /var/log/supervisor /run/dbus /var/run/dbus
if [ ! -d /state/enabled ]; then
    mkdir -p /state/enabled
    : > /state/enabled/clover
fi
chown -R pi:pi /state /px4data
touch /var/log/clover.log /var/log/clever-show.log
chown pi:pi /var/log/clover.log /var/log/clever-show.log /var/log/clover-show
mkdir -p /home/pi/.ros
chown pi:pi /home/pi/.ros

sed -i "s/^#\?host-name=.*/host-name=$(hostname)/" /etc/avahi/avahi-daemon.conf 2>/dev/null || true

exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf

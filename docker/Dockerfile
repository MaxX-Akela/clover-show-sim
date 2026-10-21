FROM ubuntu:20.04

LABEL org.opencontainers.image.title="clover-show-sim drone" \
      org.opencontainers.image.authors="MaxX-Akela" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/MaxX-Akela/clover-show-sim"

ARG CLOVER_REF=492430e9944ca27de003175f31afb2b3c1ab8a06
ARG ROS_LED_REF=4417455bdeaba00bef64a876220fda56fff66630
ARG CLEVER_SHOW_REF=2062940d8c32814eb08de57da1610ffa042a0da3

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 ROS_DISTRO=noetic

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg2 lsb-release git sudo \
    && echo "deb http://packages.ros.org/ros/ubuntu focal main" > /etc/apt/sources.list.d/ros1.list \
    && curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | apt-key add - \
    && apt-get update && apt-get install -y --no-install-recommends \
        ros-noetic-ros-base ros-noetic-mavros ros-noetic-mavros-extras ros-noetic-rosbridge-suite \
        ros-noetic-web-video-server ros-noetic-tf2-web-republisher ros-noetic-cv-camera \
        ros-noetic-image-proc ros-noetic-image-view ros-noetic-vision-msgs ros-noetic-angles \
        ros-noetic-nodelet-topic-tools ros-noetic-cmake-modules \
        python3-rosdep python3-catkin-tools python3-pip python3-numpy python3-psutil python3-opencv \
        python3-docopt build-essential libboost-all-dev \
        supervisor nginx-light socat dbus avahi-daemon libnss-mdns procps iproute2 iputils-ping nano less \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 pi && useradd -m -u 1000 -g pi -s /bin/bash pi \
    && echo "pi ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/pi

USER pi
WORKDIR /home/pi/catkin_ws/src
RUN set -e; \
    fetch() { git init -q "$1" && git -C "$1" remote add origin "$2" && git -C "$1" fetch -q --depth 1 origin "$3" && git -C "$1" checkout -q FETCH_HEAD; }; \
    fetch clover https://github.com/CopterExpress/clover "$CLOVER_REF"; \
    fetch ros_led https://github.com/CopterExpress/ros_led "$ROS_LED_REF"; \
    touch clover/clover_description/CATKIN_IGNORE clover/clover_simulation/CATKIN_IGNORE \
          ros_led/ws281x/CATKIN_IGNORE clover/docs/CATKIN_IGNORE clover/clover/www/CATKIN_IGNORE

USER root
RUN set -e; \
    rosdep init || true; \
    echo "yaml file:///home/pi/catkin_ws/src/clover/builder/assets/noetic-rosdep-clover.yaml" > /etc/ros/rosdep/sources.list.d/10-clover.list; \
    rosdep update --include-eol-distros; \
    rosdep install -y --from-paths /home/pi/catkin_ws/src --ignore-src --rosdistro noetic \
        --skip-keys="gazebo_ros gazebo_plugins"; \
    rm -rf /var/lib/apt/lists/*; \
    pip3 install --no-cache-dir flask geopy smbus2; \
    curl -fsSL https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh | bash

USER pi
WORKDIR /home/pi/catkin_ws
RUN . /opt/ros/noetic/setup.sh && catkin_make -j2 -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    && . devel/setup.sh && rosrun clover www

RUN set -e; \
    git init -q /home/pi/clever-show && git -C /home/pi/clever-show remote add origin https://github.com/CopterExpress/clever-show \
    && git -C /home/pi/clever-show fetch -q --depth 1 origin "$CLEVER_SHOW_REF" && git -C /home/pi/clever-show checkout -q FETCH_HEAD

USER root
RUN pip3 install --no-cache-dir -r /home/pi/clever-show/drone/requirements.txt

RUN mkdir -p /opt/seed && \
    cp -a /home/pi/catkin_ws/src/clover/clover/launch /opt/seed/launch && \
    cp -a /home/pi/catkin_ws/src/clover/aruco_pose/map /opt/seed/map && \
    cp -a /home/pi/clever-show /opt/seed/clever-show && \
    chown -R pi:pi /home/pi

COPY docker/sim.launch docker/supervisord.conf docker/ros-env docker/ros-params.sh docker/autostart.sh \
     docker/sim-net.sh docker/run-px4.sh docker/px4-branch.sh /opt/clover-show/
COPY docker/bridge/ /opt/clover-show/bridge/
COPY host/cshow/wire.py /opt/clover-show/bridge/wire.py
COPY px4/airframes/ /opt/clover-show/airframes/
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/systemctl docker/reboot /usr/local/bin/
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /opt/clover-show/* /opt/clover-show/bridge/*.py /usr/local/bin/systemctl /usr/local/bin/reboot /entrypoint.sh \
    && echo 'source /home/pi/catkin_ws/devel/setup.bash; export ROS_HOSTNAME=$(hostname).local ROS_MASTER_URI=http://localhost:11311' >> /home/pi/.bashrc \
    && sed -i 's/^hosts:.*/hosts: files mdns4_minimal [NOTFOUND=return] dns/' /etc/nsswitch.conf

EXPOSE 80 9090 8080 5760
ENTRYPOINT ["/entrypoint.sh"]

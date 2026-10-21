#!/bin/bash
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PX4_ARG=""
BUILD_IMAGE=0
SKIP_BLENDER=0
SKIP_SERVER=0
IMAGE="${CLOVER_SHOW_IMAGE:-ghcr.io/maxx-akela/clover-show-sim-drone:latest}"
CLEVER_SHOW_REF=2062940d8c32814eb08de57da1610ffa042a0da3
BLENDER_VER=2.93.18
BLENDER_DIR="/opt/blender-${BLENDER_VER}"

while [ $# -gt 0 ]; do
    case "$1" in
        --px4) PX4_ARG="$2"; shift 2 ;;
        --build-image) BUILD_IMAGE=1; shift ;;
        --skip-blender) SKIP_BLENDER=1; shift ;;
        --skip-server) SKIP_SERVER=1; shift ;;
        -h|--help) sed -n 2,4p "$0"; exit 0 ;;
        *) echo "Неизвестный аргумент: $1"; exit 1 ;;
    esac
done

say() { echo -e "\n=== $* ==="; }
[ "$(id -u)" -ne 0 ] || { echo "Запускайте от обычного пользователя (sudo будет вызван сам)."; exit 1; }

say "Проверка Clover VM"
if [ ! -f /opt/ros/noetic/setup.bash ]; then echo "Не найден ROS Noetic. Нужна Clover VM v1.4."; exit 1; fi
if [ ! -f "$HOME/catkin_ws/devel/setup.bash" ]; then echo "Не найден ~/catkin_ws/devel/setup.bash (Clover не собран)."; exit 1; fi
for d in "$HOME/PX4-Autopilot" "$HOME/catkin_ws/src/clover"; do
    [ -d "$d" ] || echo "ПРЕДУПРЕЖДЕНИЕ: нет $d — это точно Clover VM?"
done

say "Пакеты"
sudo apt-get update
sudo apt-get install -y docker.io whiptail python3-yaml python3-venv python3-pip curl xz-utils avahi-daemon libnss-mdns xdg-utils
sudo systemctl enable --now docker
if ! id -nG "$USER" | grep -qw docker; then
    sudo usermod -aG docker "$USER"
    echo "Пользователь добавлен в группу docker. Перелогиньтесь после установки (до этого команды идут через sg docker)."
fi
dk() { if id -nG | grep -qw docker; then docker "$@"; else sg docker -c "docker $(printf '%q ' "$@")"; fi; }

say "Команды в /usr/local/bin"
for c in clover-drone drone_pose clover-px4 clover-px4-changes clover-field; do
    sudo ln -sf "$REPO/bin/$c" "/usr/local/bin/$c"
done
sudo ln -sf "$REPO/simulate.py" /usr/local/bin/simulate.py
chmod +x "$REPO"/bin/* "$REPO"/simulate.py "$REPO"/px4/*.sh "$REPO"/host/*.sh

say "Имена дронов в /etc/hosts (запасной вариант к droneN.local)"
python3 - "$REPO" <<'PY' | sudo tee /etc/hosts.new >/dev/null
import re, sys
sys.path.insert(0, sys.argv[1] + '/host')
from cshow import common
begin, end = '# BEGIN clover-show-sim', '# END clover-show-sim'
text = open('/etc/hosts').read()
text = re.sub(r'\n?%s.*?%s\n?' % (re.escape(begin), re.escape(end)), '\n', text, flags=re.S)
lines = ['%s %s %s.local' % (common.drone_ip(i), common.drone_name(i), common.drone_name(i))
         for i in range(1, common.MAX_DRONES + 1)]
sys.stdout.write(text.rstrip('\n') + '\n' + begin + '\n' + '\n'.join(lines) + '\n' + end + '\n')
PY
sudo mv /etc/hosts.new /etc/hosts

say "Образ дрона"
if [ "$BUILD_IMAGE" -eq 1 ]; then
    (cd "$REPO" && dk build -f docker/Dockerfile -t "$IMAGE" .)
elif ! dk pull "$IMAGE"; then
    echo "Не удалось скачать $IMAGE. Соберите локально: ./install.sh --build-image"
    exit 1
fi

say "PX4"
mkdir -p "$HOME/.clover-show/px4" "$HOME/clover-show/drones"
if [ -z "$PX4_ARG" ]; then
    if [ -t 0 ] && [ -t 1 ]; then
        "$REPO/px4/select_menu.sh" || { echo "Выбор отменён, ставлю 1.13.3"; "$REPO/bin/clover-px4" use 1.13.3; }
    else
        "$REPO/bin/clover-px4" use 1.13.3
    fi
else
    "$REPO/bin/clover-px4" use "$PX4_ARG"
fi

if [ "$SKIP_SERVER" -eq 0 ]; then
    say "clever-show (сервер): установка без настройки"
    if [ ! -d "$HOME/clever-show/.git" ]; then
        git init -q "$HOME/clever-show"
        git -C "$HOME/clever-show" remote add origin https://github.com/CopterExpress/clever-show
        git -C "$HOME/clever-show" fetch -q --depth 1 origin "$CLEVER_SHOW_REF"
        git -C "$HOME/clever-show" checkout -q FETCH_HEAD
    fi
    python3 -m venv "$HOME/.clover-show/venv-server"
    "$HOME/.clover-show/venv-server/bin/pip" install -q -r "$HOME/clever-show/server/requirements.txt" \
        || echo "ПРЕДУПРЕЖДЕНИЕ: не все зависимости сервера clever-show установились (см. вывод выше)."
fi

if [ "$SKIP_BLENDER" -eq 0 ] && [ ! -x "$BLENDER_DIR/blender" ]; then
    say "Blender ${BLENDER_VER} LTS (аддон clever-show не устанавливается)"
    tmp="$(mktemp -d)"
    base="https://download.blender.org/release/Blender2.93"
    tarball="blender-${BLENDER_VER}-linux-x64.tar.xz"
    curl -fL -o "$tmp/$tarball" "$base/$tarball"
    curl -fsSL "$base/blender-${BLENDER_VER}.sha256" | grep "$tarball" > "$tmp/sha"
    (cd "$tmp" && sha256sum -c sha)
    sudo mkdir -p "$BLENDER_DIR"
    sudo tar -xf "$tmp/$tarball" -C "$BLENDER_DIR" --strip-components=1
    sudo ln -sf "$BLENDER_DIR/blender" /usr/local/bin/blender
    rm -rf "$tmp"
fi

say "Ярлыки на рабочем столе"
mkdir -p "$HOME/Desktop"
for f in "$REPO"/desktop/*.desktop; do
    dst="$HOME/Desktop/clover-show-$(basename "$f")"
    sed -e "s#@REPO@#$REPO#g" -e "s#@HOME@#$HOME#g" "$f" > "$dst"
    chmod +x "$dst"
    gio set "$dst" metadata::trusted true 2>/dev/null || true
done

say "Готово"
echo "Запуск: ярлык «Шоу: N дронов в Gazebo» или  simulate.py  (в терминале с загруженным ROS)."
echo "Папки дронов: ~/clover-show/drones/droneN/"

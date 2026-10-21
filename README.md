# clover-show-sim

Симулятор clever-show в Gazebo. И дроны целы, и рои готовы.

## Установка

```bash
git clone https://github.com/MaxX-Akela/clover-show-sim ~/clover-show-sim
cd ~/clover-show-sim
./install.sh              # меню выбора версии PX4
```

## Запуск

Ярлык «Шоу: N дронов в Gazebo» или в терминале:

```bash
source ~/catkin_ws/devel/setup.bash
simulate.py
```

Ctrl+C останавливает Gazebo, мост и контейнеры. Обычный одиночный симулятор Клевера (`roslaunch clover_simulation simulator.launch`) и ярлык «Gazebo Clover» не затрагиваются, но одновременно с шоу их запускать нельзя.

Web Клевера каждого дрона: `http://drone1.local/`, `http://drone2.local/` … (mDNS и запись в `/etc/hosts`). QGroundControl видит все дроны (UDP 14550, `MAV_SYS_ID` = номер дрона).

## Команды

| Команда | Назначение |
|---|---|
| `clover-drone list` | дроны, статус, IP, версия PX4, позиция |
| `clover-drone restart N` | перезапустить контейнер |
| `clover-drone reset N` | сбросить папку и параметры PX4 к эталону (с резервной копией в `~/clover-show/backups`) |
| `clover-drone shell N` | bash внутри дрона с окружением ROS |
| `clover-drone logs N [clover\|px4\|bridge\|clever-show\|roscore\|led\|container]` | логи |
| `drone_pose N МЕТКА [--yaw град]` | поставить дрон на центр ArUco-метки активного поля Gazebo |
| `drone_pose N` | вернуть на позицию по умолчанию |
| `drone_pose list` | позиции всех дронов |
| `clover-field list \| use <файл>` | ArUco-поле Gazebo |
| `clover-px4 list \| current \| use <версия\|путь> [--drone N]` | версии PX4 |
| `clover-px4-changes` | меню выбора версии PX4 |


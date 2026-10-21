# clover-show-sim

Симулятор clever-show в Gazebo. И дроны целы, и рои готовы.

Несколько квадрокоптеров Clover (по умолчанию 3) в одном мире Gazebo. Каждый дрон — отдельный Docker-контейнер, как отдельная Raspberry Pi: свой roscore, IP, hostname (`drone1..N`), launch-файлы, aruco-карта, web-интерфейс Клевера, PX4 SITL и клиент clever-show. Проект нужен, чтобы проверять умение настраивать Клевер, PX4 (через QGC) и clever-show так же, как на реальных дронах.

Лицензия MIT, © MaxX-Akela. Ставится поверх официальной **Clover VM v1.4** (Ubuntu 20.04, ROS Noetic, Gazebo 11, PX4 v1.13.3).

## Требования к VM

- 3D-ускорение включено в настройках VirtualBox/VMware;
- 4 и более ядра, 6–8 ГБ RAM (на каждый дрон — контейнер с ROS и PX4);
- интернет при установке (Docker, образ дрона, сборки PX4, Blender).

## Установка

```bash
git clone https://github.com/MaxX-Akela/clover-show-sim ~/clover-show-sim
cd ~/clover-show-sim
./install.sh              # меню выбора версии PX4
```

Ключи: `--px4 1.13.3|1.15.4|<путь к build/px4_sitl_default>` (без меню), `--build-image` (собрать образ дрона локально вместо скачивания), `--skip-blender`, `--skip-server`. Скрипт идемпотентен. Каталог репозитория после установки не переносите: команды в `/usr/local/bin` — симлинки на него. После установки перелогиньтесь (группа `docker`).

Что ставится: Docker, образ дрона, выбранная сборка PX4 (`~/.clover-show/px4/<версия>`), сервер clever-show в `~/clever-show` с зависимостями в `~/.clover-show/venv-server` (**не настроен и не запущен**), Blender 2.93 LTS в `/opt` (аддон clever-show не ставится), команды и ярлыки на рабочем столе. Старые ярлыки Clover VM не затрагиваются.

## Запуск

Ярлык «Шоу: N дронов в Gazebo» или в терминале:

```bash
source ~/catkin_ws/devel/setup.bash
simulate.py                       # 3 дрона
simulate.py -n 5 --headless       # 5 дронов без GUI Gazebo
simulate.py --field field6x6.txt --spacing 1.5
```

Ctrl+C останавливает Gazebo, мост и контейнеры. Обычный одиночный симулятор Клевера (`roslaunch clover_simulation simulator.launch`) и ярлык «Gazebo Clover» не затрагиваются, но одновременно с шоу их запускать нельзя.

Web Клевера каждого дрона: `http://drone1.local/`, `http://drone2.local/` … (mDNS и запись в `/etc/hosts`). QGroundControl видит все дроны (UDP 14550, `MAV_SYS_ID` = номер дрона).

## Что настраивает участник

Пользовательская конфигурация **не настроена**: при первом запуске в `~/clover-show/drones/droneN/` копируются файлы «как в свежем образе Клевера»:

| Папка | Содержимое |
|---|---|
| `launch/` | `clover.launch`, `aruco.launch` и остальные launch-файлы (правятся в VS Code) |
| `map/` | aruco-карты, которые знает дрон |
| `clever-show/` | клиент clever-show (`drone/config/client.ini` и т. д.) |
| `px4/` | параметры PX4 дрона (сохраняются между запусками) |
| `state/` | включённые сервисы |

Клиент clever-show установлен, но **не запускается автоматически**. Включается как на реальном дроне: `clover-drone shell 1`, затем `systemctl enable clever-show && systemctl start clever-show`; состояние сохраняется. Сервер: `cd ~/clever-show/server && ~/.clover-show/venv-server/bin/python server.py`. Настройка по документации clever-show и Clover.

Симуляционная «проводка» скрыта: `sim.launch` в образе включает ваш `clover.launch` и переопределяет только `fcu_conn=sitl`, `fcu_ip`, `fcu_sys_id`, `simulator=true`. `aruco`, `optical_flow`, `led` и прочее остаются из вашего файла. Заглушка `systemctl` понимает `restart/start/stop/enable/disable/status` для `clover`, `clever-show`, `roscore`; `chrony` игнорируется; `reboot` перезапускает процессы дрона.

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

**Позиции.** По умолчанию дроны стоят на линии `y = 0`: drone1 в `x = 0`, drone2 в `x = spacing`, … `drone_pose` берёт координаты метки из *поля Gazebo* (физические маркеры «на полу», `clover-field`), а не из карты, которую знает дрон. Позиция хранится в `~/clover-show/poses.yaml` и применяется при следующем запуске. Если симуляция идёт, дрон переставляется сразу, но только если он не армлен; PX4 этого дрона при этом перезапускается, чтобы оценка позиции началась с нового места.

**ArUco-поле** — файл формата карты Клевера (`id размер x y z yaw pitch roll`). Готовые: `field4x4.txt`, `field6x6.txt` (папка `fields/`), свои кладите в `~/clover-show/fields/`. Поле превращается в модель Gazebo через `aruco_gen` и применяется при запуске.

**PX4.** Версии лежат в `~/.clover-show/px4/<версия>/` и монтируются в контейнеры read-only. Готовые сборки (1.13.3, 1.15.4) скачиваются из GitHub Releases репозитория (теги `px4-<версия>`), в VM ничего не компилируется. Своя сборка (`build/px4_sitl_default`) проверяется при подключении. Airframe Клевера подкладывается автоматически для 1.13 и 1.14+. При смене версии параметры дрона сохраняются в `params-<версия>.bak` и сбрасываются.

## Как это устроено

- Хост: Gazebo (gazebo_ros, плагины Clover), модели `drone1..N` из `clover_description` (xacro + постобработка XML: свой MAVLink TCP-порт `4560+N-1` и namespace `droneN` у всех плагинов), `bridge_host.py`, QGC.
- Контейнер: supervisord вместо systemd; PX4 всегда instance 0 и подключается к `127.0.0.1:4560`, откуда `socat` пробрасывает на порт модели; GCS-линк PX4 (всегда на localhost) уходит на QGC UDP-реле.
- Мост: камера (`/main_camera/image_raw`, `camera_info`), дальномер (`/rangefinder/range`) и `/clock` идут с хоста в контейнер (`rospy.AnyMsg` + TCP, только последнее сообщение), состояние LED — из контейнера в `/droneN/led/set_leds` Gazebo (не чаще 10 Гц). В контейнере вместо `ws281x_node` работает фейковый драйвер `led` (58 светодиодов), `use_sim_time=true`.
- Веб Клевера на порту 80 раздаёт nginx (в реальном образе — monkey; содержимое то же, `~/.ros/www`).

## Известные ограничения

- Если падает один дрон, встаёт весь Gazebo (lockstep).
- При RTF < 1 шоу отстаёт от музыки, но дроны между собой синхронны.
- В SITL не работают калибровки датчиков, пульт (есть виртуальный джойстик QGC), ESC и прошивка через USB.
- Сильно изменённые сборки PX4 могут не запуститься.
- Gazebo-плагины Clover VM собраны под PX4 1.13; для 1.14+ совместимость зависит от версии (см. `px4/airframes`), при проблемах нужна сборка плагинов из `PX4/PX4-SITL_gazebo-classic`.
- Запросы к `docker` требуют группу `docker`; firewall на VM не должен блокировать подсеть `172.30.0.0/24`.

## Экспорт образа VM

`.ova` проект не генерирует. После `install.sh`: выключить VM → VirtualBox → «Файл → Экспорт конфигураций» → выбрать VM → формат OVF 2.0 / `.ova`.

## Проверки без VM

```bash
python3 -m unittest discover -s tests          # хостовая часть
shellcheck install.sh docker/*.sh px4/*.sh host/*.sh
```

## Лицензии

Код проекта — MIT, © MaxX-Akela. Образ дрона собирает из исходников Clover и ros_led (MIT, © Copter Express) и устанавливает клиент clever-show (GPL-3) из его репозитория при сборке; исходники clever-show в этот репозиторий не входят.

import os
import sys

REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
HOME = os.path.expanduser('~')

STATE_DIR = os.path.join(HOME, '.clover-show')
PX4_DIR = os.path.join(STATE_DIR, 'px4')
MODELS_DIR = os.path.join(STATE_DIR, 'models')
FIELD_LINK = os.path.join(STATE_DIR, 'field.txt')
WORLD_FILE = os.path.join(STATE_DIR, 'world.world')

USER_DIR = os.path.join(HOME, 'clover-show')
DRONES_DIR = os.path.join(USER_DIR, 'drones')
POSES_FILE = os.path.join(USER_DIR, 'poses.yaml')

IMAGE = os.environ.get('CLOVER_SHOW_IMAGE', 'ghcr.io/maxx-akela/clover-show-sim-drone:latest')
NETWORK = 'clover-show'
SUBNET = '172.30.0.0/24'
GATEWAY = '172.30.0.1'
DEFAULT_DRONES = 3
MAX_DRONES = 9

BRIDGE_PORT_BASE = 11400
SIM_TCP_BASE = 4560
SIM_UDP_PORT = 14560


def drone_ip(n):
    return '172.30.0.%d' % (10 + n)


def drone_name(n):
    return 'drone%d' % n


def container_name(n):
    return 'clover-drone%d' % n


def drone_dir(n):
    return os.path.join(DRONES_DIR, drone_name(n))


def die(msg, code=1):
    print('Ошибка: %s' % msg, file=sys.stderr)
    sys.exit(code)


def check_drone_id(n, count=None):
    limit = count or MAX_DRONES
    if not isinstance(n, int) or n < 1 or n > limit:
        die('номер дрона %s вне диапазона 1..%d' % (n, limit))

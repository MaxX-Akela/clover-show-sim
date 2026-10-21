import os
import re
import shutil
import subprocess
import tarfile
import urllib.request

from . import common

RELEASES = {'1.8.2-clever.10': 'px4-1.8.2-clever.10', '1.13.3': 'px4-1.13.3', '1.16.0': 'px4-1.16.0', '1.17.0': 'px4-1.17.0'}
REPO_URL = 'https://github.com/MaxX-Akela/clover-show-sim/releases/download/%s/px4_sitl_default-%s.tar.gz'
CURRENT = os.path.join(common.PX4_DIR, 'current')


class Px4Error(Exception):
    pass


def branch_of(version_dir):
    binary = os.path.join(version_dir, 'bin', 'px4')
    rcs = os.path.join(version_dir, 'etc', 'init.d-posix', 'rcS')
    sim = os.path.join(version_dir, 'etc', 'init.d-posix', 'px4-rc.simulator')
    if not os.path.isfile(binary):
        raise Px4Error('%s: нет bin/px4 — это не собранный PX4 SITL' % version_dir)
    if not os.path.isfile(rcs):
        if os.path.isfile(os.path.join(version_dir, 'ROMFS', 'px4fmu_common', 'mixers', 'quad_w.main.mix')):
            return '1.8'
        raise Px4Error('%s: нет etc/init.d-posix/rcS и ROMFS/px4fmu_common/mixers — это не каталог сборки SITL' % version_dir)
    if not os.path.isfile(sim):
        raise Px4Error('%s: нет px4-rc.simulator — сборка не для симулятора' % version_dir)
    with open(sim) as f:
        text = f.read()
    mavlinksim = os.path.join(version_dir, 'etc', 'init.d-posix', 'px4-rc.mavlinksim')
    if os.path.isfile(mavlinksim):
        with open(mavlinksim) as f:
            text += f.read()
    if 'simulator_mavlink' in text:
        branch = '1.14'
    elif re.search(r'\bsimulator start\b', text):
        branch = '1.13'
    else:
        raise Px4Error('%s: в px4-rc.simulator нет simulator/simulator_mavlink (нужен Gazebo Classic)' % version_dir)
    if 'PX4_SIM_HOST_ADDR' not in text:
        raise Px4Error('%s: сборка не поддерживает PX4_SIM_HOST_ADDR — подключение из контейнера невозможно' % version_dir)
    if not os.path.isdir(os.path.join(version_dir, 'etc', 'init.d-posix', 'airframes')):
        raise Px4Error('%s: нет каталога airframes, некуда положить airframe Клевера' % version_dir)
    return branch


def versions():
    if not os.path.isdir(common.PX4_DIR):
        return []
    return sorted(v for v in os.listdir(common.PX4_DIR) if v != 'current')


def current():
    if os.path.islink(CURRENT):
        return os.path.basename(os.readlink(CURRENT))
    return None


def current_dir():
    if not os.path.exists(CURRENT):
        raise Px4Error('версия PX4 не выбрана (clover-px4 use <версия>)')
    return os.path.realpath(CURRENT)


def _set_current(name):
    tmp = CURRENT + '.new'
    if os.path.lexists(tmp):
        os.remove(tmp)
    os.symlink(name, tmp)
    os.replace(tmp, CURRENT)


def register_custom(path):
    path = os.path.realpath(os.path.expanduser(path))
    branch_of(path)
    name = 'custom-' + re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(os.path.dirname(os.path.dirname(path))) or 'build')
    os.makedirs(common.PX4_DIR, exist_ok=True)
    link = os.path.join(common.PX4_DIR, name)
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(path, link)
    return name


def download(version):
    if version not in RELEASES:
        raise Px4Error('версия %s недоступна для скачивания (есть: %s)' % (version, ', '.join(RELEASES)))
    os.makedirs(common.PX4_DIR, exist_ok=True)
    url = REPO_URL % (RELEASES[version], version)
    tmp = os.path.join(common.PX4_DIR, '.download-%s.tar.gz' % version)
    dest = os.path.join(common.PX4_DIR, version)
    try:
        urllib.request.urlretrieve(url, tmp)
    except Exception as e:
        raise Px4Error('не удалось скачать %s: %s' % (url, e))
    shutil.rmtree(dest + '.new', ignore_errors=True)
    os.makedirs(dest + '.new')
    with tarfile.open(tmp) as t:
        for m in t.getmembers():
            if m.name.startswith('/') or '..' in m.name.split('/'):
                raise Px4Error('небезопасный архив')
        t.extractall(dest + '.new')
    os.remove(tmp)
    shutil.rmtree(dest, ignore_errors=True)
    os.rename(dest + '.new', dest)
    branch_of(dest)
    return dest


def resolve(arg):
    if os.sep in arg or arg.startswith(('~', '.')):
        return register_custom(arg)
    if arg in versions():
        branch_of(os.path.join(common.PX4_DIR, arg))
        return arg
    download(arg)
    return arg


def airframe_dir(branch):
    return os.path.join(common.REPO, 'px4', 'airframes', branch)


def use(arg, drone=None):
    name = resolve(arg)
    if drone is None:
        _set_current(name)
    else:
        d = common.drone_dir(drone)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'px4_version'), 'w') as f:
            f.write(name + '\n')
    return name


def version_for(drone):
    f = os.path.join(common.drone_dir(drone), 'px4_version')
    if os.path.exists(f):
        return open(f).read().strip()
    return current()


def branch_for(drone):
    ver = version_for(drone)
    if not ver:
        raise Px4Error('версия PX4 не выбрана (clover-px4 use <версия>)')
    return branch_of(os.path.realpath(os.path.join(common.PX4_DIR, ver)))


def backup_params(drone, old_version):
    pdir = os.path.join(common.drone_dir(drone), 'px4')
    if not os.path.isdir(pdir) or not os.listdir(pdir):
        return False
    bak = os.path.join(common.drone_dir(drone), 'params-%s.bak' % (old_version or 'unknown'))
    shutil.rmtree(bak, ignore_errors=True)
    shutil.move(pdir, bak)
    os.makedirs(pdir)
    return True

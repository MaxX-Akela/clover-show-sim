import os
import shutil
import subprocess

from . import common


class Marker(object):
    def __init__(self, id_, size, x, y, z=0.0, yaw=0.0):
        self.id, self.size, self.x, self.y, self.z, self.yaw = id_, size, x, y, z, yaw


def parse(path):
    markers = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            if len(p) < 4:
                continue
            try:
                markers.append(Marker(int(p[0]), float(p[1]), float(p[2]), float(p[3]),
                                      float(p[4]) if len(p) > 4 else 0.0,
                                      float(p[5]) if len(p) > 5 else 0.0))
            except ValueError:
                continue
    return markers


def available():
    res = {}
    for d in (os.path.join(common.REPO, 'fields'), os.path.join(common.USER_DIR, 'fields')):
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.txt'):
                    res[f] = os.path.join(d, f)
    return res


def resolve(arg):
    if os.path.isfile(arg):
        return os.path.abspath(arg)
    av = available()
    for key in (arg, arg + '.txt'):
        if key in av:
            return av[key]
    common.die('поле «%s» не найдено (смотрите: clover-field list)' % arg)


def active():
    if os.path.islink(common.FIELD_LINK) or os.path.exists(common.FIELD_LINK):
        return os.path.realpath(common.FIELD_LINK)
    return os.path.join(common.REPO, 'fields', 'field4x4.txt')


def activate(path):
    os.makedirs(common.STATE_DIR, exist_ok=True)
    if os.path.lexists(common.FIELD_LINK):
        os.remove(common.FIELD_LINK)
    os.symlink(os.path.realpath(path), common.FIELD_LINK)


def marker(field_path, marker_id):
    for m in parse(field_path):
        if m.id == marker_id:
            return m
    return None


def build_world(field_path, out=None):
    out = out or common.WORLD_FILE
    os.makedirs(common.MODELS_DIR, exist_ok=True)
    tool = shutil.which('aruco_gen')
    if not tool:
        common.die('aruco_gen не найден: нужен собранный пакет clover_simulation (source ~/catkin_ws/devel/setup.bash)')
    subprocess.check_call([tool, '--single-model', '--model-path', common.MODELS_DIR, field_path],
                          stdout=subprocess.DEVNULL)
    model = 'aruco_%s' % os.path.basename(field_path).replace('.', '_')
    with open(os.path.join(common.REPO, 'host', 'world', 'clover_show.world')) as f:
        text = f.read()
    with open(out, 'w') as f:
        f.write(text.replace('@FIELD_MODEL@', model))
    return out

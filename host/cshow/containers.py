import os
import shutil
import subprocess
import time

from . import common, px4

SUBDIRS = ('launch', 'map', 'clever-show', 'px4', 'state')


def docker(*args, check=True, capture=True, **kw):
    cmd = ['docker'] + list(args)
    if capture:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, **kw)
    else:
        p = subprocess.run(cmd, **kw)
    if check and p.returncode != 0:
        raise RuntimeError('docker %s: %s' % (' '.join(args[:2]), (p.stdout or '').strip()))
    return p


def ensure_docker():
    p = docker('info', check=False)
    if p.returncode != 0:
        common.die('docker недоступен (%s). Установлен ли он и добавлен ли пользователь в группу docker? '
                   'После install.sh нужно перелогиниться.' % (p.stdout or '').strip().splitlines()[-1:])


def ensure_network():
    if docker('network', 'inspect', common.NETWORK, check=False).returncode != 0:
        docker('network', 'create', '--subnet', common.SUBNET, '--gateway', common.GATEWAY, common.NETWORK)


def ensure_image():
    if docker('image', 'inspect', common.IMAGE, check=False).returncode != 0:
        print('Скачиваю образ дрона %s ...' % common.IMAGE)
        docker('pull', common.IMAGE, capture=False)


def prepare_dirs(n):
    base = common.drone_dir(n)
    for s in SUBDIRS:
        os.makedirs(os.path.join(base, s), exist_ok=True)
    return base


def px4_dir_for(n):
    ver = px4.version_for(n)
    if not ver:
        raise px4.Px4Error('версия PX4 не выбрана (clover-px4 use <версия>)')
    path = os.path.realpath(os.path.join(common.PX4_DIR, ver))
    px4.branch_of(path)
    marker = os.path.join(common.drone_dir(n), '.px4_loaded')
    old = open(marker).read().strip() if os.path.exists(marker) else None
    if old and old != ver:
        if px4.backup_params(n, old):
            print('ВНИМАНИЕ: drone%d: версия PX4 %s -> %s, параметры сброшены (копия: params-%s.bak)' % (n, old, ver, old))
    with open(marker, 'w') as f:
        f.write(ver + '\n')
    return path


def name_exists(n):
    return docker('container', 'inspect', common.container_name(n), check=False).returncode == 0


def running(n):
    p = docker('container', 'inspect', '-f', '{{.State.Running}}', common.container_name(n), check=False)
    return p.returncode == 0 and p.stdout.strip() == 'true'


def running_ids():
    p = docker('ps', '--filter', 'name=^clover-drone', '--format', '{{.Names}}', check=False)
    return sorted(int(x[len('clover-drone'):]) for x in p.stdout.split() if x.startswith('clover-drone'))


def remove(n):
    docker('rm', '-f', common.container_name(n), check=False)


def start(n):
    base = prepare_dirs(n)
    px4_path = px4_dir_for(n)
    remove(n)
    name, ip = common.drone_name(n), common.drone_ip(n)
    cdir = '/home/pi/catkin_ws/src/clover'
    mounts = [
        (px4_path, '/px4:ro'),
        (os.path.join(base, 'launch'), cdir + '/clover/launch'),
        (os.path.join(base, 'map'), cdir + '/aruco_pose/map'),
        (os.path.join(base, 'clever-show'), '/home/pi/clever-show'),
        (os.path.join(base, 'px4'), '/px4data'),
        (os.path.join(base, 'state'), '/state'),
    ]
    args = ['run', '-d', '--name', common.container_name(n), '--hostname', name,
            '--network', common.NETWORK, '--ip', ip,
            '--add-host', 'host.docker.internal:host-gateway', '--add-host', '%s.local:%s' % (name, ip),
            '-e', 'DRONE_ID=%d' % n, '-e', 'HOST_UID=%d' % os.getuid(), '-e', 'HOST_GID=%d' % os.getgid(),
            '-e', 'CLOVER_SHOW_HOST=%s' % common.GATEWAY,
            '-e', 'CLOVER_SHOW_BRIDGE_HOST=%s' % common.GATEWAY,
            '-e', 'CLOVER_SHOW_BRIDGE_PORT=%d' % (common.BRIDGE_PORT_BASE + n),
            '--label', 'clover-show=1']
    for src, dst in mounts:
        args += ['-v', '%s:%s' % (src, dst)]
    docker(*args, common.IMAGE)


def exec_(n, *cmd, tty=False, check=False, timeout=None):
    args = ['exec'] + (['-it'] if tty else []) + [common.container_name(n)] + list(cmd)
    return docker(*args, check=check, capture=not tty, timeout=timeout)


def ros(n, *cmd, timeout=15):
    return exec_(n, '/opt/clover-show/ros-env', *cmd, timeout=timeout)


def is_armed(n):
    try:
        p = ros(n, 'rostopic', 'echo', '-n', '1', '/mavros/state/armed', timeout=8)
    except subprocess.TimeoutExpired:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip().splitlines()
    for line in out:
        if line.strip() in ('True', 'False'):
            return line.strip() == 'True'
    return None


def restart_px4(n):
    exec_(n, 'supervisorctl', 'restart', 'px4')


def hosts_line(count):
    return ['%s %s %s.local' % (common.drone_ip(i), common.drone_name(i), common.drone_name(i))
            for i in range(1, count + 1)]


def wait_up(ids, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if all(running(i) for i in ids):
            return True
        time.sleep(1)
    return False


def backup_and_clear(n):
    import tarfile
    base = common.drone_dir(n)
    bdir = os.path.join(common.USER_DIR, 'backups')
    os.makedirs(bdir, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    out = os.path.join(bdir, '%s-%s.tar.gz' % (common.drone_name(n), stamp))
    if os.path.isdir(base):
        with tarfile.open(out, 'w:gz') as t:
            t.add(base, arcname=common.drone_name(n))
        for s in SUBDIRS:
            shutil.rmtree(os.path.join(base, s), ignore_errors=True)
    return out

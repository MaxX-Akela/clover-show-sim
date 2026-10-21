#!/usr/bin/env python3
import argparse
import math
import os
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'host'))
from cshow import common, containers, field, poses, px4, urdf

procs = []


def log(msg):
    print('[simulate] ' + msg, flush=True)


def require_ros():
    if not os.environ.get('ROS_DISTRO'):
        common.die('окружение ROS не загружено: source ~/catkin_ws/devel/setup.bash')


def start_gazebo(world, headless):
    env = dict(os.environ)
    env['GAZEBO_MODEL_PATH'] = common.MODELS_DIR + ':' + env.get('GAZEBO_MODEL_PATH', '')
    env['SVGA_VGPU10'] = '0'
    cmd = ['roslaunch', 'gazebo_ros', 'empty_world.launch', 'world_name:=' + world,
           'gui:=' + ('false' if headless else 'true'), 'verbose:=true']
    p = subprocess.Popen(cmd, env=env, preexec_fn=os.setsid)
    procs.append(p)
    return p


def wait_for_gazebo(timeout=120):
    import rospy
    rospy.wait_for_service('/gazebo/spawn_urdf_model', timeout=timeout)


def spawn_model(n, urdf_text, pose, results):
    import rospy
    from geometry_msgs.msg import Pose
    from gazebo_msgs.srv import SpawnModel
    x, y, z, yaw_deg, _ = pose
    p = Pose()
    p.position.x, p.position.y, p.position.z = x, y, z
    yaw = math.radians(yaw_deg)
    p.orientation.z, p.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    try:
        proxy = rospy.ServiceProxy('/gazebo/spawn_urdf_model', SpawnModel)
        r = proxy(common.drone_name(n), urdf_text, common.drone_name(n), p, 'world')
        results[n] = (r.success, r.status_message)
    except Exception as e:
        results[n] = (False, str(e))


def shutdown(*_):
    log('остановка...')
    for n in containers.running_ids():
        containers.remove(n)
    for p in reversed(procs):
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGINT)
        except ProcessLookupError:
            pass
    for p in procs:
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description='Симулятор нескольких Клеверов для clever-show')
    ap.add_argument('-n', type=int, default=common.DEFAULT_DRONES, help='число дронов (по умолчанию 3)')
    ap.add_argument('--headless', action='store_true', help='без GUI Gazebo')
    ap.add_argument('--field', help='файл или имя ArUco-поля (по умолчанию — активное, clover-field use)')
    ap.add_argument('--spacing', type=float, help='расстояние между дронами по умолчанию, м')
    args = ap.parse_args()
    if not 1 <= args.n <= common.MAX_DRONES:
        common.die('число дронов должно быть 1..%d' % common.MAX_DRONES)

    require_ros()
    containers.ensure_docker()
    containers.ensure_network()
    containers.ensure_image()
    if containers.running_ids():
        common.die('уже запущены контейнеры дронов: %s (clover-drone list). Остановите прежнюю симуляцию.'
                   % containers.running_ids())

    if args.field:
        field.activate(field.resolve(args.field))
    fpath = field.active()
    data = poses.load()
    if args.spacing:
        data['spacing'] = args.spacing
        poses.save(data)
    try:
        pose_list = {i: poses.resolve(i, data, fpath) for i in range(1, args.n + 1)}
    except ValueError as e:
        common.die(str(e))

    import subprocess as sp
    cd_path = sp.check_output(['rospack', 'find', 'clover_description'], universal_newlines=True).strip()
    raw = urdf.run_xacro(os.path.join(cd_path, 'urdf/clover/clover4.xacro'))
    try:
        branches = {i: px4.branch_for(i) for i in range(1, args.n + 1)}
    except px4.Px4Error as e:
        common.die(str(e))
    urdfs = {i: urdf.postprocess(raw, i, branches[i]) for i in range(1, args.n + 1)}

    log('поле: %s' % os.path.basename(fpath))
    world = field.build_world(fpath)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    start_gazebo(world, args.headless)
    import rospy
    rospy.init_node('clover_show_sim', disable_signals=True)
    log('жду Gazebo...')
    wait_for_gazebo()

    results = {}
    threads = [threading.Thread(target=spawn_model, args=(i, urdfs[i], pose_list[i], results), daemon=True)
               for i in range(1, args.n + 1)]
    for t in threads:
        t.start()
    time.sleep(2)

    bridge = subprocess.Popen([sys.executable, os.path.join(common.REPO, 'host', 'bridge_host.py'), '-n', str(args.n)],
                              preexec_fn=os.setsid)
    procs.append(bridge)

    for i in range(1, args.n + 1):
        log('запускаю drone%d' % i)
        containers.start(i)
    log('дроны запущены. Web: ' + ', '.join('http://%s.local/' % common.drone_name(i) for i in range(1, args.n + 1)))
    log('Ctrl+C — остановка')

    for t in threads:
        t.join()
    for i, (ok, msg) in sorted(results.items()):
        log('модель drone%d: %s' % (i, 'ок' if ok else 'ОШИБКА ' + msg))

    while True:
        time.sleep(1)
        if procs[0].poll() is not None:
            log('Gazebo завершился')
            shutdown()


if __name__ == '__main__':
    main()

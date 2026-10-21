import argparse
import math
import os

from . import common, containers, field, poses


def _range():
    ids = containers.running_ids()
    return (max(ids) if ids else common.MAX_DRONES), bool(ids)


def teleport(n, x, y, z, yaw_deg):
    try:
        import rospy
        from gazebo_msgs.msg import ModelState
        from gazebo_msgs.srv import SetModelState
    except ImportError:
        common.die('нет окружения ROS: source ~/catkin_ws/devel/setup.bash')
    rospy.init_node('drone_pose', anonymous=True, disable_signals=True)
    st = ModelState()
    st.model_name = common.drone_name(n)
    st.pose.position.x, st.pose.position.y, st.pose.position.z = x, y, z
    yaw = math.radians(yaw_deg)
    st.pose.orientation.z, st.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    st.reference_frame = 'world'
    rospy.wait_for_service('/gazebo/set_model_state', timeout=5)
    resp = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)(st)
    if not resp.success:
        common.die('Gazebo не смог переставить модель: %s' % resp.status_message)


def cmd_list():
    data = poses.load()
    fpath = field.active()
    print('Поле: %s, расстояние по умолчанию: %g м' % (os.path.basename(fpath), data['spacing']))
    top, _ = _range()
    for n in range(1, (top if containers.running_ids() else common.DEFAULT_DRONES) + 1):
        try:
            x, y, z, yaw, mid = poses.resolve(n, data, fpath)
        except ValueError as e:
            print('drone%d: ОШИБКА %s' % (n, e))
            continue
        where = 'метка %d' % mid if mid is not None else 'по умолчанию'
        print('drone%d: %s  x=%.2f y=%.2f z=%.2f yaw=%g°' % (n, where, x, y, z, yaw))


def main(argv):
    ap = argparse.ArgumentParser(prog='drone_pose',
                                 description='Стартовая позиция дрона: drone_pose <дрон> <метка> [--yaw град]; '
                                             'drone_pose <дрон> — позиция по умолчанию; drone_pose list')
    ap.add_argument('drone', help='номер дрона или list')
    ap.add_argument('marker', nargs='?', type=int, help='номер ArUco-метки активного поля Gazebo')
    ap.add_argument('--yaw', type=float, default=0.0, help='курс, градусы (по умолчанию 0)')
    ap.add_argument('--force', action='store_true', help='переставить, даже если статус arm определить не удалось')
    args = ap.parse_args(argv)

    if args.drone == 'list':
        return cmd_list()
    try:
        n = int(args.drone)
    except ValueError:
        common.die('номер дрона должен быть числом или list')
    top, live = _range()
    common.check_drone_id(n, top)

    if args.marker is not None:
        fpath = field.active()
        if field.marker(fpath, args.marker) is None:
            common.die('метки %d нет в активном поле (%s)' % (args.marker, os.path.basename(fpath)))
        data = poses.load()
        for other, e in data['drones'].items():
            if other != n and e.get('marker') == args.marker:
                common.die('метка %d уже занята дроном %d' % (args.marker, other))

    if live and containers.running(n):
        armed = containers.is_armed(n)
        if armed:
            common.die('drone%d армлен — переставлять нельзя. Сначала посадите и дизармите дрон.' % n)
        if armed is None and not args.force:
            common.die('не удалось узнать, армлен ли drone%d (mavros не отвечает). '
                       'Запустите clover или используйте --force.' % n)

    if args.marker is not None:
        poses.set_marker(n, args.marker, args.yaw)
    else:
        poses.reset(n)
    x, y, z, yaw, mid = poses.resolve(n)
    print('drone%d: %s (x=%.2f y=%.2f z=%.2f yaw=%g°)' %
          (n, 'метка %d' % mid if mid is not None else 'позиция по умолчанию', x, y, z, yaw))

    if live and containers.running(n):
        teleport(n, x, y, z, yaw)
        containers.restart_px4(n)
        print('Дрон переставлен, PX4 перезапущен.')
    else:
        print('Позиция сохранена, применится при следующем запуске simulate.py.')

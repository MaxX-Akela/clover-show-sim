import os

import yaml

from . import common, field

GROUND_GAP = 0.15
DEFAULT_SPACING = 1.0


def load():
    if not os.path.exists(common.POSES_FILE):
        return {'spacing': DEFAULT_SPACING, 'drones': {}}
    with open(common.POSES_FILE) as f:
        data = yaml.safe_load(f) or {}
    data.setdefault('spacing', DEFAULT_SPACING)
    data['drones'] = {int(k): v for k, v in (data.get('drones') or {}).items()}
    return data


def save(data):
    os.makedirs(common.USER_DIR, exist_ok=True)
    with open(common.POSES_FILE, 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def default_pose(n, spacing):
    return {'x': (n - 1) * spacing, 'y': 0.0, 'z': GROUND_GAP, 'yaw': 0.0}


def resolve(n, data=None, field_path=None):
    data = data or load()
    entry = data['drones'].get(n)
    if entry and entry.get('marker') is not None:
        m = field.marker(field_path or field.active(), entry['marker'])
        if m is None:
            raise ValueError('метки %d нет в активном поле' % entry['marker'])
        return (m.x, m.y, m.z + GROUND_GAP, float(entry.get('yaw', 0.0)), m.id)
    d = default_pose(n, data['spacing'])
    return (d['x'], d['y'], d['z'], d['yaw'], None)


def set_marker(n, marker_id, yaw, field_path=None):
    data = load()
    field_path = field_path or field.active()
    if field.marker(field_path, marker_id) is None:
        common.die('метки %d нет в активном поле (%s)' % (marker_id, os.path.basename(field_path)))
    for other, e in data['drones'].items():
        if other != n and e.get('marker') == marker_id:
            common.die('метка %d уже занята дроном %d' % (marker_id, other))
    data['drones'][n] = {'marker': marker_id, 'yaw': float(yaw)}
    save(data)
    return data


def reset(n):
    data = load()
    data['drones'].pop(n, None)
    save(data)
    return data

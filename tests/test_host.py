import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'host'))

from cshow import common, field, poses, px4, urdf, wire


class TmpHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ('STATE_DIR', 'PX4_DIR', 'MODELS_DIR', 'FIELD_LINK', 'WORLD_FILE', 'USER_DIR',
                     'DRONES_DIR', 'POSES_FILE'):
            self._patch(name, getattr(common, name).replace(common.HOME, self.tmp))
        px4.CURRENT = os.path.join(common.PX4_DIR, 'current')

    def _patch(self, name, value):
        setattr(common, name, value)

    def tearDown(self):
        shutil.rmtree(self.tmp)


class FieldAndPoses(TmpHome):
    def test_fields_have_expected_markers(self):
        self.assertEqual(len(field.parse(os.path.join(ROOT, 'fields', 'field4x4.txt'))), 16)
        self.assertEqual(len(field.parse(os.path.join(ROOT, 'fields', 'field6x6.txt'))), 36)

    def test_default_poses_on_line(self):
        data = poses.load()
        self.assertEqual([poses.resolve(i, data)[:2] for i in (1, 2, 3)], [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
        data['spacing'] = 1.5
        self.assertEqual(poses.resolve(3, data)[0], 3.0)

    def test_marker_pose_uses_active_field_and_gap(self):
        poses.save({'spacing': 1.0, 'drones': {1: {'marker': 5, 'yaw': 90}}})
        x, y, z, yaw, mid = poses.resolve(1)
        self.assertEqual((x, y, mid, yaw), (1.0, 1.0, 5, 90.0))
        self.assertAlmostEqual(z, poses.GROUND_GAP)

    def test_missing_marker_and_duplicate(self):
        with self.assertRaises(SystemExit):
            poses.set_marker(1, 99, 0)
        poses.set_marker(1, 5, 0)
        with self.assertRaises(SystemExit):
            poses.set_marker(2, 5, 0)

    def test_custom_field_parse_comments_and_short_lines(self):
        p = os.path.join(self.tmp, 'f.txt')
        open(p, 'w').write('# c\n7 0.2 1.5 2.5\nbad\n8 0.2 3 4 0.1 0.5\n')
        m = field.parse(p)
        self.assertEqual([(x.id, x.x, x.y, x.z, x.yaw) for x in m], [(7, 1.5, 2.5, 0.0, 0.0), (8, 3.0, 4.0, 0.1, 0.5)])


class Wire(unittest.TestCase):
    def test_roundtrip(self):
        a, b = socket.socketpair()
        data = os.urandom(300000)
        threading.Thread(target=lambda: a.sendall(wire.pack(wire.KIND_MSG, 3, data)), daemon=True).start()
        self.assertEqual(wire.read_frame(b), (wire.KIND_MSG, 3, data))


class Px4Detect(TmpHome):
    SRC = os.path.join(os.environ.get('PX4_SRC_DIR', ''), '')

    def _fake_build(self, rom):
        d = os.path.join(self.tmp, 'build')
        os.makedirs(os.path.join(d, 'bin'))
        open(os.path.join(d, 'bin', 'px4'), 'w').close()
        shutil.copytree(rom, os.path.join(d, 'etc'))
        return d

    @unittest.skipUnless(os.environ.get('PX4_SRC_DIR'), 'нужен PX4_SRC_DIR с px4-v1.13.3 и px4-v1.15.4')
    def test_branch_detection(self):
        for ver, branch in (('v1.13.3', '1.13'), ('v1.15.4', '1.14')):
            rom = os.path.join(os.environ['PX4_SRC_DIR'], 'px4-' + ver, 'ROMFS', 'px4fmu_common')
            d = self._fake_build(rom)
            self.assertEqual(px4.branch_of(d), branch)
            shutil.rmtree(d)

    def test_broken_build_gives_clear_error(self):
        d = os.path.join(self.tmp, 'empty')
        os.makedirs(d)
        with self.assertRaises(px4.Px4Error):
            px4.branch_of(d)

    def test_backup_params_on_version_change(self):
        pdir = os.path.join(common.drone_dir(1), 'px4')
        os.makedirs(pdir)
        open(os.path.join(pdir, 'parameters.bson'), 'w').close()
        self.assertTrue(px4.backup_params(1, '1.13.3'))
        self.assertTrue(os.path.exists(os.path.join(common.drone_dir(1), 'params-1.13.3.bak', 'parameters.bson')))
        self.assertEqual(os.listdir(pdir), [])


class Urdf(unittest.TestCase):
    RAW = os.environ.get('RAW_URDF')

    @unittest.skipUnless(os.environ.get('RAW_URDF'), 'нужен RAW_URDF — вывод xacro clover4.xacro')
    def test_ports_and_namespaces(self):
        with open(self.RAW) as f:
            raw = f.read()
        for n in (1, 2, 3):
            root = ET.fromstring(urdf.postprocess(raw, n))
            ports = [p.find('mavlink_tcp_port').text for p in root.iter('plugin') if p.find('mavlink_tcp_port') is not None]
            self.assertEqual(ports, [str(4560 + n - 1)])
            for p in root.iter('plugin'):
                self.assertEqual(p.find('robotNamespace').text, 'drone%d' % n)
            self.assertEqual([t.text for t in root.iter('topicName')], ['rangefinder/range'])


if __name__ == '__main__':
    unittest.main()

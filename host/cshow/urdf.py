import subprocess
import xml.etree.ElementTree as ET

from . import common

XACRO_ARGS = ['main_camera:=true', 'rangefinder:=true', 'led:=true', 'gps:=false',
              'maintain_camera_rate:=false', 'use_clover_physics:=false']


def run_xacro(xacro_file):
    return subprocess.check_output(['xacro', xacro_file] + XACRO_ARGS, universal_newlines=True)


def postprocess(urdf_text, n):
    ns = common.drone_name(n)
    root = ET.fromstring(urdf_text)
    root.set('name', ns)
    for plugin in root.iter('plugin'):
        rn = plugin.find('robotNamespace')
        if rn is None:
            rn = ET.SubElement(plugin, 'robotNamespace')
        rn.text = ns
        if plugin.get('filename') == 'libgazebo_mavlink_interface.so':
            port = plugin.find('mavlink_tcp_port')
            if port is None:
                raise ValueError('в mavlink_interface нет mavlink_tcp_port (изменился xacro Клевера?)')
            port.text = str(common.SIM_TCP_BASE + n - 1)
        if plugin.get('filename') == 'libgazebo_ros_range.so':
            topic = plugin.find('topicName')
            if topic is not None and topic.text.startswith('/'):
                topic.text = topic.text.lstrip('/')
    return ET.tostring(root, encoding='unicode')

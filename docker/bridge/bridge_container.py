#!/usr/bin/env python3
import json
import os
import socket
import threading
import time

import roslib.message
import rospy
from led_msgs.msg import LEDStateArray

import wire

HOST = os.environ.get('CLOVER_SHOW_BRIDGE_HOST', 'host.docker.internal')
PORT = int(os.environ['CLOVER_SHOW_BRIDGE_PORT'])


class Bridge(object):
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        rospy.Subscriber('/led/state', LEDStateArray, self.on_led, queue_size=1)

    def on_led(self, msg):
        leds = sorted(msg.leds, key=lambda l: l.index)
        payload = b''.join(bytes((l.r, l.g, l.b)) for l in leds)
        with self.lock:
            sock = self.sock
        if sock is not None:
            try:
                sock.sendall(wire.pack(wire.KIND_LED, 0, payload))
            except OSError:
                pass

    def session(self):
        sock = socket.create_connection((HOST, PORT), timeout=5)
        sock.settimeout(None)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        kind, _, payload = wire.read_frame(sock)
        if kind != wire.KIND_HELLO:
            raise ValueError('ожидался HELLO')
        pubs = []
        for t in json.loads(payload.decode()):
            cls = roslib.message.get_message_class(t['type'])
            if cls is None:
                raise ValueError('неизвестный тип %s' % t['type'])
            pubs.append((rospy.Publisher(t['name'], cls, queue_size=2), cls))
        rospy.loginfo('мост подключён к %s:%d', HOST, PORT)
        with self.lock:
            self.sock = sock
        try:
            while not rospy.is_shutdown():
                kind, idx, data = wire.read_frame(sock)
                if kind == wire.KIND_MSG and idx < len(pubs):
                    pub, cls = pubs[idx]
                    m = cls()
                    m.deserialize(data)
                    pub.publish(m)
        finally:
            with self.lock:
                self.sock = None
            sock.close()
            for pub, _ in pubs:
                pub.unregister()

    def run(self):
        while not rospy.is_shutdown():
            try:
                self.session()
            except (OSError, ConnectionError, ValueError) as e:
                rospy.logwarn_throttle(30, 'мост: %s, повтор через 2 с', e)
            time.sleep(2)


if __name__ == '__main__':
    rospy.init_node('sim_bridge')
    Bridge().run()

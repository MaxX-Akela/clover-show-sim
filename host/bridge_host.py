#!/usr/bin/env python3
import argparse
import json
import os
import socket
import sys
import threading
import time

import rospy
from led_msgs.msg import LEDState
from led_msgs.srv import SetLEDs

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from cshow import common, wire

LED_MAX_RATE = 10.0


def topics_for(n):
    ns = '/' + common.drone_name(n)
    return [
        (ns + '/main_camera/image_raw', '/main_camera/image_raw', 'sensor_msgs/Image'),
        (ns + '/main_camera/camera_info', '/main_camera/camera_info', 'sensor_msgs/CameraInfo'),
        (ns + '/rangefinder/range', '/rangefinder/range', 'sensor_msgs/Range'),
        ('/clock', '/clock', 'rosgraph_msgs/Clock'),
    ]


class Link(object):

    def __init__(self, n):
        self.n = n
        self.topics = topics_for(n)
        self.lock = threading.Condition()
        self.pending = {}
        self.conn = None
        self.led = None
        self.led_lock = threading.Lock()
        self.led_event = threading.Event()
        self.subs = [rospy.Subscriber(h, rospy.AnyMsg, self._on_msg, callback_args=i, queue_size=1)
                     for i, (h, _, _) in enumerate(self.topics)]
        threading.Thread(target=self._led_worker, daemon=True).start()
        threading.Thread(target=self._serve, daemon=True).start()

    def _on_msg(self, msg, idx):
        with self.lock:
            if self.conn is None:
                return
            self.pending[idx] = msg._buff
            self.lock.notify()

    def _serve(self):
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('0.0.0.0', common.BRIDGE_PORT_BASE + self.n))
        srv.listen(1)
        while not rospy.is_shutdown():
            conn, _ = srv.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            rospy.loginfo('drone%d: мост подключён', self.n)
            try:
                hello = json.dumps([{'name': c, 'type': t} for _, c, t in self.topics]).encode()
                conn.sendall(wire.pack(wire.KIND_HELLO, 0, hello))
                with self.lock:
                    self.pending.clear()
                    self.conn = conn
                threading.Thread(target=self._reader, args=(conn,), daemon=True).start()
                self._writer(conn)
            except (OSError, ConnectionError):
                pass
            finally:
                with self.lock:
                    self.conn = None
                conn.close()
                rospy.logwarn('drone%d: мост отключён', self.n)

    def _writer(self, conn):
        while not rospy.is_shutdown():
            with self.lock:
                while not self.pending and self.conn is conn:
                    self.lock.wait(1.0)
                if self.conn is not conn:
                    return
                batch, self.pending = self.pending, {}
            for idx, data in batch.items():
                conn.sendall(wire.pack(wire.KIND_MSG, idx, data))

    def _reader(self, conn):
        try:
            while True:
                kind, _, payload = wire.read_frame(conn)
                if kind == wire.KIND_LED:
                    with self.led_lock:
                        self.led = payload
                    self.led_event.set()
        except (OSError, ConnectionError, ValueError):
            with self.lock:
                if self.conn is conn:
                    self.conn = None
                    self.lock.notify_all()
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _led_worker(self):
        srv_name = '/%s/led/set_leds' % common.drone_name(self.n)
        proxy = None
        last_call = 0.0
        while not rospy.is_shutdown():
            if not self.led_event.wait(0.5):
                continue
            wait = last_call + 1.0 / LED_MAX_RATE - time.time()
            if wait > 0:
                time.sleep(wait)
            self.led_event.clear()
            with self.led_lock:
                data = self.led
            if not data:
                continue
            try:
                if proxy is None:
                    rospy.wait_for_service(srv_name, timeout=5)
                    proxy = rospy.ServiceProxy(srv_name, SetLEDs)
                leds = [LEDState(index=i, r=data[3 * i], g=data[3 * i + 1], b=data[3 * i + 2])
                        for i in range(len(data) // 3)]
                proxy(leds)
            except (rospy.ROSException, rospy.ServiceException):
                proxy = None
            last_call = time.time()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, default=common.DEFAULT_DRONES)
    args = ap.parse_args()
    rospy.init_node('clover_show_bridge')
    links = [Link(i) for i in range(1, args.n + 1)]
    rospy.loginfo('мост запущен для %d дронов', len(links))
    rospy.spin()


if __name__ == '__main__':
    main()

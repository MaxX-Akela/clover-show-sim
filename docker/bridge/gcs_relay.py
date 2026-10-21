#!/usr/bin/env python3
import select
import socket
import sys

GCS_PORT = 14550


def main(host, px4_port):
    inner = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    inner.bind(('127.0.0.1', GCS_PORT))
    outer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    outer.bind(('0.0.0.0', 0))
    while True:
        ready, _, _ = select.select([inner, outer], [], [])
        for s in ready:
            data, _ = s.recvfrom(65535)
            if s is inner:
                outer.sendto(data, (host, GCS_PORT))
            else:
                inner.sendto(data, ('127.0.0.1', px4_port))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 18570)

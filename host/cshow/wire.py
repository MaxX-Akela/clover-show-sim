import struct

KIND_HELLO = 0
KIND_MSG = 1
KIND_LED = 2
_HDR = struct.Struct('>BBI')
MAX_PAYLOAD = 64 * 1024 * 1024


def pack(kind, idx, payload):
    return _HDR.pack(kind, idx, len(payload)) + payload


def _recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(n - len(buf), 1 << 20))
        if not chunk:
            raise ConnectionError('соединение закрыто')
        buf += chunk
    return bytes(buf)


def read_frame(sock):
    kind, idx, length = _HDR.unpack(_recv_exact(sock, _HDR.size))
    if length > MAX_PAYLOAD:
        raise ValueError('слишком большой кадр: %d' % length)
    return kind, idx, _recv_exact(sock, length)

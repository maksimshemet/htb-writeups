"""Direct-hosted SMB transport (TCP/445) -- the NBSS-style framing layer.

This part is pure networking boilerplate, not SMB-specific parsing, so
it's implemented for you. On port 139 you'd need an actual NetBIOS
Session Request/Response handshake first; port 445 skips that and lets
you send SMB messages straight away, each wrapped in the 4-byte header
described in constants.py.
"""

import socket

from smb_enum_legacy.constants import NBSS_SESSION_MESSAGE

DEFAULT_PORT = 445


def connect(host: str, port: int = DEFAULT_PORT, timeout: float = 5.0) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    return sock


def send_smb(sock: socket.socket, payload: bytes) -> None:
    """Wrap an SMB message in its NBSS header and send it."""
    if len(payload) > 0xFFFFFF:
        raise ValueError("SMB payload too large for a single NBSS frame")
    # NBSS length is a 24-bit big-endian int, which doesn't map to a
    # native struct size, so build the header explicitly:
    header = bytes([NBSS_SESSION_MESSAGE]) + len(payload).to_bytes(3, "big")
    sock.sendall(header + payload)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed while reading SMB response")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_smb(sock: socket.socket) -> bytes:
    """Read one NBSS-framed SMB message and return just the SMB payload."""
    header = _recv_exact(sock, 4)
    msg_type = header[0]
    length = int.from_bytes(header[1:4], "big")
    if msg_type != NBSS_SESSION_MESSAGE:
        raise ValueError(f"unexpected NBSS message type: {msg_type:#x}")
    return _recv_exact(sock, length)

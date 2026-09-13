"""Pack/unpack the 32-byte SMB1 header. This is YOUR part to implement.

Layout (all multi-byte fields little-endian unless noted):

  offset  size  field
  0       4     Protocol            -- always b"\\xffSMB" (constants.SMB_PROTOCOL)
  4       1     Command             -- e.g. constants.SMB_COM_NEGOTIATE
  5       4     Status              -- 0 on a request
  9       1     Flags
  10      2     Flags2
  12      2     PIDHigh
  14      8     SecurityFeatures    -- 0 for negotiate; signature/session key later
  22      2     Reserved            -- 0
  24      2     TID
  26      2     PIDLow
  28      2     UID
  30      2     MID

That's 32 bytes total. struct.pack format hint: "<4sBLBHH8sHHHHH"
(check the sizes add up to 32 -- they should).
"""

import struct

from smb_enum_legacy.constants import SMB_PROTOCOL

SMB_HEADER_SIZE = 32

fmt = "<4sBIBHH8sHHHHH"


def pack_smb_header(
    command: int,
    *,
    status: int = 0,
    flags: int = 0,
    flags2: int = 0,
    pid: int = 0,
    tid: int = 0,
    uid: int = 0,
    mid: int = 0,
) -> bytes:
    """Build the 32-byte SMB header.

    TODO: use struct.pack to lay out the fields per the docstring above.
    Split `pid` into PIDHigh (upper 16 bits) and PIDLow (lower 16 bits).
    SecurityFeatures and Reserved are always zero at this stage.
    """

    if (struct.calcsize(fmt) != SMB_HEADER_SIZE):
        raise ValueError

    pidHigh = (pid >> 16) & 0xFFFF
    pidLow = pid & 0xFFFF

    securityFeatures = b"\x00" * 8
    reserved = 0

    return struct.pack(
        fmt,
        SMB_PROTOCOL,
        command,
        status,
        flags,
        flags2,
        pidHigh,
        securityFeatures,
        reserved,
        tid,
        pidLow,
        uid,
        mid
    )


def unpack_smb_header(data: bytes) -> dict[str, int]:
    """Parse the first 32 bytes of an SMB message into a dict of fields.

    TODO: struct.unpack the header and return at least:
      {"command": int, "status": int, "flags": int, "flags2": int,
       "pid": int, "tid": int, "uid": int, "mid": int}
    Also validate data[0:4] == SMB_PROTOCOL and raise ValueError if not --
    that's your basic sanity check that you're actually talking to an
    SMB server and not something else entirely.
    """
    if data[0:4] != SMB_PROTOCOL:
        raise ValueError

    try:
        (
            _protocol,
            command,
            status,
            flags,
            flags2,
            pidHigh,
            _securityFeatures,
            _reserved,
            tid,
            pidLow,
            uid,
            mid,
        ) = struct.unpack(fmt, data)
    except struct.error as e:
        raise ValueError("malformed SMB header") from e

    pid = (pidHigh << 16) | pidLow

    return {
        "command": command,
        "status": status,
        "flags": flags,
        "flags2": flags2,
        "pid": pid,
        "tid": tid,
        "uid": uid,
        "mid": mid,
    }

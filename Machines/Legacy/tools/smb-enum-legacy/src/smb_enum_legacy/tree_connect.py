"""SMB_COM_TREE_CONNECT_ANDX -- connect to a share (IPC$ for enumeration).

Requires a session UID from session_setup.py first -- this request's SMB
header must carry that UID, or the server has no idea which session it
belongs to.

REQUEST (WordCount = 4, 8 bytes of fixed parameters):
  offset  size  field
  0       1     AndXCommand      -- 0xFF, no chained command
  1       1     AndXReserved     -- 0
  2       2     AndXOffset       -- 0
  4       2     Flags            -- 0 for a plain connect
  6       2     PasswordLength   -- length of the Password data that follows
Then ByteCount(2) + Data:
  Password[PasswordLength]  -- share-level security only; for a null/user
                               session this is typically just one null byte
  Path (null-terminated ASCII)   -- UNC path, e.g. \\\\HOST\\IPC$
  Service (null-terminated ASCII) -- "?????" means "any type, tell me what it is"

RESPONSE (WordCount = 2 or 3 -- some servers add an OptionalSupport word):
  offset  size  field
  0       1     AndXCommand
  1       1     AndXReserved
  2       2     AndXOffset
  4       2     OptionalSupport  -- only present when WordCount == 3
Then ByteCount(2) + Data: Service (ASCII, null-terminated),
NativeFileSystem (ASCII, null-terminated). The connected share's TID is
NOT in this body -- like UID for session setup, it's in the SMB header's
TID field of the response.
"""

import struct

from smb_enum_legacy import smb_header
from smb_enum_legacy.constants import ANDX_NO_FURTHER_COMMAND, SMB_COM_TREE_CONNECT_ANDX


def build_tree_connect_request(unc_path: str, *, uid: int, mid: int = 0, service: str = "?????") -> bytes:
    """Build a TREE_CONNECT_ANDX request for `unc_path` (e.g. r"\\\\10.0.0.5\\IPC$")."""

    password = b"\x00"  # 1 null byte -- ignored under user-level security, but conventional to send

    fixed = struct.pack(
        "<BBHHH",
        ANDX_NO_FURTHER_COMMAND,  # AndXCommand
        0,  # AndXReserved
        0,  # AndXOffset
        0,  # Flags
        len(password),  # PasswordLength
    )

    path_field = unc_path.encode("ascii") + b"\x00"
    service_field = service.encode("ascii") + b"\x00"
    data = password + path_field + service_field

    word_count = 4
    body = struct.pack("<B", word_count) + fixed + struct.pack("<H", len(data)) + data

    header = smb_header.pack_smb_header(SMB_COM_TREE_CONNECT_ANDX, uid=uid, mid=mid)
    return header + body


def parse_tree_connect_response(data: bytes) -> dict:
    """Parse a TREE_CONNECT_ANDX response."""

    header = smb_header.unpack_smb_header(data[:32])
    if header["status"] != 0:
        return {"success": False, "status": header["status"], "header": header}

    word_count = data[32]
    params_len = word_count * 2
    params = data[33:33 + params_len]

    # OptionalSupport is only present when the server sent WordCount == 3;
    # treat it as absent (None) for the more minimal WordCount == 2 case.
    if word_count >= 3:
        _andx_command, _andx_reserved, _andx_offset, optional_support = struct.unpack("<BBHH", params[:6])
    else:
        _andx_command, _andx_reserved, _andx_offset = struct.unpack("<BBH", params[:4])
        optional_support = None

    byte_count_offset = 33 + params_len
    byte_count, = struct.unpack("<H", data[byte_count_offset:byte_count_offset + 2])
    body_data = data[byte_count_offset + 2:byte_count_offset + 2 + byte_count]

    strings = [s.decode("ascii", errors="replace") for s in body_data.split(b"\x00") if s]

    return {
        "success": True,
        "tid": header["tid"],  # server-assigned tree ID, needed for the RAP transaction next
        "optional_support": optional_support,
        "service": strings[0] if len(strings) > 0 else None,
        "native_file_system": strings[1] if len(strings) > 1 else None,
    }

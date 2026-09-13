"""RAP NetShareEnum over SMB_COM_TRANSACTION to \\PIPE\\LANMAN.

This is THE classic legacy-SMB1 share enumeration trick (predates the
DCERPC/SRVSVC-based enumeration modern tools use): a generic "Transaction"
addressed by name to a special virtual pipe, "\\PIPE\\LANMAN", carrying an
old, separate mini-protocol called RAP (Remote Administration Protocol)
inside the transaction's Parameters/Data blocks. RAP predates SMB1 itself
and has its own encoding conventions layered on top -- this is the part
most worth double-checking against a real capture, since RAP descriptor
strings are notoriously fiddly.

SMB_COM_TRANSACTION REQUEST (WordCount = 14 with SetupCount = 0):
  offset  size  field
  0       2     TotalParameterCount   -- total size of Trans_Parameters (may span multiple packets; we send it all in one, so equals ParameterCount)
  2       2     TotalDataCount        -- same idea for Trans_Data (0 for our request, RAP sends no request data)
  4       2     MaxParameterCount     -- how many parameter bytes we can accept back
  6       2     MaxDataCount          -- how many data bytes we can accept back
  8       1     MaxSetupCount         -- 0, we don't expect setup words back
  9       1     Reserved1
  10      2     Flags                 -- 0
  12      4     Timeout               -- 0 = no explicit timeout
  16      2     Reserved2
  18      2     ParameterCount        -- bytes of Trans_Parameters in *this* packet
  20      2     ParameterOffset       -- absolute offset from SMB header start to Trans_Parameters
  22      2     DataCount             -- bytes of Trans_Data in this packet (0 here)
  24      2     DataOffset            -- absolute offset from SMB header start to Trans_Data
  26      1     SetupCount            -- 0 for RAP (no setup words)
  27      1     Reserved3
Then ByteCount(2) + Data:
  Setup[SetupCount] words       -- none, SetupCount == 0
  Name (null-terminated ASCII)  -- "\\PIPE\\LANMAN", identifies this as a RAP call
  padding to align Trans_Parameters (offsets are explicit anyway, but
    real servers expect 4-byte alignment from the start of the SMB header)
  Trans_Parameters              -- the actual RAP call: function code +
                                    descriptor strings + call arguments
  padding, then Trans_Data      -- empty for our request

RAP call layout inside Trans_Parameters, for NetShareEnum specifically:
  H       Function       -- 0x0000 = NetShareEnum
  STRZ    ParamDesc       -- "WrLeh\\0": describes the fixed args below and
                             the *shape* of the response's output params
                             (W=input word, r=receive-buffer pointer,
                             L=receive-buffer length, e=entries returned,
                             h=total entries available)
  STRZ    DataDesc        -- "B13BWz\\0": shape of each returned share
                             record (share_info_1, see below)
  H       InfoLevel       -- 1 (share_info_1 -- name/type/comment)
  H       ReceiveBufferSize -- how much Data space we're telling the
                               server it can use for the reply

RESPONSE (WordCount = 10, SetupCount = 0):
  Same shaped fixed parameter block as the request but for the reply
  side (ParameterCount/Offset and DataCount/Offset now describe where
  the *response's* Trans_Parameters/Trans_Data actually landed in this
  packet) -- 9 H-sized fields then SetupCount(B)+Reserved(B) = 20 bytes = 10 words.

RAP response Trans_Parameters (NetShareEnum): 4 fixed 16-bit fields:
  H  Result          -- RAP status code, 0 = success
  H  Converter       -- offset-translation constant for 'z' string
                        pointers in the Data section (see below)
  H  EntryCount      -- number of share_info_1 records actually returned
  H  AvailableCount  -- total number of shares on the server (may be
                        larger than EntryCount if our buffer was too small)

RAP response Trans_Data: EntryCount consecutive share_info_1 records,
each exactly 20 bytes (matches DataDesc "B13BWz"):
  13s  NetName    -- share name, null-padded within the 13 bytes
  B    Pad        -- 1 byte alignment filler (NetName is 13 bytes, odd)
  H    ShareType  -- 0=disk, 1=printer, 2=device, 3=IPC; bit 0x8000 set
                     marks a hidden/admin share (e.g. C$, IPC$)
  I    RemarkPtr  -- NOT a real offset into Trans_Data as-is: the actual
                     offset is `RemarkPtr - Converter`, pointing at a
                     null-terminated comment string living in Trans_Data
                     after all the fixed 20-byte records.
"""

import struct

from smb_enum_legacy import smb_header
from smb_enum_legacy.constants import SMB_COM_TRANSACTION

PIPE_NAME = b"\\PIPE\\LANMAN\x00"
NET_SHARE_ENUM_FUNCTION = 0x0000
PARAM_DESC = b"WrLeh\x00"
DATA_DESC = b"B13BWz\x00"
SHARE_INFO_1_SIZE = 20


def _pad4(buf: bytes) -> bytes:
    """Pad `buf` with zero bytes up to the next multiple of 4 bytes.

    Real servers expect the Parameters/Data sections of a transaction to
    start on a 4-byte boundary measured from the start of the SMB header,
    even though the *Offset fields are explicit and self-describing.
    """
    remainder = len(buf) % 4
    if remainder == 0:
        return buf
    return buf + b"\x00" * (4 - remainder)


def build_net_share_enum_request(*, uid: int, tid: int, mid: int = 0, receive_buffer_size: int = 8192) -> bytes:
    """Build a RAP NetShareEnum request (SMB_COM_TRANSACTION to \\PIPE\\LANMAN)."""

    info_level = 1  # share_info_1: name, type, comment
    rap_params = (
        struct.pack("<H", NET_SHARE_ENUM_FUNCTION)
        + PARAM_DESC
        + DATA_DESC
        + struct.pack("<HH", info_level, receive_buffer_size)
    )
    rap_data = b""  # NetShareEnum sends no request data, only parameters

    # Everything from here after the header is built up incrementally so
    # the offset fields can be computed from real lengths, not guessed
    # fixed numbers -- unlike WordCount-based commands, transaction
    # offsets are measured from the very start of the SMB header (byte 0
    # of the whole message, same indexing as smb_header uses).
    header_size = 32
    fixed_params_size = 28  # 14 words -- see layout table above

    name_and_pad = _pad4(PIPE_NAME)
    parameter_offset = header_size + 1 + fixed_params_size + 2 + len(name_and_pad)
    # +1 for WordCount byte, +2 for ByteCount (comes right after the
    # fixed parameter block, before Setup/Name/data -- see build order below).

    params_and_pad = _pad4(rap_params)
    data_offset = parameter_offset + len(params_and_pad)

    fixed_params = struct.pack(
        "<HHHHBBHIHHHHHBB",
        len(rap_params),  # TotalParameterCount
        len(rap_data),  # TotalDataCount
        1024,  # MaxParameterCount -- generous headroom for the reply
        max(receive_buffer_size, 4096),  # MaxDataCount
        0,  # MaxSetupCount
        0,  # Reserved1
        0,  # Flags
        0,  # Timeout
        0,  # Reserved2
        len(rap_params),  # ParameterCount (all of it fits in this one packet)
        parameter_offset,  # ParameterOffset
        len(rap_data),  # DataCount
        data_offset,  # DataOffset
        0,  # SetupCount
        0,  # Reserved3
    )

    variable_data = name_and_pad + params_and_pad + rap_data
    body = struct.pack("<B", 14) + fixed_params + struct.pack("<H", len(variable_data)) + variable_data

    header = smb_header.pack_smb_header(SMB_COM_TRANSACTION, uid=uid, tid=tid, mid=mid)
    return header + body


def parse_net_share_enum_response(data: bytes) -> dict:
    """Parse a RAP NetShareEnum response into a list of shares."""

    header = smb_header.unpack_smb_header(data[:32])
    if header["status"] != 0:
        return {"success": False, "status": header["status"], "header": header}

    word_count = data[32]
    params_len = word_count * 2
    fixed = struct.unpack("<HHHHHHHHHBB", data[33:33 + params_len])
    (
        _total_param_count,
        _total_data_count,
        _reserved1,
        parameter_count,
        parameter_offset,
        _parameter_displacement,
        data_count,
        data_offset,
        _data_displacement,
        _setup_count,
        _reserved2,
    ) = fixed

    # Trust the server's own offsets rather than recomputing positions --
    # that's the whole point of Parameter/DataOffset being explicit.
    trans_params = data[parameter_offset:parameter_offset + parameter_count]
    trans_data = data[data_offset:data_offset + data_count]

    rap_result, converter, entry_count, available_count = struct.unpack("<HHHH", trans_params[:8])

    shares = []
    for i in range(entry_count):
        chunk = trans_data[i * SHARE_INFO_1_SIZE:(i + 1) * SHARE_INFO_1_SIZE]
        netname_raw, _pad, share_type, remark_ptr = struct.unpack("<13sBHI", chunk)
        netname = netname_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")

        remark = ""
        remark_offset = remark_ptr - converter
        if 0 <= remark_offset < len(trans_data):
            end = trans_data.find(b"\x00", remark_offset)
            if end == -1:
                end = len(trans_data)
            remark = trans_data[remark_offset:end].decode("ascii", errors="replace")

        shares.append({
            "name": netname,
            "type": share_type,
            "hidden": bool(share_type & 0x8000),
            "remark": remark,
        })

    return {
        "success": True,
        "rap_result": rap_result,
        "entry_count": entry_count,
        "available_count": available_count,
        "shares": shares,
    }

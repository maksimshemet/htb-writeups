"""SMB_COM_NEGOTIATE request/response -- YOUR part to implement.

This is the very first SMB exchange: the client offers a list of
dialect strings, the server picks the best one it understands (or none,
if it doesn't speak SMB1 at all). Handling that "none" case is itself
useful recon signal for this tool.

REQUEST BODY (comes after the 32-byte SMB header):
  offset  size  field
  0       1     WordCount     -- 0 for negotiate request (no parameter words)
  1       2     ByteCount     -- length in bytes of everything below
  3       ...   Dialects      -- each: 0x02 + ascii bytes + 0x00

RESPONSE BODY when the server picks "NT LM 0.12" (the common case):
  offset  size  field
  0       1     WordCount           -- 17 (0x11)
  1       2     DialectIndex        -- which offered dialect it picked
  3       1     SecurityMode        -- bit 0: user vs share level;
                                       bit 1: challenge/response enabled
  4       2     MaxMpxCount
  6       2     MaxNumberVcs
  8       4     MaxBufferSize
  12      4     MaxRawSize
  16      4     SessionKey
  20      4     Capabilities        -- bit flags: unicode, NT SMBs, extended
                                       security, etc.
  24      8     SystemTime          -- Windows FILETIME (100ns ticks since 1601)
  32      2     ServerTimeZone      -- minutes from UTC
  34      1     ChallengeLength (a.k.a. KeyLength)
  35      2     ByteCount
  37      ...   Data: challenge bytes (ChallengeLength of them) then
                domain/server name, OR if extended security is negotiated
                (SecurityMode/Capabilities say so), a 16-byte server GUID
                + an optional security blob instead.

If DialectIndex == 0xFFFF, the server rejected every dialect you offered
(i.e. it does not support SMB1 at all, or not any you listed) --
WordCount will be 0 in that case and there's no body to parse.
"""

import struct
from datetime import datetime, timedelta, timezone

from smb_enum_legacy import smb_header
from smb_enum_legacy.constants import (
    CAP_EXTENDED_SECURITY,
    DIALECT_BUFFER_FORMAT,
    LEGACY_DIALECTS,
    SMB_COM_NEGOTIATE,
    SMB_FLAGS2_UNICODE,
)

# Windows FILETIME epoch (1601-01-01 UTC) expressed as a Python datetime,
# so SystemTime (100ns ticks since that epoch) can be converted directly.
_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def build_negotiate_request(dialects: list[str] = LEGACY_DIALECTS, *, mid: int = 0) -> bytes:
    """Build a full SMB message (header + negotiate body) ready to send."""

    # Each dialect becomes: 0x02 (format marker, always this exact byte) +
    # the ASCII name + a null terminator. bytes([DIALECT_BUFFER_FORMAT])
    # turns the int 0x02 into a 1-byte `bytes` object so it can be
    # concatenated with the encoded string. join() glues all four
    # dialects' chunks into one contiguous blob, e.g.:
    #   b"\x02NT LM 0.12\x00" for a single dialect, four of those back to back.
    dialect_buffer = b"".join(
        bytes([DIALECT_BUFFER_FORMAT]) + dialect.encode("ascii") + b"\x00"
        for dialect in dialects
    )

    # NEGOTIATE has no fixed parameter words, so WordCount is always 0.
    # ByteCount just tells the receiver how many bytes of variable data
    # (the dialect buffer) follow -- without it, the receiver wouldn't
    # know where the dialect list ends.
    word_count = 0
    byte_count = len(dialect_buffer)

    # "<BH": WordCount as 1 unsigned byte, ByteCount as a 2-byte
    # little-endian unsigned short -- matches their sizes in the body
    # layout table. Then the dialect buffer itself follows immediately.
    body = struct.pack("<BH", word_count, byte_count) + dialect_buffer

    # The 32-byte SMB header goes in front of the body. TID/UID are left
    # at their defaults (0) since we have no tree or session yet at this
    # point in the exchange -- MID is the only thing worth setting here,
    # so a caller can tell multiple in-flight negotiate probes apart.
    header = smb_header.pack_smb_header(SMB_COM_NEGOTIATE, mid=mid)

    # A full SMB message is just header bytes immediately followed by
    # body bytes -- no separator needed, since fixed offsets/lengths
    # already tell the receiver where one ends and the other begins.
    return header + body


def parse_negotiate_response(data: bytes) -> dict:
    """Parse a full SMB message (header + negotiate response body)."""

    # The first 32 bytes are always the generic SMB header, regardless of
    # command -- same unpack_smb_header you already wrote and tested.
    header = smb_header.unpack_smb_header(data[:32])

    # WordCount sits right after the header, at absolute offset 32 (it's
    # offset 0 in the *body*, but the header takes up the first 32 bytes
    # of `data`). Indexing a `bytes` object with a single index gives an
    # int directly (no struct needed for one raw byte).
    word_count = data[32]

    if word_count == 0:
        # Server didn't accept any dialect we offered -- it either
        # doesn't speak SMB1 at all, or not the dialects we listed. No
        # body follows, so there's nothing further to parse.
        return {"smb1_supported": False, "header": header}

    # Fixed parameter block: 17 words (word_count) = 34 bytes, starting
    # right after WordCount at absolute offset 33, ending at 33+34=67.
    # Format string field-for-field against the layout table:
    #   H  DialectIndex      (2)
    #   B  SecurityMode      (1)
    #   H  MaxMpxCount       (2)
    #   H  MaxNumberVcs      (2)
    #   I  MaxBufferSize     (4)
    #   I  MaxRawSize        (4)
    #   I  SessionKey        (4)
    #   I  Capabilities      (4)
    #   Q  SystemTime        (8)
    #   h  ServerTimeZone    (2, signed -- it's a +/- minutes offset from UTC)
    #   B  ChallengeLength   (1)
    # 2+1+2+2+4+4+4+4+8+2+1 = 34, matching word_count * 2. Good sanity check.
    fixed_fmt = "<HBHHIIIIQhB"
    (
        dialect_index,
        security_mode,
        max_mpx_count,
        max_number_vcs,
        max_buffer_size,
        max_raw_size,
        session_key,
        capabilities,
        system_time,
        server_time_zone,
        challenge_length,
    ) = struct.unpack(fixed_fmt, data[33:67])

    # ByteCount follows the fixed block, then the variable Data section.
    byte_count, = struct.unpack("<H", data[67:69])
    body_data = data[69:69 + byte_count]

    # SystemTime is a Windows FILETIME: 100ns ticks since 1601-01-01 UTC.
    # Divide by 10 to get microseconds (timedelta's native unit) since
    # timedelta can't take 100ns units directly.
    server_time = _FILETIME_EPOCH + timedelta(microseconds=system_time / 10)

    result = {
        "smb1_supported": True,
        "header": header,
        "dialect_index": dialect_index,
        "security_mode": security_mode,
        "max_buffer_size": max_buffer_size,
        "capabilities": capabilities,
        "server_time": server_time,
        "server_time_zone_minutes": server_time_zone,
    }

    # Capabilities tells us which shape the trailing Data section has --
    # this bit has to be checked before the trailing bytes can be
    # interpreted at all, same reasoning as Flags2/Unicode in the header.
    if capabilities & CAP_EXTENDED_SECURITY:
        # Extended security: 16-byte server GUID, then an optional
        # SPNEGO security blob filling out the rest of body_data.
        result["server_guid"] = body_data[:16]
        result["security_blob"] = body_data[16:]
    else:
        # Classic security: `challenge_length` raw challenge bytes, then
        # the domain name and server name as consecutive strings.
        challenge = body_data[:challenge_length]
        names_raw = body_data[challenge_length:]

        # Whether those trailing strings are ASCII or UTF-16LE depends on
        # the Unicode bit in the *header's* Flags2 -- exactly the kind of
        # header-controls-body-parsing situation from the SMB header
        # discussion earlier.
        unicode = bool(header["flags2"] & SMB_FLAGS2_UNICODE)
        encoding = "utf-16-le" if unicode else "ascii"
        try:
            # Domain and server name are each null-terminated and
            # concatenated back to back; splitting on the null character
            # separates them (with a trailing empty string from the
            # final terminator, which strip cleans up).
            names = names_raw.decode(encoding).split("\x00")
            names = [n for n in names if n]
        except UnicodeDecodeError:
            names = None

        result["challenge"] = challenge
        result["names_raw"] = names_raw
        result["names"] = names

    return result

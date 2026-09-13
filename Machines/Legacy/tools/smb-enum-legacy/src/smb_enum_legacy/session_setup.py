"""SMB_COM_SESSION_SETUP_ANDX -- establish a session (null, or Guest, here).

This is the "classic" (non-extended-security) request/response shape,
matching the branch of parse_negotiate_response where CAP_EXTENDED_SECURITY
was NOT set. A true null session sends an empty account name and a
zero-length password; passing account_name="Guest" (still with an empty
password) tries the built-in Guest identity instead -- neither needs a
real credential, but servers can (and do) treat them differently.

"AndX" commands (SESSION_SETUP_ANDX, TREE_CONNECT_ANDX, ...) support
chaining several commands into one request/response round trip. We don't
chain anything here, so AndXCommand is always 0xFF (constants.ANDX_NO_FURTHER_COMMAND).

REQUEST (WordCount = 13, i.e. 26 bytes of fixed parameters):
  offset  size  field
  0       1     AndXCommand         -- 0xFF, no chained command
  1       1     AndXReserved        -- 0
  2       2     AndXOffset          -- 0 (unused, no chained command)
  4       2     MaxBufferSize
  6       2     MaxMpxCount
  8       2     VcNumber
  10      4     SessionKey          -- 0 is fine for a null session
  14      2     OEMPasswordLen      -- 0 for null session
  16      2     UnicodePasswordLen  -- 0 for null session
  20      4     Reserved
  24      4     Capabilities        -- 0: no unicode, no extended security
Then ByteCount(2) + Data:
  OEMPassword[OEMPasswordLen], UnicodePassword[UnicodePasswordLen],
  AccountName (null-terminated, empty here), PrimaryDomain (null-terminated,
  empty here), NativeOS (null-terminated), NativeLanMan (null-terminated)
  -- all ASCII since Capabilities didn't request unicode.

RESPONSE (WordCount = 3):
  offset  size  field
  0       1     AndXCommand
  1       1     AndXReserved
  2       2     AndXOffset
  4       2     Action              -- bit 0 set = logged in as guest
Then ByteCount(2) + Data: NativeOS, NativeLanMan, PrimaryDomain (null-terminated
strings, same encoding rule as the request). The session's UID is NOT in this
body -- it's in the SMB header's UID field of the response, same header you
already parse with smb_header.unpack_smb_header.
"""

import struct

from smb_enum_legacy import smb_header
from smb_enum_legacy.constants import ANDX_NO_FURTHER_COMMAND, SMB_COM_SESSION_SETUP_ANDX


def build_session_setup_request(*, mid: int = 0, account_name: str = "", password: str = "") -> bytes:
    """Build a SESSION_SETUP_ANDX request.

    Defaults to a true null session (empty account name, no password).
    Passing account_name="Guest" tries the built-in Guest identity instead
    -- a different, still-credential-free identity that some servers treat
    differently from an anonymous/null session (e.g. RestrictAnonymous
    configs that block null-session RAP calls but still allow Guest).
    """

    # NOTE: this only sends the password as a raw ASCII blob -- fine for
    # the empty-password case (true null session or Guest-with-no-password),
    # but a *real* password here would need to be LM/NTLM challenge-response
    # hashed against the negotiate response's challenge, not sent plaintext.
    # Not implemented, since we only ever call this with an empty password.
    oem_password = password.encode("ascii")

    fixed = struct.pack(
        "<BBHHHHIHHII",
        ANDX_NO_FURTHER_COMMAND,  # AndXCommand
        0,  # AndXReserved
        0,  # AndXOffset
        4356,  # MaxBufferSize -- arbitrary, just our advertised limit
        2,  # MaxMpxCount
        1,  # VcNumber
        0,  # SessionKey
        len(oem_password),  # OEMPasswordLen
        0,  # UnicodePasswordLen -- not sending a unicode password variant
        0,  # Reserved
        0,  # Capabilities -- keep it simple: no unicode, no extended security
    )

    account_name_field = account_name.encode("ascii") + b"\x00"
    primary_domain = b"\x00"  # empty PrimaryDomain, null-terminated
    native_os = b"smb-enum-legacy\x00"
    native_lan_man = b"smb-enum-legacy\x00"

    data = oem_password + account_name_field + primary_domain + native_os + native_lan_man

    word_count = 13
    body = struct.pack("<B", word_count) + fixed + struct.pack("<H", len(data)) + data

    header = smb_header.pack_smb_header(SMB_COM_SESSION_SETUP_ANDX, mid=mid)
    return header + body


def parse_session_setup_response(data: bytes) -> dict:
    """Parse a SESSION_SETUP_ANDX response."""

    header = smb_header.unpack_smb_header(data[:32])
    if header["status"] != 0:
        # Non-zero status means the server rejected the session setup --
        # there's no meaningful body to parse in that case.
        return {"success": False, "status": header["status"], "header": header}

    word_count = data[32]
    params_len = word_count * 2
    params = data[33:33 + params_len]

    # Response parameters: AndXCommand(B) AndXReserved(B) AndXOffset(H) Action(H)
    _andx_command, _andx_reserved, _andx_offset, action = struct.unpack("<BBHH", params[:6])

    byte_count_offset = 33 + params_len
    byte_count, = struct.unpack("<H", data[byte_count_offset:byte_count_offset + 2])
    body_data = data[byte_count_offset + 2:byte_count_offset + 2 + byte_count]

    # Three null-terminated ASCII strings back to back: NativeOS,
    # NativeLanMan, PrimaryDomain. Splitting on the null byte and
    # dropping empty trailing pieces separates them.
    strings = [s.decode("ascii", errors="replace") for s in body_data.split(b"\x00") if s]

    return {
        "success": True,
        "uid": header["uid"],  # server-assigned session UID, needed for TREE_CONNECT next
        "guest": bool(action & 0x0001),
        "native_os": strings[0] if len(strings) > 0 else None,
        "native_lan_man": strings[1] if len(strings) > 1 else None,
        "primary_domain": strings[2] if len(strings) > 2 else None,
    }

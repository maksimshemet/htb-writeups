"""Protocol constants for hand-rolled SMBv1 (CIFS) messages.

Reference: [MS-CIFS] and [MS-SMB] specs. These are just wire-format
literals -- no parsing logic lives here.
"""

# --- NetBIOS Session Service (direct TCP/445 framing) ---
# Every SMB message on the wire is prefixed with a 4-byte header:
#   byte 0     = message type
#   bytes 1..3 = big-endian 24-bit length of the payload that follows
NBSS_SESSION_MESSAGE = 0x00

# --- SMB header ---
SMB_PROTOCOL = b"\xffSMB"  # fixed 4-byte magic at the start of every SMB1 message

# SMB_COM_* command codes (there are ~100; these are the ones you'll need
# for negotiate -> session setup -> tree connect -> enumeration)
SMB_COM_NEGOTIATE = 0x72
SMB_COM_SESSION_SETUP_ANDX = 0x73
SMB_COM_TREE_CONNECT_ANDX = 0x75
SMB_COM_TRANSACTION = 0x25
SMB_COM_TRANSACTION2 = 0x32

# AndX chaining: every AndX command's parameters start with AndXCommand,
# telling the server which command (if any) is chained after this one in
# the same request. 0xFF means "nothing chained, this is the only command".
ANDX_NO_FURTHER_COMMAND = 0xFF

# Flags (1 byte) - request direction bit, case sensitivity, etc.
SMB_FLAGS_CASE_INSENSITIVE = 0x08
SMB_FLAGS_CANONICALIZED_PATHS = 0x10

# Flags2 (2 bytes) - little-endian on the wire
SMB_FLAGS2_LONG_NAMES = 0x0001
SMB_FLAGS2_EXTENDED_SECURITY = 0x0800
SMB_FLAGS2_NT_STATUS = 0x4000
SMB_FLAGS2_UNICODE = 0x8000

# --- Dialects for SMB_COM_NEGOTIATE ---
# The client offers a list; the server's response tells you the index
# (into this list) of the dialect it picked -- or refuses SMB1 outright.
# Oldest first, since that's how real clients historically ordered them.
LEGACY_DIALECTS = [
    "PC NETWORK PROGRAM 1.0",  # core protocol, pre-NT
    "LANMAN1.0",
    "LANMAN2.0",
    "NT LM 0.12",  # what every real SMB1 server from NT4 onward will pick
]

# Each dialect string in the negotiate request body is wrapped as:
#   0x02 (dialect buffer format marker) + ascii bytes + 0x00 (null terminator)
DIALECT_BUFFER_FORMAT = 0x02

# Capabilities (4 bytes, in the NEGOTIATE response) - bit flags the server
# advertises. This is the one that matters for parsing the rest of the
# negotiate response: if set, the trailing data is a server GUID (+
# optional security blob) instead of a challenge + domain/server name.
CAP_EXTENDED_SECURITY = 0x80000000

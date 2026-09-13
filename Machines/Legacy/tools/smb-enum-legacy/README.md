# smb-enum-legacy

A hand-rolled SMBv1 (CIFS) client, built from scratch against the `[MS-CIFS]`/`[MS-SMB]`
specs, to perform: `NEGOTIATE → SESSION_SETUP_ANDX (null/Guest) → TREE_CONNECT_ANDX (IPC$)
→ RAP NetShareEnum`.

> ⚠️ **Vendored here as a learning exercise, not the Legacy solution.** See
> [`../../README.md`](../../README.md#-interesting-side-quest--hand-rolled-smbv1-enumeration)
> for why this was a rabbit hole on the actual box.

## Usage

```bash
uv run smb-enum-legacy <host> [-p PORT] [-u ACCOUNT_NAME]
```

`-u ""` (default) attempts a true null session; `-u Guest` falls back to the built-in Guest
identity for servers that block anonymous RAP calls but still allow Guest.

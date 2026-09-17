# 🧩 Hack The Box — Writeups & OSCP Journey

> Penetration-testing walkthroughs for **retired** Hack The Box machines, written as I work toward the **OSCP**.
> Each writeup follows a repeatable methodology: **Recon → Enumeration → Foothold → Privilege Escalation → Lessons Learned.**

**Author:** Maksym S · **HTB:** [@d0m0vyk](https://app.hackthebox.com/profile/d0m0vyk) · **Contact:** semetm25@gmail.com

---

## ⚠️ Responsible disclosure

- Only **retired** HTB machines are documented here, in line with the [HTB Terms of Service](https://www.hackthebox.com/tos).
- **No flag values** are ever published — flags are redacted as `HTB{__REDACTED__}`.
- Everything here is for **educational and authorised testing purposes only**.

---

## 📊 Progress

| Difficulty | Owned | Total |
|-----------|:-----:|:-----:|
| 🟢 Easy    |  3    | 81    |
| 🟡 Medium  |  0    | 69    |
| 🔴 Hard    |  0    | 21    |
| ⚫ Insane  |  0    | 8     |
| **Total** | **3** | **179** |

Full checklist: [ROADMAP.md](ROADMAP.md)

---

## 📝 Writeups

| Machine | OS | Difficulty | Key Techniques | Writeup |
|---------|----|-----------|----------------|---------|
| Lame | 🐧 Linux | 🟢 Easy | distcc RCE (CVE-2004-2687), vsftpd 2.3.4 backdoor (CVE-2011-2523) | [Read](Machines/Lame/README.md) |
| Legacy | 🪟 Windows XP | 🟢 Easy | MS17-010 / EternalBlue (CVE-2017-0143) | [Read](Machines/Legacy/README.md) |
| Blue | 🪟 Windows 7 | 🟢 Easy | MS17-010 / EternalBlue (CVE-2017-0143) | [Read](Machines/Blue/README.md) |

---

## 🗂️ Repository layout

```
.
├── README.md                          # this page
├── ROADMAP.md                         # full machine checklist / progress
├── Machines/
│   └── <MachineName>/
│       ├── README.md                  # the walkthrough
│       └── images/                    # screenshots
├── Learning/
│   └── <topic>.md                     # standalone reference notes (not tied to one machine)
└── templates/
    ├── machine-writeup-template.md    # reusable walkthrough skeleton
    ├── professional-report-template.md# OSCP-style formal report skeleton
    └── metasploit-decision-tree.md    # when to spend the OSCP msf allowance vs. go manual
```

---

## 🧰 Tools & Arsenal

Tools that have earned a permanent place in my workflow:

| Tool | Purpose | Why it's great |
|------|---------|----------------|
| [**Penelope**](https://github.com/brightio/penelope) | Reverse-shell handler / listener | Auto-upgrades to a full PTY, manages multiple sessions, logs everything, and handles file up/download — a massive upgrade over raw `nc -lvnp`. |
| `nmap` | Port & service discovery | The foundation of every engagement. |
| `smbclient` / `enum4linux` | SMB enumeration | First stop on any Windows/Samba host. |
| `gtfobins` | Privesc reference | SUID/sudo abuse lookups. |

> 💡 **Quick tip — connect to SMB as guest / null session:**
> ```bash
> smbclient //<IP>/<share> -U "" -N     # empty user, no password
> ```
> Great for enumerating shares when you have no credentials yet.

---

## 🌳 Metasploit vs. manual — a decision tree

For OSCP-style engagements with a limited Metasploit allowance, this is the framework I use
to decide whether a box is worth spending it on: [templates/metasploit-decision-tree.md](templates/metasploit-decision-tree.md)
(worked example against Legacy/MS17-010 in the [Legacy writeup](Machines/Legacy/README.md#-decision-tree--use-metasploit-or-go-manual-oscp)).

---

## 🧭 Methodology

Every box is approached the same disciplined way — the habit that passes the OSCP:

1. **Recon** — full TCP/UDP port sweep, service/version detection.
2. **Enumeration** — dig into each exposed service; enumerate *before* exploiting.
3. **Foothold** — gain an initial low-privilege shell; document the reasoning, not just the payload.
4. **Privilege Escalation** — enumerate the host, identify the vector, escalate to root/SYSTEM.
5. **Lessons Learned** — what mattered, what was a rabbit hole, remediation.

---

## 🔗 Connect

- **HTB:** [@d0m0vyk](https://app.hackthebox.com/profile/d0m0vyk)
- **Email:** semetm25@gmail.com

_If a writeup helped you, a ⭐ on the repo is appreciated._

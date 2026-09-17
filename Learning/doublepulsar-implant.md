# DOUBLEPULSAR — what it is, and where to find its code

> Background reading spun out of researching an open question from `Machines/Blue/README.md`
> (the `smb_doublepulsar_rce` Metasploit module). General reference, not tied to one box.

## What it is

**DOUBLEPULSAR** is a covert kernel-mode backdoor/implant built by the NSA's Equation Group,
publicly leaked by the Shadow Brokers group in April 2017 alongside EternalBlue and the rest of
the Fuzzbunch toolkit.

- **What it does:** listens for specially-crafted SMB (or RDP) packets carrying a trigger + XOR
  key, and when it recognizes one, **reflectively injects** a supplied DLL/payload into a chosen
  process's memory (`spoolsv.exe` by default). It has essentially no built-in commands of its
  own — no interactive shell, no file browser. It's a thin, covert **stager/loader**, not a full
  C2 framework.
- **Persistence:** lives in kernel memory; non-persistent across reboots by default unless the
  operator configures otherwise.
- **Why it mattered:** once public, EternalBlue + DOUBLEPULSAR became the propagation engine for
  **WannaCry** and **NotPetya** (mid-2017) — both worms scanned for SMBv1 hosts, exploited
  EternalBlue, planted DOUBLEPULSAR, then injected their payload through it.

## Relationship to EternalBlue

They're separate tools that are commonly chained, not the same thing:

```
EternalBlue (exploit, CVE-2017-0143) → plants → DOUBLEPULSAR (implant/loader)
                                                       │
                                                       └─ injects → actual payload (e.g. a Meterpreter shell)
```

DOUBLEPULSAR doesn't exploit anything itself — it assumes it's already running, and just waits to
relay a payload. EternalBlue is one way to plant it (the famous one), but they're independent
pieces of the leaked toolkit. This is also why Metasploit's `smb_doublepulsar_rce` module does
**nothing** against a fresh, never-before-exploited host: it only talks to an implant that's
already resident, and `ms17_010_eternalblue` (used on HTB Blue) doesn't stage DOUBLEPULSAR at
all — it exploits the bug *and* injects its own Meterpreter stager directly.

## Where to find the code

There's no clean, human-readable "DOUBLEPULSAR source" release — the NSA never open-sourced it,
it only exists publicly because it was stolen and leaked. Three different tiers, from raw to
readable:

### 1. The actual leaked implant (raw, from the NSA toolkit itself)
The Shadow Brokers' April 2017 **"Lost in Translation"** release contained the Fuzzbunch
framework (which deploys DOUBLEPULSAR). Most commonly cited public mirror of the decrypted
contents:
- [`x0rz/EQGRP_Lost_in_Translation`](https://github.com/x0rz/EQGRP_Lost_in_Translation) —
  see `windows/payloads/Doublepulsar-1.3.1.0.xml` and the Eternalblue payload alongside it.

This is compiled binaries + Fuzzbunch config/XML, not clean source — it wasn't written to be read.

### 2. Reverse-engineering write-ups (readable analysis of what it actually does)
- [zerosum0x0 — "DoublePulsar Initial SMB Backdoor Ring 0 Shellcode Analysis"](https://zerosum0x0.blogspot.com/2017/04/doublepulsar-initial-smb-backdoor-ring.html) —
  full disassembly walkthrough of the ~3,600-byte kernel shellcode: locating `ntoskrnl.exe`,
  resolving kernel functions, finding `srv.sys`, and hooking `SrvTransaction2DispatchTable` to
  install itself. Written by one of the actual co-authors of Metasploit's
  `ms17_010_eternalblue` module.

### 3. Reimplementations you can run/read (built by researchers, not the NSA)
- [`WithSecureLabs/doublepulsar-usermode-injector`](https://github.com/countercept/doublepulsar-usermode-injector) —
  reimplements the reflective-DLL-injection usermode shellcode, for testing detections.
- [`smb_doublepulsar_rce.rb`](https://github.com/rapid7/metasploit-framework/blob/master/modules/exploits/windows/smb/smb_doublepulsar_rce.rb) —
  Rapid7's own reimplementation of the SMB check/control protocol.
- [Rapid7 blog — "Open-Source Command and Control of the DOUBLEPULSAR Implant"](https://www.rapid7.com/blog/post/2019/10/02/open-source-command-and-control-of-the-doublepulsar-implant/) —
  explains their reimplementation in more depth.

**To learn the technique** (kernel hooking, reflective injection), start with the zerosum0x0
write-up. To poke at the actual artifact, the x0rz mirror has the leaked binaries — expect to
need a disassembler, not a text editor.

## Sources

- [zerosum0x0 — DoublePulsar Ring 0 Shellcode Analysis](https://zerosum0x0.blogspot.com/2017/04/doublepulsar-initial-smb-backdoor-ring.html)
- [x0rz/EQGRP_Lost_in_Translation](https://github.com/x0rz/EQGRP_Lost_in_Translation)
- [WithSecureLabs/doublepulsar-usermode-injector](https://github.com/countercept/doublepulsar-usermode-injector)
- [Rapid7 — Open-Source Command and Control of the DOUBLEPULSAR Implant](https://www.rapid7.com/blog/post/2019/10/02/open-source-command-and-control-of-the-doublepulsar-implant/)
- [Rapid7 — `smb_doublepulsar_rce` module reference](https://www.rapid7.com/db/modules/exploit/windows/smb/smb_doublepulsar_rce/)
- [Microsoft — Customer Guidance for WannaCrypt Attacks](https://blogs.technet.microsoft.com/msrc/2017/05/12/customer-guidance-for-wannacrypt-attacks/)

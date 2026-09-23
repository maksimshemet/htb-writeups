# Methodology — OS-agnostic playbook

General workflow discipline for any box, distilled from practice across multiple machines and
periodically revised after post-box debriefs. Written to be **re-read before starting every box**,
not just once. OS-specific technique ladders live in [`Methodology/Windows.md`](Methodology/Windows.md)
and [`Methodology/Linux.md`](Methodology/Linux.md).

> This file intentionally contains no box-specific details (IPs, hostnames, CVE numbers tied to a
> single machine, credentials, or exact exploit chains) — see the root `README.md`'s Responsible
> Disclosure section for why: content here must stay generic enough to be useful without spoiling
> any specific box, retired or active.

---

## The three rules that save the most time

1. **Enumerate everything before exploiting anything.** Recon is breadth-first; exploitation is
   depth-first. Never go deep on one service while others sit un-enumerated — the real path is
   often the *un-touched* service, not the interesting one you already found.
2. **Time-box every target: pick a hard limit (e.g. 15 min) and use a real, external trigger** (a
   physical timer, not a mental note). When it fires, you either have a confirmed exploit landing,
   or you stop and move to the next target. Willpower alone doesn't reliably interrupt a curiosity
   tunnel — the alarm has to do it.
3. **Documented abuse before derivation.** For any CVE, tool, or privesc binary: search for the
   known technique first (GTFOBins, HackTricks, a search engine, the tool's own issue tracker).
   Derive a solution from source/man pages only once every lookup source comes up empty.

---

## Target prioritisation — "protagonist vs. plumbing"

On a multi-service box, rank targets before touching any of them:

- **HIGH priority — things a human actually logs into or interacts with.** Web apps, named
  products with a login page, file shares. This is almost always the biggest surface and the
  intended entry point.
- **LOW priority — usually pivots, not entries.** Databases, directory services, RPC/RMI/JMX-style
  management interfaces, message queues — especially anything bound to loopback or returning a
  `127.0.0.1`-style callback address.

Signals a service is "plumbing" rather than "the door":
- Returns a **loopback address** in its own responses → you can't reach it directly from outside →
  deprioritize.
- **Several open ports all belong to one backend product** → that's supporting infrastructure; the
  lone user-facing app is the protagonist.
- A **wildcard TLS certificate** or an unexpected redirect target → there's more web surface
  (subdomains/vhosts) worth enumerating before anything else.

Ask, on every unfamiliar-but-shiny service: **"Is this the path, or is it just new to me?"**
Novelty is a magnet and often a trap — note it and come back only after the obvious paths are
exhausted.

---

## The first 15 minutes — parallel opening routine

Fire the slow scans, then start web/service enumeration immediately while they run — nothing
should sit idle. Use multiple terminal panes.

```bash
IP=<target>
mkdir -p boxname/nmap && cd boxname

# Pane 1 — full TCP sweep (slow, background)
nmap -p- -T4 -oA nmap/allports $IP

# Pane 2 — service/script scan on top ports (runs while pane 1 works)
nmap -sCV -oA nmap/quick $IP

# Pane 3 — UDP top ports
sudo nmap -sU --top-ports 50 -oA nmap/udp $IP
```

The moment a web port is confirmed, web enumeration becomes the priority:

```bash
# add the host (and any vhost hinted at by a TLS cert) to /etc/hosts first
echo "$IP domain.tld" | sudo tee -a /etc/hosts
whatweb https://domain.tld ; curl -sik https://domain.tld

ffuf -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt:FUZZ \
  -u https://domain.tld/FUZZ -k -ac -c -t 50 -mc 200,204,301,302,307,401,403

# a wildcard cert is a strong hint there are vhosts/subdomains to find
ffuf -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt:FUZZ \
  -u https://domain.tld/ -H "Host: FUZZ.domain.tld" -k -ac -c -t 50
```

**Free-loot checks — run immediately whenever these show up in a scan, never skip them:**

```bash
# any flavor of "anonymous"/"null"/"OK" auth in a service banner = check now, costs nothing
ldapsearch -x -H ldap://$IP:PORT -b "dc=domain,dc=tld"
showmount -e $IP
smbclient -L //$IP -N
```

An anonymous bind, null SMB session, open NFS export, or anonymous FTP can hand you usernames,
directory structure, or files in minutes — treat any such nmap line as an immediate, mandatory
check before moving on, not an optional side-quest.

---

## Behavioral discipline (the real gap is usually behavior, not knowledge)

Most avoidable time loss is *knowing* the right move and doing the wrong one anyway (curiosity
tunnel-vision on an interesting-but-non-critical service). Fixes are mechanical, not motivational:

- **A physical countdown timer**, reset per target.
- **A visible reminder** of the one question that matters: *"Is this the path, or just new to me?"*
- **A `rabbitholes.txt` file** — when something fascinating-but-non-critical appears, write one
  line about it and leave it. Return only once the obvious paths are exhausted. This scratches the
  "don't want to lose the thread" itch without paying the hours for it.
- **Score before curiosity.** Treat exploring the interesting tangent as a reward you spend *after*
  you've made progress, not before.

---

## Foothold lookup ladder (stop at the first hit)

For any identified service/version or suspected vulnerability:

1. **Offline exploit database** (e.g. `searchsploit <product>`).
2. **A curated technique reference** (e.g. HackTricks), organized by port/service.
3. **A search engine** — `<product> <version> exploit` / `<product> RCE`. **Rotate engines** if one
   returns only noise — for very recent vulnerabilities, one engine indexing faster than another is
   common; a second engine can surface a working PoC that the first didn't.
4. **Read any PoC end-to-end before running it** — know how it delivers its payload (a header? a
   parameter? a file?), whether the exploit primitive is fixed or needs customization, and what it
   returns. This matters both for trust (you're about to run someone else's code) and for writing
   an accurate report afterward.

---

## Privilege-escalation lookup ladder (stop at the first hit)

The moment a sudo rule or a SUID binary is identified:

1. **A binary-abuse reference** (e.g. GTFOBins) — search the binary, read the section matching your
   context (sudo / SUID / capability / file-read, etc.). A miss is common — these references only
   cover commonly-abused binaries.
2. **Miss → search `<binary> privilege escalation` / `<binary> sudo exploit`.** Plenty of real,
   well-documented privesc techniques exist for binaries a curated list hasn't caught up to yet. A
   miss on a curated list does **not** mean "derive it yourself" — it means try the next source.
3. **Still thin → search using distinguishing details** (the exact rule string, a flag combination,
   an unusual argument). Known CTF/training platforms frequently reuse published techniques.
4. **Only if every lookup source is empty → read `--help`/man/source and derive it yourself.** This
   is the last resort, not the second step.

Standard enumeration to run first, every time:

```bash
sudo -l                                    # always check first
id                                         # groups worth noting: disk, docker, lxd, adm, etc.
find / -perm -4000 -type f 2>/dev/null     # SUID
getcap -r / 2>/dev/null                    # capabilities
# then a full enumeration script for breadth — but triage its output (see below), don't trust it blindly
```

---

## Reading automated-enumeration output without rabbit-holing

- **Automated enum scripts flag by file-mode/pattern, not by actual exploitability.** Plenty of
  "interesting permission" findings under system directories (systemd, dbus, package-manager,
  udev, journal paths) are normal and unexploitable — learn to dismiss these on sight rather than
  chasing every flagged line.
- Triage every lead with two questions: **(a) can *I* write to or influence it?** and **(b) does it
  run as, or get read by, someone more privileged than me?** If either answer is no, it's
  recon-only — note it and move on.
- A privileged config/directory you can only *read* (not influence) is worth reading for
  intelligence (credentials, internal service info) — but that's reconnaissance, not a privesc
  vector by itself.
- **Don't abandon a proven, in-progress primitive to chase a newer, unproven lead.** Finish
  confirming the thing that's already working before exploring the shiny new one.

---

## Error-reading cheatsheet (whose fault is it?)

A large share of wasted time comes from misreading *which layer* produced an error:

| Symptom | Likely meaning | Fix |
|---|---|---|
| Shell redirection/operator syntax fails unexpectedly | Script ran under a POSIX shell (`/bin/sh`/dash) instead of bash | Force bash explicitly (`bash -c '...'`), or use a POSIX-portable payload |
| A tool's own format-string artifacts leak into output | Bug in the tool's own string formatting | Note it, doesn't indicate your input/logic is wrong |
| Java 9+ "module does not export/open" errors | JPMS blocking reflective access used by older tooling | Add the relevant `--add-opens` flags, or fall back to an older JRE |
| "class not found" (PHP/Java) after a namespace guess | Wrong assumed namespace/FQCN | Read the actual source header — don't guess twice |
| "undefined constant/bootstrap not initialized" | Framework code run outside its normal entrypoint | Define the missing constant, or load the framework's real bootstrap |
| A sudo rule stops matching after you thought you followed it | Your invocation drifted from the exact pinned command string | Keep the fixed portion byte-for-byte identical; only vary what the rule actually allows to vary |
| "not a repository"/"not initialized" from a backup-style tool | Wrong subcommand/mode for a fresh target path | Check whether the tool has a distinct "create fresh copy" vs. "restore into existing" mode |
| HTTP 200 with an error message in the body | Request reached the app; rejected at the application logic layer | Read the body, not just the status code |
| HTTP 500 specifically on crafted/injected input | Input reached executing code and broke something | This may be your real oracle — treat it as a signal, not just noise |

**Meta-rule:** an error surfaced *by the target/tool itself* (a usage or logic error) usually means
you're already authenticated/executing and just have the arguments wrong. An error surfaced by an
intermediate layer (sudo's own rejection, TLS negotiation, your own shell) usually means you never
reached the target at all. Fix the layer the error is actually coming from.

---

## Serialized / encoded data reflexes

- A value that decodes to a binary "magic number" for a serialization format (check known magic
  bytes for your stack — e.g. Java serialization, .NET BinaryFormatter, PHP `serialize()`) means
  you're looking at **serialized object data**, not an opaque token — decode and inspect it; forms
  and cookies built this way often leak internal hostnames, distinguished names, or class/type
  info useful for other vectors.
- A hash-looking value using a **recognized slow hashing scheme** (bcrypt, etc.) needs
  **cracking** — slow and not guaranteed to succeed.
- A base64-looking blob sitting next to a service that must *use* the underlying secret at runtime
  is a strong signal of **reversible encryption**, not hashing — the decryption key is on disk
  somewhere the service can reach it. **Encrypted ≠ hashed.** Finding the key and decrypting beats
  cracking every time it's available — always check for the reversible case before reaching for a
  cracker.
- A "password" that looks suspiciously structured (a clean permutation, uniform case, a narrow
  alphabet) is often **encoded, not literal** — decode before trusting it as a real credential.

---

## Credential-reuse reflex

Every cleartext credential recovered — from any source — gets sprayed immediately across every
other reachable auth surface, not just the service it came from:

```bash
grep -E 'sh$' /etc/passwd        # every user with a real shell
nxc ssh $IP -u <user> -p '<pass>'   # or hydra / manual attempts
su <user>                            # local account switch
ldapsearch ... -D "<binddn>" -w '<pass>'   # directory services
```

Service-account credentials are especially prime candidates for reuse against human/interactive
accounts — password reuse across a service account and a real user is one of the most common
lateral-movement patterns.

---

## Session recording — measure your own speed

You can't fix time-sinks you can't see. Recording sessions and reviewing the timeline afterward is
how recurring patterns actually get fixed rather than just noticed once.

### Per-box timed capture (best for review)

```bash
# start of box
script -T ~/boxes/boxname/timing.log ~/boxes/boxname/session.log
# ... work the entire box ...
exit

# replay in real time to watch your own pacing
scriptreplay -t ~/boxes/boxname/timing.log ~/boxes/boxname/session.log
```

Mark milestones afterward and measure the gaps between them: first scan → first real web/service
request, first request → foothold, foothold → user, user → root. Large gaps are your time-sinks —
they're the numbers worth shrinking on the next box.

### Multi-pane logging (best for real-time work)

A tmux logging plugin that auto-logs every pane to timestamped files keeps a full record without
remembering to start one manually per pane.

### Timestamped shell history (always-on, zero effort)

```bash
# bash
export HISTTIMEFORMAT="%F %T "
# zsh
setopt EXTENDED_HISTORY
```

### Recommended combo

Timed `script` capture per box (for milestone measurement) + always-on multi-pane logging (for
day-to-day work) + timestamped history (a zero-effort backstop). Review a replay after each of the
first several boxes — recurring time-sinks are exactly what makes them fixable.

---

## Post-box debrief (do this every time)

After reaching the deepest point you're going to reach on a box, before moving to the next one:

1. What was the intended path, and what signal pointed to it that was seen or missed early on?
2. Where did the session rabbit-hole, and why didn't the time-box trigger fire?
3. Which errors cost real time, and what did each one actually mean once understood?
4. What would the first 15 minutes look like differently next time?
5. Looking at a session replay/timeline — which single gap was the biggest?

The debrief is the second half of the learning — a solved box that never gets debriefed only
delivers half of what it could have.

---

## One-line creed

**Enumerate wide before digging deep. Time-box every target. Look up the known technique before
deriving one from scratch. Read the error's layer before trying to fix it. Decrypting beats
cracking. Spray every credential you recover. And always ask: is this the path, or just new to me?**

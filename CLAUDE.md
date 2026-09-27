# HTB / OSCP Writeups — Project Notes

## Obsidian vault (raw practice notes)

Raw, in-progress notes for each VM live in a separate Obsidian vault, **outside this repo**:

```
/home/user/Documents/OSCP_Vault/OSCP/
```

Key folders inside the vault:

| Path | Contents |
|---|---|
| `Practise/<Machine>.md` | One note per machine (e.g. `Practise/Blue.md`, `Practise/Lame.md`) — recon logs, loot, exploitation transcripts. Often ends in a `Questions:` section with open questions the user hasn't resolved yet. |
| `Practise/HTB VMs.md` | Master roadmap/checklist of every HTB machine, by difficulty. |
| `Methodology/` | The user's own playbook notes (`Per-Box Playbook — Every Box.md`, `Linux — …`, `Windows — …`) — the run-every-box routine, cross-linked to the reference notes below. |
| `Linux/`, `Protocols/`, `Networking/`, `LOLBaS/`, `Software/`, `Programming/`, `LLM/` | Reference notes (tool cheatsheets, protocol notes, LOLBaS entries) not tied to one machine. |

**Relationship to this repo:** the vault holds the messy working notes; `/home/user/Study/htb`
(this repo) holds the polished, public writeups distilled from them. When asked to write up or
research a machine, treat `Practise/<Machine>.md` as the primary source and
`Machines/<Machine>/README.md` here as the output.

Use the **`vault-research`** skill (`.claude/skills/vault-research/SKILL.md`) to automate pulling
a machine's open questions from the vault, researching them, and updating the writeup here.

## Terminal session logs (per-box `script` captures)

The user records every box with `script -T` (timed capture) and hands over the archive for analysis
(mistakes/debrief). Regular locations:

| Path | Contents |
|---|---|
| `/home/user/Coding/YYYY-MM-DD_sessions-<Box>.tar.gz` | The delivered archive for a box (e.g. `2026-09-27_sessions-Jerry.tar.gz`). Extract to a temp dir. |
| `pentest-logs/<ts>_<pid>.log` + `.timing` (inside the archive; `~/pentest-logs/` on the Kali box) | Raw `script` captures. Strip ANSI (`sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/\r/\n/g'`) and `export LC_ALL=C` before grepping; the big interactive logs are tens of MB of terminal noise. Replay a timeline with `scriptreplay -t <ts>.timing <ts>.log`. |

When analyzing logs, clean up the extracted temp dir afterward.

## Key repo paths (used regularly)

| Path | Purpose |
|---|---|
| `Machines/<Machine>/README.md` | The published writeup (retired boxes only). |
| `Machines/<Machine>/images/` | Screenshots for that writeup. |
| `Methodology.md` + `Methodology/Windows.md` + `Methodology/Linux.md` | Sanitized, **public**, box-agnostic methodology (mirror of the vault playbook; never put active-box specifics here). |
| `Learning/<topic>.md` | Standalone reference notes not tied to one machine. |
| `templates/` | Writeup + report skeletons, msf decision tree. |

## Repo conventions

- Only **retired** HTB machines get a full writeup (per the Responsible Disclosure section in `README.md`).
- **Active (non-retired) box pwned →** create `Machines/<Machine>/README.md` as a **placeholder only**
  (pwned date + "writeup after retirement" note — no recon/exploit/CVE/host details), and list it under
  the "🕓 Pwned — writeup pending retirement" section in `ROADMAP.md` (kept out of the 179 progress
  count). Examples: `Machines/Management/`, `Machines/Cohort/`. Verify retirement status before writing
  a full writeup.
- Flags are always redacted — match whichever redaction style the machine's existing section uses
  (`HTB{__REDACTED__}` or `<redacted>`).
- Every writeup follows `templates/machine-writeup-template.md`:
  Summary → Reconnaissance → Enumeration → Foothold → Privilege Escalation → Proof →
  Lessons Learned → Remediation → References.
- Finishing a machine means updating both `ROADMAP.md` (checkbox + progress count) and the
  writeups table in `README.md`.
- Author: Maksym S · HTB: [@d0m0vyk](https://app.hackthebox.com/profile/d0m0vyk) · Contact: semetm25@gmail.com

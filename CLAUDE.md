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
| `Linux/`, `Protocols/`, `Networking/`, `LOLBaS/`, `Software/`, `Programming/`, `LLM/` | Reference notes (tool cheatsheets, protocol notes, LOLBaS entries) not tied to one machine. |

**Relationship to this repo:** the vault holds the messy working notes; `/home/user/Study/htb`
(this repo) holds the polished, public writeups distilled from them. When asked to write up or
research a machine, treat `Practise/<Machine>.md` as the primary source and
`Machines/<Machine>/README.md` here as the output.

Use the **`vault-research`** skill (`.claude/skills/vault-research/SKILL.md`) to automate pulling
a machine's open questions from the vault, researching them, and updating the writeup here.

## Repo conventions

- Only **retired** HTB machines get a writeup (per the Responsible Disclosure section in `README.md`).
- Flags are always redacted — match whichever redaction style the machine's existing section uses
  (`HTB{__REDACTED__}` or `<redacted>`).
- Every writeup follows `templates/machine-writeup-template.md`:
  Summary → Reconnaissance → Enumeration → Foothold → Privilege Escalation → Proof →
  Lessons Learned → Remediation → References.
- Finishing a machine means updating both `ROADMAP.md` (checkbox + progress count) and the
  writeups table in `README.md`.
- Author: Maksym S · HTB: [@d0m0vyk](https://app.hackthebox.com/profile/d0m0vyk) · Contact: semetm25@gmail.com

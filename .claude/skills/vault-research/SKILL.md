---
name: vault-research
description: Pulls open questions out of an OSCP practice-vault note (Practise/<Machine>.md in the Obsidian vault), researches them on the web in a mandatory two-pass gather-then-verify process, and writes the surviving, trusted-source-backed answers into this repo's Machines/<Machine>/README.md writeup. Use when the user asks to research a machine's "Questions" section, answer open questions from their notes, or generate/update a writeup from vault notes.
arguments: [machine]
allowed-tools: Read Write Edit Bash Grep Glob WebSearch WebFetch
---

## Inputs

- `$machine` / `$0` — a machine name (e.g. `Blue`, `Legacy`). Match case-insensitively against
  vault note filenames.
- Vault note: `/home/user/Documents/OSCP_Vault/OSCP/Practise/<machine>.md` (see root `CLAUDE.md`
  for the vault layout).
- Repo writeup: `Machines/<machine>/README.md`.

If `$machine` is missing, ask which machine before doing anything else. If the vault note doesn't
exist, say so and stop — don't fabricate one.

## Procedure

1. **Read the vault note.** Open `Practise/<machine>.md` in full.
2. **Extract the open-question material.** This is usually a trailing `Questions:` block, but
   also treat any inline `???`, "not sure why...", or similar marked uncertainty in the note as
   an open question. List every question found before researching anything.
3. **Locate or scaffold the writeup.**
   - If `Machines/<machine>/README.md` doesn't exist, create the `Machines/<machine>/` directory
     (with an `images/` subfolder to match `Lame`/`Legacy`) and scaffold the README from
     `templates/machine-writeup-template.md`, filling in what the vault note already answers
     (recon output, foothold, privesc, proof) using the same style as the existing `Lame` and
     `Legacy` writeups.
   - If it already exists, **only add or amend content** — never blow away sections a human wrote.
     Append research results in a `## 🔬 Research notes` section (create it before `## 🔗 References`
     if missing), or inline where the answer clearly belongs (e.g. next to the relevant recon
     output), whichever fits the existing writeup better.
4. **Research every open question using the two-pass method below.** Do this before writing
   anything to the repo.
5. **Write only verified answers**, each with an inline citation link. For anything that didn't
   survive verification, write an explicit `> ⚠️ Unconfirmed:` callout summarizing the open
   question and why — never silently drop a question or guess to fill the gap.
6. **Update tracking files** if a writeup went from absent/partial to complete: check the box in
   `ROADMAP.md`, bump its progress count, and add/update the row in `README.md`'s writeups table —
   matching their existing formatting exactly.
7. **Report back** a short summary: which questions got answered (with sources), which stayed
   unconfirmed, and what files changed.

## Two-step research (mandatory — never collapse into a single pass)

Full method and the trusted/untrusted source lists: `references/research-method.md` and
`references/trusted-sources.md`. Summary:

- **Step 1 — Gather.** For each question, run several web searches and pull candidate answers
  from whatever turns up (vendor docs, blogs, forums, write-ups, exploit code comments). Collect
  candidates with their source URLs — don't filter yet, just gather breadth.
- **Step 2 — Verify & filter.** Re-examine every candidate from Step 1 against the trusted-source
  criteria in `references/trusted-sources.md`. Keep a claim only if it's stated by (or corroborated
  against) a trusted source. Discard or downgrade-to-unconfirmed anything that only appears in
  low-trust sources (random blog posts with no citations, forum speculation, unverified AI
  summaries), even if it sounded plausible in Step 1. When trusted sources disagree, note the
  disagreement instead of picking one silently.

Never merge these into one search-and-write pass — the point of Step 2 is to catch confident-sounding
but wrong information that Step 1 will inevitably surface.

## Repo conventions to respect while writing

- Only retired HTB machines get written up.
- Redact flags exactly as the existing sections in this box's note do (`HTB{__REDACTED__}` or `<redacted>`).
- Match the section headings, emoji, and tone already used in `Machines/Lame/README.md` and
  `Machines/Legacy/README.md`.
- Keep exploit transcripts/log blocks verbatim from the vault note (don't paraphrase terminal output).

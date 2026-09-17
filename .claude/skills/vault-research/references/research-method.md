# Two-step research method

This is the detailed version of the process summarized in `SKILL.md`. Apply it per-question, not
once for the whole batch — different questions can end up with different verdicts.

## Step 1 — Gather (breadth, no filtering yet)

Goal: surface every plausible answer and its source, cheaply.

1. Rephrase the question 1-3 ways and run `WebSearch` for each phrasing (exact error strings,
   CVE IDs, module/tool names, and a plain-English version of the question all tend to surface
   different results).
2. Pull full context for the most promising hits with `WebFetch` rather than trusting search
   snippets — snippets truncate caveats and version-specific details.
3. Record, for every candidate answer: the claim, the URL, and who/what is asserting it (official
   vendor, named researcher, anonymous forum post, etc.). Do not discard anything yet, even
   sources that look weak — Step 2 needs the full set to compare against.
4. Stop gathering once new searches stop turning up new information (diminishing returns), or
   once you have at least one candidate from a source that already looks trustworthy.

## Step 2 — Verify & filter (apply trust criteria, then write)

Goal: only let through claims a reasonably skeptical reviewer would accept.

1. Classify every candidate from Step 1 against `trusted-sources.md`'s allow/deny criteria.
2. For each question, check:
   - Does at least one **trusted** source directly support the claim? → usable, cite it.
   - Do **multiple independent trusted-or-mid-tier** sources agree, even if none is top-tier
     alone? → usable, cite the strongest one(s).
   - Does the claim appear **only** in low-trust sources (forum comments, uncited blog posts,
     unverified gists asserting facts rather than showing code, AI-generated summaries)? →
     do not write it as fact. Either leave it unconfirmed, or explicitly label it "unverified,
     seen only in [low-trust source]" if it's worth mentioning at all.
   - Do trusted sources **conflict**? → report the disagreement explicitly instead of silently
     picking a side (e.g. "vendor advisory says X; a later CVE re-analysis says Y — unresolved").
3. Sanity-check specifics against primary sources where possible: a CVE ID should resolve on
   MITRE/NVD, a Metasploit module name should match what `msfconsole`'s local module database
   actually contains (verifiable with `Bash: msfconsole -q -x "search <name>; exit"` if
   Metasploit is installed, or the exploit-db/Rapid7 module page), a security-bulletin claim
   should match the vendor's own advisory page.
4. Only after this filtering write the surviving claims into the repo, each with its citation.

## Worked example (from Blue.md's open questions)

Question: *"what is exploit/windows/smb/smb_doublepulsar_rce and why isn't it working, despite
having 'great' rank?"*

- Step 1 gather: search "smb_doublepulsar_rce metasploit", "DOUBLEPULSAR implant metasploit
  module", "doublepulsar rce not working target not infected" → turns up the Rapid7 module docs
  page, several blog walkthroughs, and forum posts guessing at causes.
- Step 2 verify: Rapid7's own module reference (trusted — the maintainer of the module) states
  this module *executes a payload through an existing DOUBLEPULSAR implant* — it is **not** an
  initial-infection exploit, it's a hook into an implant that a *prior* EternalBlue/DOUBLEPULSAR
  infection must have already planted. That directly explains "why it's not working" on a fresh
  HTB Blue box: nothing has planted DOUBLEPULSAR on it yet, so there's no implant to hook. The
  "great" rank reflects reliability *of the RCE technique once DOUBLEPULSAR is present*, not
  reliability as a standalone initial-access exploit. Forum posts speculating other causes
  (wrong target arch, firewall) are dropped as unconfirmed/lower-trust and unnecessary once the
  primary-source explanation resolves the question.

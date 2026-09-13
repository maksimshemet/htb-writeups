# Decision tree: is this box worth spending the Metasploit allowance on?

A framework for deciding, box by box, whether spending an OSCP exam's limited Metasploit
allowance is justified — first worked out while triaging Legacy/MS17-010 (see the
[Legacy writeup](../Machines/Legacy/README.md#-decision-tree--use-metasploit-or-go-manual-oscp)
for a fully worked example).

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

# Trusted vs. untrusted sources for security research

Used by `vault-research`'s Step 2 (verify & filter). When in doubt, treat a source as lower-trust
and say so rather than upgrading it.

## Trusted (usable as sole support for a claim)

- **Vulnerability databases / authorities:** MITRE CVE, NVD (nvd.nist.gov), CISA/US-CERT advisories.
- **Vendor security bulletins & docs:** Microsoft MSRC/Technet, Samba.org security advisories,
  vsftpd/distcc upstream changelogs and security notes, and equivalent official vendor pages for
  whatever product is in question.
- **Exploit/tooling maintainers' own documentation:** Rapid7's Metasploit module docs
  (rapidsevendocs / docs.metasploit.com), official tool man pages and READMEs.
- **Standards/spec documents:** RFCs, Microsoft's `[MS-*]` protocol specs (e.g. `[MS-CIFS]`,
  `[MS-SMB]`), IETF documents.
- **Named, credentialed security researchers publishing under their own identity/employer**, with
  cited technical detail (e.g. a vendor/company research blog — Rapid7, Tenable, Mandiant/Google
  Threat Intelligence, CrowdStrike, Project Zero — that shows its work: PoC, root-cause analysis,
  version numbers).
- **Established, citation-heavy technical references** (textbooks, official language/OS docs)
  when the question is about underlying mechanics rather than a specific incident.

## Mid-trust (usable if corroborated by another mid- or top-tier source)

- Well-known independent security blogs / write-up sites with a track record but no institutional
  backing (e.g. a named pentester's blog with detailed, reproducible steps).
- Conference talks/slides (DEF CON, Black Hat, etc.) from named speakers.
- HTB's own official write-ups/discussions for **retired** machines — useful for cross-checking a
  technique, not as the sole source for a general security fact.

## Untrusted (never sole support for a written claim — flag as unconfirmed instead)

- Anonymous forum posts, Reddit/Discord comments, unattributed "I heard that..." claims.
- Blog posts or listicles with no author, no date, no citations, or that read as SEO content farms.
- Unverified GitHub gists/repos used as a source of *facts* (they're fine as PoC *code* to read
  and test yourself, but a comment in a gist asserting "this is why X happens" isn't a citation).
- AI-generated summaries or answers with no traceable primary source.
- Outdated pages superseded by a later vendor advisory (check dates — security info ages fast).

## Practical rule of thumb

If you can't name who is asserting the claim and why they'd know, it's untrusted. If removing the
source would leave the claim with zero backing, don't write the claim as fact — write it as an
open question or an explicitly labeled guess.

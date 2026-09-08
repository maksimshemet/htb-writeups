# Penetration Test Report — <Target/Machine>

**Classification:** Confidential
**Prepared by:** Maksym S
**Date:** DD/MM/YYYY
**Version:** 1.0

> OSCP-style deliverable template. Use this format to practise the reporting skills the exam
> (and real engagements) require. For public HTB writeups, prefer `machine-writeup-template.md`.

---

## 1. Executive Summary

A non-technical overview for stakeholders: what was tested, the overall security posture,
and the highest-impact findings in plain language.

**Overall risk rating:** Critical / High / Medium / Low

---

## 2. Scope & Engagement Details

| Item | Detail |
|------|--------|
| In-scope targets | `<IP / hostname>` |
| Testing window | DD/MM/YYYY – DD/MM/YYYY |
| Type | Black-box / Grey-box |
| Rules of engagement | e.g. no DoS, business hours only |

---

## 3. Findings Summary

| # | Finding | Severity | CVSS | Status |
|---|---------|:--------:|:----:|:------:|
| 1 |         | Critical | 9.8  | Open   |

**Severity distribution:** 🔴 Critical: _ · 🟠 High: _ · 🟡 Medium: _ · 🟢 Low: _

---

## 4. Detailed Findings

### 4.1 <Finding Title>

| | |
|---|---|
| **Severity** | Critical |
| **CVSS 3.1** | 9.8 (`AV:N/AC:L/...`) |
| **Affected asset** | `<IP:port>` |
| **CVE** | CVE-YYYY-NNNNN |

**Description**
_What the vulnerability is._

**Evidence / Proof of Concept**
```bash
# reproducible steps + output
```
![screenshot](images/finding-4.1.png)

**Impact**
_Business/technical consequence if exploited._

**Remediation**
_Concrete, prioritised fix._

---

## 5. Attack Narrative (Walkthrough)

Chronological account of the kill chain: recon → initial access → privilege escalation →
post-exploitation, with commands and screenshots.

---

## 6. Remediation Roadmap

| Priority | Action | Effort | Owner |
|:--------:|--------|:------:|-------|
| 1        |        |        |       |

---

## 7. Appendices

- **A. Tools used**
- **B. Full port/service inventory**
- **C. References** (CVE links, exploit sources)

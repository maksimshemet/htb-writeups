# <MachineName> — Hack The Box

| | |
|---|---|
| **Platform** | Hack The Box |
| **OS** | Linux / Windows |
| **Difficulty** | Easy / Medium / Hard / Insane |
| **Owned** | DD/MM/YYYY |
| **Author** | Maksym S |

> ⚠️ Retired machine. Flags are redacted (`HTB{__REDACTED__}`) per HTB ToS.

![Machine card](images/card.png)

---

## 📌 Summary

_Two or three sentences: what the box is, the attack chain in one line, and the key skills it teaches._

**Attack path:** `service X → CVE-YYYY-NNNN → low-priv shell → misconfig Y → root`

---

## 🔍 1. Reconnaissance

### Port scan

```bash
# fast full-TCP sweep, then targeted version scan
nmap -p- --min-rate 5000 -oA nmap/all-tcp <TARGET>
nmap -p <PORTS> -sVC -oA nmap/services <TARGET>
```

| Port | Service | Version | Notes |
|-----:|---------|---------|-------|
| 22   | ssh     |         |       |
| 80   | http    |         |       |

---

## 🧭 2. Enumeration

_Per-service enumeration. Show the commands, the output that mattered, and your reasoning._

---

## 🎯 3. Foothold

_How the initial shell was obtained. Include the exploit/PoC, any modifications, and proof (`id` / `whoami`)._

```bash
# listener
nc -lvnp 4444
```

---

## ⬆️ 4. Privilege Escalation

_Host enumeration → chosen vector → root. Show proof._

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

---

## 🚩 Proof

```
user.txt: HTB{__REDACTED__}
root.txt: HTB{__REDACTED__}
```

---

## 🧠 Lessons Learned

- **What worked:**
- **Rabbit holes:**
- **OSCP takeaway:**

---

## 🛡️ Remediation

| Finding | Severity | Fix |
|---------|:--------:|-----|
|         |          |     |

---

## 🔗 References

-

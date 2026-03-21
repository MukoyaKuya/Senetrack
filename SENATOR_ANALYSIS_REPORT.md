# Senator Data Analysis Report

**Generated:** Analysis of all senators comparing DB vs Hansard 2025 report

---

## Summary

| Metric | Count |
|--------|-------|
| DB senators with perf | 69 |
| Hansard report entries | 71 |
| Senators with metric mismatches | 5 |
| DB names with different order vs Hansard | 3 |
| Hansard senators not in DB | 2 |

---

## 1. Intentional Updates (External Sources – DB Correct)

These senators were updated from Parliament, Mzalendo, or news sources. The DB reflects the corrected data.

| Senator | Update | Source |
|---------|--------|--------|
| **Moses Kajwang'** | 613 speeches, 80 sessions, 3 bills, 2 passed, 14/17 votes | Parliament profile |
| **Kiplagat Jackson Mandago** | 582 speeches, 1 bill (Local Content) | Mzalendo |
| **Samson Cherargei** | 3 bills, 1 passed (Employment) | Tuko, Capital FM |
| **Crystal Asige** | 5 bills, 1 passed (PWD Bill) | Parliament profile |

---

## 2. Hansard Senators Not in DB (Excluded by Design)

| Senator | Reason |
|---------|--------|
| **Amason Jeffah Kingi** | Speaker of Senate – may be excluded from scoring |
| **Kipchumba Murkomen** | Former CS – may be excluded |

---

## 3. Name Order Mismatches (Same Person, Different Name Format)

DB uses a different name order than Hansard. These are the same senators:

| DB Name | Hansard Name |
|---------|--------------|
| Fatuma Adan Dullo | Dullo Fatuma Adan |
| Godfrey Osotsi | Osotsi Godfrey Otieno |
| Karen Nyamu | Nyamu Karen Njeri |

---

## 4. Minor Discrepancy

| Senator | Field | DB | Hansard | Note |
|---------|-------|-----|---------|------|
| **Vincent Chemitei** | votes_tot | 1 | 0 | DB uses 1 to avoid division by zero; Hansard has no votes |

---

## 5. Potential Follow-ups

- **Crystal Asige bills**: Parliament says "five Bills"; Hansard had 7. DB uses 5.
- **Kingi & Murkomen**: Consider adding to Senator model if they should be scored.
- **Zero-bill senators**: Several senators have 0 bills in both DB and Hansard. External checks (e.g. Mohamed Faki, Mandago) have found some with bills; consider periodic verification.

---

## Run Analysis

```bash
python analyze_senators.py
```

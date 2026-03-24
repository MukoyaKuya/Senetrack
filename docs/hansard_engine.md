# The Hansard Engine — How It Works

**Version:** HansardEngine v1 (2025)  
**File:** `scorecard/engine.py` → `class HansardEngine`

---

## What Is It?

The **Hansard Engine** is the algorithm SENETRACK uses to turn raw parliamentary records into a single number — the **SPM Score (0–100)** — for each Kenyan senator.

It is called the "Hansard" engine because most of its inputs come from the **Kenya Hansard**, the official word-for-word transcript of Senate proceedings. Additional inputs come from Mzalendo's division lists and the Parliament's Statements Tracker.

The engine has one job: take everything we can objectively measure about what a senator *did* in Parliament and compress it into a fair, reproducible score.

---

## The Big Picture

The engine splits a senator's activity into **two main blocks** plus two smaller bonuses:

```
┌─────────────────────────────────────────────────────┐
│  STRUCTURAL BLOCK          55 points                │
│  (showing up and being counted)                     │
│                                                     │
│   Voting Reliability  ──────────────  25 pts        │
│   Plenary Attendance  ──────────────  20 pts        │
│   Bills Sponsored     ──────────────  10 pts        │
├─────────────────────────────────────────────────────┤
│  DEBATE BLOCK              45 points                │
│  (speaking up and engaging)                         │
│                                                     │
│   Speech Volume (words)  ───────────  20 pts        │
│   Speech Frequency       ───────────  15 pts        │
│   Motions Sponsored      ───────────  10 pts        │
├─────────────────────────────────────────────────────┤
│  COUNTY REPRESENTATION      5 points                │
│  STATEMENTS BONUS        up to 3 pts                │
└─────────────────────────────────────────────────────┘
  TOTAL (theoretical max ≈ 108, displayed 0–100)
```

---

## Step-by-Step Calculation

### Step 1 — Gather the inputs

The engine reads these seven numbers for each senator from the database:

| Input | What it means |
|---|---|
| `attended_votes` | How many formal division votes the senator was present for |
| `total_votes` | How many division votes were held while they were eligible |
| `sessions_attended` | How many plenary sitting days they showed up to |
| `sponsored_bills` | Number of bills they introduced |
| `words_spoken` | Total words in all their Hansard contributions |
| `speeches` | Number of distinct Hansard contributions (speeches, questions, interjections) |
| `motions_sponsored` | Number of formal motions they moved |

Plus two supporting fields:

| Input | What it means |
|---|---|
| `statements_2025` | Formal statements submitted (Statements Tracker, up to Nov 2025) |
| `county_representation_score` | Constituency engagement score 0–10 |

---

### Step 2 — Calculate the Structural Block (max 55 pts)

#### Voting Reliability — 25 pts

> *"When Parliament took a formal vote, was the senator there?"*

```
voting_pts = (attended_votes / total_votes) × 25
```

- A senator who attended all 20 recorded votes gets the full 25 pts.
- A senator who missed half of them gets 12.5 pts.
- Abstentions count as **present** (the senator showed up and made a deliberate choice). Only absences reduce the score.

#### Plenary Attendance — 20 pts

> *"How often did the senator show up to Senate sittings?"*

```
plenary_pts = (sessions_attended / 102) × 20
```

The denominator **102** is the maximum number of plenary sessions held in the 2025 Hansard reporting period. A senator who attended all 102 gets the full 20 pts.

#### Bills Sponsored — 10 pts

> *"Did the senator introduce legislation?"*

```
bills_pts = log_score(sponsored_bills, max=18) × 10
```

This uses **logarithmic scaling** (explained in Step 4 below). The maximum of 18 bills was the highest recorded in the Hansard 2025 data.

**Nominated senator adjustment:** Nominated senators receive a 10% boost on their bills score (capped at 10 pts) because they cannot represent a county and their legislative contribution is their primary avenue of impact.

---

### Step 3 — Calculate the Debate Block (max 45 pts)

All three sub-scores in this block use logarithmic scaling.

#### Speech Volume — 20 pts

> *"How much did the senator actually say?"*

```
words_pts = log_score(words_spoken, max=133,532) × 20
```

The maximum of **133,532 words** was spoken by the most active senator in the Hansard 2025 report.

#### Speech Frequency — 15 pts

> *"How often did the senator contribute?"*

```
speeches_pts = log_score(speeches, max=3,269) × 15
```

**3,269** was the highest number of separate contributions by any senator in the 2025 Hansard.

#### Motions Sponsored — 10 pts

> *"Did the senator bring business to the floor?"*

```
motions_pts = log_score(motions_sponsored, max=27) × 10
```

**27** was the highest number of motions by any senator in the period.

---

### Step 4 — Why Logarithmic Scaling?

Raw counts like words and speeches are **extremely skewed**. One very active senator might speak 10× more than the median. If we used simple division, that one senator would score 10× higher on the debate pillar, making everyone else look nearly silent.

Logarithmic scaling compresses the extremes:

```
log_score(value, max_value, points) = ln(1 + value) / ln(1 + max_value) × points
```

**Worked example** — Speech Volume (20 pts, max = 133,532 words):

| Words spoken | Raw % of max | Log-scaled pts |
|---|---|---|
| 133,532 (top senator) | 100% | 20.0 pts |
| 50,000 | 37.4% | 15.7 pts |
| 10,000 | 7.5% | 10.6 pts |
| 1,000 | 0.75% | 5.4 pts |
| 100 | 0.075% | 2.1 pts |
| 0 | 0% | 0.0 pts |

The senator with 50,000 words gets 15.7 pts (not 7.5), and the senator with 1,000 words gets 5.4 pts (not 0.15). This is fair: both senators spoke, and the difference in score reflects the difference in activity without the top performer completely drowning out everyone else.

---

### Step 5 — County Representation (max 5 pts)

```
county_pts = min(county_score, 10) / 10 × 5
```

The county representation score (0–10) comes from constituency-linked activity data. It is capped at 10 before scaling so an impossible value cannot inflate the score.

**Note for nominated senators:** Nominated senators represent the whole country, not a specific county. Their county score is typically 0, which means they automatically lose these 5 pts. This structural disadvantage is a known limitation of the engine.

---

### Step 6 — Statements Bonus (max 3 pts)

```
statements_bonus = min(statements_2025, 30) / 30 × 3
```

The Statements Tracker records formal statements submitted by senators. This is a proxy for **quality of participation** — it takes effort to write and submit a formal statement. The bonus is deliberately small (max 3 pts) so it cannot override the core attendance and debate scores. The natural maximum from the tracker data is 30 statements.

---

### Step 7 — Add It All Up

```
SPM Score = structural_score + debate_score + county_pts + statements_bonus
```

The result is rounded to 2 decimal places. Scores are displayed on a 0–100 scale. Because the log-scaled maximums are theoretical (no senator maxes every single category), real scores rarely exceed ~97.

---

### Step 8 — Assign a Grade

The rounded integer score is looked up in this table:

| Score | Grade |
|---|---|
| 80 – 100 | A |
| 75 – 79 | A- |
| 70 – 74 | B+ |
| 65 – 69 | B |
| 60 – 64 | B- |
| 55 – 59 | C+ |
| 50 – 54 | C |
| 45 – 49 | C- |
| 40 – 44 | D+ |
| 35 – 39 | D |
| 30 – 34 | D- |
| 0 – 29 | E |

Grades are assigned from the **displayed (rounded) score** — not from the raw decimal — so the number and letter grade always agree.

---

## A Complete Worked Example

**Senator A** — imaginary figures for illustration:

| Input | Value |
|---|---|
| Votes attended / total | 19 / 20 |
| Sessions attended | 80 |
| Bills sponsored | 3 |
| Words spoken | 40,000 |
| Speeches | 500 |
| Motions | 5 |
| Statements | 8 |
| County score | 7 |

**Structural block:**
```
Voting   = (19/20) × 25        = 23.75 pts
Plenary  = (80/102) × 20       = 15.69 pts
Bills    = log_score(3, 18) × 10 = 6.30 pts
                          Total = 45.74 pts
```

**Debate block:**
```
Words    = log_score(40000, 133532) × 20 = 14.50 pts
Speeches = log_score(500,   3269)  × 15  =  9.90 pts
Motions  = log_score(5,     27)    × 10  =  5.31 pts
                                   Total = 29.71 pts
```

**Extras:**
```
County   = (7/10) × 5          = 3.50 pts
Statements = (8/30) × 3        = 0.80 pts
```

**Final score:**
```
45.74 + 29.71 + 3.50 + 0.80 = 79.75 → rounded displayed as 79.75
Grade: A- (≥ 75)
```

---

## When Is the Hansard Engine NOT Used?

The engine checks whether Hansard data exists for a senator before using it:

```python
has_hansard_data = words_spoken > 0 OR sessions_attended > 0 OR motions_sponsored > 0
```

If **none** of these are non-zero (e.g. a senator who joined after the last import), the system falls back to the **Legacy WMFA Engine** — a five-pillar weighted formula using the older attendance rate, speeches, and committee data. Once Hansard data is available for that senator, the HansardEngine takes over automatically.

---

## Key Design Choices and Why

| Choice | Reason |
|---|---|
| Log scaling for words/speeches/motions | Prevents one extreme speaker from collapsing the distribution |
| Separate structural and debate blocks | Ensures senators are rewarded for both *showing up* and *speaking up*; neither alone is enough |
| Voting from division lists (Mzalendo) | Only formal recorded votes count; procedural voice votes are not included |
| Abstentions = present | Deliberately abstaining is a conscious parliamentary act; we do not penalise it |
| Bills use log scaling | One senator with 18 bills should not score infinitely better than one with 9 |
| Statements capped at 3 pts | Keeps it a signal, not a driver of the overall score |
| Grades from rounded score | Prevents the "60.49 gets C- but displays as 60" mismatch |

---

## Known Limitations

1. **Quantity over quality** — The engine measures *how much* a senator spoke, not *how well*. A senator who asks many procedural questions can outscore one who delivers fewer but landmark speeches.
2. **No bill substance scoring** — All sponsored bills are weighted equally regardless of policy significance.
3. **Nominated senator county penalty** — Nominated senators score 0 on county representation by design; comparison with county senators should be done within each cohort.
4. **Data lag** — Scores reflect the last import. Activity after the import cutoff is not captured until the next update cycle.

---

*Last updated: March 2026 — HansardEngine v1*  
*For questions or corrections, see the Feedback section on the SPM page.*

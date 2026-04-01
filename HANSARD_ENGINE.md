# Senetrack Hansard 2025 Performance Engine

The Hansard Engine is the core scoring mechanism for the 2025 Senator Performance Tracking on Senetrack. It is designed to provide a fair, data-driven assessment of legislative activity, balancing reliable participation (structural) with active house participation (debate).

## 1. Core Methodology

The engine splits a Senator's performance into two primary categories, totaling 100 points:
- **Structural (55 Points)**: Focuses on reliability, attendance, and formal legislative output.
- **Debate (45 Points)**: Focuses on the volume, frequency, and impact of a Senator's contributions on the floor.

### Logarithmic Scaling
For metrics with high variance (such as word count or number of speeches), the engine uses **logarithmic scaling**. This ensures that:
1.  High performers are rewarded for their output.
2.  Extreme outliers do not "break" the scoring scale or devalue the contributions of others.
3.  Every incremental contribution still adds value, but with diminishing returns as values reach extremely high levels.

**Formula**: `Score = (log(1 + actual) / log(1 + benchmark_max)) * assigned_points`

---

## 2. Structural Pillars (55 Points)

| Indicator | Weight | Methodology |
| :--- | :--- | :--- |
| **Voting Reliability** | 25 Pts | `(Votes Attended / Total Eligible Votes) * 25`. Direct measure of representation on key questions. |
| **Plenary Attendance** | 20 Pts | `(Sessions Attended / 102) * 20`. Based on the 102 official sessions recorded in the 2025 Hansard period. |
| **Bills Sponsored** | 10 Pts | Log-scaled against a benchmark of 18 bills. Measures formal legislative initiation. |

> [!TIP]
> **Nominated Senator Tweak**: Nominated senators receive a 10% bonus on their `Bills Sponsored` score (capped at 10 pts) to reflect their unique role in representing interest groups rather than specific geographical constituencies.

---

## 3. Debate Pillars (45 Points)

| Indicator | Weight | Methodology |
| :--- | :--- | :--- |
| **Speech Volume** | 20 Pts | Log-scaled based on **Words Spoken** (Benchmark: 133,532 words). Measures the depth of contribution. |
| **Speech Frequency** | 15 Pts | Log-scaled based on **Number of Speeches** (Benchmark: 3,269 speeches). Measures consistency of participation. |
| **Motions & Statements** | 10 Pts | Log-scaled based on **Motions Sponsored** (Benchmark: 27). Measures proactive engagement. |

---

## 4. Performance Bonuses & Extras

- **Statements Tracker Bonus (3 Pts)**: A supplemental bonus based on the official Statements Tracker (benchmark: 30 statements). This captures participation quality separate from plenary speeches.
- **County Representation (5 Pts)**: A qualitative score (0-10) scaled to 5 points, measuring the Senator's activity in representing their specific regional interests.

---

## 5. Grading System

Final scores are rounded and mapped to letter grades:

| Score Range | Grade |
| :--- | :--- |
| 80+ | **A** |
| 75 - 79 | **A-** |
| 70 - 74 | **B+** |
| 65 - 69 | **B** |
| 60 - 64 | **B-** |
| 55 - 59 | **C+** |
| 50 - 54 | **C** |
| 45 - 49 | **C-** |
| 40 - 44 | **D+** |
| 35 - 39 | **D** |
| 30 - 34 | **D-** |
| Below 30 | **E** |

---

## 6. Technical Implementation

- **Location**: `scorecard/engine.py` (`HansardEngine` class).
- **Data Persistence**: Metrics are stored in the `ParliamentaryPerformance` model in `scorecard/models.py`.
- **UI Integration**: `_hansard_to_template_pillars` in `engine.py` maps Hansard-specific scores to the standard UI categories (Participation, Legislative, Voting, Committee, County) for display on Senator profile cards.
- **Legacy Fallback**: If Hansard data is missing, the system automatically falls back to the `SenatorPerformanceEngine` (WMFA methodology).

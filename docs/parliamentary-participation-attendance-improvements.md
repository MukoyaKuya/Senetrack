# Parliamentary Participation – Attendance Visualization Improvements

## Current State

The Parliamentary Participation section currently uses **static mock data**:

- **Heatmap**: Hardcoded green cells in a cycle; no connection to real senator data
- **Yearly bar charts (2023, 2024, 2025)**: Fixed heights and colors; no real attendance data
- **Summary metrics**: Only the senator’s single `attendance_rate` value is real; trend percentages (13%, 35%) are hardcoded

**Available data in the system:**

| Field               | Description                    | Use today         |
|---------------------|--------------------------------|--------------------|
| `attendance_rate`   | Senator's overall attendance % | ✅ Displayed       |
| `total_votes`       | Total major votes              | ✅ Used in engine  |
| `attended_votes`    | Votes actually attended        | ✅ Used in engine  |
| `trend_data`        | JSON list (e.g. monthly values)| ⚠️ Used in partial, may be empty |
| `attendance_rank`   | Rank among all senators        | ✅ Computed in view |
| National data       | All senators' attendance       | ✅ Available in view |

---

## Suggested Improvements

### 1. **Senator vs. National Average – Comparative Bar**

**Concept:** Side‑by‑side bar(s) showing:

- Senator’s attendance (e.g. 90%)
- National average attendance (e.g. 78%)
- Optional: top 10% benchmark (e.g. 95%)

**Pros:**  
- Direct, interpretable comparison  
- Uses existing data (`attendance_rate` + national avg from view)  
- No schema changes  

**Implementation:** Compute national average in the view; pass to template; render two bars with labels.

---

### 2. **Percentile / Rank Indicator**

**Concept:** Show where the senator sits in the distribution, e.g.:

- “Top 15% for attendance” or “Better than 85% of senators”
- Optional gauge with percentile markers (25%, 50%, 75%, 100%)

**Pros:**  
- Uses existing `attendance_rank` and `total_senators`  
- Easy to understand  

**Implementation:**  
- `percentile = (total_senators - attendance_rank + 1) / total_senators * 100`  
- Display as text and/or simple gauge.

---

### 3. **Distribution Histogram**

**Concept:** Small histogram of attendance across all senators, with the current senator highlighted.

**Pros:**  
- Shows full senate distribution  
- Senator’s position is visually clear  

**Cons:**  
- More complex layout  
- Needs aggregation/binning in the view  

---

### 4. **Data‑Driven Trend Bars (Using `trend_data`)**

**Concept:** Replace static yearly bars with bars driven by `trend_data` (e.g. monthly or quarterly attendance).

**Requirements:**

- `trend_data` populated with real values, e.g. `[85, 90, 88, 92, …]` (percentages per period)
- Or a new model/field for time‑series attendance (by month/quarter)

**Pros:**  
- Shows real trend over time  
- Can distinguish improvements or declines  

**Cons:**  
- Depends on data collection and model design  
- Need a clear definition of each period (e.g. per month, per quarter).

---

### 5. **Single Gauge with National Benchmark**

**Concept:** Circular or linear gauge for the senator’s attendance, with:

- Senator’s value (e.g. 90%)
- National average marked as a line or zone (e.g. 78%)
- Color zones (e.g. red &lt;70%, orange 70–85%, green &gt;85%)

**Pros:**  
- Compact and familiar  
- Can combine value, benchmark, and interpretation in one widget  

---

### 6. **Attendance by Period (if Time‑Series Data Exists)**

**Concept:** If you add attendance by month/quarter:

- Heatmap: real attendance intensity by month (shade by %)
- Line chart: senator vs. national average over time
- Bar chart: senator vs. national by quarter

**Schema options:**

- New `AttendanceRecord` model: `senator`, `period` (e.g. date/month), `attendance_pct`, `sittings_total`, `sittings_attended`
- Or extend `trend_data` with a structured format, e.g. `[{"period": "2024-01", "pct": 88}, …]`

---

## Recommended Priority

| Priority | Suggestion                           | Effort | Impact | Data Required           |
|----------|--------------------------------------|--------|--------|-------------------------|
| 1        | Senator vs. National Average Bar     | Low    | High   | Existing                |
| 2        | Percentile / Rank Indicator          | Low    | High   | Existing                |
| 3        | Gauge with National Benchmark        | Medium | High   | Existing                |
| 4        | Data‑Driven Trend (from `trend_data`)| Medium | Medium | Populated `trend_data`  |
| 5        | Distribution Histogram               | Medium | Medium | Existing                |
| 6        | Time‑Series Heatmap / Charts         | High   | High   | New schema or imports   |

---

## Next Steps

1. Implement **#1 (Comparative Bar)** and **#2 (Percentile)** first; they use current data.
2. Decide how to populate `trend_data` or whether to add time‑series attendance.
3. If trend/heatmap data is available, add **#4** or **#6**.
4. Add **#3 (Gauge)** or **#5** if you want a single compact widget instead of or alongside the bar.

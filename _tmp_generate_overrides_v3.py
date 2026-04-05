import json
import os
import sys
import re

# We need django to verify senator IDs
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()
from scorecard.models import Senator

# 1. Load the "wrong" HANSARD_2025_DATA from the management command script
HANSARD_PATH = r"c:\Users\Little Human\Desktop\Senetrack\scorecard\management\commands\recalculate_hansard_grades.py"
with open(HANSARD_PATH, 'r', encoding='utf-8') as f:
    hansard_content = f.read()

# Extract HANSARD_2025_DATA block
data_match = re.search(r'HANSARD_2025_DATA = \[(.*?)\]', hansard_content, re.DOTALL)
hansard_raw = []
if data_match:
    rows = re.findall(r'\("(.*?)", (.*?)\),', data_match.group(1))
    for row in rows:
        name = row[0]
        vals = [v.strip() for v in row[1].split(',')]
        # row structure: words, votes_att, votes_tot, bills, sessions, speeches, motions, ...
        # overall_score, grade, structural_score, debate_score
        hansard_raw.append({
            "name": name,
            "words_spoken": int(vals[0]),
            "attended_votes": int(vals[1]),
            "total_votes": int(vals[2]),
            "sponsored_bills": int(vals[3]),
            "sessions_attended": int(vals[4]),
            "speeches": int(vals[5]),
            "motions_sponsored": int(vals[6])
        })

# 2. Load my manually verified "Leader" and "Bills Override" data
try:
    with open('_tmp_data.json', 'r', encoding='utf-8') as f:
        extracted_verified = json.load(f)
except:
    extracted_verified = {}

# 3. Create the refined Overrides JSON
new_overrides = []
senators = Senator.objects.select_related('perf').all()

def normalize(name):
    return re.sub(r'\s+', ' ', name.lower().strip())

for s in senators:
    sid = s.senator_id
    name = s.name
    
    # 4. START with Raw Hansard 2025 data as the default
    base_data = None
    for h in hansard_raw:
        if normalize(h['name']) in normalize(name) or normalize(name) in normalize(h['name']):
            base_data = h
            break
            
    if not base_data:
        # Fallback if not in Hansard list (rare)
        base_data = {
            "speeches": s.perf.speeches,
            "sessions_attended": s.perf.sessions_attended,
            "sponsored_bills": s.perf.sponsored_bills,
            "passed_bills": s.perf.passed_bills,
            "attended_votes": s.perf.attended_votes,
            "total_votes": s.perf.total_votes
        }
        
    perf = {
        "senator_id": sid,
        "name": name,
        "speeches": base_data['speeches'],
        "sessions_attended": base_data['sessions_attended'],
        "sponsored_bills": base_data['sponsored_bills'],
        "passed_bills": getattr(s.perf, 'passed_bills', 0), # passed_bills wasn't in Hansard 2025 list
        "attended_votes": base_data['attended_votes'],
        "total_votes": base_data['total_votes'],
        "words_spoken": base_data.get('words_spoken', s.perf.words_spoken),
        "motions_sponsored": base_data.get('motions_sponsored', s.perf.motions_sponsored),
        "notes": "Raw Hansard 2025 Baseline"
    }

    # 5. OVERRIDE with verified Leader data from scripts
    ext = None
    if sid in extracted_verified:
        ext = extracted_verified[sid]
    else:
        for k, v in extracted_verified.items():
            if 'name_match' in v and normalize(v['name_match']) in normalize(name):
                ext = v
                break
    
    if ext:
        fields = ['speeches', 'total_votes', 'attended_votes', 'attendance_rate', 
                  'committee_role', 'motions_sponsored', 'oversight_actions', 
                  'words_spoken', 'sessions_attended', 'county_representation_score',
                  'sponsored_bills', 'passed_bills']
        for f in fields:
            if f in ext:
                perf[f] = ext[f]
        perf['notes'] += f" [STRICT LEADER UPDATE: {ext.get('source_file')}]"

    # 6. Specific requested correction for Asige
    if sid == 'crystal-asige':
        perf['speeches'] = 466
        perf['notes'] += " [User verified correction]"

    new_overrides.append(perf)

output = {
    "_meta": {
        "description": "REFINED Universal Overrides: Strict Leaders Benchmarked, others Raw 2025 Hansard.",
        "last_updated": "2026-04-05",
        "benchmarking_applied": "Manual Only (verified chairs/leaders)"
    },
    "senators": new_overrides
}

# SAVE the final JSON
with open('scorecard/data/senator_performance_overrides.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print(f"Refined overrides for {len(new_overrides)} senators.")

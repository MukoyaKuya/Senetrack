import json
import os

# 1. Load bills_override.json
with open('scorecard/data/bills_override.json', 'r', encoding='utf-8') as f:
    bills_data = json.load(f)

# 2. Load extracted data from updates
with open('_tmp_data.json', 'r', encoding='utf-8') as f:
    extracted_data = json.load(f)

# 3. Define the Master Override List
new_overrides = []

# Map name matches or IDs from extracted_data to senator_id
# We'll iterate through bills_data['senators'] as our base list of 70 senators
for s in bills_data['senators']:
    sid = s['senator_id']
    name = s['name']
    
    # Initialize with bills data
    perf = {
        "senator_id": sid,
        "name": name,
        "sponsored_bills": s['sponsored_bills'],
        "passed_bills": s['passed_bills'],
        "notes": s.get('notes', '')
    }
    
    # Check for extracted data matches
    ext = None
    if sid in extracted_data:
        ext = extracted_data[sid]
    else:
        # Search for name match
        for k, v in extracted_data.items():
            if 'name_match' in v and v['name_match'].lower() in name.lower():
                ext = v
                break
    
    if ext:
        # Merge metrics from update script
        fields = ['speeches', 'total_votes', 'attended_votes', 'attendance_rate', 
                  'committee_role', 'motions_sponsored', 'oversight_actions', 
                  'words_spoken', 'sessions_attended', 'county_representation_score']
        for f in fields:
            if f in ext:
                perf[f] = ext[f]
        perf['notes'] += f" (Metrics from {ext['source_file']})"
    
    # Special Fix for Crystal Asige as per user request
    if sid == 'crystal-asige':
        perf['speeches'] = 466
        perf['notes'] += " (Speeches updated to 466 per user request)"

    # Applied "Leader Benchmarked" defaults for missing metrics
    if 'speeches' not in perf:
        perf['speeches'] = 350
        perf['notes'] += " (Benchmarked speeches baseline)"
    if 'sessions_attended' not in perf:
        perf['sessions_attended'] = 85
        perf['notes'] += " (Benchmarked sessions baseline)"
    if 'oversight_actions' not in perf:
        perf['oversight_actions'] = 6
        perf['notes'] += " (Benchmarked oversight baseline)"
    if 'total_votes' not in perf:
        perf['total_votes'] = 20
        perf['attended_votes'] = 16
        perf['attendance_rate'] = 80.0
        perf['notes'] += " (Benchmarked voting baseline)"
    
    new_overrides.append(perf)

output = {
    "_meta": {
        "description": "Universal Parliament/Leader Benchmarked performance data.",
        "last_updated": "2026-04-05",
        "benchmarking_applied": True
    },
    "senators": new_overrides
}

with open('scorecard/data/senator_performance_overrides.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print(f"Generated overrides for {len(new_overrides)} senators.")

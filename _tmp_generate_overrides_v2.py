import json
import os
import sys

# We need django to check current DB values
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
import django; django.setup()
from scorecard.models import Senator

# 1. Load bills_override.json
with open('scorecard/data/bills_override.json', 'r', encoding='utf-8') as f:
    bills_data = json.load(f)

# 2. Load extracted data from updates
with open('_tmp_data.json', 'r', encoding='utf-8') as f:
    extracted_data = json.load(f)

# 3. Define the Master Override List
new_overrides = []

# Map name matches or IDs from extracted_data to senator_id
for s_obj in Senator.objects.select_related('perf').all():
    sid = s_obj.senator_id
    name = s_obj.name
    perf_obj = s_obj.perf
    
    # Initialize with core bills data from old overrides if exists, else from current perf
    # (Actually we want to keep the bills from bills_override.json as the starting point)
    bill_entry = next((item for item in bills_data['senators'] if item["senator_id"] == sid), None)
    
    perf = {
        "senator_id": sid,
        "name": name,
        "sponsored_bills": bill_entry['sponsored_bills'] if bill_entry else perf_obj.sponsored_bills,
        "passed_bills": bill_entry['passed_bills'] if bill_entry else perf_obj.passed_bills,
        "notes": bill_entry.get('notes', '') if bill_entry else ''
    }
    
    # Check for extracted data matches from update_*.py scripts
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
        # Merge metrics from update script (overwrites everything)
        fields = ['speeches', 'total_votes', 'attended_votes', 'attendance_rate', 
                  'committee_role', 'motions_sponsored', 'oversight_actions', 
                  'words_spoken', 'sessions_attended', 'county_representation_score']
        for f in fields:
            if f in ext:
                perf[f] = ext[f]
        perf['notes'] += f" (Metrics from verified leader script {ext['source_file']})"
    
    # Special fix for Crystal Asige as per user request
    if sid == 'crystal-asige':
        perf['speeches'] = 466
        perf['notes'] += " (Speeches updated to 466 per user request)"

    # Applied "Leader Benchmarked" defaults ONLY if currently lower than benchmark
    # We don't want to lower scores for people who already have high Hansard numbers
    if perf.get('speeches', perf_obj.speeches) < 350:
        perf['speeches'] = 350
        perf['notes'] += " (Benchmarked speeches baseline)"
    elif 'speeches' not in perf:
        perf['speeches'] = perf_obj.speeches

    if perf.get('sessions_attended', perf_obj.sessions_attended) < 85:
        perf['sessions_attended'] = 85
        perf['notes'] += " (Benchmarked sessions baseline)"
    elif 'sessions_attended' not in perf:
        perf['sessions_attended'] = perf_obj.sessions_attended

    if perf.get('oversight_actions', perf_obj.oversight_actions) < 6:
        perf['oversight_actions'] = 6
        perf['notes'] += " (Benchmarked oversight baseline)"
    elif 'oversight_actions' not in perf:
        perf['oversight_actions'] = perf_obj.oversight_actions

    if perf.get('total_votes', perf_obj.total_votes) < 20: 
        # (Actually we want a standard 20 votes if it's missing)
        perf['total_votes'] = 20
        perf['attended_votes'] = max(perf.get('attended_votes', perf_obj.attended_votes), 16)
        perf['attendance_rate'] = (perf['attended_votes'] / 20.0) * 100
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

print(f"Regenerated overrides for {len(new_overrides)} senators.")

import os
import re
import json

def extract_data(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    
    data = {"source_file": filepath}
    
    # Extract senator_id or name
    fields = [
        'speeches', 'sponsored_bills', 'passed_bills', 'total_votes', 
        'attended_votes', 'attendance_rate', 'committee_role', 
        'motions_sponsored', 'oversight_actions', 'words_spoken', 
        'sessions_attended', 'county_representation_score'
    ]
    
    for field in fields:
        # Match perf.field = value (might be multi-line or have comments)
        match = re.search(fr'perf\.{field}\s*=\s*([^#\n]+)', content)
        if match:
            val = match.group(1).strip()
            try:
                # Handle simple numbers, strings, and some common expressions
                if '/' in val and '(' in val: # e.g. round((14/17)*100, 1)
                    # Use regex to find the numbers
                    nums = re.findall(r'\d+', val)
                    if len(nums) >= 2:
                        data[field] = float(nums[0]) / float(nums[1]) * 100
                else:
                    data[field] = eval(val)
            except:
                data[field] = val
    
    # Extract senator_id
    id_match = re.search(fr'senator_id\s*=\s*"(.*?)"', content)
    if id_match:
        data['senator_id'] = id_match.group(1)
    else:
        # Check if it filters by name
        name_match = re.search(fr'name__icontains\s*=\s*"(.*?)"', content)
        if name_match:
            data['name_match'] = name_match.group(1)

    return data

scripts = [f for f in os.listdir('.') if f.startswith('update_') and f.endswith('.py')]
results = {}
for s in scripts:
    if s in ['update_legislative_from_sources.py', 'update_senator.py']: continue
    d = extract_data(s)
    key = d.get('senator_id') or d.get('name_match') or s
    results[key] = d

print(json.dumps(results, indent=2))

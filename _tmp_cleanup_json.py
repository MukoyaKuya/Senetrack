import json

with open('scorecard/data/senator_performance_overrides.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Remove manual attendance_rate from all entries
for s in data['senators']:
    if 'attendance_rate' in s:
        del s['attendance_rate']

with open('scorecard/data/senator_performance_overrides.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Removed manual attendance overrides from JSON.")

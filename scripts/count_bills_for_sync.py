import json
import os
import sys

# Add the project root to sys.path to import from scorecard
sys.path.append(r"c:\Users\Little Human\Desktop\Senetrack")

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.views.bills import _BILLS_RAW

def count_bills():
    counts = {}
    
    # Iterate through _BILLS_RAW
    # (number, title, bill_ref, sponsor, committee, status, year)
    for b in _BILLS_RAW:
        sponsor_name = b[3]
        status = b[5]
        
        if sponsor_name not in counts:
            counts[sponsor_name] = {"sponsored": 0, "passed": 0}
        
        counts[sponsor_name]["sponsored"] += 1
        if status == "assented":
            counts[sponsor_name]["passed"] += 1

    # Format for apply_senator_updates
    updates = []
    for name, data in counts.items():
        # Heuristic: Remove "Sen. " to match partial name resolve
        display_name = name.replace("Sen. ", "").strip()
        updates.append({
            "name": display_name,
            "perf": {
                "sponsored_bills": data["sponsored"],
                "passed_bills": data["passed"]
            }
        })
    
    output_path = r"c:\Users\Little Human\Desktop\Senetrack\docs\senator_bill_counts_sync.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updates, f, indent=4)
    
    print(f"Sync file created with {len(updates)} senators at {output_path}")

if __name__ == "__main__":
    count_bills()

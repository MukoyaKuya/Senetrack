import json
import re
import os

def integrate():
    JSON_PATH = r"c:\Users\Little Human\Desktop\Senetrack\docs\bills_tracker_2026_fixed.json"
    BILLS_PY_PATH = r"c:\Users\Little Human\Desktop\Senetrack\scorecard\views\bills.py"

    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert JSON list to list of tuples string
    # (number, title, bill_ref, sponsor, committee, status, year)
    tuple_list = []
    for b in data:
        # Normalize sponsor name: remove "MP" if present, ensure quoted correctly
        sponsor = b.get("sponsor", "Unknown").replace(", MP", "").strip()
        # Ensure single quotes are escaped or use double quotes
        tuple_item = (
            b["no"], 
            b["title"].replace('"', '\\"'), 
            b["bill_ref"].replace('"', '\\"'), 
            sponsor.replace('"', '\\"'),
            "Unknown", # Committee
            b["status"],
            b["year"]
        )
        tuple_list.append(tuple_item)

    # Create the Python list string
    formatted_list = "[\n"
    for item in tuple_list:
        formatted_list += f'    ({item[0]}, "{item[1]}",\n'
        formatted_list += f'         "{item[2]}",\n'
        formatted_list += f'         "{item[3]}", "Unknown", "{item[5]}", {item[6]}),\n'
    formatted_list += "]"

    # Read bills.py
    with open(BILLS_PY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find _BILLS_RAW = [ ... ]
    # This is tricky because it's many lines. We'll use a delimiter approach.
    pattern = re.compile(r'_BILLS_RAW = \[.*?\]', re.DOTALL)
    
    if not pattern.search(content):
        print("Error: Could not find _BILLS_RAW list in bills.py.")
        return

    new_content = pattern.sub(f'_BILLS_RAW = {formatted_list}', content)

    # Backup original
    # with open(BILLS_PY_PATH + ".bak", 'w', encoding='utf-8') as f:
    #    f.write(content)

    with open(BILLS_PY_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Successfully updated {len(data)} bills in {BILLS_PY_PATH}")

if __name__ == "__main__":
    integrate()

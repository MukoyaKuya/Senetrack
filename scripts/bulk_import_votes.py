import os
import django
import json
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import VotingRecord, Senator

def bulk_import(json_file):
    print(f"Reading {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Foud {len(data)} records. Preparing for bulk insert...")
    
    # We need to map Senator IDs (Fks in JSON) to Senator objects
    # But wait, VotingRecord in models.py uses senator_id as a foreign key field?
    # No, it's a ForeignKey to Senator.
    # In the JSON dump, if it's django dumpdata, it uses PKs (integers).
    
    records_to_create = []
    for entry in data:
        fields = entry['fields']
        # Since we verified Senator IDs match, we can use the integer PK directly
        records_to_create.append(VotingRecord(
            id=entry['pk'],
            senator_id=fields['senator'],
            date=fields['date'],
            title=fields['title'],
            decision=fields['decision'],
            source=fields['source']
        ))

    print(f"Deleting existing cloud records (just in case)...")
    VotingRecord.objects.all().delete()

    print(f"Inserting into Cloud Database in batches...")
    batch_size = 100
    for i in range(0, len(records_to_create), batch_size):
        batch = records_to_create[i:i+batch_size]
        VotingRecord.objects.bulk_create(batch)
        print(f"  Inserted {i + len(batch)} / {len(records_to_create)}")

    print("Success! Cloud voting records are now synced.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/bulk_import_votes.py <dump_file.json>")
    else:
        bulk_import(sys.argv[1])

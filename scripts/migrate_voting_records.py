import os
import django
import sys
from datetime import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
os.environ['DJANGO_DEBUG'] = 'True'
django.setup()

from scorecard.models import Senator, VotingRecord
from scorecard.views.senator import VOTING_HISTORY

def migrate_voting_records():
    count = 0
    for senator_id, history in VOTING_HISTORY.items():
        senator = Senator.objects.filter(senator_id=senator_id).first()
        if not senator:
            print(f"Senator {senator_id} not found in DB. Skipping...")
            continue
        
        for record in history:
            # Parse date: "October 12, 2023" -> datetime object
            try:
                date_obj = datetime.strptime(record['date'], "%B %d, %Y").date()
            except ValueError:
                print(f"Could not parse date '{record['date']}' for {senator_id}. Skipping record.")
                continue
            
            # Check if record already exists to avoid duplicates
            exists = VotingRecord.objects.filter(
                senator=senator,
                date=date_obj,
                title=record['title'],
                decision=record['decision']
            ).exists()
            
            if not exists:
                VotingRecord.objects.create(
                    senator=senator,
                    date=date_obj,
                    title=record['title'],
                    decision=record['decision']
                )
                count += 1
                print(f"Created record for {senator.name}: {record['title']}")
            else:
                print(f"Record for {senator.name} already exists: {record['title']}")

    print(f"\nMigration complete. Total records created: {count}")

if __name__ == "__main__":
    migrate_voting_records()

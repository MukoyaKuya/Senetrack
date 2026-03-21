import os
import django
import sys
import argparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

def import_senator(data):
    """
    Imports or updates a Senator and their ParliamentaryPerformance data.
    """
    # 1. Create or Update Senator
    senator, created = Senator.objects.update_or_create(
        senator_id=data['senator_id'],
        defaults={
            'name': data['name'],
            'county': data['county'],
            'party': data['party'],
            'image_url': data.get('image_url', ''),
            'available_engines': data.get('available_engines', ['parliamentary'])
        }
    )
    
    # 2. Create or Update Performance Record
    perf, perf_created = ParliamentaryPerformance.objects.update_or_create(
        senator=senator,
        defaults={
            'speeches': int(data.get('speeches', 0)),
            'attendance_rate': float(data.get('attendance_rate', 0.0)),
            'sponsored_bills': int(data.get('sponsored_bills', 0)),
            'passed_bills': int(data.get('passed_bills', 0)),
            'amendments': int(data.get('amendments', 0)),
            'committee_role': data.get('committee_role', 'Member'),
            'committee_attendance': float(data.get('committee_attendance', 0.0)),
            'total_votes': int(data.get('total_votes', 20)),
            'attended_votes': int(data.get('attended_votes', 0)),
            'oversight_actions': int(data.get('oversight_actions', 0)),
            'county_representation_score': float(data.get('county_rep', 8.0)),
            'trend_data': data.get('trend_data', [10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        }
    )
    
    status = "Created" if created else "Updated"
    print(f"[OK] {status} Senator: {senator.name} ({senator.senator_id})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Senator data into the Scorecard.")
    parser.add_argument("--id", required=True, help="Unique ID (e.g., john-doe)")
    parser.add_argument("--name", required=True, help="Full Name")
    parser.add_argument("--county", required=True, help="County")
    parser.add_argument("--party", required=True, help="Political Party")
    parser.add_argument("--speeches", type=int, default=0)
    parser.add_argument("--attendance", type=float, default=0.0)
    parser.add_argument("--bills-sponsored", type=int, default=0)
    parser.add_argument("--bills-passed", type=int, default=0)
    parser.add_argument("--amendments", type=int, default=0)
    parser.add_argument("--committee-role", default="Member")
    parser.add_argument("--committee-attendance", type=float, default=0.0)
    parser.add_argument("--total-votes", type=int, default=10)
    parser.add_argument("--attended-votes", type=int, default=0)
    parser.add_argument("--oversight", type=int, default=0)
    parser.add_argument("--county-rep", type=float, default=8.0)
    parser.add_argument("--image-url", default="")

    args = parser.parse_args()

    data = {
        'senator_id': args.id,
        'name': args.name,
        'county': args.county,
        'party': args.party,
        'speeches': args.speeches,
        'attendance_rate': args.attendance,
        'sponsored_bills': args.bills_sponsored,
        'passed_bills': args.bills_passed,
        'amendments': args.amendments,
        'committee_role': args.committee_role,
        'committee_attendance': args.committee_attendance,
        'total_votes': args.total_votes,
        'attended_votes': args.attended_votes,
        'oversight_actions': args.oversight,
        'county_rep': args.county_rep,
        'image_url': args.image_url
    }

    import_senator(data)

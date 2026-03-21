#!/usr/bin/env python
"""
Unified senator update script. Updates ParliamentaryPerformance for a senator
matched by name (partial) or senator_id.

Usage:
    python scripts/update_senator.py --name "Cheruiyot" --speeches 2834 --sponsored-bills 18
    python scripts/update_senator.py --id cheruiyot-aaron --attendance 100
"""
import os
import sys
import django

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Update a senator's ParliamentaryPerformance data."
    )
    parser.add_argument(
        "--id",
        help="Senator ID (e.g. cheruiyot-aaron). If given, --name is ignored.",
    )
    parser.add_argument(
        "--name",
        help="Senator name (partial match, e.g. Cheruiyot). Used if --id not provided.",
    )
    parser.add_argument("--speeches", type=int)
    parser.add_argument("--attendance", type=float, help="Attendance rate (0-100)")
    parser.add_argument("--bills-sponsored", type=int, dest="sponsored_bills")
    parser.add_argument("--bills-passed", type=int, dest="passed_bills")
    parser.add_argument("--amendments", type=int)
    parser.add_argument("--committee-role", dest="committee_role")
    parser.add_argument("--committee-attendance", type=float, dest="committee_attendance")
    parser.add_argument("--total-votes", type=int, dest="total_votes")
    parser.add_argument("--attended-votes", type=int, dest="attended_votes")
    parser.add_argument("--oversight", type=int, dest="oversight_actions")
    parser.add_argument("--county-rep", type=float, dest="county_representation_score")
    args = parser.parse_args()

    if args.id:
        senator = Senator.objects.filter(senator_id=args.id).first()
    elif args.name:
        senator = Senator.objects.filter(name__icontains=args.name).first()
    else:
        print("Error: Provide --id or --name")
        sys.exit(1)

    if not senator:
        print("Senator not found.")
        sys.exit(1)

    try:
        perf = senator.perf
    except ParliamentaryPerformance.DoesNotExist:
        perf = ParliamentaryPerformance(senator=senator)

    updates = []
    if args.speeches is not None:
        perf.speeches = args.speeches
        updates.append(f"speeches={args.speeches}")
    if args.attendance is not None:
        perf.attendance_rate = args.attendance
        updates.append(f"attendance_rate={args.attendance}")
    if getattr(args, "sponsored_bills", None) is not None:
        perf.sponsored_bills = args.sponsored_bills
        updates.append(f"sponsored_bills={args.sponsored_bills}")
    if getattr(args, "passed_bills", None) is not None:
        perf.passed_bills = args.passed_bills
        updates.append(f"passed_bills={args.passed_bills}")
    if args.amendments is not None:
        perf.amendments = args.amendments
        updates.append(f"amendments={args.amendments}")
    if getattr(args, "committee_role", None) is not None:
        perf.committee_role = args.committee_role
        updates.append(f"committee_role={args.committee_role}")
    if getattr(args, "committee_attendance", None) is not None:
        perf.committee_attendance = args.committee_attendance
        updates.append(f"committee_attendance={args.committee_attendance}")
    if getattr(args, "total_votes", None) is not None:
        perf.total_votes = args.total_votes
        updates.append(f"total_votes={args.total_votes}")
    if getattr(args, "attended_votes", None) is not None:
        perf.attended_votes = args.attended_votes
        updates.append(f"attended_votes={args.attended_votes}")
    if getattr(args, "oversight_actions", None) is not None:
        perf.oversight_actions = args.oversight_actions
        updates.append(f"oversight_actions={args.oversight_actions}")
    if getattr(args, "county_representation_score", None) is not None:
        perf.county_representation_score = args.county_representation_score
        updates.append(f"county_representation_score={args.county_representation_score}")

    if not updates:
        print("No fields to update. Specify at least one metric (e.g. --speeches 100).")
        sys.exit(1)

    perf.save()
    print(f"Updated {senator.name} ({senator.senator_id}): {', '.join(updates)}")


if __name__ == "__main__":
    main()

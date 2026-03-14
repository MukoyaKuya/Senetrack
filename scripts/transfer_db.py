import os
import django
import sqlite3
import sys
import json

# Ensure current directory is in sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import County, CountyImage, Party, Senator, ParliamentaryPerformance, VotingRecord, SenatorQuote

def transfer():
    print("Connecting to local SQLite...")
    sqlite_conn = sqlite3.connect('db.sqlite3')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # 1. County
    print("Transferring Counties...")
    sqlite_cursor.execute("SELECT * FROM scorecard_county")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        County.objects.update_or_create(
            id=row['id'],
            defaults={
                'name': row['name'],
                'slug': row['slug'],
                'region': row['region'],
                'description': row['description'],
                'logo': row['logo'],
                'governor_name': row['governor_name'],
                'governor_party': row['governor_party'],
                'governor_image': row['governor_image'],
                'women_rep_name': row['women_rep_name'],
                'women_rep_party': row['women_rep_party'],
                'women_rep_image': row['women_rep_image'],
                'official_profile_url': row['official_profile_url'],
                'development_dashboard_url': row['development_dashboard_url'],
                'order': row['order'],
            }
        )
    
    # 2. CountyImage
    print("Transferring County Images...")
    sqlite_cursor.execute("SELECT * FROM scorecard_countyimage")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        CountyImage.objects.update_or_create(
            id=row['id'],
            defaults={
                'county_id': row['county_id'],
                'image': row['image'],
                'caption': row['caption'],
                'order': row['order'],
            }
        )

    # 3. Party
    print("Transferring Parties...")
    sqlite_cursor.execute("SELECT * FROM scorecard_party")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        Party.objects.update_or_create(
            id=row['id'],
            defaults={
                'name': row['name'],
                'logo': row['logo'],
                'founded_year': row['founded_year'],
                'leader_name': row['leader_name'],
                'history': row['history'],
            }
        )

    # 4. Senator
    print("Transferring Senators...")
    sqlite_cursor.execute("SELECT * FROM scorecard_senator")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        Senator.objects.update_or_create(
            id=row['id'],
            defaults={
                'senator_id': row['senator_id'],
                'name': row['name'],
                'county_fk_id': row['county_fk_id'],
                'nomination': row['nomination'],
                'party': row['party'],
                'image_url': row['image_url'],
                'image': row['image'],
                'available_engines': json.loads(row['available_engines']) if isinstance(row['available_engines'], str) else row['available_engines'],
                'is_deceased': row['is_deceased'],
                'is_still_computing': row['is_still_computing'],
            }
        )

    # 5. ParliamentaryPerformance
    print("Transferring ParliamentaryPerformance...")
    sqlite_cursor.execute("SELECT * FROM scorecard_parliamentaryperformance")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        ParliamentaryPerformance.objects.update_or_create(
            id=row['id'],
            defaults={
                'senator_id': row['senator_id'],
                'speeches': row['speeches'],
                'attendance_rate': row['attendance_rate'],
                'sponsored_bills': row['sponsored_bills'],
                'passed_bills': row['passed_bills'],
                'amendments': row['amendments'],
                'committee_role': row['committee_role'],
                'committee_attendance': row['committee_attendance'],
                'total_votes': row['total_votes'],
                'attended_votes': row['attended_votes'],
                'oversight_actions': row['oversight_actions'],
                'county_representation_score': row['county_representation_score'],
                'statements_2025': row['statements_2025'],
                'statements_total': row['statements_total'],
                'overall_score': row['overall_score'],
                'grade': row['grade'],
                'structural_score': row['structural_score'],
                'debate_score': row['debate_score'],
                'words_spoken': row['words_spoken'],
                'motions_sponsored': row['motions_sponsored'],
                'sessions_attended': row['sessions_attended'],
                'trend_data': json.loads(row['trend_data']) if isinstance(row['trend_data'], str) else row['trend_data'],
            }
        )

    # 6. SenatorQuote
    print("Transferring Quotes...")
    sqlite_cursor.execute("SELECT * FROM scorecard_senatorquote")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        SenatorQuote.objects.update_or_create(
            id=row['id'],
            defaults={
                'senator_id': row['senator_id'],
                'quote': row['quote'],
                'date': row['date'],
                'order': row['order'],
            }
        )

    # 7. VotingRecord
    print("Transferring Voting Records...")
    sqlite_cursor.execute("SELECT * FROM scorecard_votingrecord")
    rows = sqlite_cursor.fetchall()
    for row in rows:
        VotingRecord.objects.update_or_create(
            id=row['id'],
            defaults={
                'senator_id': row['senator_id'],
                'date': row['date'],
                'title': row['title'],
                'decision': row['decision'],
                'source': row['source'],
            }
        )

    print("Transfer complete!")
    sqlite_conn.close()

if __name__ == "__main__":
    transfer()

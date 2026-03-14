import os
import django
import json
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import Senator, ParliamentaryPerformance

def run_import(json_file_path):
    if not os.path.exists(json_file_path):
        print(f"File not found: {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated_count = 0
    not_found_count = 0

    for item in data:
        name = item['name']
        senator = Senator.objects.filter(name__icontains=name).first()
        
        if not senator:
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1]
                senator = Senator.objects.filter(name__icontains=last_name).first()

        if senator:
            perf, created = ParliamentaryPerformance.objects.get_or_create(senator=senator)
            
            perf.overall_score = item['score']
            perf.grade = item['grade']
            perf.structural_score = item['structural_score']
            perf.debate_score = item['debate_score']
            
            perf.words_spoken = item['words']
            perf.speeches = item['speeches']
            perf.motions_sponsored = item['statements']
            perf.sessions_attended = item['sessions']
            perf.attended_votes = item['votes_attended']
            perf.total_votes = item['votes_total']
            perf.sponsored_bills = item['bills']
            
            perf.save()
            updated_count += 1
            print(f"Updated {senator.name}")
        else:
            print(f"Senator not found: {name}")
            not_found_count += 1

    print(f"Successfully updated {updated_count} senators. {not_found_count} not found.")

if __name__ == "__main__":
    run_import('senator_performance_data.json')

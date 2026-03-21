import json
import os
from django.core.management.base import BaseCommand
from scorecard.models import Senator, ParliamentaryPerformance

class Command(BaseCommand):
    help = 'Import recalculated senator performance data from JSON'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the senator_performance_data.json file')

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        if not os.path.exists(json_file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {json_file_path}"))
            return

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        updated_count = 0
        not_found_count = 0

        for item in data:
            name = item['name']
            # Attempt to find the senator by name (fuzzy match if needed, but names in export are Mzalendo names)
            senator = Senator.objects.filter(name__icontains=name).first()
            
            if not senator:
                # Try a broader search if the exact full name isn't found
                parts = name.split()
                if len(parts) > 1:
                    last_name = parts[-1]
                    senator = Senator.objects.filter(name__icontains=last_name).first()

            if senator:
                perf, created = ParliamentaryPerformance.objects.get_or_create(senator=senator)
                
                # Update scores
                perf.overall_score = item['score']
                perf.grade = item['grade']
                perf.structural_score = item['structural_score']
                perf.debate_score = item['debate_score']
                
                # Update granular metrics
                perf.words_spoken = item['words']
                perf.speeches = item['speeches']
                perf.motions_sponsored = item['statements']
                perf.sessions_attended = item['sessions']
                perf.attended_votes = item['votes_attended']
                perf.total_votes = item['votes_total']
                perf.sponsored_bills = item['bills']
                
                perf.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated {senator.name}"))
            else:
                self.stderr.write(self.style.WARNING(f"Senator not found: {name}"))
                not_found_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} senators. {not_found_count} not found."))

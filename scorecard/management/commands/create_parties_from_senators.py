"""Create Party records for each distinct party name used by senators. Run once, then upload logos in admin."""
from django.core.management.base import BaseCommand

from scorecard.models import Senator, Party


class Command(BaseCommand):
    help = "Create Party records for each distinct party name from senators. Upload logos in admin afterward."

    def handle(self, *args, **options):
        parties = set()
        for s in Senator.objects.values_list("party", flat=True).distinct():
            name = (s or "").strip()
            if name:
                parties.add(name)

        created = 0
        for name in sorted(parties):
            _, was_created = Party.objects.get_or_create(name=name)
            if was_created:
                created += 1
                self.stdout.write(f"Created: {name}")

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} new parties. Upload logos in admin: /admin/scorecard/party/"))

from django.core.management.base import BaseCommand, CommandError

from scorecard.models import County, Senator


class Command(BaseCommand):
    help = "Update a senator's basic fields (party, county_fk, image, etc.)."

    def add_arguments(self, parser):
        parser.add_argument("senator_id", help="Senator ID (value of Senator.senator_id)")
        parser.add_argument("--name")
        parser.add_argument("--party")
        parser.add_argument("--county-slug", help="Slug of County to link as county_fk")
        parser.add_argument(
            "--is-deceased",
            action="store_true",
            help="Mark the senator as deceased",
        )
        parser.add_argument(
            "--is-still-computing",
            action="store_true",
            help="Mark the senator as still computing (no full score yet)",
        )
        parser.add_argument("--image-url", help="External image URL to store on the record")
        parser.add_argument("--nomination", help="Nomination description for nominated senators")

    def handle(self, *args, **options):
        senator_id = options["senator_id"]
        try:
            senator = Senator.objects.get(senator_id=senator_id)
        except Senator.DoesNotExist:
            raise CommandError(f"Senator {senator_id!r} does not exist")

        if options.get("name") is not None:
            senator.name = options["name"]
        if options.get("party") is not None:
            senator.party = options["party"]
        if options.get("image_url") is not None:
            senator.image_url = options["image_url"]
        if options.get("is_deceased"):
            senator.is_deceased = True
        if options.get("is_still_computing"):
            senator.is_still_computing = True
        if options.get("nomination") is not None:
            senator.nomination = options["nomination"]

        county_slug = options.get("county_slug")
        if county_slug:
            try:
                county = County.objects.get(slug=county_slug)
            except County.DoesNotExist:
                raise CommandError(f"County with slug {county_slug!r} does not exist")
            senator.county_fk = county

        senator.save()
        self.stdout.write(self.style.SUCCESS(f"Updated senator {senator_id}"))


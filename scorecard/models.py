"""
Scorecard models: County, Party, Senator, performance, and related data.

Asset optimization (images):
  ImageFields (County.logo, governor_image, women_rep_image; Party.logo; Senator.image;
  CountyImage.image) use default local media storage. For higher traffic or global users:
  - Switch to remote storage: set DEFAULT_FILE_STORAGE (e.g. django-storages S3 or
    Cloudinary) in settings; no model changes required.
  - Add thumbnails: use django-imagekit ImageSpecField on the same ImageField, then
    use the spec URL in templates for cards/lists; keep full image for detail pages.
  See docs/ASSETS.md for options and examples.
"""
import logging
import os

from django.db import models

logger = logging.getLogger(__name__)


def _get_cloudinary_cloud_name(settings):
    """Return the configured Cloudinary cloud name, or None if not set."""
    name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME') or ''
    if not name:
        logger.warning(
            "CLOUDINARY_CLOUD_NAME is not configured. "
            "Set it via CLOUDINARY_CLOUD_NAME env var for production media URLs."
        )
    return name or None


class County(models.Model):
    """Kenya's 47 counties for the Counties browse page."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    region = models.CharField(max_length=50, help_text="Region/frontier: coast, eastern, central, rift_valley, nyanza, western, north_eastern")
    description = models.TextField(blank=True, help_text="County profile description (optional)")
    logo = models.ImageField(upload_to='counties/', blank=True, null=True, help_text="County logo/crest for the card")
    governor_name = models.CharField(max_length=150, blank=True, help_text="County governor's name")
    governor_party = models.CharField(max_length=100, blank=True, help_text="Governor's political party")
    governor_image = models.ImageField(upload_to='counties/governors/', blank=True, null=True, help_text="Governor's photo")
    women_rep_name = models.CharField(max_length=150, blank=True, help_text="County women representative's name")
    women_rep_party = models.CharField(max_length=100, blank=True, help_text="Women representative's political party")
    women_rep_image = models.ImageField(upload_to='counties/women_rep/', blank=True, null=True, help_text="Women representative's photo")
    official_profile_url = models.URLField(blank=True, help_text="Link to official county government profile (e.g. county website)")
    development_dashboard_url = models.URLField(blank=True, help_text="Link to county development/project dashboard (e.g. PTMMS)")
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order (lower = first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Counties'

    def __str__(self):
        return self.name

    @property
    def display_governor_image_url(self):
        """Standardized URL resolution for governor photos."""
        from django.conf import settings
        url = self.governor_image.url if self.governor_image else ""
        if "res.cloudinary.com" in url:
            return url
        if url.startswith('/media/'):
            is_cloud = os.environ.get('K_SERVICE') is not None
            if not settings.DEBUG or is_cloud:
                cloud_name = _get_cloudinary_cloud_name(settings)
                if cloud_name:
                    relative_path = url.replace('/media/', '')
                    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{relative_path}"
        return url

    @property
    def display_women_rep_image_url(self):
        """Standardized URL resolution for women rep photos."""
        from django.conf import settings
        url = self.women_rep_image.url if self.women_rep_image else ""
        if "res.cloudinary.com" in url:
            return url
        if url.startswith('/media/'):
            is_cloud = os.environ.get('K_SERVICE') is not None
            if not settings.DEBUG or is_cloud:
                cloud_name = _get_cloudinary_cloud_name(settings)
                if cloud_name:
                    relative_path = url.replace('/media/', '')
                    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{relative_path}"
        return url


class CountyImage(models.Model):
    """Images for county profile pages (admin can add multiple per county)."""
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='counties/gallery/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order (lower = first)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.county.name} image"


class Party(models.Model):
    """Political party for senator cards. Upload logos via admin."""
    name = models.CharField(max_length=100, unique=True, help_text="Exact name as used on senators (e.g. United Democratic Alliance)")
    logo = models.ImageField(upload_to='parties/', blank=True, null=True, help_text="Party logo for senator cards")
    founded_year = models.PositiveIntegerField(blank=True, null=True, help_text="Year the party was founded (e.g. 2000)")
    leader_name = models.CharField(max_length=150, blank=True, help_text="Current national party leader")
    history = models.TextField(blank=True, help_text="Short history/description to show in party info card")

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Parties'

    def __str__(self):
        return self.name

    @property
    def display_logo_url(self):
        """Standardized URL resolution for party logos. Fallback to static for repo-managed assets."""
        from django.conf import settings
        from django.templatetags.static import static
        url = self.logo.url if self.logo else ""
        if not url:
            return ""
        if "res.cloudinary.com" in url:
            return url
        if url.startswith('/media/'):
            is_cloud = os.environ.get('K_SERVICE') is not None
            if not settings.DEBUG or is_cloud:
                relative_path = url.replace('/media/parties/', '')
                if relative_path in ['upa_logo.png', 'kanu_logo.png', 'anc_logo.png']:
                    return static(f'scorecard/images/parties/{relative_path}')
                cloud_name = _get_cloudinary_cloud_name(settings)
                if cloud_name:
                    return f"https://res.cloudinary.com/{cloud_name}/image/upload/parties/{relative_path}"
        return url


class Senator(models.Model):
    senator_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    county_fk = models.ForeignKey(
        County,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        related_name="senators",
        help_text="Linked county record, where applicable",
    )
    nomination = models.CharField(max_length=150, blank=True, help_text="For nominated senators, e.g. 'Women Affairs Interest'")
    party = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, null=True, help_text="External image URL (used if no photo uploaded)")
    image = models.ImageField(upload_to='senators/', blank=True, null=True, help_text="Upload a photo directly")
    available_engines = models.JSONField(default=list) # e.g., ["parliamentary"]
    is_deceased = models.BooleanField(default=False, help_text="Mark if senator has passed on")
    is_still_computing = models.BooleanField(
        default=False,
        help_text="Mark if this senator is newly added and performance data is still being computed.",
    )
    is_no_longer_serving = models.BooleanField(
        default=False,
        help_text="Mark if this senator is no longer serving in the Senate (e.g. expelled, resigned).",
    )

    @property
    def display_image_url(self):
        """Preferred image URL for cards/lists. Resolves local media to Cloudinary in production."""
        from django.conf import settings
        url = ""
        if self.image:
            url = self.image.url
        else:
            url = self.image_url or ""
            
        if "res.cloudinary.com" in url:
            return url

        if url.startswith('/media/'):
            is_cloud = os.environ.get('K_SERVICE') is not None
            if not settings.DEBUG or is_cloud:
                cloud_name = _get_cloudinary_cloud_name(settings)
                if cloud_name:
                    relative_path = url.replace('/media/', '')
                    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{relative_path}"
            
        return url

    def __str__(self):
        return self.name

class SenatorQuote(models.Model):
    senator = models.ForeignKey(Senator, on_delete=models.CASCADE, related_name="quotes")
    quote = models.TextField(help_text="The quote text (without surrounding quotes)")
    date = models.DateField(help_text="Date the quote was said or published")
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order (lower = first)")

    class Meta:
        ordering = ["order", "-date"]

    def __str__(self):
        return (self.quote[:50] + "…") if len(self.quote) > 50 else self.quote


class VotingRecord(models.Model):
    """Formal voting record for a senator on a specific question or bill."""

    senator = models.ForeignKey(Senator, on_delete=models.CASCADE, related_name="voting_records")
    date = models.DateField(help_text="Date of the vote as recorded in the Hansard/division list")
    title = models.CharField(max_length=255, help_text="Short description of the motion, bill, or question")
    decision = models.CharField(
        max_length=20,
        help_text="Recorded position, e.g. Yes, No, Abstain, Absent",
    )
    source = models.URLField(
        blank=True,
        help_text="Optional link to the official record (Hansard, Mzalendo, Parliament portal)",
    )

    class Meta:
        ordering = ["-date", "senator__name"]

    def __str__(self):
        return f"{self.senator.name}: {self.title} ({self.decision})"


class ParliamentaryPerformance(models.Model):
    senator = models.OneToOneField(Senator, on_delete=models.CASCADE, related_name="perf")
    speeches = models.IntegerField(default=0)
    attendance_rate = models.FloatField(default=0.0)
    sponsored_bills = models.IntegerField(default=0)
    passed_bills = models.IntegerField(default=0)
    amendments = models.IntegerField(default=0)
    committee_role = models.CharField(max_length=100, default="Member")
    committee_attendance = models.FloatField(default=0.0)
    total_votes = models.IntegerField(default=20)
    attended_votes = models.IntegerField(default=0)
    oversight_actions = models.IntegerField(default=0)
    county_representation_score = models.FloatField(default=0.0) # Out of 10
    # Formal statements from official Statements Tracker (e.g. up to Nov 2025)
    statements_2025 = models.IntegerField(default=0)
    statements_total = models.IntegerField(default=0)
    
    # Recalculated Scores from Hansard Engine
    overall_score = models.FloatField(default=0.0)
    grade = models.CharField(max_length=5, blank=True, null=True)
    structural_score = models.FloatField(default=0.0)
    debate_score = models.FloatField(default=0.0)
    
    # Granular Metrics
    words_spoken = models.IntegerField(default=0)
    motions_sponsored = models.IntegerField(default=0)
    sessions_attended = models.IntegerField(default=0)
    
    trend_data = models.JSONField(default=list)

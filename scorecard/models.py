from django.db import models

class Senator(models.Model):
    senator_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    nomination = models.CharField(max_length=150, blank=True, help_text="For nominated senators, e.g. 'Women Affairs Interest'")
    party = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, null=True, help_text="External image URL (used if no photo uploaded)")
    image = models.ImageField(upload_to='senators/', blank=True, null=True, help_text="Upload a photo directly")
    available_engines = models.JSONField(default=list) # e.g., ["parliamentary"]

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
    trend_data = models.JSONField(default=list)

#!/usr/bin/env python
"""Remove SenatorQuote containing the Narcotic Drugs bill text."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from scorecard.models import SenatorQuote

# Match the narcotic/psychotropic bill quote
keywords = ["NARCOTIC DRUGS", "PSYCHOTROPIC SUBSTANCES", "SENATE BILLS NO. 1 OF 2024"]
deleted = 0
for q in SenatorQuote.objects.all():
    if any(kw in q.quote for kw in keywords):
        print(f"Removing quote (id={q.id}, senator={q.senator.name}): {q.quote[:80]}...")
        q.delete()
        deleted += 1

print(f"Deleted {deleted} quote(s).")

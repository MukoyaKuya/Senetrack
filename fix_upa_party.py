import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from scorecard.models import Party

# Part 1: Add United Progressive Alliance (UPA)
# We already copied upa_logo.png to media/parties/
upa_party, created = Party.objects.get_or_create(
    name='United Progressive Alliance',
    defaults={'logo': 'parties/upa_logo.png', 'history': 'The United Progressive Alliance (UPA) is a Kenyan political party known for its soap symbol and "Safisha Kenya" slogan.'}
)

if not created:
    if not upa_party.logo:
        upa_party.logo = 'parties/upa_logo.png'
        upa_party.save()
        print("Updated logo for United Progressive Alliance")
    else:
        print(f"United Progressive Alliance already has logo: {upa_party.logo}")
else:
    print("Created United Progressive Alliance with logo")

# Part 2: Add other common missing parties (placeholders or variants)
# KANU
kanu, created = Party.objects.get_or_create(
    name='Kenya Africa National Union',
    defaults={'logo': 'parties/lumina-enhanced-1773062860431_1.png'} # Using a placeholder for now
)
if created: print("Created KANU")

# ANC
anc, created = Party.objects.get_or_create(
    name='Amani National Congress',
    defaults={'logo': 'parties/lumina-enhanced-1773062337550.png'} # Using a placeholder for now
)
if created: print("Created ANC")

# Part 3: Map common variants for existing parties if they appear in senators but aren't in Party table
# (The view logic handles partial matches, so adding the primary records is usually enough)

print("Party update script completed.")

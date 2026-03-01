import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from django.template.loader import render_to_string
try:
    print("ATTEMPTING TO RENDER")
    html = render_to_string('scorecard/scorecard.html', {'senator': None, 'results': {}})
    if "{{ results.overall_score" in html:
        print("LITERAL TAG FOUND IN RENDERED HTML!")
    else:
        print("RENDER SUCCESSFUL. NO LITERAL TAGS.")
except Exception as e:
    print("RENDER FAILED:", repr(e))

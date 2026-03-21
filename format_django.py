import re
import os

filepath = 'scorecard/templates/scorecard/scorecard.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace newlines within {% ... %}
content = re.sub(
    r'\{%.*?%\}',
    lambda m: m.group(0).replace('\n', ' ').replace('  ', ' '),
    content,
    flags=re.DOTALL
)

# Replace newlines within {{ ... }}
content = re.sub(
    r'\{\{.*?\}\}',
    lambda m: m.group(0).replace('\n', ' ').replace('  ', ' '),
    content,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Template formatted successfully.")

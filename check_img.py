import urllib.request
import re

url = "https://senetrack-1073897174388.us-east1.run.app/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html)
        for img in imgs:
            print("FOUND IMAGE:", img)
except Exception as e:
    print("Error:", e)

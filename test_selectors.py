import os
import requests
from bs4 import BeautifulSoup

ZYTE_API_KEY = "9607a9b635ee4007807f34f83dbe30c9"
url = "https://www.daft.ie/property-for-rent/dublin-city?rentalPrice_from=1000&rentalPrice_to=1700&propertyType=share"

# Fetch with Zyte
zyte_url = "https://api.zyte.com/v1/extract"
payload = {"url": url, "browserHtml": True}
response = requests.post(zyte_url, json=payload, auth=(ZYTE_API_KEY, ''), timeout=60)
html = response.json().get('browserHtml', '')

# Parse
soup = BeautifulSoup(html, 'html.parser')

# Save a snippet for analysis
with open('page_sample.html', 'w', encoding='utf-8') as f:
    f.write(html[:50000])  # First 50k chars

print(f"Total HTML length: {len(html)}")
print(f"Saved first 50k characters to page_sample.html")

# Try to find listings with different selectors
print("\nTrying different selectors:")
selector1 = '[data-testid="result"]'
selector2 = '[data-testid="results"]'
selector3 = 'div[class*="SearchPage"]'
selector4 = 'ul > li'
selector5 = 'a[href*="for-rent"]'

print(f"  {selector1}: {len(soup.select(selector1))}")
print(f"  {selector2}: {len(soup.select(selector2))}")
print(f"  {selector3}: {len(soup.select(selector3))}")
print(f"  {selector4}: {len(soup.select(selector4))}")
print(f"  {selector5}: {len(soup.select(selector5))}")

# Look for specific patterns
if 'data-testid' in html:
    print("\n'data-testid' found in HTML")
    import re
    testids = re.findall(r'data-testid="([^"]+)"', html)
    unique_testids = list(set(testids))[:20]
    print(f"Sample data-testid values: {unique_testids}")

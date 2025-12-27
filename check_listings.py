import os
import requests
from bs4 import BeautifulSoup

ZYTE_API_KEY = "9607a9b635ee4007807f34f83dbe30c9"

# Try a broader search - all Dublin properties for rent (not just shares)
url = "https://www.daft.ie/property-for-rent/dublin?rentalPrice_from=1000&rentalPrice_to=1700"

print(f"Testing with broader search: {url}\n")

# Fetch with Zyte
zyte_url = "https://api.zyte.com/v1/extract"
payload = {"url": url, "browserHtml": True}
response = requests.post(zyte_url, json=payload, auth=(ZYTE_API_KEY, ''), timeout=60)
html = response.json().get('browserHtml', '')

# Parse
soup = BeautifulSoup(html, 'html.parser')

print(f"Page title: {soup.find('title').text if soup.find('title') else 'N/A'}")
print(f"HTML length: {len(html)} characters\n")

# Check meta description
meta_desc = soup.find('meta', {'name': 'description'})
if meta_desc:
    print(f"Meta description: {meta_desc.get('content', '')}\n")

# Try different selectors
selectors = [
    '[data-testid="result"]',
    'ul[data-testid="results"] > li',
    'ul[data-testid="results"] li',
    'a[data-testid="listing-link"]',
    'div[data-testid="listing"]',
]

print("Testing selectors:")
for selector in selectors:
    results = soup.select(selector)
    print(f"  {selector}: {len(results)} results")

# Look for the results container
results_container = soup.select_one('[data-testid="results"]')
if results_container:
    print(f"\nFound results container!")
    print(f"  Children: {len(list(results_container.children))}")
    # Get first few children
    for i, child in enumerate(list(results_container.children)[:3]):
        if child.name:
            print(f"  Child {i}: {child.name} - classes: {child.get('class', [])}")

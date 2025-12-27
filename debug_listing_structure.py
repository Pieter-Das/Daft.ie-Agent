import requests
from bs4 import BeautifulSoup

ZYTE_API_KEY = "9607a9b635ee4007807f34f83dbe30c9"
url = "https://www.daft.ie/property-for-rent/dublin-city?rentalPrice_from=1000&rentalPrice_to=1700"

# Fetch with Zyte
zyte_url = "https://api.zyte.com/v1/extract"
payload = {"url": url, "browserHtml": True}
response = requests.post(zyte_url, json=payload, auth=(ZYTE_API_KEY, ''), timeout=60)
html = response.json().get('browserHtml', '')

# Parse
soup = BeautifulSoup(html, 'html.parser')
listing_cards = soup.select("ul[data-testid='results'] > li")

if listing_cards:
    first_card = listing_cards[0]
    print("First listing card structure:")
    print("=" * 60)
    
    # Find all testid elements
    testids = first_card.find_all(attrs={'data-testid': True})
    print("\nElements with data-testid:")
    for elem in testids[:10]:
        testid = elem.get('data-testid')
        text = elem.get_text(strip=True)[:50]
        print(f"  [{testid}]: {text}")
    
    # Find headings
    print("\nHeadings:")
    for tag in ['h1', 'h2', 'h3', 'h4']:
        headings = first_card.find_all(tag)
        if headings:
            for h in headings:
                print(f"  <{tag}>: {h.get_text(strip=True)}")
    
    # Find link
    link = first_card.select_one("a")
    if link:
        print(f"\nLink href: {link.get('href', '')}")

"""
Daft.ie Room Hunter Bot
Scans Daft.ie for available rooms in Dublin and sends email notifications.
"""

import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict, Optional
import logging
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PRICE_MIN = 1000
PRICE_MAX = 1700
SEEN_LISTINGS_FILE = "seen_listings.txt"
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587

# Daft.ie search URL for sharing in Dublin
DAFT_SEARCH_URL = "https://www.daft.ie/property-for-rent/dublin-city?rentalPrice_from={min_price}&rentalPrice_to={max_price}&propertyType=share"


def load_seen_listings() -> Set[str]:
    """Load the set of previously seen listing IDs from file."""
    seen_file = Path(SEEN_LISTINGS_FILE)
    if not seen_file.exists():
        logger.info(f"No {SEEN_LISTINGS_FILE} found. Creating new file.")
        seen_file.touch()
        return set()

    with open(seen_file, 'r') as f:
        seen_ids = {line.strip() for line in f if line.strip()}

    logger.info(f"Loaded {len(seen_ids)} previously seen listings.")
    return seen_ids


def save_listing_id(listing_id: str) -> None:
    """Append a new listing ID to the seen listings file."""
    with open(SEEN_LISTINGS_FILE, 'a') as f:
        f.write(f"{listing_id}\n")
    logger.info(f"Saved listing ID: {listing_id}")


def send_email_notification(listing: Dict) -> bool:
    """
    Send an email notification for a new listing.

    Args:
        listing: Dictionary containing listing details

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.error("Email credentials not found in environment variables!")
        return False

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS
        msg['Subject'] = f"🏠 New Room: €{listing['price']} - {listing['address']}"

        # HTML email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2c3e50;">New Room Available in Dublin!</h2>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 10px 0;"><strong>Price:</strong> <span style="color: #27ae60; font-size: 18px;">€{listing['price']}/month</span></p>
                    <p style="margin: 10px 0;"><strong>Address:</strong> {listing['address']}</p>
                    {f"<p style='margin: 10px 0;'><strong>Title:</strong> {listing.get('title', '')}</p>" if listing.get('title') else ""}
                    {f"<p style='margin: 10px 0;'><strong>Bedrooms:</strong> {listing.get('bedrooms', 'N/A')}</p>" if listing.get('bedrooms') else ""}
                </div>

                <div style="margin: 30px 0;">
                    <a href="{listing['link']}"
                       style="background-color: #3498db; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        View Full Listing on Daft.ie
                    </a>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #7f8c8d;">
                    This is an automated notification from your Room Hunter bot.<br>
                    Listing ID: {listing['id']}<br>
                    Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully for listing {listing['id']}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


def extract_listing_id(url: str) -> Optional[str]:
    """Extract listing ID from Daft.ie URL."""
    # Daft URLs typically look like: https://www.daft.ie/for-rent/...-12345
    match = re.search(r'-(\d+)/?$', url)
    if match:
        return match.group(1)
    return url  # Fallback to full URL if we can't extract ID


def parse_price(price_text: str) -> Optional[int]:
    """Extract numeric price from price text."""
    if not price_text:
        return None

    # Remove everything except digits
    numbers = re.findall(r'\d+', price_text.replace(',', ''))
    if numbers:
        return int(numbers[0])
    return None


def search_daft_listings() -> List[Dict]:
    """
    Search Daft.ie for rooms matching our criteria using web scraping.

    Returns:
        List of listing dictionaries
    """
    logger.info("Starting Daft.ie search...")

    try:
        # Build search URL
        url = DAFT_SEARCH_URL.format(min_price=PRICE_MIN, max_price=PRICE_MAX)

        # Create a session with realistic browser headers
        session = requests.Session()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-IE,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.daft.ie/'
        }

        logger.info(f"Fetching: {url}")
        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all listing cards
        # Daft uses different class names, let's try multiple selectors
        listing_cards = soup.find_all('div', {'data-testid': 'result'})

        if not listing_cards:
            # Try alternative selectors
            listing_cards = soup.find_all('a', href=re.compile(r'/for-rent/'))
            logger.info(f"Found {len(listing_cards)} listing links (alternative selector)")

        logger.info(f"Found {len(listing_cards)} total listings on page")

        results = []
        for card in listing_cards:
            try:
                # Extract link
                link_elem = card if card.name == 'a' else card.find('a', href=re.compile(r'/for-rent/'))
                if not link_elem:
                    continue

                link = link_elem.get('href', '')
                if not link.startswith('http'):
                    link = f"https://www.daft.ie{link}"

                # Extract listing ID
                listing_id = extract_listing_id(link)

                # Extract price
                price_elem = card.find('span', {'data-testid': 'price'})
                if not price_elem:
                    price_elem = card.find(string=re.compile(r'€\s*\d'))

                price_text = price_elem.get_text(strip=True) if price_elem else 'N/A'
                price_numeric = parse_price(price_text)

                # Filter by price range
                if price_numeric and (price_numeric < PRICE_MIN or price_numeric > PRICE_MAX):
                    continue

                # Extract title/address
                title_elem = card.find('h2') or card.find('h3') or card.find('p')
                title = title_elem.get_text(strip=True) if title_elem else 'No title'

                # Extract address (usually in a different element)
                address_elem = card.find('p', {'data-testid': 'address'})
                if not address_elem:
                    address_elem = card.find('p', string=re.compile(r'Dublin'))

                address = address_elem.get_text(strip=True) if address_elem else title

                # Extract bedrooms if available
                beds_elem = card.find(string=re.compile(r'bed', re.IGNORECASE))
                bedrooms = beds_elem.strip() if beds_elem else None

                listing_data = {
                    'id': listing_id,
                    'price': price_text,
                    'price_numeric': price_numeric,
                    'address': address,
                    'title': title,
                    'link': link,
                    'bedrooms': bedrooms
                }

                results.append(listing_data)
                logger.debug(f"Parsed listing: {address} - {price_text}")

            except Exception as e:
                logger.warning(f"Error processing listing card: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(results)} listings")
        return results

    except requests.RequestException as e:
        logger.error(f"Error fetching Daft.ie: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error searching Daft.ie: {str(e)}")
        return []


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Room Hunter Bot Started")
    logger.info(f"Search criteria: €{PRICE_MIN}-€{PRICE_MAX}, Dublin City (D6, D7, D8)")
    logger.info("=" * 60)

    # Load previously seen listings
    seen_listings = load_seen_listings()

    # Search for new listings
    listings = search_daft_listings()

    if not listings:
        logger.info("No listings found matching criteria.")
        return

    # Process new listings
    new_listings_count = 0
    email_sent_count = 0

    for listing in listings:
        listing_id = listing['id']

        if listing_id in seen_listings:
            logger.debug(f"Skipping already seen listing: {listing_id}")
            continue

        new_listings_count += 1
        logger.info(f"New listing found: {listing['address']} - €{listing['price']}")

        # Send email notification
        if send_email_notification(listing):
            # Only mark as seen if email was sent successfully
            save_listing_id(listing_id)
            seen_listings.add(listing_id)
            email_sent_count += 1
        else:
            logger.warning(f"Email failed for listing {listing_id}, will retry next run")

    # Summary
    logger.info("=" * 60)
    logger.info(f"Scan complete: {len(listings)} total, {new_listings_count} new, {email_sent_count} notified")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

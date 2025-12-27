"""
Daft.ie Room Hunter Bot
Scans Daft.ie for available rooms in Dublin and sends email notifications.
Uses Zyte API to bypass Cloudflare protection.
"""

import os
import smtplib
import re
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict
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
ZYTE_API_KEY = os.environ.get("ZYTE_API_KEY")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Daft.ie search URL (removed propertyType=share as there are currently no share listings)
DAFT_SEARCH_URL = "https://www.daft.ie/property-for-rent/dublin-city?rentalPrice_from={min_price}&rentalPrice_to={max_price}"


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


def fetch_page_with_zyte(url: str) -> str:
    """
    Fetch webpage content using Zyte API.

    Args:
        url: The URL to fetch

    Returns:
        str: HTML content of the page
    """
    if not ZYTE_API_KEY:
        logger.error("ZYTE_API_KEY not found in environment variables!")
        raise ValueError("ZYTE_API_KEY is required")

    zyte_url = "https://api.zyte.com/v1/extract"

    payload = {
        "url": url,
        "browserHtml": True
    }

    try:
        logger.info(f"Fetching page with Zyte API: {url}")
        response = requests.post(
            zyte_url,
            json=payload,
            auth=(ZYTE_API_KEY, ''),
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        html_content = result.get('browserHtml', '')

        if not html_content:
            logger.warning("No browserHtml in response, trying httpResponseBody")
            html_content = result.get('httpResponseBody', '')

        logger.info(f"Successfully fetched page ({len(html_content)} characters)")
        return html_content

    except requests.exceptions.RequestException as e:
        logger.error(f"Zyte API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        raise


def extract_listing_id(url: str) -> str:
    """Extract listing ID from Daft.ie URL."""
    match = re.search(r'-(\d+)/?$', url)
    if match:
        return match.group(1)
    return url.split('/')[-1]


def parse_price(price_text: str) -> str:
    """Clean up price text."""
    if not price_text:
        return 'N/A'
    # Remove whitespace and extra characters
    return price_text.strip().replace('\n', ' ')


def search_daft_listings() -> List[Dict]:
    """
    Search Daft.ie for rooms matching our criteria using Zyte API.

    Returns:
        List of listing dictionaries
    """
    logger.info("Starting Daft.ie search with Zyte API...")

    try:
        # Build search URL
        url = DAFT_SEARCH_URL.format(min_price=PRICE_MIN, max_price=PRICE_MAX)
        logger.info(f"Searching: {url}")

        # Fetch page content with Zyte API
        html_content = fetch_page_with_zyte(url)

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check page title for debugging
        page_title = soup.find('title')
        logger.info(f"Page title: {page_title.text if page_title else 'N/A'}")

        # Check if we see "no results" message
        if "no results" in html_content.lower() or "0 results" in html_content.lower():
            logger.info("Page explicitly states no results found")

        # Find all listing cards using the correct selector
        listing_cards = soup.select("ul[data-testid='results'] > li")
        logger.info(f"Found {len(listing_cards)} listing cards")

        results = []
        for card in listing_cards:
            try:
                # Extract link - look for main listing link
                link_elem = card.select_one("a")
                if not link_elem:
                    continue

                link = link_elem.get('href', '')
                if not link:
                    continue

                # Make absolute URL if needed
                if link.startswith('/'):
                    link = f"https://www.daft.ie{link}"

                # Skip non-listing links (ads, etc.)
                if '/for-rent/' not in link and '/sharing/' not in link:
                    continue

                # Extract listing ID
                listing_id = extract_listing_id(link)

                # Extract price - look in subunit-card-container or find € sign
                price_elem = card.select_one("[data-testid='subunit-card-container']")
                if price_elem:
                    # Find first occurrence of € price
                    price_match = price_elem.find(string=re.compile(r'€[\d,]+'))
                    price_text = price_match.strip() if price_match else 'N/A'
                else:
                    # Fallback: try data-testid='price'
                    price_elem = card.select_one("[data-testid='price']")
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                    else:
                        # Last resort: find any € sign
                        price_match = card.find(string=re.compile(r'€[\d,]+'))
                        price_text = price_match.strip() if price_match else 'N/A'

                price = parse_price(price_text)

                # Extract title and address from card-container
                card_container = card.select_one("[data-testid='card-container']")
                if card_container:
                    # The card-container text contains: "TH EnquiriesCoolevally, Shankill, Dublin 18 , Shan..."
                    # We need to extract the address part
                    container_text = card_container.get_text(strip=True)
                    # Remove "TH Enquiries" prefix if present
                    container_text = container_text.replace('TH Enquiries', '').strip()
                    title = container_text if container_text else "No title"
                    address = title
                else:
                    # Fallback to headings
                    title_elem = card.find('h2') or card.find('h3') or card.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else "No title"
                    address = title

                listing_data = {
                    'id': listing_id,
                    'price': price,
                    'address': address,
                    'title': title,
                    'link': link
                }

                results.append(listing_data)
                logger.debug(f"Parsed listing: {address} - {price}")

            except Exception as e:
                logger.warning(f"Error processing listing card: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(results)} listings")
        return results

    except Exception as e:
        logger.error(f"Error during Zyte scraping: {str(e)}")
        return []


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Room Hunter Bot Started (Zyte API Mode)")
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
        logger.info(f"New listing found: {listing['address']} - {listing['price']}")

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

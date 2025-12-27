"""
Daft.ie Room Hunter Bot
Scans Daft.ie for available rooms in Dublin and sends email notifications.
Uses Daft.ie's internal API for reliable scraping.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict
import logging
import requests

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

# Daft.ie API endpoint
DAFT_API_URL = "https://gateway.daft.ie/old/v1/listings"


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


def search_daft_listings() -> List[Dict]:
    """
    Search Daft.ie for rooms matching our criteria using their API.

    Returns:
        List of listing dictionaries
    """
    logger.info("Starting Daft.ie search via API...")

    try:
        # Build API request parameters
        params = {
            "section": "sharing",
            "location": "dublin-city",
            "minPrice": PRICE_MIN,
            "maxPrice": PRICE_MAX,
            "pageSize": 50,
            "from": 0,
            "sort": "publishDateDesc"
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'platform': 'web'
        }

        logger.info(f"Fetching from Daft API: {DAFT_API_URL}")
        logger.info(f"Search params: €{PRICE_MIN}-€{PRICE_MAX}, Dublin City, Sharing")

        response = requests.get(DAFT_API_URL, params=params, headers=headers, timeout=30)

        # If API fails, try alternative approach
        if response.status_code != 200:
            logger.warning(f"API returned status {response.status_code}, using fallback method")
            return search_daft_fallback()

        data = response.json()

        if 'listings' not in data:
            logger.warning("No 'listings' key in API response")
            return []

        listings = data['listings']
        logger.info(f"Found {len(listings)} total listings from API")

        results = []
        for listing in listings:
            try:
                listing_id = str(listing.get('id', ''))
                if not listing_id:
                    continue

                price = listing.get('price', 'N/A')
                title = listing.get('title', 'No title')
                address = listing.get('abbreviatedAddress') or listing.get('address', title)

                # Get number of bedrooms
                bedrooms = listing.get('numBedrooms', listing.get('bedrooms'))

                # Build Daft.ie URL
                seo_friendly_path = listing.get('seoFriendlyPath', '')
                link = f"https://www.daft.ie{seo_friendly_path}" if seo_friendly_path else f"https://www.daft.ie/for-rent/{listing_id}"

                listing_data = {
                    'id': listing_id,
                    'price': price,
                    'address': address,
                    'title': title,
                    'link': link,
                    'bedrooms': bedrooms
                }

                results.append(listing_data)
                logger.debug(f"Parsed listing: {address} - €{price}")

            except Exception as e:
                logger.warning(f"Error processing listing: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(results)} listings")
        return results

    except requests.RequestException as e:
        logger.error(f"Error fetching Daft.ie API: {str(e)}")
        return search_daft_fallback()
    except Exception as e:
        logger.error(f"Error searching Daft.ie: {str(e)}")
        return []


def search_daft_fallback() -> List[Dict]:
    """
    Fallback method: Return empty list and log for manual checking.
    In production, you could implement email notification to manually check Daft.ie.
    """
    logger.warning("Fallback: Unable to fetch listings automatically")
    logger.info("Please check Daft.ie manually: https://www.daft.ie/property-for-rent/dublin-city?rentalPrice_from=1000&rentalPrice_to=1700&propertyType=share")
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

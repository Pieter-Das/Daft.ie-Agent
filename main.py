"""
Daft.ie Room Hunter Bot
Scans Daft.ie for available rooms in Dublin and sends email notifications.
Uses Selenium with Chrome to bypass Cloudflare protection.
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

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

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
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Daft.ie search URL
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


def setup_driver():
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-setuid-sandbox')

    # Add page load timeout
    chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources

    # Disable automation flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.managed_default_content_settings.images': 2  # Don't load images for speed
    })

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set page load and script timeouts
        driver.set_page_load_timeout(60)  # 60 seconds max for page load
        driver.set_script_timeout(30)

        # Execute CDP commands to hide webdriver
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {str(e)}")
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
    Search Daft.ie for rooms matching our criteria using Selenium.

    Returns:
        List of listing dictionaries
    """
    logger.info("Starting Daft.ie search with Selenium...")
    driver = None

    try:
        # Set up Chrome driver
        driver = setup_driver()

        # Build search URL
        url = DAFT_SEARCH_URL.format(min_price=PRICE_MIN, max_price=PRICE_MAX)
        logger.info(f"Navigating to: {url}")

        # Navigate to page
        driver.get(url)

        # Wait for Cloudflare check (if any)
        time.sleep(5)

        # Check if we're on Cloudflare page
        if "checking your browser" in driver.page_source.lower() or "cloudflare" in driver.page_source.lower():
            logger.warning("Cloudflare challenge detected, waiting longer...")
            time.sleep(10)

        # Wait for listings to load
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='results']"))
            )
            logger.info("Page loaded successfully")
        except TimeoutException:
            logger.warning("Timeout waiting for listings, trying to parse anyway...")

        # Check page title for debugging
        page_title = driver.title
        logger.info(f"Page title: {page_title}")

        # Save page source for debugging if needed
        page_source = driver.page_source
        logger.info(f"Page source length: {len(page_source)} characters")

        # Check if we see "no results" message
        if "no results" in page_source.lower() or "0 results" in page_source.lower():
            logger.info("Page explicitly states no results found")

        # Find all listing cards
        listing_cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='result']")
        logger.info(f"Found {len(listing_cards)} cards with [data-testid='result']")

        if not listing_cards:
            # Try alternative selectors
            listing_cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/for-rent/']")
            logger.info(f"Alternative selector 1: found {len(listing_cards)} links")

        if not listing_cards:
            # Try even more generic selector
            listing_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-testid*='listing'], div[class*='SearchPage'], li[data-testid='result']")
            logger.info(f"Alternative selector 2: found {len(listing_cards)} elements")

        logger.info(f"Found {len(listing_cards)} total listing cards to process")

        results = []
        for card in listing_cards:
            try:
                # Extract link
                try:
                    link_elem = card if card.tag_name == 'a' else card.find_element(By.CSS_SELECTOR, "a[href*='/for-rent/']")
                    link = link_elem.get_attribute('href')
                except NoSuchElementException:
                    continue

                if not link or 'daft.ie' not in link:
                    continue

                # Extract listing ID
                listing_id = extract_listing_id(link)

                # Extract price
                try:
                    price_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='price']")
                    price_text = price_elem.text
                except NoSuchElementException:
                    try:
                        price_text = card.find_element(By.XPATH, ".//*[contains(text(), '€')]").text
                    except:
                        price_text = 'N/A'

                price = parse_price(price_text)

                # Extract title/address
                try:
                    title_elem = card.find_element(By.TAG_NAME, "h2")
                    title = title_elem.text.strip()
                except NoSuchElementException:
                    try:
                        title_elem = card.find_element(By.TAG_NAME, "h3")
                        title = title_elem.text.strip()
                    except:
                        title = "No title"

                # Extract address
                try:
                    address_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='address']")
                    address = address_elem.text.strip()
                except NoSuchElementException:
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
        logger.error(f"Error during Selenium scraping: {str(e)}")
        return []

    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Room Hunter Bot Started (Selenium Mode)")
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

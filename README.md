# 🏠 Daft.ie Room Hunter Bot

Automated bot that scans Daft.ie for available rooms in Dublin and sends email notifications when matches are found.

## ✅ Current Status: FULLY FUNCTIONAL

**Solution Implemented:** Selenium with Chrome WebDriver

The bot now uses Selenium with a headless Chrome browser to bypass Cloudflare protection. This mimics a real user browsing the website and successfully retrieves listings.

**Technology Stack:**
- ✅ Selenium WebDriver (automated browser)
- ✅ Chrome headless mode
- ✅ Anti-detection measures
- ✅ Outlook email notifications
- ✅ GitHub Actions automation (every 15 minutes)

## 📋 What's Already Working

✅ Email notification system (Outlook SMTP)
✅ State management (tracks seen listings)
✅ GitHub Actions automation (runs every 15 minutes)
✅ Error handling and logging
✅ Clean, maintainable code

## 🚀 Setup Instructions

### 1. Repository Secrets
Already configured:
- `EMAIL_ADDRESS`: Your Outlook email
- `EMAIL_APP_PASSWORD`: App password for authentication

### 2. Current Workflow
The bot runs every 15 minutes via GitHub Actions at:
`.github/workflows/scraper.yml`

### 3. Search Criteria
- **Location:** Dublin City (D6, D7, D8)
- **Type:** Sharing (Rooms)
- **Price:** €1,000 - €1,700/month
- **Availability:** Immediate or from Feb 9th, 2025

## 📝 Files

- `main.py` - Main bot logic
- `requirements.txt` - Python dependencies
- `.github/workflows/scraper.yml` - GitHub Actions automation
- `seen_listings.txt` - Tracks processed listings (auto-updated)

## ⚡ Performance

- **Run time:** ~30-60 seconds per scan (includes browser startup and page load)
- **Frequency:** Every 15 minutes via GitHub Actions
- **Cost:** 100% Free (uses GitHub's free tier)

## 📧 Email Format

When a match is found, you'll receive:
- **Subject:** 🏠 New Room: €1,400 - Dublin 7, Phibsborough
- **Body:** HTML formatted with:
  - Price (highlighted)
  - Address
  - Bedrooms
  - Clickable "View on Daft.ie" button
  - Listing ID for tracking

## 🔍 Monitoring

View bot activity:
- [GitHub Actions](https://github.com/Pieter-Das/Daft.ie-Agent/actions)
- Check `seen_listings.txt` in the repo for processed listings

## 📜 License

Personal project - use as you wish!

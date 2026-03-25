import requests
from bs4 import BeautifulSoup
import json
import os
import hashlib

# --- Configuration ---
URLS = {
    "Bodenseekreis": "https://verbraucherinfo-bw.de/,Lde/Startseite/Lebensmittelkontrolle/Bodenseekreis",
    "Ravensburg": "https://verbraucherinfo-bw.de/,Lde/Startseite/Lebensmittelkontrolle/Ravensburg"
}

# Pull secrets from GitHub Actions environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "crawler_state.json"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")

def fetch_and_hash_content(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Hash the main table to track changes
        table_content = soup.find('table') 
        if table_content:
            text_content = " ".join(table_content.get_text(strip=True).split())
            return hashlib.md5(text_content.encode('utf-8')).hexdigest()
        return "EMPTY_TABLE"
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            previous_state = json.load(f)
    else:
        previous_state = {}

    current_state = {}
    updates_found = []

    for region, url in URLS.items():
        print(f"Checking {region}...")
        content_hash = fetch_and_hash_content(url)
        
        if content_hash:
            current_state[region] = content_hash
            if region not in previous_state or previous_state[region] != content_hash:
                updates_found.append(
                    f"🚨 <b>New Lebensmittelkontrolle Update!</b>\n"
                    f"Region: <b>{region}</b>\n"
                    f"<a href='{url}'>Click here to view the official report</a>"
                )
        else:
            current_state[region] = previous_state.get(region, "") 

    if updates_found:
        message = "\n\n".join(updates_found)
        send_telegram_message(message)
        print("Updates found! Sent message to Telegram.")
    else:
        print("No new updates found today.")
        
    # ALWAYS save the state, whether updated or not, so GitHub Actions can commit it
    with open(STATE_FILE, 'w') as f:
        json.dump(current_state, f)

if __name__ == "__main__":
    main()

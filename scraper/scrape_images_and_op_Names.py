# operator_scraper.py
import os
import requests
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- Configuration ---

# Get the absolute path of the directory where this script is located.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPERATORS_LIST_FILE = os.path.join(SCRIPT_DIR, 'operators_list.json')
IMAGE_DIR = os.path.join(SCRIPT_DIR, 'images')

ATTACKER_URL = 'https://www.ubisoft.com/en-au/game/rainbow-six/siege/game-info/operators?role=attacker'
DEFENDER_URL = 'https://www.ubisoft.com/en-au/game/rainbow-six/siege/game-info/operators?role=defender'

# --- Default lists to be used ONLY if 'operators_list.json' doesn't exist ---
# Updated keys to ATTACKERS and DEFENDERS for easier integration.
DEFAULT_DATA = {
    "ATTACKERS": ["Striker", "Sledge", "Thatcher", "Ash", "Thermite", "Twitch", "Montagne", "Glaz", "Fuze", "Blitz", "IQ", "Buck", "Blackbeard", "CAPITÃO", "Hibana", "Jackal", "Ying", "Zofia", "Dokkaebi", "Lion", "Finka", "Maverick", "Nomad", "Gridlock", "NØKK", "Amaru", "Kali", "Iana", "Ace", "Zero", "Flores", "Osa", "Sens", "Grim", "Brava", "Ram", "Deimos", "Rauora"],
    "DEFENDERS": ["Sentry", "Smoke", "Mute", "Castle", "Pulse", "Doc", "Rook", "Kapkan", "Tachanka", "Jäger", "Bandit", "Frost", "Valkyrie", "Caveira", "Echo", "Mira", "Lesion", "Ela", "Vigil", "Maestro", "Alibi", "Clash", "Kaid", "Mozzie", "Warden", "Goyo", "Wamai", "Oryx", "Melusi", "Aruni", "Thunderbird", "Thorn", "Azami", "Solis", "Fenrir", "Tubarão", "Skopós"]
}

def load_or_create_operator_lists():
    """Loads operator lists from the JSON file or creates it with defaults."""
    if not os.path.exists(OPERATORS_LIST_FILE):
        print(f"'{os.path.basename(OPERATORS_LIST_FILE)}' not found. Creating it with default lists...")
        # Use the new keys when creating the default file.
        write_operator_lists(DEFAULT_DATA["ATTACKERS"], DEFAULT_DATA["DEFENDERS"])

    with open(OPERATORS_LIST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Use the new keys when loading data from the file.
    return data["ATTACKERS"], data["DEFENDERS"]

def write_operator_lists(attackers, defenders):
    """Writes the given operator lists to the JSON file with custom formatting."""
    attackers_json_string = json.dumps(attackers, ensure_ascii=False)
    defenders_json_string = json.dumps(defenders, ensure_ascii=False)
    # Use the new keys in the final JSON output string.
    final_json_string = (
        "{\n"
        f'    "ATTACKERS": {attackers_json_string},\n'
        f'    "DEFENDERS": {defenders_json_string}\n'
        "}"
    )
    with open(OPERATORS_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write(final_json_string)
    print(f"\nUpdated '{os.path.basename(OPERATORS_LIST_FILE)}'.")

def setup_environment():
    """Creates the 'images' directory if it doesn't already exist."""
    if not os.path.exists(IMAGE_DIR):
        print(f"Creating directory to store images: '{os.path.basename(IMAGE_DIR)}'")
        os.makedirs(IMAGE_DIR)

def create_driver():
    """Creates and configures a Chrome WebDriver instance."""
    chrome_options = Options()
    
    # --- Options to reduce console noise ---
    # This will suppress most of the informational messages from ChromeDriver.
    chrome_options.add_argument('--log-level=3') 
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Make it less detectable as a bot
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Optional: Run headless (no visible browser window)
    # Uncomment the next line if you don't want to see the browser window
    # chrome_options.add_argument("--headless")
    
    # Set smaller window size
    chrome_options.add_argument("--window-size=1280,720")
    
    # Set user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        # Try to create driver (assumes chromedriver is in PATH)
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except WebDriverException as e:
        print(f"!!! Error creating Chrome driver: {e}")
        print("Make sure you have Chrome installed and chromedriver in your PATH.")
        print("Download chromedriver from: https://chromedriver.chromium.org/")
        return None

def create_session():
    """Creates a requests session with realistic browser headers for image downloads."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive'
    })
    return session

def download_image(session, url, filepath):
    """Downloads a single image from a URL using the provided session."""
    try:
        response = session.get(url, stream=True, timeout=15)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.exceptions.RequestException:
        return False

def extract_operators_with_selenium(driver, url, role_name):
    """Extract operators from a URL using Selenium."""
    try:
        driver.get(url)
        
        # Wait for the operator cards to load
        wait = WebDriverWait(driver, 15)
        
        # Wait for operator cards to be present
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.oplist__card")))
        
        # Give extra time for JavaScript filtering to complete
        time.sleep(3)
        
        # Get the page source after JavaScript has executed
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        op_cards = soup.find_all('a', class_='oplist__card')
        operator_names = []
        missing_images = []
        
        for card in op_cards:
            name_span = card.find('span')
            if not name_span:
                continue
                
            # Extract and clean the operator name
            operator_name = name_span.text.strip()
            operator_names.append(operator_name)
            
            # Check for missing main image
            main_img = card.find('img', class_='oplist__card__img')
            if main_img and main_img.get('src'):
                filename = f"{main_img.get('alt', operator_name)}.{main_img['src'].split('.')[-1].split('?')[0]}"
                filepath = os.path.join(IMAGE_DIR, filename)
                if not os.path.exists(filepath):
                    missing_images.append({'url': main_img['src'], 'filepath': filepath, 'filename': filename})
            
            # Check for missing icon image
            icon_img = card.find('img', class_='oplist__card__icon')
            if icon_img and icon_img.get('src'):
                filename = f"{icon_img.get('alt', f'{operator_name} icon')}.{icon_img['src'].split('.')[-1].split('?')[0]}"
                filepath = os.path.join(IMAGE_DIR, filename)
                if not os.path.exists(filepath):
                    missing_images.append({'url': icon_img['src'], 'filepath': filepath, 'filename': filename})
        
        return operator_names, missing_images
        
    except TimeoutException:
        print(f"!!! Timeout waiting for {role_name} page to load")
        return [], []
    except Exception as e:
        print(f"!!! Error extracting {role_name} operators: {e}")
        return [], []

def main():
    """Main function to run the scraper."""
    print("--- Starting Rainbow Six Siege Operator Scraper with Selenium --- (Φ ω Φ)")
    setup_environment()

    # Create Chrome driver
    driver = create_driver()
    if not driver:
        print("!!! Cannot proceed without Chrome driver. Exiting.")
        return

    # Create session for image downloads
    session = create_session()

    known_attackers, known_defenders = load_or_create_operator_lists()
    
    # Create copies to work with (avoid modifying originals until we're sure)
    updated_attackers = known_attackers.copy()
    updated_defenders = known_defenders.copy()
    
    all_missing_images = []
    new_operators_found = False

    try:
        # --- Process Attackers ---
        print("\n--- Checking Attackers... ---")
        attacker_names_from_site, attacker_missing_images = extract_operators_with_selenium(
            driver, ATTACKER_URL, "Attacker"
        )
        
        print(f"Extracted {len(attacker_names_from_site)} attackers: {attacker_names_from_site[:5]}..." if len(attacker_names_from_site) > 5 else f"Extracted attackers: {attacker_names_from_site}")
        
        # Find new attackers (those not in our known attackers list)
        new_attackers = [name for name in attacker_names_from_site if name not in known_attackers]
        if new_attackers:
            new_operators_found = True
            print(f"New Attackers found: {new_attackers}")
            for name in new_attackers:
                print(f"✨ New Attacker: {name}")
                updated_attackers.append(name)
        else:
            print("No new attackers found.")
        
        all_missing_images.extend(attacker_missing_images)

        # --- Add a pause before checking the next page ---
        print("\nPausing for 3 seconds before checking defenders...")
        time.sleep(3)

        # --- Process Defenders ---
        print("\n--- Checking Defenders... ---")
        defender_names_from_site, defender_missing_images = extract_operators_with_selenium(
            driver, DEFENDER_URL, "Defender"
        )
        
        print(f"Extracted {len(defender_names_from_site)} defenders: {defender_names_from_site[:5]}..." if len(defender_names_from_site) > 5 else f"Extracted defenders: {defender_names_from_site}")

        # Find new defenders (those not in our known defenders list)
        new_defenders = [name for name in defender_names_from_site if name not in known_defenders]
        if new_defenders:
            new_operators_found = True
            print(f"New Defenders found: {new_defenders}")
            for name in new_defenders:
                print(f"✨ New Defender: {name}")
                updated_defenders.append(name)
        else:
            print("No new defenders found.")
        
        all_missing_images.extend(defender_missing_images)

    finally:
        # Always close the browser
        print("\nClosing browser...")
        driver.quit()

    # --- Download Missing Images ---
    if all_missing_images:
        # Remove duplicates while preserving order
        unique_images = []
        seen_urls = set()
        for image_info in all_missing_images:
            if image_info['url'] not in seen_urls:
                unique_images.append(image_info)
                seen_urls.add(image_info['url'])
        
        total_images = len(unique_images)
        print(f"\nFound {total_images} missing image(s) to download...")
        for i, image_info in enumerate(unique_images, 1):
            print(f"[{i}/{total_images}] Downloading {image_info['filename']}...", end='', flush=True)
            success = download_image(session, image_info['url'], image_info['filepath'])
            print(" ✓ Done!" if success else " ✗ Failed!")
    else:
        print("\nAll operator images are already downloaded. (b ᵔ▽ᵔ)b")

    # --- Update the JSON file if new operators were found ---
    if new_operators_found:
        print(f"\nUpdating operator lists:")
        print(f"  Attackers: {len(updated_attackers)} total ({len(updated_attackers) - len(known_attackers)} new)")
        print(f"  Defenders: {len(updated_defenders)} total ({len(updated_defenders) - len(known_defenders)} new)")
        write_operator_lists(updated_attackers, updated_defenders)
    else:
        print("\nOperator lists are already up to date.")

    print("\n--- Script finished! --- ૮ ˶´ ˘ ` olursa ა")

if __name__ == "__main__":
    main()

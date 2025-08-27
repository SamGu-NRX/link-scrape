import time
import pandas as pd
import re
# Removed: import keyboard (due to bus error)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Set up Selenium with Chrome
options = Options()
# NON-HEADLESS for manual login (visible browser)
# options.add_argument("--headless")  # Uncomment for background mode AFTER testing
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")  # Updated UA for 2025

# Add proxy (uncomment and replace; e.g., from ScrapeOps or free lists)
# options.add_argument('--proxy-server=http://your-proxy-ip:port')  # Example: 'http://123.45.67.89:8080'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def manual_login():
    driver.get("https://www.linkedin.com/login")
    print("Browser opened to LinkedIn login page. Please log in manually (enter credentials, solve CAPTCHA if needed).")
    input("Press Enter in this terminal AFTER you've logged in and the page has loaded...")

def interactive_menu(profile_name):
    """Provides a blocking interactive menu for the user."""
    print(f"\n--- Finished scraping {profile_name} ---")
    print("   's' + Enter: Skip to the next profile")
    print("   'q' + Enter: Quit the script entirely")
    choice = input("Press Enter to continue to the next profile, or choose an option: ").strip().lower()

    if choice == 's':
        return 'skip'
    elif choice == 'q':
        return 'quit'
    return 'continue'

def scroll_gradually_until_end(url):
    """Navigates to the URL and scrolls gradually down the page until no new content loads."""
    driver.get(url)
    time.sleep(3)  # Initial load for the page content

    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_attempts = 0
    max_no_change_attempts = 5 # How many times we try without new content before giving up
    scroll_increment = 500 # Pixels to scroll each time

    print("Starting gradual scroll...")
    while no_change_attempts < max_no_change_attempts:
        # Scroll down by a fixed increment
        driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
        time.sleep(1 + (no_change_attempts * 0.5)) # Variable delay (1s to 3.5s)

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            no_change_attempts += 1
            print(f"No new content loaded. Attempt {no_change_attempts}/{max_no_change_attempts}.")
            time.sleep(2) # Extra wait for very slow loads
        else:
            last_height = new_height
            no_change_attempts = 0 # Reset counter as new content was found
            print(f"New content loaded. Current height: {last_height}px")

    print("Reached end of scrollable content (or max no-change attempts reached).")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") # Ensure truly at bottom
    time.sleep(3) # Final wait for any last-minute rendering

    print("Double-checking: Scrolling back to top and down gradually again.")
    driver.execute_script("window.scrollTo(0, 0);") # Scroll to top
    time.sleep(2) # Wait for page to settle at top

    # Perform the second full gradual scroll down
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_attempts = 0
    while no_change_attempts < max_no_change_attempts:
        driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
        time.sleep(1 + (no_change_attempts * 0.5)) # Variable delay

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            no_change_attempts += 1
            print(f"Double-check: No new content. Attempt {no_change_attempts}/{max_no_change_attempts}.")
            time.sleep(2)
        else:
            last_height = new_height
            no_change_attempts = 0
            print(f"Double-check: New content. Current height: {last_height}px")

    print("Double-check scroll complete.")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") # Ensure truly at bottom
    time.sleep(3) # Final wait
    return True

def extract_posts_from_source(page_source):
    """Parses the page source and extracts post data."""
    soup = BeautifulSoup(page_source, 'html.parser')
    post_elements = soup.find_all('div', class_=['feed-shared-update-v2', 'update-components-article'])

    posts = []
    for post in post_elements:
        try:
            # Extract text (preserve newlines)
            text_elem = post.find('div', class_='update-components-text') or post.find('span', class_='break-words')
            text = text_elem.get_text(separator='\n', strip=True) if text_elem else 'N/A'

            # Extract date (e.g., "8h" or "2d")
            date_elem = post.find('span', class_='update-components-actor__sub-description') or post.find('time')
            date_text = date_elem.get_text(strip=True) if date_elem else 'N/A'
            # Use regex to find relative time, e.g., "8h", "2d", "1w", "1mo", "1y"
            date_match = re.search(r'^\d+[hwdmoy]', date_text)
            date = date_match.group(0).strip() if date_match else date_text.split('•')[0].strip()

            # Extract likes (from reactions button)
            likes_elem = post.find('span', class_='social-details-social-counts__reactions-count')
            likes = likes_elem.get_text(strip=True).replace(',', '') if likes_elem else '0'  # Remove commas for numeric

            # Extract comments (specific to comments li)
            comments_li = post.find('li', class_=lambda x: x and 'comments' in x)
            comments_elem = comments_li.find('button') if comments_li else None
            comments_text = comments_elem.get_text(strip=True) if comments_elem else '0 comments'
            comments = re.search(r'\d+', comments_text).group(0) if re.search(r'\d+', comments_text) else '0'

            # Extract reposts (specific to reposts li)
            reposts_li = post.find('li', class_=lambda x: x and 'reposts' in x)
            reposts_elem = reposts_li.find('button') if reposts_li else None
            reposts_text = reposts_elem.get_text(strip=True) if reposts_elem else '0 reposts'
            reposts = re.search(r'\d+', reposts_text).group(0) if re.search(r'\d+', reposts_text) else '0'

            # Extract post URL
            post_urn_match = re.search(r'urn:li:activity:(\d+)', str(post))
            if post_urn_match:
                post_id = post_urn_match.group(1)
                post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}/"
            else:
                post_url_elem = post.find('a', class_='app-aware-link') or post.find('a', href=True)
                post_url = post_url_elem['href'] if post_url_elem else 'N/A'


            posts.append({
                'text': text,
                'date': date,
                'likes': likes,
                'comments': comments,
                'reposts': reposts,
                'url': post_url
            })
        except Exception as e:
            print(f"Error parsing a post: {e}")

    return posts

# Main script execution flow
try:
    manual_login()  # Login once

    # Read URLs from TXT file
    with open('people_urls.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    for url in urls:
        # Extract profile name (e.g., "ken-cheng-991849b6" -> "ken_cheng_991849b6")
        match = re.search(r'/in/([^/]+)', url)
        if match:
            profile_identifier = match.group(1)
            profile_name = profile_identifier.replace('-', '_') # Keep full identifier for unique filename
        else:
            profile_name = 'unknown_profile'

        # Show interactive menu before processing each profile
        menu_action = interactive_menu(profile_name)
        if menu_action == 'skip':
            print(f"Skipping {profile_name}.")
            continue  # Move to the next URL
        elif menu_action == 'quit':
            print("Quitting script.")
            break  # Exit the loop and finally quit driver

        print(f"Starting to scrape posts for {profile_name} from {url}")

        # Perform gradual scrolling and double-check
        scroll_gradually_until_end(url)

        # Extract posts from the fully scrolled page
        posts_data = extract_posts_from_source(driver.page_source)

        # De-dupe: Use a set to track unique posts (hash of text + date + url)
        unique_posts = []
        seen = set()
        for post in posts_data:
            post_hash = (post['text'], post['date'], post['url'])
            if post_hash not in seen:
                seen.add(post_hash)
                unique_posts.append(post)

        if not unique_posts:
            print(f"No unique posts found for {profile_name}. Ensure the profile has activity or check selectors.")
        else:
            # Save to CSV
            df = pd.DataFrame(unique_posts)
            csv_filename = f"{profile_name}_posts.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Scraped {len(unique_posts)} unique posts for {profile_name} and saved to {csv_filename}")

except Exception as e:
    print(f"An unexpected error occurred during scraping: {e}")
    # Optional: Save page source on error for debugging
    # with open("error_page_source.html", "w", encoding="utf-8") as f:
    #     f.write(driver.page_source)

finally:
    print("Closing browser.")
    driver.quit()

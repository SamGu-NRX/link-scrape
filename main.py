import time
import pandas as pd
import re
import csv
import threading
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Set up Selenium with Chrome
options = Options()
# NON-HEADLESS for manual login (visible browser)
# options.add_argument("--headless")  # Uncomment to run headless (saves memory)
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

# Global flag for pause/resume/skip/quit
control_command = None
lock = threading.Lock()

def listen_for_commands():
    global control_command
    while True:
        cmd = input().strip().lower()
        with lock:
            control_command = cmd
        if cmd == 'q':
            print("Quitting and restarting from beginning...")
            driver.quit()
            sys.exit(0)  # Exit to restart (re-run script manually)

# Start listener thread
listener_thread = threading.Thread(target=listen_for_commands, daemon=True)
listener_thread.start()

print("Command listener started. Type 'p' + Enter to pause, 'r' to resume, 's' to skip profile, 'q' to quit/restart.")

def check_control():
    global control_command
    with lock:
        cmd = control_command
        control_command = None  # Reset
    if cmd == 'p':
        print("Paused. Type 'r' + Enter to resume or 's' to skip.")
        while True:
            time.sleep(0.1)
            with lock:
                resume_cmd = control_command
                control_command = None
            if resume_cmd == 'r':
                print("Resuming...")
                return 'resume'
            elif resume_cmd == 's':
                print("Skipping...")
                return 'skip'
            elif resume_cmd == 'q':
                return 'quit'
    return 'continue'

def gradual_scroll_and_parse_incrementally(url, csv_filename, seen):
    driver.get(url)
    time.sleep(3)  # Initial load

    current_height = 0
    total_height = driver.execute_script("return document.body.scrollHeight")
    step_count = 0
    chunk_size = 10  # Parse every 10 steps to save memory

    while current_height < total_height:
        try:
            driver.execute_script(f"window.scrollTo(0, {current_height});")
            time.sleep(1 + (step_count % 3) * 0.3)  # Variable delay 1-1.9s for loading

            action = check_control()
            if action == 'skip' or action == 'quit':
                return seen  # Return current seen for partial save

            current_height += 500
            new_height = driver.execute_script("return document.body.scrollHeight")
            print(f"Scrolled to height: {new_height}")
            if new_height > total_height:
                total_height = new_height

            step_count += 1
            if step_count % chunk_size == 0:
                # Incremental parse and save
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                post_elements = soup.find_all('div', class_=['feed-shared-update-v2', 'update-components-article'])

                new_posts = []
                for post in post_elements:
                    try:
                        text_elem = post.find('div', class_='update-components-text') or post.find('span', class_='break-words')
                        text = text_elem.get_text(separator=' ', strip=True).replace('"', '`') if text_elem else 'N/A'

                        date_elem = post.find('span', class_='update-components-actor__sub-description') or post.find('time')
                        date_text = date_elem.get_text(strip=True) if date_elem else 'N/A'
                        date = re.search(r'^\d+[hwdmoy]?', date_text).group(0).strip() if re.search(r'^\d+[hwdmoy]?', date_text) else date_text

                        likes_elem = post.find('span', class_='social-details-social-counts__reactions-count')
                        likes = likes_elem.get_text(strip=True).replace(',', '') if likes_elem else '0'

                        comments_li = post.find('li', class_=lambda x: x and 'comments' in x)
                        comments_elem = comments_li.find('button') if comments_li else None
                        comments_text = comments_elem.get_text(strip=True) if comments_elem else '0 comments'
                        comments = re.search(r'\d+', comments_text).group(0) if re.search(r'\d+', comments_text) else '0'

                        reposts_li = post.find('li', class_=lambda x: x and 'reposts' in x)
                        reposts_elem = reposts_li.find('button') if reposts_li else None
                        reposts_text = reposts_elem.get_text(strip=True) if reposts_elem else '0 reposts'
                        reposts = re.search(r'\d+', reposts_text).group(0) if re.search(r'\d+', reposts_text) else '0'

                        post_url_elem = post.find('a', class_='app-aware-link') or post.find('a', href=True)
                        post_url = post_url_elem['href'] if post_url_elem else 'N/A'

                        post_hash = (text, date, post_url)
                        if post_hash not in seen:
                            seen.add(post_hash)
                            new_posts.append({
                                'text': text,
                                'date': date,
                                'likes': likes,
                                'comments': comments,
                                'reposts': reposts,
                                'url': post_url
                            })
                    except Exception as e:
                        print(f"Error parsing post in chunk: {e}")

                # Append new posts to CSV
                if new_posts:
                    os.makedirs(os.path.dirname(csv_filename), exist_ok=True) # Ensure data directory exists
                    mode = 'a' if os.path.exists(csv_filename) else 'w'
                    with open(csv_filename, mode, newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=['text', 'date', 'likes', 'comments', 'reposts', 'url'], quoting=csv.QUOTE_MINIMAL)
                        if mode == 'w':
                            writer.writeheader()
                        for post in new_posts:
                            writer.writerow(post)
                    print(f"Saved {len(new_posts)} new posts incrementally to {csv_filename}. Total unique: {len(seen)}")

        except Exception as e:
            print(f"Error during scrolling: {e}. Saving partial data...")
            return seen  # Return seen for final count

    print("Scrolling completed.")
    return seen

# Run the scraper
try:
    manual_login()  # Login once

    # Read URLs from TXT file
    with open('people_urls.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    for url in urls:
        # Extract profile name (improved: handle name and ID separately)
        match = re.search(r'/in/([a-zA-Z0-9_-]+)-([a-zA-Z0-9]+)', url)
        profile_name = match.group(1).replace('-', '_') if match else 'unknown'
        csv_filename = f"data/{profile_name}_posts.csv" # Save to data/ subdirectory
        print(f"Scraping posts for {profile_name} from {url}")

        # Load existing seen hashes from CSV for resume/de-dupe
        seen = set()
        if os.path.exists(csv_filename):
            df_existing = pd.read_csv(csv_filename)
            for _, row in df_existing.iterrows():
                seen.add((row['text'], row['date'], row['url']))
            print(f"Resuming from {len(seen)} existing unique posts.")

        # Scroll and parse incrementally
        seen = gradual_scroll_and_parse_incrementally(url, csv_filename, seen)

        print(f"Scraped and saved {len(seen)} unique posts for {profile_name} to {csv_filename}")
except Exception as e:
    print(f"Scraping failed: {e}. Possible block—try a proxy or manual check.")

# Clean up
driver.quit()

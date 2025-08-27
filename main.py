import time
import pandas as pd
import re
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
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")  # Updated UA for 2025

# Add proxy (uncomment and replace; e.g., from ScrapeOps or free lists)
# options.add_argument('--proxy-server=http://your-proxy-ip:port')  # Example: 'http://123.45.67.89:8080'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def manual_login():
    # Navigate to LinkedIn login page
    driver.get("https://www.linkedin.com/login")
    print("Browser opened to LinkedIn login page. Please log in manually (enter credentials, solve CAPTCHA if needed).")
    input("Press Enter in this terminal AFTER you've logged in and the page has loaded...")

def scroll_and_load_posts(url):
    driver.get(url)
    time.sleep(3)  # Initial load

    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_attempts = 0
    max_no_change = 3  # Stop after 3 failed loads

    while no_change_attempts < max_no_change:
        # Scroll down gradually
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2 + (no_change_attempts % 3))  # Variable delay (2-4s) to mimic human and allow loading

        # Check for new height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_attempts += 1
            print(f"No change detected ({no_change_attempts}/{max_no_change})—trying again...")
            time.sleep(2)  # Extra wait before retry
        else:
            no_change_attempts = 0  # Reset on success
            last_height = new_height

    print("Reached end of page—no more posts loading.")

    # Parse with Beautiful Soup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find all post elements
    post_elements = soup.find_all('div', class_=['feed-shared-update-v2', 'update-components-article'])

    posts = []
    for post in post_elements:
        try:
            # Extract text (full content with breaks)
            text_elem = post.find('div', class_='update-components-text') or post.find('span', class_='break-words')
            text = text_elem.get_text(strip=True, separator=' ') if text_elem else 'N/A'

            # Extract date (e.g., "8h •" from sub-description)
            date_elem = post.find('span', class_='update-components-actor__sub-description') or post.find('time')
            date_text = date_elem.get_text(strip=True) if date_elem else 'N/A'
            date = re.search(r'^\d+[hwdmoy]?\s*•?', date_text).group(0).strip() if re.search(r'^\d+[hwdmoy]?\s*•?', date_text) else date_text  # Extract relative time

            # Extract likes (e.g., "437")
            likes_elem = post.find('span', class_='social-details-social-counts__reactions-count')
            likes = likes_elem.get_text(strip=True) if likes_elem else '0'

            # Extract comments (e.g., "52" from "52 comments")
            comments_elem = post.find('button', class_='social-details-social-counts__count-value')  # Comments button
            comments_text = comments_elem.get_text(strip=True) if comments_elem else '0 comments'
            comments = re.search(r'\d+', comments_text).group(0) if re.search(r'\d+', comments_text) else '0'

            # Extract post URL
            post_url_elem = post.find('a', class_='app-aware-link') or post.find('a', href=True)
            post_url = post_url_elem['href'] if post_url_elem else 'N/A'

            posts.append({
                'text': text,
                'date': date,
                'likes': likes,
                'comments': comments,
                'url': post_url
            })
        except Exception as e:
            print(f"Error parsing post: {e}")

    return posts

# Run the scraper
try:
    manual_login()  # Login once

    # Read URLs from TXT file
    with open('people_urls.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    for url in urls:
        # Extract profile name from URL (e.g., "ken-cheng-991849b6" → "ken_cheng")
        profile_name = re.search(r'/in/([^/]+)', url).group(1).replace('-', '_').split('_')[0] + '_' + re.search(r'/in/([^/]+)', url).group(1).replace('-', '_').split('_')[1] if re.search(r'/in/([^/]+)', url) else 'unknown'
        print(f"Scraping posts for {profile_name} from {url}")

        posts_data = scroll_and_load_posts(url)

        # De-dupe: Use a set to track unique posts (hash of text + date + url)
        unique_posts = []
        seen = set()
        for post in posts_data:
            post_hash = (post['text'], post['date'], post['url'])  # Tuple for uniqueness
            if post_hash not in seen:
                seen.add(post_hash)
                unique_posts.append(post)

        if not unique_posts:
            print(f"No posts found for {profile_name}. Ensure the profile has activity.")
        else:
            # Save to CSV
            df = pd.DataFrame(unique_posts)
            csv_filename = f"{profile_name}_posts.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Scraped {len(unique_posts)} unique posts for {profile_name} and saved to {csv_filename}")
except Exception as e:
    print(f"Scraping failed: {e}. Possible block—try a proxy or manual check.")

# Clean up (close browser only after all profiles)
driver.quit()

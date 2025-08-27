import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# URL of the user's activity page (public posts, but we'll access via login)
PROFILE_ACTIVITY_URL = "https://www.linkedin.com/in/ken-cheng-991849b6/recent-activity/all/"

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
    # Navigate to LinkedIn login page
    driver.get("https://www.linkedin.com/login")
    print("Browser opened to LinkedIn login page. Please log in manually (enter credentials, solve CAPTCHA if needed).")
    input("Press Enter in this terminal AFTER you've logged in and the page has loaded...")

def scroll_and_load_posts(url):
    driver.get(url)
    time.sleep(3)  # Initial load

    posts = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    no_change_attempts = 0
    max_no_change = 3  # Stop after 3 failed loads (handles true end-of-page)

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

    # Parse with Beautiful Soup (updated selectors for 2025 LinkedIn structure)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Updated post elements
    post_elements = soup.find_all('div', class_=['feed-shared-update-v2', 'update-components-article'])

    for post in post_elements:
        try:
            # Extract text (robust selector)
            text_elem = post.find('span', class_='break-words') or post.find('div', class_='update-components-text')
            text = text_elem.get_text(strip=True) if text_elem else 'N/A'

            # Extract date
            date_elem = post.find('time') or post.find('span', class_='visually-hidden')
            date = date_elem.get_text(strip=True) if date_elem else 'N/A'

            # Extract likes/comments (aria-label based, more reliable)
            likes_elem = post.find('span', {'aria-label': lambda x: x and 'likes' in x.lower()})
            likes = likes_elem.get_text(strip=True) if likes_elem else '0'

            comments_elem = post.find('span', {'aria-label': lambda x: x and 'comments' in x.lower()})
            comments = comments_elem.get_text(strip=True) if comments_elem else '0'

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

# Run the scraper with manual login and error handling
try:
    manual_login()  # Pause for manual login
    posts_data = scroll_and_load_posts(PROFILE_ACTIVITY_URL)

    # De-dupe: Use a set to track unique posts (hash of text + date + url)
    unique_posts = []
    seen = set()
    for post in posts_data:
        post_hash = (post['text'], post['date'], post['url'])  # Tuple for uniqueness
        if post_hash not in seen:
            seen.add(post_hash)
            unique_posts.append(post)

    if not unique_posts:
        print("No posts found. Ensure the profile has public activity, or try a different proxy/account.")
    else:
        # Save to CSV
        df = pd.DataFrame(unique_posts)
        df.to_csv('ken_cheng_linkedin_posts.csv', index=False)
        print(f"Scraped {len(unique_posts)} unique posts (after de-duping) and saved to ken_cheng_linkedin_posts.csv")
except Exception as e:
    print(f"Scraping failed: {e}. Possible block—try a proxy, different account, or manual check.")

# Clean up
driver.quit()

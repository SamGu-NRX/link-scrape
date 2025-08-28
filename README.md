<h1 align="center">Link‑Scrape</h1>
<p align="center"><em>Scrape lightly. Only what you’re allowed to see. Ethically.</em></p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-2B2B2B?logo=python&logoColor=FFE873&style=flat">
  <img alt="Selenium" src="https://img.shields.io/badge/Selenium-Automation-2B2B2B?logo=selenium&logoColor=43B02A&style=flat">
  <img alt="BeautifulSoup4" src="https://img.shields.io/badge/BeautifulSoup4-Parser-2B2B2B?style=flat">
  <img alt="pandas" src="https://img.shields.io/badge/pandas-Data%20Frames-2B2B2B?logo=pandas&logoColor=white&style=flat">
  <img alt="Chrome" src="https://img.shields.io/badge/Chrome-Required-2B2B2B?logo=googlechrome&logoColor=4285F4&style=flat">
  <img alt="OS" src="https://img.shields.io/badge/OS-macOS%20|%20Linux%20|%20Windows-2B2B2B?style=flat">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-2B2B2B?style=flat">
</p>

---

## Why Link-Scrape?

Link-Scrape helps researchers, analysts, and builders collect publicly visible LinkedIn posts from profiles they already have access to. It’s designed to be:

- Lightweight and resilient
- Human-in-the-loop (manual login, interactive controls)
- Respectful of platforms, people, and policies

---

## What it does

- Automated session bootstrap via Selenium (you log in manually)
- Incremental scroll-and-parse to avoid memory spikes
- De-duplication to keep your data clean
- Interactive controls (pause/resume/skip/restart) from your terminal
- Multi-profile queue via `people_urls.txt`
- CSV export per profile

---

## What it doesn’t do

- It does not bypass authentication, CAPTCHAs, or paywalls
- It does not collect data you can’t already access
- It does not run headless by default (you see the browser)

---

## Ethics & Responsible Use

- Respect Terms of Service and robots.txt where applicable
- Only scrape content you’re authorized to view
- Honor user consent and privacy expectations
- Rate-limit and go slow; avoid disruptive patterns
- Use collected data responsibly; comply with laws in your jurisdiction

If you’re unsure whether a use case is appropriate, don’t run it.

---

## Quick Start

### Prerequisites
- Python 3.9+ recommended
- Google Chrome installed
  - Download: https://googlechromelabs.github.io/chrome-for-testing/
- ChromeDriver is handled automatically by Selenium Manager in recent Selenium versions; if you need a specific driver, ensure it matches your Chrome version

### Install

```bash
git clone https://github.com/SamGu-NRX/link-scrape.git
cd link-scrape

python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows (PowerShell)
# venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Configure profiles

Edit `people_urls.txt` with one LinkedIn profile feed per line. Use the “recent activity – all” path to capture posts:

```text
https://www.linkedin.com/in/john-doe/recent-activity/all/
https://www.linkedin.com/in/jane-smith/recent-activity/all/
```

Tip: Open a profile in your browser, click “See all activity,” then “All,” and copy that URL.

### Run

```bash
python main.py
```

- A Chrome window opens to LinkedIn.
- Log in manually.
- After the target page loads, return to the terminal and press Enter to continue.

### Interactive controls

From the terminal:
- `p` + Enter — Pause
- `r` + Enter — Resume
- `s` + Enter — Skip current profile
- `q` + Enter — Quit and restart session

### Output

- CSVs saved under `data/`
- One file per profile: `[profile_slug]_posts.csv`

---

## Data Schema (WIP)

Each row represents a public post or reshare found under the profile’s activity:

- profile_url
- profile_name
- post_id (stable hash/identifier used for de-duplication)
- post_url
- post_type (post | reshare | article)
- content_text
- content_html (optional, if captured)
- hashtags (comma-separated)
- media (list/urls if present)
- timestamp (ISO 8601)
- collected_at (ISO 8601)

Note: Fields may vary based on what is publicly visible and page layout at scrape time.

---

## Performance & Stability

- Incremental scrolling and chunked parsing limit memory usage and ensures all posts are scraped
- De-duplication prevents repeated rows across runs
- If LinkedIn’s structure changes, selectors may need updates in `main.py`
- Network latency and anti-automation measures can slow results; patience helps

---

## Troubleshooting

- Blank CSV or few rows:
  - Verify the URL ends with `/recent-activity/all/`
  - Ensure the profile has public posts
  - Scroll timeouts may need adjustment (see settings in `main.py`)

- Login loops or CAPTCHA:
  - Complete manual verification in the Chrome window
  - Wait for the feed to fully load before pressing Enter

- Driver issues:
  - Ensure Chrome is installed
  - Update Selenium and Chrome to recent versions

---

## Project Structure

```text
link-scrape/
├── data/
│   └── (generated CSV files)
├── main.py
├── people_urls.txt
├── requirements.txt
└── README.md
```

---

## Configuration knobs (in-code, WIP)

- Scroll delay / max scrolls
- Selector strings for post containers, timestamps, text blocks
- Output directory
- Logging verbosity

These can be adjusted in `main.py` to match your environment and site changes.

---

## Contributing

- Fork, branch, and open a PR
- Keep changes small and documented
- Favor clear selectors and explicit waits over brittle timing hacks
- Add sample outputs or tests if you change parsing

---

## License

MIT. Please use responsibly and lawfully.

LIHKG Web Scraper – Configuration & Usage Guide

This scraper collects thread links from a specified LIHKG (lihkg.com) category, extracts post details (date, likes, dislikes), and filters results by a target date range. Finally it saves the data as a CSV file.

Important Note about Page Loading:
LIHKG's category page does NOT load all threads at once. You MUST scroll down (either manually or through code) to trigger loading of more posts. This script simulates scrolling automatically using JavaScript. However, if you encounter issues with automatic scrolling (e.g., CAPTCHA or slow network), you can uncomment the manual CAPTCHA handling section and scroll manually once.

Main Features

- Simulates downward scrolling on the category page to load all visible thread links.
- Visits each thread, extracts the post date, likes, dislikes, and title.
- Filters posts by a date window (TARGET_START ~ TARGET_END).
- Saves a sorted CSV (by total engagement = likes + dislikes).

---

Configuration Parameters (Edit these inside the script)

Parameter Description

TARGET_START: Start date for filtering posts (inclusive). Format: "YYYY-MM-DD". Example: "2026-03-16"

TARGET_END: End date for filtering posts (inclusive). Format: "YYYY-MM-DD". Example: "2026-03-22"

TOP_PERCENT: Fraction of posts to keep after sorting by total engagement. 1 = keep all. 0.2 = keep top 20% (e.g., only most engaging posts). Example: 1

SAVE_PATH: Directory where the CSV file will be saved. Use raw string (r"...") to avoid escape issues. Example: r"C:\Users\...\project"

FILE_NAME: Name of the output CSV file. Example: "LIHKG_SOCI_FINAL_DATA.csv"

---

How to Change the Target Category (e.g., from "Housing" to something else)

The current script uses category 37 – which is "房屋台" (Housing Board).

To scrape a different board:

1. Go to https://lihkg.com/category/<category_id> while browsing LIHKG.
2. Find the desired category ID from the URL. For example:
   - https://lihkg.com/category/42 → ID 42 (maybe "時事台")
   - https://lihkg.com/category/1  → ID 1  ("吹水台")
3. In the script, locate the line:
   driver.get("https://lihkg.com/category/37")
   Change 37 to your desired category ID.

Note: Some categories may have different HTML structures. The selectors used (e.g., a[href^='/thread/'], span[data-tip]) are consistent across most LIHKG categories, so they should still work.

---

Web Scraping Workflow

Phase 1 – Collect thread links from the category page
- Opens the category page. The script then repeatedly simulates scrolling down by 1200 pixels (using JavaScript window.scrollBy) and waits 5 seconds for new content to load.
- Because LIHKG requires scrolling to preload more threads, this simulation continues until no new links are added after two consecutive scrolls.
- Extracts all <a href="/thread/..."> links and stores them in all_links (duplicates removed).

Phase 2 – Visit each thread and extract data
For each thread link:
- Optional CAPTCHA handling block (commented by default). Uncomment if you face human verification pages.
- Waits for the element span[data-tip] (which holds the post timestamp).
- Parses the date (Chinese format -> YYYY-MM-DD).
- If the date is within TARGET_START and TARGET_END:
  - Extracts likes/dislikes using selectors: label[for$='-like-like'] and label[for$='-dislike-like'].
  - Stores: title, date, likes, dislikes, net likes, total engagement, URL.
- Otherwise skips the thread.

Phase 3 – Save data
- Converts the list of dictionaries into a Pandas DataFrame.
- Sorts by total_engagement descending.
- Keeps only the top TOP_PERCENT fraction.
- Exports to CSV with utf-8-sig encoding (Excel-friendly for Chinese characters).

---

Optional: Manual CAPTCHA Handling

If LIHKG presents a Cloudflare or custom verification page when you enter a thread, you can uncomment the following lines inside the "for i, link in enumerate(all_links):" loop:

# print(">>> Possible CAPTCHA detected. Waiting 5-10 seconds for manual solving...")
# time.sleep(5)   # Adjust as needed (e.g., 8, 10 seconds)
# input("Press Enter after you have solved the CAPTCHA and the page has loaded...")

Once uncommented, the script will pause for 5 seconds and then wait for you to press Enter after solving the CAPTCHA manually. You can also keep only the time.sleep() part for a simple fixed delay.

If automatic scrolling on the category page fails (e.g., because of a CAPTCHA or network issue), you can also temporarily add a similar input() break after the initial driver.get() to manually scroll and then continue.

---

Dependencies & Setup

Install required Python packages:

pip install pandas selenium

Additionally, you need Microsoft Edge WebDriver:
- Download the version matching your Edge browser from Microsoft Edge WebDriver (https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/).
- Place the msedgedriver.exe in a folder that is in your system PATH, or specify its location directly in the script (not needed if using the default webdriver.Edge() with proper PATH).

---

Running the Script

Simply execute:

python your_scraper_filename.py

The browser will open automatically (images disabled for speed). You may need to manually solve the initial CAPTCHA on the first load – the script gives 15 seconds for that. After that, the script will simulate scrolling to load threads.

---

Output Example (CSV columns)

title, date, likes, dislikes, net_likes, total_engagement, url
Example post title, 2026-03-20, 123, 45, 78, 168, https://lihkg.com/thread/...

---

Troubleshooting

- No data saved: Check that the date range covers the actual post dates from the threads. LIHKG may not have posts in that period.
- Stuck scrolling: If the script stops scrolling early (no new links but you see more posts further down), increase the waiting time (time.sleep(5) to a larger value, e.g., 8) or increase the scroll distance (1200 to 1500). You can also add a longer initial wait after the page loads.
- Element not found errors: LIHKG may have changed its HTML structure. Inspect the page and update CSS selectors accordingly.
- The script seems to scroll but no new links appear: This often means the page requires manual intervention (CAPTCHA). Uncomment the manual CAPTCHA handling section and scroll a little manually.

---

Notes

- The script disables image loading (--blink-settings=imagesEnabled=false) for faster scraping.
- It uses WebDriverWait with a 12-second timeout to wait for dynamic content.
- The TOP_PERCENT parameter works after date filtering, so it only reduces the final dataset, not the number of visited threads.
- Because LIHKG loads more posts only when you scroll down, the script's automatic scrolling is essential. If you want to test manually, you can comment out the scrolling loop and scroll by hand while the script waits for keyboard input.

Happy scraping!

import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- 1. Configuration ----------
TARGET_START = pd.to_datetime("2026-03-16")
TARGET_END = pd.to_datetime("2026-03-22")
TOP_PERCENT = 1          # 1 = keep 100% of posts; 0.2 = top 20% by engagement

SAVE_PATH = "./data"
FILE_NAME = "LIHKG.csv"


def start_spider():
    # --- Initialization ---
    if not os.path.exists(SAVE_PATH):
        os.makedirs(SAVE_PATH)
        print(f">>> Created folder: {SAVE_PATH}")

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Edge(options=options)
    all_links = []

    try:
        # --- Phase 1: Scroll and collect all visible thread links ---
        print(">>> Scrolling homepage to collect all possible thread links...")
        driver.get("https://lihkg.com/category/37") #category 37 is specifically for "房屋台," edit this part if you want to collect data from the other sections
        time.sleep(15)   # Allow time for manual CAPTCHA or initial load

        last_height = driver.execute_script("return document.body.scrollHeight")
        no_new_links_count = 0   # Counter to detect when no new links appear after scrolling

        while True:
            # Find all thread links on current page
            threads = driver.find_elements(By.CSS_SELECTOR, "a[href^='/thread/']")
            new_links_found = False
            for t in threads:
                try:
                    link = t.get_attribute("href")
                    if link and "/thread/" in link and link not in all_links:
                        all_links.append(link)
                        new_links_found = True
                except:
                    continue

            print(f"    Current total unique links: {len(all_links)}")

            # Scroll down by 1200 pixels
            driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(5)

            # Check if page height increased
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # If no height increase and no new links were added in this iteration, likely reached bottom
                if not new_links_found:
                    no_new_links_count += 1
                else:
                    no_new_links_count = 0

                if no_new_links_count >= 2:   # Two consecutive scrolls with no new links -> stop
                    print("    [!] No new links detected after scrolling. Stopping collection.")
                    break
            else:
                no_new_links_count = 0

            last_height = new_height

        print(f"\n--- Link collection completed, total unique links: {len(all_links)} ---")

        # --- Phase 2: Extract details from each thread ---
        all_data = []
        for i, link in enumerate(all_links):
            driver.get(link)

            # ===== OPTIONAL MANUAL CAPTCHA HANDLING =====
            # Uncomment the following lines if you encounter human verification challenges
            # on individual thread pages (e.g., Cloudflare or LIHKG's own protection).
            # It will pause for 5–10 seconds, giving you time to manually solve the CAPTCHA.
            # -------------------------------------------------------------
            # print(">>> Possible CAPTCHA detected. Waiting 5-10 seconds for manual solving...")
            # time.sleep(5)   # Adjust as needed (e.g., 8, 10 seconds)
            # input("Press Enter after you have solved the CAPTCHA and the page has loaded...")
            # =============================================================

            try:
                wait = WebDriverWait(driver, 12)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-tip]")))

                time_elements = driver.find_elements(By.CSS_SELECTOR, "span[data-tip]")
                post_date = None
                raw_dt_display = "Unknown"
                for elem in time_elements:
                    raw_dt = elem.get_attribute("data-tip")
                    if raw_dt and "年" in raw_dt:
                        raw_dt_display = raw_dt
                        clean_dt = raw_dt.split(' ')[0].replace('年', '-').replace('月', '-').replace('日', '')
                        post_date = pd.to_datetime(clean_dt)
                        break

                print(f"[{i+1}/{len(all_links)}] Date: {raw_dt_display}", end=" ")

                if post_date and TARGET_START <= post_date <= TARGET_END:
                    likes, dislikes = 0, 0
                    for _ in range(3):
                        try:
                            l_el = driver.find_element(By.CSS_SELECTOR, "label[for$='-like-like']")
                            d_el = driver.find_element(By.CSS_SELECTOR, "label[for$='-dislike-like']")
                            l_txt = l_el.get_attribute("textContent").strip()
                            d_txt = d_el.get_attribute("textContent").strip()
                            if l_txt.isdigit():
                                likes, dislikes = int(l_txt), int(d_txt)
                                break
                        except:
                            pass
                        time.sleep(1)

                    all_data.append({
                        "title": driver.title.split(' - ')[0],
                        "date": post_date,
                        "likes": likes,
                        "dislikes": dislikes,
                        "net_likes": likes - dislikes,
                        "total_engagement": likes + dislikes,
                        "url": link
                    })
                    print(f" -> [✅ MATCH] likes:{likes} | net:{likes-dislikes}")
                else:
                    print(" -> [x] SKIP")
            except Exception:
                print(f"[{i+1}/{len(all_links)}] -> [!] Timeout, skipping")
                continue

        # --- Phase 3: Save data ---
        if all_data:
            df = pd.DataFrame(all_data)
            df = df.sort_values(by="total_engagement", ascending=False)
            top_n = max(1, int(len(df) * TOP_PERCENT))
            final_df = df.head(top_n)

            full_save_path = os.path.join(SAVE_PATH, FILE_NAME)
            final_df.to_csv(full_save_path, index=False, encoding="utf-8-sig")
            print(f"\n🎉 Done! File saved to: {full_save_path}")
        else:
            print("\nNo data found within the date range.")

    except Exception as e:
        print(f"\nProgram error: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    start_spider()

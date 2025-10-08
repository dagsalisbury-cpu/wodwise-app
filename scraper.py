import os
import time
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- Configuration ---
LEADERBOARD_URL_TEMPLATE = 'https://games.crossfit.com/leaderboard/open/2025?view=0&division=1&region=0&scaled=0&sort=0&page={}'
BASE_URL = 'https://games.crossfit.com'
START_PAGE = 101
END_PAGE = 120  # Set how many pages to loop through
ATHLETES_TO_SCRAPE = 1000

def setup_driver():
    """Sets up the Selenium Chrome driver with images disabled for speed."""
    print("--- Setting up browser (with images disabled) ---")

    # 1. Create an options object
    chrome_options = webdriver.ChromeOptions()

    # 2. Add the preference to disable images
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    # 3. Pass the options when creating the driver
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_athlete_profile(driver, profile_url):
    """
    Visits an athlete's page and scrapes a pre-defined list of benchmark stats.
    """
    print(f"  - Scraping profile: {profile_url}")
    driver.get(profile_url)
    athlete_data = {'profile_url': profile_url}
    wait = WebDriverWait(driver, 20)

    # A master list of the exact benchmark names as they appear on the website
    BENCHMARKS_TO_FIND = [
        "Back Squat", "Chad1000x","Clean and Jerk", "Deadlift", "Fight Gone Bad", 
        "Filthy 50", "Fran", "Grace", "Helen", "L1 Benchmark", "Max Pull-ups", "Murph",
        "Run 5k", "Snatch", "Sprint 400m"
    ]

    try:
        wait.until(EC.visibility_of_element_located((By.ID, "athleteProfile")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Scrape Name, Country, and Gender (no changes here)
        try:
            first_name_el = soup.select_one("#athleteProfile > div.page-cover > div.athlete-info-container > div > div.athlete-name > h1 > span:nth-child(1)")
            last_name_el = soup.select_one("#athleteProfile > div.page-cover > div.athlete-info-container > div > div.athlete-name > h1 > span:nth-child(2)")
            athlete_data['name'] = f"{first_name_el.text.strip()} {last_name_el.text.strip()}"
        except Exception: athlete_data['name'] = 'N/A'
        try:
            country_el = soup.select_one("#athleteProfile > div.page-cover > div.athlete-info-container > div > div.country-block > span.country-name")
            athlete_data['country'] = country_el.text.strip()
        except Exception: athlete_data['country'] = 'N/A'
        try:
            gender_el = soup.select_one("#athleteProfile > div.page-cover > div.athlete-info-container > div > div.stats-level-block > ul > li > a")
            athlete_data['gender'] = gender_el.text.strip()
        except Exception: athlete_data['gender'] = 'N/A'

          # Scrape the 2025 Open Rank
        open_heading = soup.find('h4', string='Open')
        if open_heading:
            open_table = open_heading.find_next('table')
            if open_table:
                rows = open_table.find('tbody').find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if cells and cells[0].text.strip() == '2025':
                        rank_span = cells[1].find('span', class_='rank')
                        if rank_span:
                            rank_text = rank_span.text.strip()
                            rank_number = ''.join(filter(str.isdigit, rank_text))
                            athlete_data['open_2025_rank_worldwide'] = rank_number
                        break 

        # --- NEW, MORE PRECISE STATS SCRAPING LOGIC ---
        # Initialize all benchmark columns with a blank value
        for b in BENCHMARKS_TO_FIND:
            key = b.lower().replace(' ', '').replace('-', '')
            athlete_data[key] = ''

        benchmark_container = soup.find('div', id='benchmarkStats')
        if benchmark_container:
            # Loop through our desired benchmarks, not all rows on the page
            for benchmark_name in BENCHMARKS_TO_FIND:
                # Find the header cell with the exact benchmark name
                header = benchmark_container.find('th', class_='stats-header', string=lambda text: text and benchmark_name.lower() in text.lower())

                if header:
                    # Find the corresponding data cell in the same row
                    data_cell = header.find_next_sibling('td')
                    if data_cell and data_cell.text.strip() != '--':
                        stat_name_key = benchmark_name.lower().replace(' ', '').replace('-', '')
                        stat_value = data_cell.text.strip().split(' ')[0]
                        athlete_data[stat_name_key] = stat_value
        # --- END OF NEW LOGIC ---

        return athlete_data

    except Exception as e:
        print(f"    - ❌ Error scraping {profile_url}: {e}")
        return None

if __name__ == "__main__":
    start_time = time.time()
    driver = setup_driver()
    all_unique_links = set()
    all_athlete_stats = []
    
    try:
        # --- Stage 1: Loop through each Leaderboard Page ---
        print(f"--- Stage 1: Scraping pages {START_PAGE} to {END_PAGE} ---")
        for page_num in range(START_PAGE, END_PAGE + 1):
            url = LEADERBOARD_URL_TEMPLATE.format(page_num)
            print(f"\n  - Navigating to page {page_num}: {url}")
            driver.get(url)
            
            try:
                wait = WebDriverWait(driver, 5)
                # Find and click "Expand All" on the CURRENT page
                print("    - Waiting for 'Expand All' link...")
                expand_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Expand All')]")))
                driver.execute_script("arguments[0].click();", expand_link)
                
                # Wait for the page to expand with new links
                print("    - Waiting for full list to load...")
                wait.until(lambda d: len(d.find_elements(By.XPATH, "//a[text()='View Profile']")) >= 50)
                
                # Scrape the links from the now-expanded page
                profile_link_elements = driver.find_elements(By.XPATH, "//a[text()='View Profile']")
                for link_element in profile_link_elements:
                    href = link_element.get_attribute('href')
                    if href:
                        all_unique_links.add(href)
                print(f"    - ✅ Success. Total unique links found so far: {len(all_unique_links)}")

            except Exception as e:
                print(f"    - ⚠️  Could not expand or scrape page {page_num}. Moving to next. Error: {e}")
                continue
        
        links_to_scrape = list(all_unique_links)
        
        # --- Stage 2: Scrape Individual Profiles ---
        if links_to_scrape:
            print(f"\n--- Scraping the first {ATHLETES_TO_SCRAPE} athlete profiles ---")
            
            output_csv_file = 'scraped_athletes_2025_M_251007.csv'
            
            # --- Initialize counters ---
            success_count = 0
            error_count = 0
            total_to_scrape = min(ATHLETES_TO_SCRAPE, len(links_to_scrape))

            for i, url in enumerate(links_to_scrape[:total_to_scrape]):
                stats = scrape_athlete_profile(driver, url)
                
                if stats:
                    # Convert the single athlete's data into a DataFrame
                    df_single_athlete = pd.DataFrame([stats])

                    # Check if the file already exists to decide on writing the header
                    write_header = not os.path.exists(output_csv_file)

                    # Append the data to the CSV file
                    df_single_athlete.to_csv(
                        output_csv_file, 
                        mode='a',          # 'a' stands for append mode
                        header=write_header, # Only write the header if the file is new
                        index=False
                    )
                    print(f"    - ✅ Saved {stats.get('name')} to CSV.")
                    success_count += 1
                else:
                    # This handles cases where scrape_athlete_profile returns None
                    error_count += 1
                
                # --- Print status update after each attempt ---
                print(f"    -> Progress: [{i + 1}/{total_to_scrape}] | Successes: {success_count} | Errors: {error_count}")
                
                time.sleep(1)
    finally:
        if driver:
            print("--- Closing browser ---")
            driver.quit()


    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n--- Total execution time: {duration:.2f} seconds ---")
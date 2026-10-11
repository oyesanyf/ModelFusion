import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_argument('--headless=new')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
options.add_argument('--window-size=1400,900')

driver = webdriver.Chrome(options=options)
try:
    url = "https://www.linkedin.com/jobs/view/staff-security-engineer-ai-at-linkedin-4425661803"
    print(f"Navigating to {url}...")
    driver.get(url)
    time.sleep(3)
    
    print(f"Page Title: {driver.title}")
    
    # Check buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"Total buttons found: {len(buttons)}")
    for b in buttons:
        text = b.text.strip()
        aria = b.get_attribute("aria-label") or ""
        cls = b.get_attribute("class") or ""
        if "apply" in text.lower() or "apply" in aria.lower() or "apply" in cls.lower():
            print(f"  [APPLY BUTTON] text='{text}', aria='{aria}', class='{cls[:50]}'")
            
    # Check links
    links = driver.find_elements(By.TAG_NAME, "a")
    for a in links:
        text = a.text.strip()
        href = a.get_attribute("href") or ""
        if "apply" in text.lower() or "apply" in href.lower():
            print(f"  [APPLY LINK] text='{text}', href='{href[:80]}'")
            
finally:
    driver.quit()

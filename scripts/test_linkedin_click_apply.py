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
    time.sleep(2)
    
    apply_btns = driver.find_elements(By.CSS_SELECTOR, "button.apply-button, .jobs-apply-button")
    if apply_btns:
        print("Clicking Apply button with JS click...")
        driver.execute_script("arguments[0].click();", apply_btns[-1])
        time.sleep(3)
        print("Current URL:", driver.current_url)
        print("Current Title:", driver.title)
        
        # Check inputs and modal
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal, [role='dialog'], .contextual-sign-in-modal")
        print(f"Modals count: {len(modals)}")
        for m in modals:
            text = m.text.strip()
            if text:
                print("Modal text:\n", text[:300])
                
        # Check sign in fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"Inputs count: {len(inputs)}")
        for inp in inputs:
            inp_type = inp.get_attribute("type")
            inp_name = inp.get_attribute("name") or inp.get_attribute("id") or inp.get_attribute("placeholder")
            print(f"  Input: type={inp_type}, name/id={inp_name}")
finally:
    driver.quit()

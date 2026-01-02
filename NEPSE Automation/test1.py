from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from openpyxl import Workbook

print("Step 1: Creating folder on Desktop...")
# Desktop pe folder banaye
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
folder_path = os.path.join(desktop, "NEPSE_Data")

if not os.path.exists(folder_path):
    os.makedirs(folder_path)
    print(f"✅ Folder created: {folder_path}")
else:
    print(f"✅ Folder already exists: {folder_path}")

print("Step 2: Opening browser and NEPSE website...")
# Browser start karo
driver = webdriver.Chrome()
driver.maximize_window()

# Direct NEPSE website pe jao
driver.get("https://www.nepalstock.com/")
time.sleep(3)

print("Step 3: Clicking NEPSE dropdown...")
# NEPSE dropdown click
driver.find_element(By.ID, "navbarDropdown").click()
time.sleep(2)

print("Step 4: Clicking N's Day Trading link...")
# N's Day link click
try:
    driver.find_element(By.XPATH, "/html/body/app-root/div/app-header/header/div[1]/div/nav/div/div/ul/li[2]/div/div[5]/a").click()
    print("✅ Clicked using full XPath")
except:
    try:
        driver.find_element(By.XPATH, "//a[contains(text(),'Trading Average Price')]").click()
        print("✅ Clicked using text search")
    except:
        driver.get("https://www.nepalstock.com/todaysprice")
        print("✅ Navigated directly")

time.sleep(3)

print("Step 5: Setting N's Day to 180...")
# N's Day set to 180
driver.find_element(By.ID, "nDays").clear()
driver.find_element(By.ID, "nDays").send_keys("180")
driver.find_element(By.ID, "nDays").send_keys(Keys.RETURN)
time.sleep(5)

print("Step 6: Setting items per page to 500...")
# Items per page 500 select karo
select_element = driver.find_element(By.TAG_NAME, "select")
dropdown = Select(select_element)
dropdown.select_by_visible_text("500")
time.sleep(5)

print("Step 7: Extracting data...")
# Data extract karo
headers = [th.text for th in driver.find_elements(By.TAG_NAME, "th")]
data_cells = [td.text for td in driver.find_elements(By.TAG_NAME, "td")]

print(f"✅ Found {len(headers)} headers and {len(data_cells)} data cells")

# Data organize karo
num_cols = len(headers)
rows = [data_cells[i:i + num_cols] for i in range(0, len(data_cells), num_cols)]

print(f"✅ Organized into {len(rows)} rows")

print("Step 8: Closing browser...")
# Browser band karo
driver.quit()

print("Step 9: Creating Excel file...")
# Excel save karo
wb = Workbook()
sheet = wb.active
sheet.title = "NEPSE Data"

sheet.append(headers)
for row in rows:
    sheet.append(row)

# File save karo desktop folder me
file_path = os.path.join(folder_path, "NEPSE_180days.xlsx")
wb.save(file_path)

print("\n" + "="*50)
print("✅ SUCCESS SUMMARY")
print("="*50)
print(f"✅ Folder location: {folder_path}")
print(f"✅ File saved as: NEPSE_180days.xlsx")
print(f"✅ Full path: {file_path}")
print(f"✅ Total headers: {len(headers)}")
print(f"✅ Total rows saved: {len(rows)}")
print("="*50)

# Folder open karne ke liye (Windows)
try:
    os.startfile(folder_path)
    print("✅ Folder opened automatically!")
except:
    print("⚠️ Could not open folder automatically")

print("\n🎉 Script completed successfully!")
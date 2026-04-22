from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
options=Options()
options.chrome_executable_path="/Users/charles/Desktop/Python_training/chromedriver-mac-x64/chromedriver"
driver=webdriver.Chrome(options=options)
driver.maximize_window()
driver.get("https://www.linkedin.com/jobs/search?trk=guest_homepage-basic_guest_nav_menu_jobs&original_referer=https%3A%2F%2Fwww.linkedin.com%2F&position=1&pageNum=0")

n=0
while n<3 :
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    n+=1 

titletags=driver.find_elements(By.CLASS_NAME,"base-search-card__title")
for tag in titletags: 
    print(tag.text)


driver.close()

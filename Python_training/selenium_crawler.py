from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
options=Options()
options.chrome_executable_path="/Users/charles/Desktop/Python_training/chromedriver-mac-x64/chromedriver"
driver=webdriver.Chrome(options=options)
driver.maximize_window()
driver.get("https://www.ptt.cc/bbs/Stock/index.html")
tags=driver.find_elements(By.CLASS_NAME,"title")
for tag in tags: 
    print(tag.text)
Link=driver.find_elements(By.LINK_TEXT,"‹ 上頁")
Link.click()
tags=driver.find_elements(By.CLASS_NAME,"title")
for tag in tags: 
    print(tag.text)

driver.close()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
options=Options()
options.chrome_executable_path="/Users/charles/Desktop/Python_training/chromedriver-mac-x64/chromedriver"
driver=webdriver.Chrome(options=options)
driver.maximize_window()
driver.get("https://www.google.com")
driver.close()

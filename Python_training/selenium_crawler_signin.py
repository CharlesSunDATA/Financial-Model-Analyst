from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
options=Options()
options.chrome_executable_path="/Users/charles/Desktop/Python_training/chromedriver-mac-x64/chromedriver"
driver=webdriver.Chrome(options=options)
driver.maximize_window()
driver.get("https://leetcode.com/accounts/login/")
time.sleep(10)
usernamelogin=driver.find_element(By.ID,"id_login")
passwordlogin=driver.find_element(By.ID,"id_password")
usernamelogin.send_keys("zerokingxiii")
passwordlogin.send_keys("Apple9097@")
signinbtn=driver.find_element(By.ID,"signin_btn")
time.sleep(3)
signinbtn.send_keys(Keys.ENTER)
time.sleep(5)
driver.get("https://leetcode.com/problemset/")
time.sleep(5)
scoreelement=driver.find_element(By.CSS_SELECTOR,"[data-difficulty=TOTAL]")
colums=scoreelement.text.split("\n")
print(colums[1])
driver.close()

#
print(scoreelement.text)






#driver.close()

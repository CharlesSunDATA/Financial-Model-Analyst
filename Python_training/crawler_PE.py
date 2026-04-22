import urllib.request as req
import ssl
from bs4 import BeautifulSoup
import gspread

# 设置 URL
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
url = "https://stockanalysis.com/stocks/nvda/statistics/"


request = req.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
})

# 发送 GET 请求
with req.urlopen(request, context=context) as response:
    data = response.read().decode("utf-8")

# 检查响应是否成功

    # 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(data, 'html.parser')


    # 查找 PE Ratio 的元素
forward_pe_tag = soup.find_all(string="Forward PE")
print(forward_pe_tag.string)
#print(forward_pe_tag.string)
#forward_pe_tag2=forward_pe_tag.find_next()
#forward_pe_tag3=forward_pe_tag2.find_next()
#print(forward_pe_tag," : ",forward_pe_tag2.string)



        
        # 设置 Google Sheets 凭证
gc = gspread.service_account(filename='/Users/charles/Desktop/Python_training/Json/alert-cedar-419523-21be939107a8.json')

        # 授权访问 Google Sheets
sh = gc.open("python import")
worksheet = sh.sheet1
        
        # 将数据写入指定的单元格范围
worksheet.update('A1', [[forward_pe_tag.string,forward_pe_tag2.string]])
#worksheet.update('B1', [[forward_pe_tag3]])

    #else:
        #print("PE Ratio not found on the webpage.")
#else:
    #print("Failed to retrieve data from the URL.")



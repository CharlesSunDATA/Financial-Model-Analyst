# import urllib.request as request
# import json
# src="https://data.taipei/api/v1/dataset/296acfa2-5d93-4706-ad58-e83cc951863c?scope=resourceAquire"
# with request.urlopen(src) as response:
#     data = json.read(response)
# print(data)


import json
from urllib import request
import ssl

# 创建未验证的 SSL 上下文
context = ssl._create_unverified_context()

src = "https://data.taipei/api/v1/dataset/296acfa2-5d93-4706-ad58-e83cc951863c?scope=resourceAquire"

try:
    with request.urlopen(src, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))
    clist=data["result"]["results"]
    with open ("data.txt","w",encoding="utf-8") as file:
        for company in clist:
            file.write(company["公司名稱"]+"\n")
        #print("name:", data.get("name"))
        #print("version:", data.get("version"))
except Exception as e:
    print("Error:", e)


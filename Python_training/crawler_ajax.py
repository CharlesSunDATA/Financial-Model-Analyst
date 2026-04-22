# import urllib.request as req
# url="https://www.ptt.cc/bbs/movie/index1.html"
# request=req.Request(url,headers={
#     "User-Agenr":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
#     })
# with req.urlopen(request) as response:
#     data=response.read().decode("utf-8")
# print(data)

import json
import urllib.request as req
import ssl

# 创建不验证 SSL 证书的上下文
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

url = "https://medium.com/_/api/home-feed"


request = req.Request(url,headers={
"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
})
with req.urlopen(request, context=context) as response:
    data = response.read().decode("utf-8")


#json

data=data.replace("XXXXXXXX","")
data=json.load(data)
posts=data["payload"]["reference"]["post"]
for key in posts:
    post=posts[key]
    print(post["title"])




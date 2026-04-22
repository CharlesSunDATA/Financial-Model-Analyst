
import json
import urllib.request as req
import ssl

def getData(url):
    # 创建不验证 SSL 证书的上下文
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    


    request = req.Request(url,headers={
        "Cookie":"over18=1",
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    })
    with req.urlopen(request, context=context) as response:
        data = response.read().decode("utf-8")

    import bs4
    root=bs4.BeautifulSoup(data,"html.parser")
    #print(root.title.string)
    titles=root.find_all("div",class_="title")
    # for title in titles:
    #     if title.a !=None:
            #print(title.a.string)

    with open("data.txt",mode="w",encoding="utf-8") as file:
        for title in titles:
            if title.a !=None:
                file.write(title.a.string + "\n")
    nextLink=root.find("a",string="‹ 上頁") #找到內文的文字
    return nextLink["href"]
pageurl = "https://www.ptt.cc/bbs/Gossiping/index.html"

count=0
while count<3:
    pageurl="https://www.ptt.cc"+getData(pageurl)
    count+=1
    print(pageurl)

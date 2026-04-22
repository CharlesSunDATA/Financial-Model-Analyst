# with open("data.txt",mode="w",encoding="utf-8") as file:
#     file.write("5\n 3")
# sum=0
# with open("data.txt",mode="r",encoding="utf-8") as file:
#     for line in file:
#         sum+=int(line)
# print(sum)

import json
with open("config.json",mode="r") as file:
    data=json.load(file)
print("name",data["name"])
print("version",data["version"])




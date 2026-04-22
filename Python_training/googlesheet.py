import gspread
#from google.oauth2.service_account import Credentials

# 設置 API 凭證
#scopes = ['https://www.googleapis.com/auth/spreadsheets']
#credentials = Credentials.from_service_account_file('/Users/charles/Desktop/Python_training/Json/googlesheet.json', scopes=scopes)

# 授權訪問 Google Sheets
#client = gspread.authorize(credentials)

# 打開 Google Sheets 文檔（需要提前創建）
sa =gspread.service_account()
sh = sa.open("python import")


#sheet = client.open('python import').sheet1
worksheet = sh.sheet1
# 準備要寫入的數據
data = [
    ['Name', 'Age'],
    ['Alice', 30],
    ['Bob', 25],
    ['Charlie', 35]
]

# 將數據寫入指定的單元格範圍
worksheet.update('A1:B4', data)


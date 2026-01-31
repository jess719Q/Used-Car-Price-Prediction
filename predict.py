import sqlite3
from tabulate import tabulate
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from sklearn.neighbors import KNeighborsRegressor
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, MaxNLocator
import time
from matplotlib import rcParams

rcParams['font.family'] = 'Microsoft YaHei'  # 設定中文字型

# 連接到 SQLite 數據庫
conn = sqlite3.connect('C:/Users/fang/Desktop/hwww/113-1/Database/final/car_data.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM car_brands ORDER BY brand_name')
rows = cursor.fetchall()

brand_list = []
for row in rows:
    brand_list.append(f"{row[0]:<3d} {row[1]}")
brand_list = [brand_list[i:i + 4] for i in range(0, len(brand_list), 4)]
brand_table= tabulate(brand_list, tablefmt="grid")


# 設置 Chrome 無頭模式
chrome_options = Options()
chrome_options.add_argument("--headless")         # 啟用無頭模式
chrome_options.add_argument("--disable-gpu")      # 禁用 GPU 加速，提升兼容性
chrome_options.add_argument("--no-sandbox")       # 適用於某些 Linux 環境
chrome_options.add_argument("--disable-logging")  # 禁用日誌
chrome_options.add_argument("--log-level=3")      # 禁止一些非錯誤信息
chrome_options.add_argument('blink-settings=imagesEnabled=false') # 禁用圖片加載
chrome_options.page_load_strategy="eager"         # 頁面結構和JS腳本下載完成即開始交互

cmap = plt.get_cmap('plasma')

def fitModel(X_train, y_train):
    knn_model = KNeighborsRegressor(n_neighbors=3,weights="distance")
    knn_model.fit(X_train, y_train)
    return knn_model

def get_data(brand,series):
    # 初始化 WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    # 打開網站
    url = f"https://www.hotcar.com.tw/UsedCarSell/CarFilter?vBrand={brand}&vCarSeries={series}"
    i=1

    price_list = []
    year = []
    mileage = []
    while True:
        driver.get(url)
        num=driver.find_element(By.CLASS_NAME, "txtRed")
        if(int(num.text)<=0):
            break

        for result_info in ["sResult1","sResult2"]:
            result=driver.find_element(By.ID, result_info)
            cars=result.find_elements(By.CLASS_NAME, "dataBox")

            for car in cars:
                price_info = car.find_element(By.CLASS_NAME, "price")
                try:
                    price = price_info.find_element(By.CSS_SELECTOR, "b")
                    price_float = float(price.text.replace("萬", ""))
                    if(price_float>1000):
                        continue
                    price_list.append(price_float)
                except:
                    continue
                
                datas = car.find_element(By.CLASS_NAME, "secInfo")
                datas2 = datas.find_elements(By.CSS_SELECTOR, "span")
                year.append(int(datas2[0].text.replace("年", "")))
                if "英里" in datas2[1].text:
                    mileage.append(int(datas2[1].text.replace(",", "").replace("英里", ""))*1.609344)
                else:
                    mileage.append(int(datas2[1].text.replace(",", "").replace("公里", "")))
        i+=1
        
        url=f"https://www.hotcar.com.tw/UsedCarSell/CarFilter?vBrand={brand}&vCarSeries={series}&pageNo={i}"
    
    driver.quit()
    
    return ([year,mileage],price_list)

def predict_price(x,y):
    print("fitting the model...")
    min_year = min(x[0])
    range_year = max(x[0])-min_year
    min_mileage = min(x[1])
    range_mileage = max(x[1])-min_mileage
    
    nor_x = [ [(year - min_year) / range_year, (mileage - min_mileage) / range_mileage]
                for year, mileage in zip(x[0], x[1])]
    model = fitModel(nor_x,y)
    
    print("start prediction")
    
    cont=True
    while cont:
        try:
            y1 = int(input("Year of production: "))
            if y1 < 1900 or y1 > 2025:
                raise ValueError("Invalid year.")
            m1 = int(input("Mileage(km): "))
            if m1 < 0:
                raise ValueError("Invalid mileage.")
            result= model.predict([[(y1- min_year) / range_year , (m1- min_mileage) / range_mileage]])
            print(f"Recommended price: {result[0]:.2f}萬元")
            
            # plt.figure(figsize=(6, 6))
            plt.scatter(y1, m1,c=result[0],marker="*",s=70, cmap=cmap, vmin=min(y), vmax=max(y), label=f"prediction: {result[0]:.2f}萬元")
            plt.scatter(x[0], x[1], c=y, s=35,cmap=cmap, vmin=min(y), vmax=max(y))
            plt.colorbar()
            plt.title(f"The distrubution of {series_list[select_series][0]}")
            plt.ylabel("mileage (km)")
            plt.xlabel("production year")
            plt.rcParams["xtick.direction"]="in"
            plt.rcParams["ytick.direction"]="in"
            plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
            plt.gca().yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
            plt.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
            plt.legend()
            plt.show()
            
            while 1:
                print(f"continue predictinog in {series_list[select_series][0]} ? (y/n)")
                ans = input()
                if ans=="y":
                    break
                elif ans=="n":
                    cont=False
                    break
        
        except Exception as e:
            print(f"Invalid input: {e}")

while True:
    print(f'select the Brand \033[90m{"(input [show] to see the brand table, or [end] to leave)"}\033[0m')
    select_brand = input()
    
    if(select_brand=="show"):
        print(brand_table)
        continue
    elif(select_brand=="end"):
        break
    
    try:
        select_brand = int(select_brand)
        cursor.execute(f'SELECT brand_name FROM car_brands where id={select_brand}')
        select_brand_name = cursor.fetchone()[0]
        if select_brand_name==None:
            print("no such brand")
            continue
        
        print(f"select the series from {select_brand_name}")
        cursor.execute(f'SELECT series_name FROM car_series where brand_id={select_brand}')
        series_list = cursor.fetchall()
        series_toPrint = [f"{i} {series_list[i][0]}" for i in range(0, len(series_list))]
        series_toPrint = [series_toPrint[i:i + 8] for i in range(0, len(series_toPrint), 8)]
        print(tabulate(series_toPrint, tablefmt="grid"))
        
        select_series = int(input())
        
        st = time.time()
        print(f"searching datas for {select_brand_name} {series_list[select_series][0]} car series...")
        x,y = get_data(select_brand, series_list[select_series][0])
        et = time.time()
        print(f"take {et-st:.2f} seconds")

        if(len(y)<5):
            print("The size of the data set is too small (<5) to fit, please try another series")
            continue
        
        predict_price(x,y)


    except Exception as e:
        print("Invalid input:", e)
        continue

conn.close()
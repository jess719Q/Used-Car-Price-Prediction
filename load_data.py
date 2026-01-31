from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import sqlite3

# =========================
# SQLite 設定
# =========================
conn = sqlite3.connect('car_data.db')
cur = conn.cursor()

# 清空資料表
cur.execute("DELETE FROM car_brands;")
cur.execute("DELETE FROM car_series;")
conn.commit()

# =========================
# ChromeDriver 設定 (隱藏 USB log)
# =========================
from selenium.webdriver.chrome.options import Options
chrome_options = Options()
chrome_options.add_argument("--log-level=3")  # 僅顯示嚴重錯誤
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

url = "https://www.hotcar.com.tw/"
driver.get(url)
time.sleep(1)

wait = WebDriverWait(driver, 10)  # 最多等 10 秒

# =========================
# 爬取品牌與車系
# =========================
try:
    brand_dropdown = wait.until(
        EC.presence_of_element_located((By.ID, "form-horizontal-select"))
    )
    brand_count = len(brand_dropdown.find_elements(By.TAG_NAME, "option"))

    MAX_RETRY = 5  # 每個品牌最多重試次數
    prev_first_car = None  # 上一品牌的第一個車系

    for i in range(brand_count):
        retry = 0
        while retry < MAX_RETRY:
            try:
                # 每輪都重新抓元素，避免 stale
                brand_dropdown = wait.until(
                    EC.presence_of_element_located((By.ID, "form-horizontal-select"))
                )
                brand_options = brand_dropdown.find_elements(By.TAG_NAME, "option")
                option = brand_options[i]

                brand_name = option.text.strip()
                if not brand_name or brand_name == "請選擇":
                    break

                brand_id = option.get_attribute("value")
                print(f"Brand: {brand_name} value:{brand_id}")
                cur.execute(f"INSERT OR IGNORE INTO car_brands VALUES({brand_id},'{brand_name}')")

                # 點擊品牌
                option.click()

                # 等車系 select 更新，並確保抓到對應品牌車系
                for _ in range(20):  # 最多重試 20 次
                    car_select = driver.find_elements(By.CLASS_NAME, "uk-select")[1]
                    car_type_options = [o for o in car_select.find_elements(By.TAG_NAME, "option") if o.text.strip() != "請選擇"]
                    if car_type_options:
                        first_car = car_type_options[0].text.strip()
                        if first_car != prev_first_car:
                            prev_first_car = first_car
                            break
                    time.sleep(0.2)
                else:
                    # 若 20 次還沒更新，跳過
                    print(f"Warning: car series for brand {brand_name} may not be updated correctly")

                # 抓車系
                for car_option in car_type_options:
                    car_type = car_option.text.strip()
                    if car_type and car_type != "請選擇":
                        print(f"  Car Type: {car_type}")
                        cur.execute(f'INSERT OR IGNORE INTO car_series VALUES({brand_id},"{car_type}")')

                break  # 成功抓到品牌車系，跳出 retry

            except Exception as e:
                print(f"Retry {retry+1} for brand index {i} due to error: {e}")
                time.sleep(0.3)
                retry += 1

        # 回到品牌下拉準備下一輪
        try:
            brand_dropdown = wait.until(
                EC.presence_of_element_located((By.ID, "form-horizontal-select"))
            )
            brand_dropdown.click()
            time.sleep(0.1)
        except Exception as e:
            print(f"Warning: unable to click brand dropdown for next iteration: {e}")

except Exception as e:
    print("Error in main loop:", e)

finally:
    driver.quit()
    conn.commit()
    conn.close()

print("\nDone.")

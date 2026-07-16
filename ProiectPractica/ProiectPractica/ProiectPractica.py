import time
import re
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("bot pornit")


def selecteaza_data(driver, data_str):

    zi, luna, an = data_str.split(".")
    zi = str(int(zi))             
    luna_idx = str(int(luna) - 1)
    an = str(int(an))

    wait = WebDriverWait(driver, 10)


    camp_data = wait.until(EC.element_to_be_clickable((By.ID, "input-date-departure")))
    camp_data.click()
    time.sleep(0.5)

    for _ in range(36):
        zile_luna_dorita = driver.find_elements(
            By.XPATH,
            f'//table[contains(@class, "ui-datepicker-calendar")]'
            f'//td[@data-month="{luna_idx}" and @data-year="{an}"]/a'
        )
        if zile_luna_dorita:
            break
        buton_next = driver.find_element(By.CLASS_NAME, "ui-datepicker-next")
        driver.execute_script("arguments[0].click();", buton_next)  
        time.sleep(0.3)
    else:
        raise Exception(f"Nu am gasit luna {luna}/{an} in calendar dupa 36 de incercari")

    zi_element = driver.find_element(
        By.XPATH,
        f'//table[contains(@class, "ui-datepicker-calendar")]'
        f'//td[@data-month="{luna_idx}" and @data-year="{an}"]/a[@data-date="{zi}"]'
    )
    driver.execute_script("arguments[0].click();", zi_element)
    time.sleep(0.5)


def citeste_parametri():
    plecare = input("Statie de plecare: ").strip()
    while not plecare:
        plecare = input("Gol").strip()

    sosire = input("Statie de destinatie: ").strip()
    while not sosire:
        sosire = input("Gol").strip()

    data_input = input(
        "Data calatorie (format ZZ.LL.AAAA, sau 'azi' / 'maine'): "
    ).strip().lower()

    if data_input in ("azi"):
        data_calatorie = datetime.now().strftime("%d.%m.%Y")
    elif data_input in ("maine"):
        data_calatorie = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    else:
        while not re.match(r"^\d{2}\.\d{2}\.\d{4}$", data_input):
            data_input = input(
                "Pune bre corect"
            ).strip().lower()
        data_calatorie = data_input

    print(f"\nCauta: {plecare} -> {sosire}, data {data_calatorie}\n")

    return {"plecare": plecare, "sosire": sosire, "data": data_calatorie}


parametri = citeste_parametri()

driver = uc.Chrome(version_main=150)
driver.maximize_window()
actions = ActionChains(driver)

# momentan cfr; selectare dupa transport dorit SAU cautam toate site-urile
try:
    driver.get("https://www.google.com")
    time.sleep(5)
    try:
        buton_cookie = driver.find_element(By.XPATH, '//button[contains(., "Acceptă tot")]')
        buton_cookie.click()
        time.sleep(5)
    except Exception:
        print("nu a aparut")

    cautare = driver.find_element(By.NAME, "q")
    print("scrie in search bar")
    cautare.send_keys("CFR Calatori")
    cautare.send_keys(Keys.RETURN)
    time.sleep(5)

    try:
        first_res = driver.find_element(By.XPATH, '//a//h3')
        first_res.click()
        print("accesare site")
        time.sleep(5)
    except Exception:
        print("aia e nu merge(da o sa mearga)")

    try:
        buton_plecare = driver.find_element(By.XPATH, '//input[@placeholder="Stație de plecare"]')
        buton_plecare.send_keys(parametri["plecare"])
        time.sleep(1.5)
        buton_plecare.send_keys(Keys.ARROW_DOWN)
        buton_plecare.send_keys(Keys.ENTER)  # scrape pe lista de rezultate si selectare dupa statia dorita?
        time.sleep(5)

        buton_sosire = driver.find_element(By.XPATH, '//input[@placeholder="Stație de sosire"]')
        buton_sosire.send_keys(parametri["sosire"])
        time.sleep(1.5)
        buton_sosire.send_keys(Keys.ARROW_DOWN)
        buton_sosire.send_keys(Keys.ENTER)  # si aici tot asa
        time.sleep(1.5)

        try:
            selecteaza_data(driver, parametri["data"])
            print(f"data: {parametri['data']}")
        except Exception as e:
            print("ce data ai pus bre", e)

        actions.send_keys(Keys.ENTER).perform()
        print("introdus datele")
        time.sleep(6.5)
    except Exception as e:
        print("nu asa se face", e)

    try:
        time.sleep(5)
        trenuri = driver.find_elements(By.XPATH, '//div[contains(@class, "div-itineraries-row-main")]')
        print(f"Detectat {len(trenuri)} plecari")
        for index, tren in enumerate(trenuri, start=1):
            try:
                try:
                    id_tren = tren.find_element(By.XPATH, './/a[contains(@href, "Tren")]').text
                    id_tren = id_tren.strip().replace('\n', ' ')
                except Exception:
                    continue
                try:
                    ora_plecare = tren.find_element(By.XPATH, '(.//span[contains(@class, "text-1-4rem")])[1]').text
                except Exception:
                    ora_plecare = "unde-i?"
                try:
                    ora_sosire = tren.find_element(
                        By.XPATH, '(.//span[contains(@class, "text-1-4rem")])[2]'
                    ).get_attribute("textContent")
                except Exception:
                    ora_sosire = "unde-i?"
                print(f"{index}: Tren: {id_tren}")
                print(f"Plecare: {ora_plecare.strip()} | Sosire: {ora_sosire.strip()}")
            except Exception as e:
                print(f"nuh uh tren{index}: {e}")
    except Exception:
        print("ceva nu-i bun")
finally:
    driver.quit()
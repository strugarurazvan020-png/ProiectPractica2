import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

print("bot pornit")

driver = uc.Chrome()
driver.maximize_window()
actions = ActionChains(driver)
#momentan cfr; selectare dupa transport dorit SAU cautam toate site-urile scrape pt fiecare mod de transport si afisare date dorite
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
        buton_plecare.send_keys("Bucuresti Nord") 
        time.sleep(1.5)
        buton_plecare.send_keys(Keys.ARROW_DOWN)
        buton_plecare.send_keys(Keys.ENTER)     #scrape pe lista de rezultate si apoi selectarea dupa statia dorita?
        time.sleep(5)
        buton_sosire = driver.find_element(By.XPATH, '//input[@placeholder="Stație de sosire"]')
        buton_sosire.send_keys("Suceava")
        time.sleep(1.5)
        buton_sosire.send_keys(Keys.ARROW_DOWN)
        buton_sosire.send_keys(Keys.ENTER)      #si aici tot asa
        time.sleep(1.5)
        actions.send_keys(Keys.ENTER).perform()
        print("introdus datele")
        time.sleep(6.5)
    except Exception as e:
        print("nu asa se face",e)


    try:
        time.sleep(5)
        trenuri = driver.find_elements(By.XPATH, '//div[contains(@class, "div-itineraries-row-main")]')
        print(f"Detectat {len(trenuri)} plecari")

        for index, tren in enumerate(trenuri, start = 1):
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
                    ora_sosire = tren.find_element(By.XPATH, '(.//span[contains(@class, "text-1-4rem")])[2]').get_attribute("textContent")
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
import time
import re
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    plecare = input("Statie de plecare (ex: Bucuresti Nord): ").strip()
    while not plecare:
        plecare = input("Nu poate fi gol. Statie de plecare: ").strip()

    sosire = input("Statie de destinatie (ex: Suceava): ").strip()
    while not sosire:
        sosire = input("Nu poate fi gol. Statie de destinatie: ").strip()

    data_input = input("Data calatoriei (format ZZ.LL.AAAA, sau 'azi' / 'maine'): ").strip().lower()

    if data_input in ("azi", "astazi"):
        data_calatorie = datetime.now().strftime("%d.%m.%Y")
    elif data_input in ("maine", "mâine"):
        data_calatorie = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    else:
        while not re.match(r"^\d{2}\.\d{2}\.\d{4}$", data_input):
            data_input = input("Format invalid. Foloseste ZZ.LL.AAAA (ex: 20.07.2026): ").strip().lower()
        data_calatorie = data_input

    print()
    return {"plecare": plecare, "sosire": sosire, "data": data_calatorie}


def nume_oras_pentru_avion(statie_tren):
    sufixe = ["Nord", "Sud", "Est", "Vest", "Centrala", "Calatori", "Triaj", "Vama"]
    cuvinte = statie_tren.strip().split()
    while len(cuvinte) > 1 and cuvinte[-1] in sufixe:
        cuvinte.pop()
    return " ".join(cuvinte)


def verifica_disponibilitate(tren_element, n):
    try:
        buton_cumpara = tren_element.find_element(By.ID, f"button-itinerary-{n}-buy")
    except Exception:
        return "Epuizat/indisponibil"

    dezactivat = (
        buton_cumpara.get_attribute("disabled") is not None
        or buton_cumpara.get_attribute("aria-disabled") == "true"
        or "disabled" in (buton_cumpara.get_attribute("class") or "")
    )
    return "Epuizat" if dezactivat else "Disponibil"


def extrage_pret(driver, tren_element, wait, n):
    try:
        buton_detalii = driver.find_element(By.ID, f"button-itinerary-{n}-details")
        driver.execute_script("arguments[0].click();", buton_detalii)
        time.sleep(1)

        buton_fares = wait.until(EC.element_to_be_clickable((By.ID, f"button-itinerary-{n}-fares")))
        driver.execute_script("arguments[0].click();", buton_fares)
        time.sleep(1)

        buton_calc = wait.until(EC.element_to_be_clickable((By.ID, f"button-calculate-fare-itinerary-{n}")))
        driver.execute_script("arguments[0].click();", buton_calc)

        rezultat_div = wait.until(EC.presence_of_element_located((By.ID, f"div-fare-result-itinerary-{n}")))
        pret_element = WebDriverWait(driver, 10).until(
            lambda d: rezultat_div.find_element(By.TAG_NAME, "strong")
            if rezultat_div.find_element(By.TAG_NAME, "strong").text.strip()
            else False
        )
        return pret_element.text.strip()
    except Exception:
        return None


LUNI_RO_CALENDAR = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]

def selecteaza_doar_dus(driver, wait):
    eticheta_tip_zbor = wait.until(EC.presence_of_element_located((By.XPATH, '//label[contains(text(), "Tip zbor")]')))
    id_eticheta = eticheta_tip_zbor.get_attribute("id")
    buton_tip_zbor = wait.until(EC.element_to_be_clickable((By.XPATH, f'//button[contains(@aria-labelledby, "{id_eticheta}")]')))
    driver.execute_script("arguments[0].click();", buton_tip_zbor)

    id_listbox = buton_tip_zbor.get_attribute("aria-controls")
    wait.until(EC.visibility_of_element_located((By.ID, id_listbox)))
    time.sleep(0.3)

    optiune_doar_dus = wait.until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="{id_listbox}"]//*[@role="option" and contains(., "Doar dus")]')))
    driver.execute_script("arguments[0].click();", optiune_doar_dus)
    wait.until(lambda d: "Doar dus" in buton_tip_zbor.text)
    time.sleep(0.5)


def introdu_statie(driver, wait, eticheta_camp, valoare):
    container = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        f'//div[contains(@class, "city-helper-trigger")]'
        f'[.//div[contains(@class, "search-form-label") and normalize-space(text())="{eticheta_camp}"]]'
    )))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
    driver.execute_script("arguments[0].click();", container)
    time.sleep(0.5)

    input_camp = wait.until(
        lambda d: next(
            (el for el in d.find_elements(By.CSS_SELECTOR, 'input[data-testid="city-helper-input"]') if el.is_displayed()),
            False
        )
    )
    input_camp.send_keys(Keys.CONTROL, "a")
    input_camp.send_keys(Keys.DELETE)
    time.sleep(0.3)
    input_camp.send_keys(valoare)
    time.sleep(1.5)
    input_camp.send_keys(Keys.ARROW_DOWN)
    time.sleep(0.3)
    input_camp.send_keys(Keys.ENTER)
    time.sleep(0.5)


def selecteaza_data_vola(driver, wait, data_str):
    zi, luna, an = data_str.split(".")
    zi = str(int(zi))
    luna_nume = LUNI_RO_CALENDAR[int(luna) - 1]
    an = str(int(an))
    text_cautat = f"{luna_nume} {zi}, {an}"

    buton_data = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@id, "date-picker-trigger-btn")]')))
    driver.execute_script("arguments[0].click();", buton_data)
    time.sleep(1)

    try:
        tab_data = driver.find_element(By.XPATH, '//*[self::button or self::div][normalize-space(text())="Date"]')
        driver.execute_script("arguments[0].click();", tab_data)
        time.sleep(0.3)
    except Exception:
        pass

    zi_gasita = False
    for _ in range(12):
        zile = driver.find_elements(By.XPATH, f'//div[contains(@class, "calendar-month__date-day") and contains(@aria-label, "{text_cautat}")]')
        if zile:
            driver.execute_script("arguments[0].click();", zile[0])
            zi_gasita = True
            break
        try:
            sageti = driver.find_elements(By.CSS_SELECTOR, "button.calendar-nav_btn")
            driver.execute_script("arguments[0].click();", sageti[-1])
            time.sleep(0.5)
        except Exception:
            break

    if not zi_gasita:
        raise Exception(f"Nu am gasit data '{text_cautat}' in calendarul Vola")
    time.sleep(0.5)


def apasa_cauta_vola(driver, wait):
    butoane = wait.until(lambda d: [b for b in d.find_elements(By.CSS_SELECTOR, '[data-testid="search-flight-btn"]') if b.is_displayed()] or False)
    driver.execute_script("arguments[0].click();", butoane[0])
    time.sleep(3)


def inchide_modal_upsell(driver, wait):
    try:
        buton_inchide = WebDriverWait(driver, 6).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="modal-go-back-icon-btn"]')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", buton_inchide)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", buton_inchide)
        time.sleep(0.5)
    except Exception:
        pass


def extrage_zboruri_vola(driver):
    rezultate = []
    try:
        WebDriverWait(driver, 35).until(EC.presence_of_element_located((By.CLASS_NAME, 'flight-card')))
        time.sleep(2)
    except Exception:
        return rezultate

    carduri = driver.find_elements(By.CLASS_NAME, 'flight-card')

    for card in carduri:
        try:
            elemente_text = card.find_elements(By.XPATH, './/span | .//div')
            ore = []
            for el in elemente_text:
                text = el.text.strip()
                if re.match(r'^\d{2}:\d{2}$', text):
                    if text not in ore:
                        ore.append(text)

            ora_plecare = ore[0] if len(ore) > 0 else "?"
            ora_sosire = ore[1] if len(ore) > 1 else "?"

            pret = "?"
            try:
                elemente_cu_aria = card.find_elements(By.XPATH, './/*[contains(@aria-label, "ofertă") or contains(@aria-label, "oferta") or contains(@aria-label, "zbor")]')
                for el in elemente_cu_aria:
                    label = el.get_attribute("aria-label")
                    if label and ("ofertă" in label.lower() or "oferta" in label.lower()):
                        label_curat = label.replace('\xa0', ' ')
                        cautare_pret = re.search(r'(\d+)\s*€', label_curat)
                        if cautare_pret:
                            pret = f"{cautare_pret.group(1)} €"
                            break

                if pret == "?":
                    text_complet_card = card.get_attribute("innerText").replace('\xa0', ' ')
                    linii = text_complet_card.split('\n')
                    linii_cu_euro = [l.strip() for l in linii if '€' in l]
                    if linii_cu_euro:
                        cautare_bruta = re.search(r'(\d+)\s*€', linii_cu_euro[-1])
                        if cautare_bruta:
                            pret = f"{cautare_bruta.group(1)} €"
                        else:
                            pret = linii_cu_euro[-1]
            except Exception:
                pass

            rezultate.append({
                "plecare": ora_plecare,
                "sosire": ora_sosire,
                "pret": pret,
            })
        except Exception:
            continue

    return rezultate


def scrape_vola(driver, plecare, sosire, data_str):
    wait = WebDriverWait(driver, 15)
    driver.get("https://www.vola.ro")
    time.sleep(3)

    try:
        buton_cookie = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//button[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZĂÂÎȘȚ", "abcdefghijklmnopqrstuvwxyzăâîșț"), "permite toate") '
            'or contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZĂÂÎȘȚ", "abcdefghijklmnopqrstuvwxyzăâîșț"), "accept")]'
        )))
        driver.execute_script("arguments[0].click();", buton_cookie)
        time.sleep(2)
    except Exception:
        pass

    try:
        selecteaza_doar_dus(driver, wait)
        time.sleep(1)
    except Exception:
        pass

    try:
        introdu_statie(driver, wait, "Din", plecare)
        introdu_statie(driver, wait, "Către", sosire)
    except Exception:
        pass

    try:
        selecteaza_data_vola(driver, wait, data_str)
    except Exception:
        pass

    try:
        apasa_cauta_vola(driver, wait)
    except Exception:
        pass

    inchide_modal_upsell(driver, wait)
    time.sleep(1)
    return extrage_zboruri_vola(driver)


def scrape_flixbus(driver, plecare, sosire, data_str):
    rezultate = []
    wait = WebDriverWait(driver, 15)

    driver.get("https://shop.flixbus.ro/search")
    time.sleep(3)

    try:
        script_cookie = """
            let host = document.querySelector('#usercentrics-cmp-ui') || document.querySelector('div[id*="usercentrics"]');
            if (host && host.shadowRoot) {
                let btn = host.shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]') || 
                          host.shadowRoot.querySelector('#uc-btn-accept-banner') ||
                          host.shadowRoot.querySelector('button.uc-btn-accept-all');
                if (btn) {
                    btn.click();
                    return true;
                }
            }
            return false;
        """
        for _ in range(5):
            if driver.execute_script(script_cookie):
                time.sleep(1.5)
                break
            time.sleep(1)
    except Exception:
        pass

    try:
        input_plecare = wait.until(EC.element_to_be_clickable((By.ID, "searchInput-from")))
        input_plecare.click()
        time.sleep(0.5)
        input_plecare.send_keys(Keys.CONTROL, "a")
        input_plecare.send_keys(Keys.DELETE)
        input_plecare.send_keys(plecare)
        time.sleep(1.5)
        input_plecare.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        input_plecare.send_keys(Keys.ENTER)
        time.sleep(1)
    except Exception:
        pass

    try:
        input_sosire = wait.until(EC.element_to_be_clickable((By.ID, "searchInput-to")))
        input_sosire.click()
        time.sleep(0.5)
        input_sosire.send_keys(Keys.CONTROL, "a")
        input_sosire.send_keys(Keys.DELETE)
        input_sosire.send_keys(sosire)
        time.sleep(1.5)
        input_sosire.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        input_sosire.send_keys(Keys.ENTER)
        time.sleep(1)
    except Exception:
        pass

    try:
        zi = int(data_str.split(".")[0])
        camp_data = wait.until(EC.element_to_be_clickable((By.ID, "dateInput-from")))
        camp_data.click()
        time.sleep(1)

        zi_gasita = False
        for _ in range(12):
            butoane_zile = driver.find_elements(By.CSS_SELECTOR, 'button[class*="hcr-calendar__btn"]')
            for btn in butoane_zile:
                if btn.text.strip() == str(zi) and btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    zi_gasita = True
                    time.sleep(0.5)
                    break
            if zi_gasita:
                break
            try:
                btn_next = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Show next month"]')
                driver.execute_script("arguments[0].click();", btn_next)
                time.sleep(0.5)
            except Exception:
                break
    except Exception:
        pass

    try:
        url_initial = driver.current_url
        btn_cauta = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'div[data-e2e="search-button"] button')
        ))
        driver.execute_script("arguments[0].click();", btn_cauta)
        WebDriverWait(driver, 15).until(lambda d: d.current_url != url_initial or "search" in d.current_url.lower())
        time.sleep(4)
    except Exception:
        pass

    try:
        driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(2)

        try:
            curse_li = WebDriverWait(driver, 20).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, 'li[aria-posinset]') or False
            )
        except Exception:
            curse_li = driver.find_elements(By.CSS_SELECTOR, 'li[data-e2e="search-result-item"]')

        for index_cursa, cursa in enumerate(curse_li):
            try:
                ora_p = "?"
                ora_s = "?"
                pret = "?"

                try:
                    el_plecare = cursa.find_element(
                        By.CSS_SELECTOR, '[data-e2e="search-result-departure-time"] time'
                    )
                    ora_p = el_plecare.text.strip()
                except Exception:
                    pass

                try:
                    el_sosire = cursa.find_element(
                        By.CSS_SELECTOR, '[data-e2e="search-result-arrival-time"] time'
                    )
                    ora_s = el_sosire.text.strip()
                except Exception:
                    pass

                try:
                    el_buton_pret = cursa.find_element(By.CSS_SELECTOR, 'button[class*="priceBook"]')
                    pret = (el_buton_pret.get_attribute("aria-label") or "").replace('\xa0', ' ').strip()
                except Exception:
                    pass
                if not pret or pret == "?":
                    try:
                        el_pret = cursa.find_element(By.CSS_SELECTOR, '[data-e2e="search-result-prices"]')
                        pret = el_pret.text.replace('\xa0', ' ').strip()
                    except Exception:
                        pass

                txt = cursa.text.replace('\xa0', ' ')

                if (ora_p == "?" or pret == "?") and index_cursa < 2:
                    print(f"FlixBus DEBUG cursa {index_cursa}: lungime text = {len(txt)}, "
                          f"continut text (primele 300 caractere) = {txt[:300]!r}")

                if ora_p == "?" or ora_s == "?":
                    ore = re.findall(r'\b\d{1,2}:\d{2}(?:\s*[AP]M)?\b', txt, re.IGNORECASE)
                    if ora_p == "?":
                        ora_p = ore[0] if len(ore) > 0 else "?"
                    if ora_s == "?":
                        ora_s = ore[1] if len(ore) > 1 else "?"

                if pret == "?":
                    cautare_pret = re.search(r'([$€]\s*\d+(?:[\.,]\d+)?|\d+(?:[\.,]\d+)?\s*(?:lei|RON|€|\$))', txt, re.IGNORECASE)
                    pret = cautare_pret.group(0) if cautare_pret else "Indisponibil"

                rezultate.append({
                    "plecare": ora_p,
                    "sosire": ora_s,
                    "pret": pret
                })
            except Exception:
                continue
    except Exception:
        pass

    return rezultate


if __name__ == "__main__":
    parametri = citeste_parametri()

    chrome_options = uc.ChromeOptions()
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.notifications": 2,
    })

    driver = uc.Chrome(version_main=150, options=chrome_options, use_subprocess=True)
    driver.maximize_window()
    actions = ActionChains(driver)

    try:
        driver.get("https://www.google.com")
        time.sleep(3)
        try:
            buton_cookie = driver.find_element(By.XPATH, '//button[contains(., "Acceptă tot")]')
            buton_cookie.click()
            time.sleep(2)
        except Exception:
            pass

        cautare = driver.find_element(By.NAME, "q")
        cautare.send_keys("CFR Calatori")
        cautare.send_keys(Keys.RETURN)
        time.sleep(3)

        try:
            first_res = driver.find_element(By.XPATH, '//a//h3')
            first_res.click()
            time.sleep(5)
        except Exception:
            pass

        try:
            buton_plecare = driver.find_element(By.XPATH, '//input[@placeholder="Stație de plecare"]')
            buton_plecare.send_keys(parametri["plecare"])
            time.sleep(1.5)
            buton_plecare.send_keys(Keys.ARROW_DOWN)
            buton_plecare.send_keys(Keys.ENTER)
            time.sleep(2)

            buton_sosire = driver.find_element(By.XPATH, '//input[@placeholder="Stație de sosire"]')
            buton_sosire.send_keys(parametri["sosire"])
            time.sleep(1.5)
            buton_sosire.send_keys(Keys.ARROW_DOWN)
            buton_sosire.send_keys(Keys.ENTER)
            time.sleep(1.5)

            try:
                selecteaza_data(driver, parametri["data"])
            except Exception:
                pass

            actions.send_keys(Keys.ENTER).perform()
            time.sleep(6.5)
        except Exception:
            pass

        print("REZULTATE TRENURI (CFR)")
        try:
            wait = WebDriverWait(driver, 10)
            trenuri = driver.find_elements(By.XPATH, '//div[contains(@class, "div-itineraries-row-main")]')

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
                        ora_plecare = "?"
                    try:
                        ora_sosire = tren.find_element(By.XPATH, '(.//span[contains(@class, "text-1-4rem")])[2]').get_attribute("textContent")
                    except Exception:
                        ora_sosire = "?"

                    try:
                        buton_detalii = tren.find_element(By.XPATH, './/button[contains(@id, "-details")]')
                        n = re.search(r"button-itinerary-(\d+)-details", buton_detalii.get_attribute("id")).group(1)
                    except Exception:
                        n = None

                    disponibilitate = verifica_disponibilitate(tren, n) if n else "Necunoscut"
                    pret = extrage_pret(driver, tren, wait, n) if n else None
                    pret_afisat = pret if pret else "indisponibil"

                    print(f"CFR: {id_tren} | {ora_plecare.strip()} -> {ora_sosire.strip()} | Pret: {pret_afisat} | [{disponibilitate}]")
                except Exception:
                    continue
        except Exception:
            print("Nu s-au putut prelua datele CFR.")

        print("\nREZULTATE ZBORURI (VOLA)")
        try:
            oras_avion_plecare = nume_oras_pentru_avion(parametri["plecare"])
            oras_avion_sosire = nume_oras_pentru_avion(parametri["sosire"])

            rezultate_vola = scrape_vola(driver, oras_avion_plecare, oras_avion_sosire, parametri["data"])

            if rezultate_vola:
                for r in rezultate_vola:
                    print(f"Vola: {r['plecare']} -> {r['sosire']} | Pret: {r['pret']}")
            else:
                print("Nu s-au găsit zboruri pe această rută/dată.")
        except Exception:
            print("A apărut o eroare la scanarea Vola.")

        print("\nREZULTATE AUTOBUZ (FLIXBUS)")
        try:
            oras_autobuz_plecare = nume_oras_pentru_avion(parametri["plecare"])
            oras_autobuz_sosire = nume_oras_pentru_avion(parametri["sosire"])

            rezultate_flix = scrape_flixbus(driver, oras_autobuz_plecare, oras_autobuz_sosire, parametri["data"])
            if rezultate_flix:
                for f in rezultate_flix:
                    print(f"FlixBus: {f['plecare']} -> {f['sosire']} | Pret: {f['pret']}")
            else:
                print("Nu s-au găsit curse FlixBus pe această rută/dată.")
        except Exception:
            print("A apărut o eroare la scanarea FlixBus.")

    finally:
        try:
            driver.quit()
        except Exception:
            pass
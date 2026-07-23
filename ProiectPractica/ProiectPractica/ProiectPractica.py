import time
import re
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RATE_SCHIMB = {
    "eur": 4.97,
    "€": 4.97,
    "usd": 4.60,
    "$": 4.60,
    "pln": 1.15,
    "zl": 1.15,
    "zł": 1.15,
    "huf": 0.013,
    "ft": 0.013,
    "czk": 0.20,
    "kc": 0.20,
    "kč": 0.20,
    "lei": 1.0,
    "ron": 1.0
}

def converteste_in_ron(text_pret):
    if not text_pret or text_pret in ("?", "Indisponibil", "Epuizat", "Epuizat/indisponibil", "indisponibil"):
        return text_pret

    m = re.search(r'([$€]?)\s*(\d+(?:[\.,]\d+)?)\s*([a-zA-Z€\$złŁčČ]+)?', text_pret)
    if not m:
        return text_pret

    prefix_simbol, val_str, sufix_moneda = m.groups()
    val_str = val_str.replace(',', '.')

    try:
        valoare = float(val_str)
    except ValueError:
        return text_pret

    moneda = (sufix_moneda or prefix_simbol or "").lower().strip()

    if moneda in RATE_SCHIMB and moneda not in ("ron", "lei"):
        val_ron = valoare * RATE_SCHIMB[moneda]
        return f"{text_pret} (~{val_ron:.0f} RON)"
    elif moneda in ("ron", "lei"):
        return text_pret
    else:
        return text_pret

def obtine_valoare_in_ron(text_pret):
    """Returnează valoarea numerică în RON pentru comparații de preț."""
    if not text_pret or text_pret in ("?", "Indisponibil", "Epuizat", "Epuizat/indisponibil", "indisponibil"):
        return float('inf')
    
    m_ron = re.search(r'~(\d+)\s*RON', text_pret)
    if m_ron:
        return float(m_ron.group(1))

    m = re.search(r'([$€]?)\s*(\d+(?:[\.,]\d+)?)\s*([a-zA-Z€\$złŁčČ]+)?', text_pret)
    if not m:
        return float('inf')

    prefix_simbol, val_str, sufix_moneda = m.groups()
    val_str = val_str.replace(',', '.')
    try:
        valoare = float(val_str)
    except ValueError:
        return float('inf')

    moneda = (sufix_moneda or prefix_simbol or "").lower().strip()
    if moneda in RATE_SCHIMB:
        return valoare * RATE_SCHIMB[moneda]
    return float('inf')

def parseaza_durata_in_minute(text_durata):
    """Convertește un șir de genul '3h 20m' sau '1h' în minute pentru a putea fi comparat."""
    if not text_durata or text_durata == "?":
        return float('inf')
    
    ore = 0
    minute = 0
    m_ore = re.search(r'(\d+)\s*h', text_durata, re.IGNORECASE)
    m_min = re.search(r'(\d+)\s*m', text_durata, re.IGNORECASE)
    
    if m_ore:
        ore = int(m_ore.group(1))
    if m_min:
        minute = int(m_min.group(1))
        
    if not m_ore and not m_min:
        m_cifre = re.search(r'(\d+)', text_durata)
        if m_cifre and 'h' in text_durata.lower():
            ore = int(m_cifre.group(1))
        elif m_cifre:
            minute = int(m_cifre.group(1))
            
    total_minute = ore * 60 + minute
    return total_minute if total_minute > 0 else float('inf')

def parseaza_pret(text_pret):
    if not text_pret:
        return None
    text_pret = text_pret.replace('\xa0', ' ').strip()
    text_curatat = re.sub(r'(?<=\d)\s+(?=\d)', '', text_pret)
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*([^\d\s]+)', text_curatat)
    if not m:
        return None
    valoare = float(m.group(1).replace(',', '.'))
    moneda = m.group(2).strip()
    return valoare, moneda

def extrage_taxa_platforma(driver, timeout=3):
    try:
        elemente_taxa = WebDriverWait(driver, timeout).until(
            lambda d: [e for e in d.find_elements(By.CSS_SELECTOR, 'div[class*="PlatformFees_price"]') if e.is_displayed()] or False
        )
        text_taxa = elemente_taxa[0].text.replace('\xa0', ' ').strip()
        rezultat = parseaza_pret(text_taxa)
        return rezultat
    except Exception:
        return None

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
        ziles = driver.find_elements(By.XPATH, f'//div[contains(@class, "calendar-month__date-day") and contains(@aria-label, "{text_cautat}")]')
        if ziles:
            driver.execute_script("arguments[0].click();", ziles[0])
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

            durata = "?"
            try:
                text_card_durata = card.get_attribute("innerText").replace('\xa0', ' ')
                cautare_durata = re.search(r'\b(\d{1,2}h\s*\d{1,2}m)\b', text_card_durata, re.IGNORECASE)
                if cautare_durata:
                    durata = cautare_durata.group(1)
            except Exception:
                pass

            rezultate.append({
                "plecare": ora_plecare,
                "sosire": ora_sosire,
                "durata": durata,
                "pret": pret,
                "sursa": "Vola"
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

REGEX_PRET_MULTIVALUTA = re.compile(
    r'([$€]\s*\d+(?:[\.,]\d+)?'
    r'|\d+(?:[\.,]\d+)?\s*(?:lei|RON|EUR|USD|PLN|HUF|CZK|€|\$|zł|Zł|ZŁ|Ft|FT|Kč|KČ|kc)\b)',
    re.IGNORECASE
)

def scrape_flixbus_pe_domenii(driver, plecare, sosire, data_str):
    wait = WebDriverWait(driver, 15)

    domenii = [
        ("romania", "https://shop.flixbus.ro/search"),
        ("germania", "https://shop.flixbus.de/search"),
        ("franta", "https://shop.flixbus.fr/search"),
        ("italia", "https://shop.flixbus.it/search"),
        ("spania", "https://shop.flixbus.es/search"),
        ("polonia", "https://shop.flixbus.pl/search"),
        ("ungaria", "https://shop.flixbus.hu/search"),
        ("cehia", "https://shop.flixbus.cz/search")
    ]

    toate_rezultatele_flixbus = []

    for nume_tara, url_baza in domenii:
        print(f"\nscrape pe site-ul flixbus {nume_tara}:")
        rezultate = []

        try:
            driver.get(url_baza)
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
                time.sleep(5)
            except Exception:
                pass

            try:
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(3)

                try:
                    curse_li = WebDriverWait(driver, 15).until(
                        lambda d: d.find_elements(By.CSS_SELECTOR, 'li[aria-posinset]') or False
                    )
                except Exception:
                    curse_li = driver.find_elements(By.CSS_SELECTOR, 'li[data-e2e="search-result-item"]')

                taxa_platforma = extrage_taxa_platforma(driver)

                for cursa in curse_li:
                    try:
                        ora_p = "?"
                        ora_s = "?"
                        pret = "?"
                        durata = "?"

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
                            el_durata = cursa.find_element(
                                By.CSS_SELECTOR, '[data-e2e="search-result-duration"]'
                            )
                            durata = el_durata.text.replace('\xa0', ' ').strip()
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

                        if ora_p == "?" or ora_s == "?":
                            ore_gasite = re.findall(r'\b\d{1,2}:\d{2}(?:\s*[AP]M)?\b', txt, re.IGNORECASE)
                            ore_unice = []
                            for o in ore_gasite:
                                if o not in ore_unice:
                                    ore_unice.append(o)
                            if ora_p == "?":
                                ora_p = ore_unice[0] if len(ore_unice) > 0 else "?"
                            if ora_s == "?":
                                ora_s = ore_unice[1] if len(ore_unice) > 1 else "?"

                        if pret == "?":
                            for cautare_pret in REGEX_PRET_MULTIVALUTA.finditer(txt):
                                cifre = re.sub(r'[^\d]', '', cautare_pret.group(0))
                                if cifre and int(cifre) >= 5:
                                    pret = cautare_pret.group(0)
                                    break
                            if pret == "?":
                                pret = "Indisponibil"

                        if taxa_platforma and pret not in ("?", "Indisponibil"):
                            info_pret = parseaza_pret(pret)
                            if info_pret:
                                valoare_bilet, moneda_bilet = info_pret
                                valoare_taxa, moneda_taxa = taxa_platforma
                                total = valoare_bilet + valoare_taxa
                                pret = f"{total:.2f} {moneda_bilet} (bilet {valoare_bilet:.2f} + taxă {valoare_taxa:.2f})"

                        rezultate.append({
                            "plecare": ora_p,
                            "sosire": ora_s,
                            "durata": durata,
                            "pret": pret,
                            "regiune": nume_tara
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            if rezultate:
                for f in rezultate:
                    pret_final = converteste_in_ron(f['pret'])
                    print(f"FlixBus ({nume_tara}): {f['plecare']} -> {f['sosire']} ({f.get('durata', '?')}) | Pret: {pret_final}")
                toate_rezultatele_flixbus.extend(rezultate)
            else:
                print(f"Nu s-au găsit curse FlixBus pe regiunea {nume_tara}.")

        except Exception:
            print(f"A apărut o eroare la scanarea FlixBus {nume_tara}.")

    return toate_rezultatele_flixbus

def accepta_cookies_esky(driver, wait, timeout=10):
    script_cookie = """
        function cautaButonInShadow(nod) {
            if (!nod || !nod.shadowRoot) return null;
            const butoane = nod.shadowRoot.querySelectorAll('button');
            for (const b of butoane) {
                const text = (b.textContent || '').trim().toLowerCase();
                if (text === 'agree' || text.includes('accept') || text === 'i accept') {
                    return b;
                }
            }
            const toateElementele = nod.shadowRoot.querySelectorAll('*');
            for (const el of toateElementele) {
                const gasit = cautaButonInShadow(el);
                if (gasit) return gasit;
            }
            return null;
        }

        let host = document.querySelector('#usercentrics-root') || document.querySelector('div[id*="usercentrics"]');
        let buton = cautaButonInShadow(host);
        if (buton) {
            buton.click();
            return true;
        }
        return false;
    """

    sfarsit = time.time() + timeout
    acceptat = False
    while time.time() < sfarsit:
        try:
            if driver.execute_script(script_cookie):
                acceptat = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if acceptat:
        time.sleep(1)
    else:
        print("[debug esky] nu am gasit butonul de cookie in shadow DOM")

    try:
        driver.execute_script("""
            let host = document.querySelector('#usercentrics-root');
            if (host) {
                host.style.pointerEvents = 'none';
                host.style.display = 'none';
            }
        """)
    except Exception:
        pass

    return acceptat

def selecteaza_data_esky(driver, wait, data_str):
    zi, luna, an = data_str.split(".")
    zi = str(int(zi))
    luna_nume = LUNI_RO_CALENDAR[int(luna) - 1]
    an = str(int(an))
    text_cautat = f"{zi} {luna_nume} {an}"

    camp_data = wait.until(EC.presence_of_element_located((By.ID, "dates_from")))
    valoare_initiala = camp_data.get_attribute("value")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", camp_data)
    time.sleep(0.3)

    calendar_deschis = False
    for incercare in range(3):
        try:
            camp_data.click()
        except Exception:
            try:
                ActionChains(driver).move_to_element(camp_data).click().perform()
            except Exception:
                pass
        time.sleep(0.7)

        celule_test = [c for c in driver.find_elements(By.CSS_SELECTOR, 'div[data-track="Day"]') if c.is_displayed()]
        if celule_test:
            calendar_deschis = True
            break

        try:
            buton_popover = driver.find_element(
                By.XPATH, '//label[.//input[@id="dates_from"]]//button[@popovertarget]'
            )
            ActionChains(driver).move_to_element(buton_popover).click().perform()
            time.sleep(0.7)
            celule_test = [c for c in driver.find_elements(By.CSS_SELECTOR, 'div[data-track="Day"]') if c.is_displayed()]
            if celule_test:
                calendar_deschis = True
                break
        except Exception:
            pass

    if not calendar_deschis:
        return

    zi_gasita = False
    for _ in range(12):
        zile = driver.find_elements(
            By.XPATH,
            f'//div[@role="gridcell" and @data-track="Day" and contains(@aria-label, "{text_cautat}")]'
        )
        zile_vizibile = [z for z in zile if z.is_displayed()]

        if zile_vizibile:
            element_zi = zile_vizibile[0]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_zi)
            time.sleep(0.3)

            try:
                element_zi.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", element_zi)
                except Exception:
                    pass

            time.sleep(0.8)

            valoare_dupa = camp_data.get_attribute("value")
            if valoare_dupa != valoare_initiala:
                zi_gasita = True
                break
            else:
                try:
                    driver.execute_script("""
                        const el = arguments[0];
                        el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                        el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                        el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    """, element_zi)
                    time.sleep(0.8)
                    valoare_dupa = camp_data.get_attribute("value")
                    if valoare_dupa != valoare_initiala:
                        zi_gasita = True
                        break
                except Exception:
                    pass
                break
        else:
            try:
                buton_next = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="next" i], button[aria-label*="urm" i]')
                buton_next.click()
                time.sleep(0.5)
            except Exception:
                break

    time.sleep(0.5)

def scrape_esky(driver, plecare, sosire, data_str):
    wait = WebDriverWait(driver, 15)
    driver.get("https://www.esky.ro/zboruri")
    time.sleep(3)

    accepta_cookies_esky(driver, wait)

    try:
        eticheta_doar_dus = driver.find_element(By.XPATH, '//label[@data-track="OneWay"]')
        driver.execute_script("arguments[0].click();", eticheta_doar_dus)
        time.sleep(0.5)
    except Exception:
        pass

    try:
        input_plecare = wait.until(EC.element_to_be_clickable((By.ID, "qsf-departure")))
        driver.execute_script("arguments[0].click();", input_plecare)
        input_plecare.send_keys(Keys.CONTROL, "a")
        input_plecare.send_keys(Keys.DELETE)
        input_plecare.send_keys(plecare)
        time.sleep(1.5)
        input_plecare.send_keys(Keys.ARROW_DOWN)
        input_plecare.send_keys(Keys.ENTER)
        time.sleep(1)
    except Exception:
        return []

    try:
        input_sosire = wait.until(EC.element_to_be_clickable((By.ID, "qsf-arrival")))
        driver.execute_script("arguments[0].click();", input_sosire)
        input_sosire.send_keys(Keys.CONTROL, "a")
        input_sosire.send_keys(Keys.DELETE)
        input_sosire.send_keys(sosire)
        time.sleep(1.5)
        input_sosire.send_keys(Keys.ARROW_DOWN)
        input_sosire.send_keys(Keys.ENTER)
        time.sleep(1)
    except Exception:
        return []

    try:
        selecteaza_data_esky(driver, wait, data_str)
    except Exception:
        pass

    try:
        butoane_cauta = wait.until(
            lambda d: [b for b in d.find_elements(By.CSS_SELECTOR, 'button[type="submit"][pi-color="accent-2"]') if b.is_displayed()] or False
        )
        driver.execute_script("arguments[0].click();", butoane_cauta[0])
        time.sleep(6)
    except Exception:
        return []

    return extrage_zboruri_esky(driver)

def extrage_zboruri_esky(driver):
    rezultate = []
    try:
        WebDriverWait(driver, 25).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, 'so-fsr-flight-card, [class*="flight-result"]')
        )
        time.sleep(2)
    except Exception:
        return rezultate

    carduri = driver.find_elements(By.CSS_SELECTOR, 'so-fsr-flight-card')

    for card in carduri:
        try:
            ora_p = card.find_element(By.CSS_SELECTOR, '[data-testid="leg-departure"] [data-testid="time"]').text.strip()
        except Exception:
            ora_p = "?"

        try:
            ora_s = card.find_element(By.CSS_SELECTOR, '[data-testid="leg-arrival"] [data-testid="time"]').text.strip()
        except Exception:
            ora_s = "?"

        try:
            durata = card.find_element(By.CSS_SELECTOR, '[data-testid="duration"]').text.strip()
        except Exception:
            durata = "?"

        try:
            suma = card.find_element(By.CSS_SELECTOR, '[data-testid="formatted-price"] span[class*="amount"]').text.strip()
            moneda = card.find_element(By.CSS_SELECTOR, '[data-testid="formatted-price"] span[class*="currency"]').text.strip()
            pret = f"{suma} {moneda}"
        except Exception:
            pret = "?"

        if ora_p != "?" or ora_s != "?":
            rezultate.append({
                "plecare": ora_p,
                "sosire": ora_s,
                "durata": durata,
                "pret": pret,
                "sursa": "eSky"
            })

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

    toate_trenurile = []
    toate_zborurile = []
    toate_autocarele = []

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
                        durata = tren.find_element(
                            By.XPATH, './/span[contains(@class, "d-inline-block")]'
                        ).text.strip()
                    except Exception:
                        durata = "?"

                    try:
                        buton_detalii = tren.find_element(By.XPATH, './/button[contains(@id, "-details")]')
                        n = re.search(r"button-itinerary-(\d+)-details", buton_detalii.get_attribute("id")).group(1)
                    except Exception:
                        n = None

                    disponibilitate = verifica_disponibilitate(tren, n) if n else "Necunoscut"
                    pret = extrage_pret(driver, tren, wait, n) if n else None
                    pret_afisat = converteste_in_ron(pret) if pret else "indisponibil"

                    print(f"CFR: {id_tren} | {ora_plecare.strip()} -> {ora_sosire.strip()} ({durata}) | Pret: {pret_afisat} | [{disponibilitate}]")
                    
                    if disponibilitate == "Disponibil" and pret:
                        toate_trenurile.append({
                            "nume": id_tren,
                            "plecare": ora_plecare.strip(),
                            "sosire": ora_sosire.strip(),
                            "durata": durata,
                            "pret_text": pret_afisat,
                            "valoare_pret": obtine_valoare_in_ron(pret),
                            "valoare_durata": parseaza_durata_in_minute(durata)
                        })
                except Exception:
                    continue
        except Exception:
            print("Nu s-au putut prelua datele CFR.")

        oras_avion_plecare = nume_oras_pentru_avion(parametri["plecare"])
        oras_avion_sosire = nume_oras_pentru_avion(parametri["sosire"])

        print("\nREZULTATE ZBORURI (VOLA)")
        try:
            rezultate_vola = scrape_vola(driver, oras_avion_plecare, oras_avion_sosire, parametri["data"])

            if rezultate_vola:
                for r in rezultate_vola:
                    pret_final = converteste_in_ron(r['pret'])
                    print(f"Vola: {r['plecare']} -> {r['sosire']} ({r.get('durata', '?')}) | Pret: {pret_final}")
                    toate_zborurile.append({
                        "plecare": r['plecare'],
                        "sosire": r['sosire'],
                        "durata": r.get('durata', '?'),
                        "pret_text": pret_final,
                        "valoare_pret": obtine_valoare_in_ron(r['pret']),
                        "valoare_durata": parseaza_durata_in_minute(r.get('durata', '?')),
                        "platforma": "Vola"
                    })
            else:
                print("Nu s-au găsit zboruri pe această rută/dată.")
        except Exception:
            print("A apărut o eroare la scanarea Vola.")

        print("\nREZULTATE ZBORURI (ESKY)")
        try:
            rezultate_esky = scrape_esky(driver, oras_avion_plecare, oras_avion_sosire, parametri["data"])
            if rezultate_esky:
                for r in rezultate_esky:
                    pret_final = converteste_in_ron(r['pret'])
                    print(f"Esky: {r['plecare']} -> {r['sosire']} ({r.get('durata', '?')}) | Pret: {pret_final}")
                    toate_zborurile.append({
                        "plecare": r['plecare'],
                        "sosire": r['sosire'],
                        "durata": r.get('durata', '?'),
                        "pret_text": pret_final,
                        "valoare_pret": obtine_valoare_in_ron(r['pret']),
                        "valoare_durata": parseaza_durata_in_minute(r.get('durata', '?')),
                        "platforma": "eSky"
                    })
            else:
                print("Nu s-au găsit zboruri pe eSky pentru această rută/dată.")
        except Exception as e:
            print(f"A apărut o eroare la scanarea eSky: {e}")

        print("\nREZULTATE AUTOBUZ (FLIXBUS)")
        try:
            oras_autobuz_plecare = nume_oras_pentru_avion(parametri["plecare"])
            oras_autobuz_sosire = nume_oras_pentru_avion(parametri["sosire"])

            rezultate_flix = scrape_flixbus_pe_domenii(driver, oras_autobuz_plecare, oras_autobuz_sosire, parametri["data"])
            if rezultate_flix:
                for f in rezultate_flix:
                    pret_final = converteste_in_ron(f['pret'])
                    toate_autocarele.append({
                        "plecare": f['plecare'],
                        "sosire": f['sosire'],
                        "durata": f.get('durata', '?'),
                        "pret_text": pret_final,
                        "valoare_pret": obtine_valoare_in_ron(f['pret']),
                        "valoare_durata": parseaza_durata_in_minute(f.get('durata', '?')),
                        "regiune": f.get('regiune', 'necunoscută')
                    })
        except Exception as e:
            print(f"A apărut o eroare la scanarea FlixBus: {e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print("Cele mai Bune Optiuni:")

    if toate_trenurile:
        cel_mai_ieftin_tren = min(toate_trenurile, key=lambda x: x["valoare_pret"])
        cel_mai_rapid_tren = min(toate_trenurile, key=lambda x: x["valoare_durata"])
        
        print(f"cel mai ieftin tren: {cel_mai_ieftin_tren['nume']} ({cel_mai_ieftin_tren['plecare']} - {cel_mai_ieftin_tren['sosire']}), Durata: {cel_mai_ieftin_tren['durata']}, Preț: {cel_mai_ieftin_tren['pret_text']}")
        print(f"cel mai rapid tren: {cel_mai_rapid_tren['nume']} ({cel_mai_rapid_tren['plecare']} - {cel_mai_rapid_tren['sosire']}), Durata: {cel_mai_rapid_tren['durata']}, Preț: {cel_mai_rapid_tren['pret_text']}")
    else:
        print("cel mai ieftin tren: Nu există date disponibile.")
        print("cel mai rapid tren: Nu există date disponibile.")

    if toate_zborurile:
        cel_mai_ieftin_avion = min(toate_zborurile, key=lambda x: x["valoare_pret"])
        cel_mai_rapid_avion = min(toate_zborurile, key=lambda x: x["valoare_durata"])

        print(f"cel mai ieftin avion: {cel_mai_ieftin_avion['plecare']} - {cel_mai_ieftin_avion['sosire']} ({cel_mai_ieftin_avion['durata']}) cu {cel_mai_ieftin_avion['platforma']}, Preț: {cel_mai_ieftin_avion['pret_text']}")
        print(f"cel mai rapid avion: {cel_mai_rapid_avion['plecare']} - {cel_mai_rapid_avion['sosire']} ({cel_mai_rapid_avion['durata']}) cu {cel_mai_rapid_avion['platforma']}, Preț: {cel_mai_rapid_avion['pret_text']}")
    else:
        print("cel mai ieftin avion: Nu există date disponibile.")
        print("cel mai rapid avion: Nu există date disponibile.")

    if toate_autocarele:
        cel_mai_ieftin_autocar = min(toate_autocarele, key=lambda x: x["valoare_pret"])
        cel_mai_rapid_autocar = min(toate_autocarele, key=lambda x: x["valoare_durata"])

        print(f"cel mai ieftin autocar: {cel_mai_ieftin_autocar['plecare']} - {cel_mai_ieftin_autocar['sosire']} ({cel_mai_ieftin_autocar['durata']}), Preț: {cel_mai_ieftin_autocar['pret_text']} (pe regiunea: {cel_mai_ieftin_autocar['regiune']})")
        print(f"cel mai rapid autocar: {cel_mai_rapid_autocar['plecare']} - {cel_mai_rapid_autocar['sosire']} ({cel_mai_rapid_autocar['durata']}), Preț: {cel_mai_rapid_autocar['pret_text']} (pe regiunea: {cel_mai_rapid_autocar['regiune']})")
    else:
        print("cel mai ieftin autocar: Nu există date disponibile.")
        print("cel mai rapid autocar: Nu există date disponibile.")
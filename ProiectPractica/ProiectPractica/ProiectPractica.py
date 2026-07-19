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


# C1. Introducere parametri cautare (Plecare, Destinatie, Data)
def citeste_parametri():
    print("=== Introducere parametri cautare tren ===")

    plecare = input("Statie de plecare (ex: Bucuresti Nord): ").strip()
    while not plecare:
        plecare = input("Nu poate fi gol. Statie de plecare: ").strip()

    sosire = input("Statie de destinatie (ex: Suceava): ").strip()
    while not sosire:
        sosire = input("Nu poate fi gol. Statie de destinatie: ").strip()

    data_input = input(
        "Data calatoriei (format ZZ.LL.AAAA, sau 'azi' / 'maine'): "
    ).strip().lower()

    if data_input in ("azi", "astazi"):
        data_calatorie = datetime.now().strftime("%d.%m.%Y")
    elif data_input in ("maine", "mâine"):
        data_calatorie = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    else:
        while not re.match(r"^\d{2}\.\d{2}\.\d{4}$", data_input):
            data_input = input(
                "Format invalid. Foloseste ZZ.LL.AAAA (ex: 20.07.2026): "
            ).strip().lower()
        data_calatorie = data_input

    print(f"\nCautam: {plecare} -> {sosire}, data {data_calatorie}\n")

    return {"plecare": plecare, "sosire": sosire, "data": data_calatorie}


# C2. Verificare disponibilitate locuri / bilete epuizate pentru un tren
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

# C6. Extragere pret pentru un tren
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
    except Exception as e:
        print("nu am putut extrage pretul:", e)
        return None


def nume_oras_pentru_avion(statie_tren):
    sufixe = ["Nord", "Sud", "Est", "Vest", "Centrala", "Calatori", "Triaj", "Vama"]
    cuvinte = statie_tren.strip().split()
    while len(cuvinte) > 1 and cuvinte[-1] in sufixe:
        cuvinte.pop()
    return " ".join(cuvinte)


MAPA_AEROPORTURI = {
    "bucuresti": "OTP",
    "cluj": "CLJ",
    "cluj-napoca": "CLJ",
    "iasi": "IAS",
    "timisoara": "TSR",
    "sibiu": "SBZ",
    "craiova": "CRA",
    "suceava": "SCV",
    "targu mures": "TGM",
    "bacau": "BCM",
    "oradea": "OMR",
    "arad": "ARW",
    "londra": "LTN",
    "roma": "FCO",
    "milano": "BGY",
    "paris": "ORY",
    "barcelona": "BCN",
    "madrid": "MAD",
    "viena": "VIE",
    "berlin": "BER",
    "amsterdam": "AMS",
    "budapesta": "BUD",
    "varsovia": "WAW",
    "praga": "PRG",
    "atena": "ATH",
    "dublin": "DUB",
    "bruxelles": "CRL",
    "lisabona": "LIS",
    "cracovia": "KRK",
}


def cod_iata(oras):
    cheie = oras.strip().lower()
    cheie = (cheie.replace("ă", "a").replace("â", "a").replace("î", "i")
             .replace("ș", "s").replace("ş", "s").replace("ț", "t").replace("ţ", "t"))
    return MAPA_AEROPORTURI.get(cheie)


# C3. Scraping preturi avioane - Wizz Air
def scrape_wizzair(driver, plecare, sosire, data_str):
    cod_plecare = cod_iata(plecare)
    cod_sosire = cod_iata(sosire)

    if not cod_plecare or not cod_sosire:
        lipsa = plecare if not cod_plecare else sosire
        print(f"Wizz Air: nu cunosc codul IATA pentru '{lipsa}'. Adauga-l in MAPA_AEROPORTURI din script.")
        return []

    zi, luna, an = data_str.split(".")
    data_url = f"{an}-{int(luna):02d}-{int(zi):02d}"

    url = (f"https://www.wizzair.com/ro-ro/booking/select-flight/"
           f"{cod_plecare}/{cod_sosire}/{data_url}/null/1/0/0/null")

    wait = WebDriverWait(driver, 15)

    print("Wizz Air: vizitez homepage-ul pentru a stabili sesiunea...")
    driver.get("https://wizzair.com/ro-ro")
    time.sleep(3)

    cookie_acceptat = False
    for _ in range(10):
        rezultat = driver.execute_script("""
            const host = document.querySelector('#usercentrics-cmp-ui');
            if (host && host.shadowRoot) {
                const butoane = host.shadowRoot.querySelectorAll('button');
                for (const b of butoane) {
                    if (b.textContent && /accept/i.test(b.textContent)) {
                        b.click();
                        return true;
                    }
                }
            }
            return false;
        """)
        if rezultat:
            cookie_acceptat = True
            break
        time.sleep(1)
    if not cookie_acceptat:
        print("Wizz Air: nu am gasit/inchis bannerul de cookie-uri (poate nu a aparut)")
    time.sleep(1)

    print(f"Wizz Air: navighez la {url}")
    driver.get(url)
    time.sleep(4)

    try:
        e_webdriver = driver.execute_script("return navigator.webdriver")
        print(f"Wizz Air: navigator.webdriver = {e_webdriver} (True = site-ul poate detecta automatizarea)")
    except Exception:
        pass

    try:
        print("Wizz Air: astept pagina de rezultate (poate dura pana la 20s)...")
        wait_rezultate = WebDriverWait(driver, 20)
        try:
            wait_rezultate.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="departure-time"]')))
            print("Wizz Air: pagina de rezultate a aparut")
        except Exception:
            try:
                print("Wizz Air: niciun zbor la data exacta, incerc 'urmatorul zbor disponibil'...")
                buton_urmatorul = driver.find_element(By.XPATH, '//button[contains(., "zbor disponibil")]')
                driver.execute_script("arguments[0].click();", buton_urmatorul)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="departure-time"]'))
                )
                print("Wizz Air: pagina de rezultate a aparut (data alternativa)")
            except Exception:
                print("Wizz Air: incerc un reload al paginii ca ultima incercare...")
                driver.refresh()
                time.sleep(3)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="departure-time"]'))
                )
                print("Wizz Air: pagina de rezultate a aparut dupa reload")
    except Exception as e:
        print(f"Wizz Air: nu a aparut pagina de rezultate ({type(e).__name__}) - posibil ca nu exista zbor direct pe aceasta ruta:", e)
        try:
            driver.save_screenshot("wizzair_eroare.png")
            print("Wizz Air: screenshot salvat ca wizzair_eroare.png")
        except Exception:
            pass
        return []

    rezultate = []
    try:
        ore_plecare = driver.find_elements(By.CSS_SELECTOR, '[data-test="departure-time"]')
        ore_sosire = driver.find_elements(By.CSS_SELECTOR, '[data-test="arrival-time"]')
        preturi_toate = driver.find_elements(By.CSS_SELECTOR, '.fare-button .current-price')

        for i in range(len(ore_plecare)):
            op = ore_plecare[i].text.strip()
            os_ = ore_sosire[i].text.strip() if i < len(ore_sosire) else "?"
            idx_pret = i * 2
            pr = preturi_toate[idx_pret].text.strip() if idx_pret < len(preturi_toate) else "?"
            rezultate.append({"companie": "Wizz Air", "plecare": op, "sosire": os_, "pret": pr})
            print(f"Wizz Air: {op} -> {os_} | Pret: {pr}")

        if not rezultate:
            print("Wizz Air: pagina a aparut dar nu am gasit niciun zbor extras")
    except Exception as e:
        print("Wizz Air: nu am putut extrage rezultatul zborului:", e)

    return rezultate


parametri = citeste_parametri()

driver = uc.Chrome(version_main=150)
driver.maximize_window()
actions = ActionChains(driver)

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
        buton_plecare.send_keys(Keys.ENTER)
        time.sleep(5)

        buton_sosire = driver.find_element(By.XPATH, '//input[@placeholder="Stație de sosire"]')
        buton_sosire.send_keys(parametri["sosire"])
        time.sleep(1.5)
        buton_sosire.send_keys(Keys.ARROW_DOWN)
        buton_sosire.send_keys(Keys.ENTER)
        time.sleep(1.5)

        try:
            selecteaza_data(driver, parametri["data"])
            print(f"data selectata: {parametri['data']}")
        except Exception as e:
            print("nu am putut selecta data in calendar:", e)

        actions.send_keys(Keys.ENTER).perform()
        print("introdus datele")
        time.sleep(6.5)
    except Exception as e:
        print("nu asa se face", e)

    try:
        time.sleep(5)
        wait = WebDriverWait(driver, 10)
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

                try:
                    buton_detalii = tren.find_element(By.XPATH, './/button[contains(@id, "-details")]')
                    n = re.search(r"button-itinerary-(\d+)-details", buton_detalii.get_attribute("id")).group(1)
                except Exception:
                    n = None

                disponibilitate = verifica_disponibilitate(tren, n) if n else "Necunoscut"
                pret = extrage_pret(driver, tren, wait, n) if n else None
                pret_afisat = pret if pret else "indisponibil"

                print(f"{index}: Tren: {id_tren}")
                print(
                    f"Plecare: {ora_plecare.strip()} | Sosire: {ora_sosire.strip()} "
                    f"| Pret: {pret_afisat} | Status: {disponibilitate}"
                )
            except Exception as e:
                print(f"nuh uh tren{index}: {e}")
    except Exception:
        print("ceva nu-i bun")

    try:
        oras_plecare = nume_oras_pentru_avion(parametri["plecare"])
        oras_sosire = nume_oras_pentru_avion(parametri["sosire"])
        print(f"\nCautam zboruri Wizz Air: {oras_plecare} -> {oras_sosire}, data {parametri['data']}")
        rezultate_wizzair = scrape_wizzair(driver, oras_plecare, oras_sosire, parametri["data"])
    except Exception as e:
        print("Wizz Air: eroare generala:", e)
finally:
    driver.quit()
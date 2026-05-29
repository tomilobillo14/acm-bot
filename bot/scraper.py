import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

def scrape_link(url):
    try:
        if "zonaprop" in url:
            return _scrape_zonaprop(url)
        elif "argenprop" in url:
            return _scrape_argenprop(url)
        elif "mercadolibre" in url:
            return _scrape_mercadolibre(url)
        else:
            return _scrape_generic(url)
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

def _scrape_zonaprop(url):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    article = soup.find("article") or soup
    text = article.get_text(" ", strip=True)
    data = {"tipo": "oferta", "url": url}

    title = soup.find("title")
    if title:
        data["direccion"] = title.text.split(" - ")[0].strip()
    else:
        h1 = soup.find("h1")
        data["direccion"] = h1.text.strip() if h1 else url

    for pat in [r"USD\s*([\d\.]+)", r"U\$[Ss]\s*([\d\.]+)", r"([\d\.]+)\s*USD"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                data["precio"] = float(m.group(1).replace(".", "").replace(",", "."))
                break
            except Exception:
                pass

    for pat, key in [
        (r"([\d,\.]+)\s*m[²2]\s*tot", "sup_total"),
        (r"([\d,\.]+)\s*m[²2]\s*cub", "sup_cubierta"),
        (r"([\d,\.]+)\s*m[²2]\s*semi", "sup_semi"),
        (r"([\d,\.]+)\s*m[²2]\s*(?:desc|terr)", "sup_desc"),
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                data[key] = float(m.group(1).replace(",", "."))
            except Exception:
                pass

    if "sup_cubierta" not in data and "sup_total" in data:
        data["sup_cubierta"] = data["sup_total"]
    if "sup_total" not in data and "sup_cubierta" in data:
        data["sup_total"] = data["sup_cubierta"]
    data.setdefault("sup_semi", 0)
    data.setdefault("sup_desc", 0)

    m = re.search(r"(\d+)\s*años?", text, re.IGNORECASE)
    if m:
        data["antiguedad"] = int(m.group(1))

    m = re.search(r"(\d+)[°º]\s*[Pp]iso", text)
    data["piso"] = int(m.group(1)) if m else 0

    m = re.search(r"[Pp]ublicado\s+hace\s+(\d+)\s+d[íi]as?", text)
    data["dias_publicado"] = int(m.group(1)) if m else 0

    data["cochera"] = 1 if re.search(r"cochera", text, re.IGNORECASE) else 0

    return data if data.get("sup_cubierta") else None

def _scrape_argenprop(url):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    data = {"tipo": "oferta", "url": url, "piso": 0, "sup_semi": 0, "sup_desc": 0, "cochera": 0, "dias_publicado": 0}

    h1 = soup.find("h1")
    data["direccion"] = h1.text.strip() if h1 else url

    for pat in [r"USD\s*([\d\.]+)", r"U\$[Ss]\s*([\d\.]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                data["precio"] = float(m.group(1).replace(".", ""))
                break
            except Exception:
                pass

    for pat, key in [
        (r"([\d,\.]+)\s*m[²2]\s*(?:tot|total)", "sup_total"),
        (r"([\d,\.]+)\s*m[²2]\s*(?:cub|cubiertos?)", "sup_cubierta"),
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                data[key] = float(m.group(1).replace(",", "."))
            except Exception:
                pass

    if "sup_cubierta" not in data and "sup_total" in data:
        data["sup_cubierta"] = data["sup_total"]

    m = re.search(r"(\d+)\s*años?", text, re.IGNORECASE)
    if m:
        data["antiguedad"] = int(m.group(1))
    m = re.search(r"(\d+)[°º]\s*[Pp]iso", text)
    if m:
        data["piso"] = int(m.group(1))

    return data if data.get("sup_cubierta") else None

def _scrape_mercadolibre(url):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    data = {"tipo": "oferta", "url": url, "piso": 0, "sup_semi": 0, "sup_desc": 0, "cochera": 0, "dias_publicado": 0}

    h1 = soup.find("h1")
    data["direccion"] = h1.text.strip() if h1 else url

    m = re.search(r"U\$[Ss]\s*([\d\.]+)", text, re.IGNORECASE)
    if m:
        try:
            data["precio"] = float(m.group(1).replace(".", ""))
        except Exception:
            pass

    m = re.search(r"([\d,\.]+)\s*m[²2]?\s*(?:tot|total|cubiertos?)", text, re.IGNORECASE)
    if m:
        try:
            data["sup_cubierta"] = float(m.group(1).replace(",", "."))
        except Exception:
            pass

    data.setdefault("sup_cubierta", 0)
    data["sup_total"] = data["sup_cubierta"]
    return data if data.get("sup_cubierta") else None

def _scrape_generic(url):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text(" ", strip=True)
    data = {"tipo": "oferta", "url": url, "piso": 0, "sup_semi": 0, "sup_desc": 0, "cochera": 0, "dias_publicado": 0}

    title = soup.find("title")
    data["direccion"] = title.text.split("-")[0].strip() if title else url

    for pat in [r"USD\s*([\d\.]+)", r"U\$[Ss]\s*([\d\.]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                data["precio"] = float(m.group(1).replace(".", ""))
                break
            except Exception:
                pass

    m = re.search(r"([\d,\.]+)\s*m[²2]", text)
    if m:
        try:
            data["sup_cubierta"] = float(m.group(1).replace(",", "."))
            data["sup_total"] = data["sup_cubierta"]
        except Exception:
            pass

    return data

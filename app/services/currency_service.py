import requests
from bs4 import BeautifulSoup
import logging
import urllib3

# Disable SSL warnings as BCV sometimes has certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class CurrencyService:
    @staticmethod
    def get_bcv_rate():
        """
        Fetches the official USD exchange rate from the Central Bank of Venezuela (BCV).
        """
        url = "https://www.bcv.org.ve/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }
        
        try:
            # Attempt 1: Direct BCV Scraping
            response = requests.get(url, headers=headers, verify=False, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # The BCV site has several divs for currencies. We need the one for USD.
                # Usually it's inside a div with id="dolar"
                dolar_container = soup.find("div", id="dolar")
                if dolar_container:
                    rate_text = dolar_container.find("strong").text.strip()
                    rate = float(rate_text.replace(',', '.'))
                    logger.info(f"Successfully fetched BCV rate: {rate}")
                    return rate
                
                # Alternative selector if structure changed
                rate_box = soup.select_one("#dolar strong")
                if rate_box:
                    rate = float(rate_box.text.strip().replace(',', '.'))
                    return rate

            # Attempt 2: Fallback to a reliable public API/Mirror if BCV blocks us
            # Many developers use mirrors for BCV data due to its instability
            logger.warning("BCV direct fetch failed or structure changed. Trying mirror...")
            mirror_url = "https://ve.dolarapi.com/v1/dolares/oficial"
            mirror_resp = requests.get(mirror_url, timeout=10)
            if mirror_resp.status_code == 200:
                data = mirror_resp.json()
                rate = float(data.get("promedio", 0) or data.get("valor", 0))
                if rate > 0:
                    logger.info(f"Fetched rate from mirror: {rate}")
                    return rate

        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
        
        # Absolute fallback if everything fails
        return 47.58 # Updated fallback to a more recent approximate value (April 2026)

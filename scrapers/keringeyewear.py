
import json
import requests
import threading
import datetime
from time import sleep
from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from models.store import Store
from models.brand import Brand
from models.product import Product
from models.metafields import Metafields
from models.variant import Variant
from unidecode import unidecode

from selenium.webdriver.chrome.service import Service as ChromeService

class myScrapingThread(threading.Thread):
    def __init__(self, thread_id, name, scraper, brand, glasses_type, product_number, product_url, headers):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.scraper = scraper
        self.brand = brand
        self.glasses_type = glasses_type
        self.product_number = product_number
        self.product_url = product_url
        self.headers = headers
        self.status = "in progress"

    def run(self):
        try:
            self.scraper.scrape_product(self.brand, self.glasses_type, self.product_number, self.product_url, self.headers)
            self.status = "completed"
        except Exception as e:
            self.status = "failed"
            self.scraper.print_logs(f'Exception in thread {self.name}: {e}')

class myScrapingThreadController:
    def __init__(self, max_threads: int, DEBUG, logs_filename: str) -> None:
        self.thread_list = []
        self.thread_counter = 0
        self.max_threads = max_threads
        self.lock = threading.Lock()
        self.data = []
        self.DEBUG = DEBUG
        self.logs_filename = logs_filename

    def create_thread(self, brand: Brand, glasses_type: str, product_number: str, product_url: str, headers: dict):
        self.manage_thread_list()
        thread_name = "Thread-" + str(self.thread_counter)
        new_thread = myScrapingThread(self.thread_counter, thread_name, self, brand, glasses_type, product_number, product_url, headers)
        
        with self.lock:
            self.thread_list.append(new_thread)
            self.thread_counter += 1
        
        new_thread.start()

    def clean_completed_threads(self):
        with self.lock:
            self.thread_list = [thread for thread in self.thread_list if thread.status != "completed"]

    def manage_thread_list(self):
        while len(self.thread_list) >= self.max_threads:
            self.clean_completed_threads()
            sleep(1)

    def is_thread_list_completed(self) -> bool:
        with self.lock:
            for obj in self.thread_list:
                if obj.status == "in progress":
                    return False
            return True

    def wait_for_thread_list_to_complete(self):
        while not self.is_thread_list_completed():
            sleep(1)
        with self.lock:
            self.thread_counter = 0
            self.thread_list.clear()

    def print_logs(self, log: str) -> None:
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

    def printProgressBar(self, iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r") -> None:
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()

    def get_response(self, url: str, headers: dict) -> requests.Response:
        response = None
        try:
            for _ in range(10):
                try:
                    response = requests.get(url=url, headers=headers, timeout=60)
                    if response.status_code == 200:
                        break
                except Exception as e: 
                    self.print_logs(f'Exception in get_response: {e}')
                    sleep(0.1)
        except Exception as e: self.print_logs(f'Exception in get_response: {e}')
        return response

    def scrape_product(self, brand: Brand, glasses_type: str, product_number: str, product_url: str, headers: dict):
        try:
            URL = product_url
            response = self.get_response(URL, headers)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                products_data = self.get_product_data(product_number, soup)
                
                for product_data in products_data:
                    try:
                        product = Product()
                        product.brand = brand.name
                        product.number = product_data['number']
                        product.frame_code = product_data['frame_code']
                        product.type = glasses_type
                        product_url = product_data['product_url']

                        if product_url not in URL:
                            URL = product_url
                            response = self.get_response(URL, headers)
                            if response and response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'lxml')

                        metafields = self.scrape_product_metafields(product_data, product, soup)
                        try: product.bridge = str(metafields.size_bridge_template).strip().split('-')[1].strip()
                        except: pass
                        try: product.template = str(metafields.size_bridge_template).strip().split('-')[-1].strip()
                        except: pass
                        variant = self.scrape_product_variant(product, metafields, soup)
                        
                        metafields.gtin1 = variant.barcode_or_gtin
                        metafields.frame_color = product_data['frame_color']
                        metafields.lens_color = product_data['lens_color']

                        product.metafields = metafields
                        product.add_single_variant(variant) 

                        self.data.append(product)
                    except Exception as e: self.print_logs(f'Exception in product: {e}')
            else:
                if response: self.print_logs(f'{response.status_code} for {URL}')
                else: self.print_logs(f'Timeout exception for {URL}')
        except Exception as e: self.print_logs(f'Exception in scrape_product: {e}')
    
    def get_product_data(self, product_number: str, soup: BeautifulSoup) -> list[dict]:
        products_data = []
        try:
            for div in soup.select('div[class*="variants"] > div[class^="product-item space purchasable-plp set-border"]'):
                product_url, number, frame_code, product_size, frame_color, lens_color = '', '', '', '', '', ''
                product_url = div.select_one('form[class="js-product-page"]').get('action')
                if 'https://my.keringeyewear.com' not in product_url: product_url = f'https://my.keringeyewear.com{product_url}'
                text = str(div.select_one('div[class="col-md-12 product-description"] > div[class="details brand"] > a').text).strip()
                number = product_number.strip().upper()
                frame_code = str(text).split('-')[-1].strip().upper()
                frame_code = text.lower().replace(str(number).strip().lower(), '').strip().upper()
                if frame_code[0] == '-': frame_code = frame_code[1:]
                for details_div in div.select('div[class="col-md-12 product-description"] > div[class="details counter-variant"]'):
                    if 'CALIBERS:' in str(details_div.text).strip().upper():
                        product_size = str(details_div.find('span').text).strip()
                    elif 'FRONT:' in str(details_div.text).strip().upper():
                        frame_color = str(details_div.find('span').text).strip()
                    elif 'LENS:' in str(details_div.text).strip().upper():
                        lens_color = str(details_div.find('span').text).strip()

                json_data = {
                    'product_url': product_url,
                    'number': number,
                    'frame_code': frame_code,
                    'frame_color': frame_color,
                    'lens_color': lens_color,
                    'product_size': product_size
                }
                if json_data not in products_data: products_data.append(json_data)
           
        except Exception as e: self.print_logs(f'Exception in get_product_data: {str(e)}')
        finally: return products_data

    def scrape_product_metafields(self, product_data: dict, product: Product, soup: BeautifulSoup) -> Metafields:
        metafields = Metafields()
        try:
            if str(product_data['product_size']).strip() != '-0-0':
                metafields.size_bridge_template = str(product_data['product_size']).strip().replace(' ', '')

            try:
                for div in soup.select('div[id="kering-product-characteristics"] > div[id="kering-product-characteristics-collapsable"] > div[class="col-sm-12 col-xs-12"]'):
                    if str(div.select_one('span[class*="characteristics-title"]').text).strip().lower() == 'gender':
                        metafields.for_who = str(div.find_all('span')[1].text).strip().title()
                        break
            except Exception as e: 
                self.print_logs(f'Exception in metafields.for_who: {e}')
                sleep(0.15)

            try:
                for div in soup.select('div[id="kering-product-characteristics"] > div[id="kering-product-characteristics-collapsable"] > div[class="col-sm-6 col-xs-12"]'):
                    if str(div.select_one('span[class*="characteristics-title"]').text).strip().lower() == 'temple main':
                        metafields.frame_material = str(div.find_all('span')[1].text).strip().title()
                    if str(div.select_one('span[class*="characteristics-title"]').text).strip().lower() == 'lens':
                        text = str(div.find_all('span')[1].text).strip().title()
                        if str(product.metafields.lens_color).strip().lower() != str(text).strip().lower():
                            metafields.lens_material = text
                    if metafields.frame_material and metafields.lens_material: break
            except Exception as e: 
                self.print_logs(f'Exception in metafields.frame_material: {e}')
                sleep(0.15)

            try:
                img_tag = soup.select_one('div > img[class="lazyOwl"]')
                product.image = img_tag.get('src') if img_tag else ''
                if 'missing_product_EN_512x512.png' in product.image: product.image = ''
            except Exception as e: 
                self.print_logs(f'Exception in metafields.img_url: {e}')
                sleep(0.15)

            try:
                main_div = soup.select_one('div[class="badge-area"]')
                for badges in main_div.select('p[class="best-feature"]'):
                    badge_text = str(badges.text).strip()
                    if badge_text not in product.tags:
                        product.tags.append(badge_text)
            except Exception as e: 
                    self.print_logs(f'Exception in product.tags: {e}')
                    sleep(0.15)

            if product.image:
                try:
                    images_360 = []
                    for img_tag in soup.select('div[class="item"] > img[class="lazyOwl"]'):
                        images_360.append(img_tag.get('src'))
                    product.images_360 = images_360
                except Exception as e: 
                    self.print_logs(f'Exception in metafields.img_360_urls: {e}')
                    sleep(0.15)
        except Exception as e: self.print_logs(f'Exception in scrape_product_metafields: {e}')
        return metafields

    def scrape_product_variant(self, product: Product, metafields: Metafields, soup: BeautifulSoup) -> Variant:
        variant = Variant()
        try:
            if metafields.size_bridge_template: 
                variant.title = str(metafields.size_bridge_template).split('-')[0].strip()
                variant.size = str(metafields.size_bridge_template).strip().replace(' ', '')
            if variant.title: variant.sku = f'{product.number} {product.frame_code} {variant.title}'
            else: variant.sku = f'{product.number} {product.frame_code}'

            try:
                for span_tag in soup.select('div[class^="srp price-srp"] >span'):
                    if '€' in str(span_tag.text).strip(): 
                        variant.listing_price = str(span_tag.text).strip().replace('€', '').strip().replace('1\u202f', '')
                        
                        if '.' in variant.listing_price: variant.listing_price = variant.listing_price.replace(',', '')
                        else: variant.listing_price = variant.listing_price.replace(',', '.')
                        
                        if variant.listing_price: variant.listing_price = float(variant.listing_price)
                        break
            except Exception as e: 
                self.print_logs(f'Exception in variant.price: {e} for {product.number}-{product.frame_code}')
                sleep(0.15)
            variant.found_status = 1

            try:
                if '/available.svg' in soup.select_one('div[class^="package-status"] > img').get('src'):
                    variant.inventory_quantity = 5
                else: variant.inventory_quantity = 0
            except: variant.inventory_quantity = 0
        
            try:
                for div in reversed(soup.select('div[id="kering-product-characteristics"] > div[id="kering-product-characteristics-collapsable"] > div[class="col-sm-6 col-xs-12"]')):
                    if str(div.select_one('span[class*="characteristics-title"]').text).strip().lower() == 'upc':
                        value = str(div.find_all('span')[1].text).strip()
                        if value != 'None': variant.barcode_or_gtin = value
                        break
            except Exception as e: 
                self.print_logs(f'Exception in variant.barcode_or_gtin: {e}')
                sleep(0.15)
        except Exception as e: self.print_logs(f'Exception in scrape_product_variant: {e}')
        return variant

class Keringeyewear_Scraper:
    def __init__(self, DEBUG: bool, result_filename: str, logs_filename: str, chrome_path: str) -> None:
        self.DEBUG = DEBUG
        self.result_filename = result_filename
        self.logs_filename = logs_filename
        self.max_threads = 15
        self.myScrapingThreadController_obj = myScrapingThreadController(self.max_threads, self.DEBUG, self.logs_filename)
        self.chrome_options = Options()
        self.chrome_options.add_argument('--disable-infobars')
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.browser = webdriver.Chrome(service=ChromeService(chrome_path), options=self.chrome_options)
        pass

    def controller(self, store: Store) -> None:
        try:

            self.initialize_browser(store)
            if self.login(store.username, store.password):

                for brand in store.brands:
                    print(f'Brand: {brand.name}')
                    self.print_logs(f'Brand: {brand.name}')
                    
                    for glasses_type in brand.product_types:

                        try: ActionChains(self.browser).move_to_element(self.browser.find_element(By.CSS_SELECTOR, 'li[class="col-md-auto plp-menu"]')).perform()
                        except: pass
                        sleep(0.8)

                        brand_url = self.get_brand_url(brand)
                        
                        if brand_url:
                            brand_url_with_glasses_type = str(brand_url).strip().replace('&type=Style', '%3AarticleType%3ASun&target=product&type=Style#') if glasses_type == 'Sunglasses' else str(brand_url).strip().replace('&type=Style', '%3AarticleType%3AOptical&target=product&type=Style#')
                            
                            self.open_new_tab(brand_url_with_glasses_type)
                            self.wait_until_loading()
                            
                            total_products = self.get_total_products()
                            if int(total_products) == 0:
                                login_flag = False

                                while not login_flag:
                                    if self.login(store.username, store.password):
                                        login_flag = True
                                        self.browser.get(brand_url_with_glasses_type)
                                        self.wait_until_loading()
                                        total_products = self.get_total_products()
                                    

                            print(f'Type: {glasses_type} | Total products: {total_products}')
                            start_time = datetime.now()
                            print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                            self.print_logs(f'Type: {glasses_type} | Total products: {total_products}')
                            self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                            product_cookies = self.get_cookies_for_product()
                            headers = self.get_headers_for_product(product_cookies, brand_url_with_glasses_type)
                            
                            if total_products and int(total_products) > 0: 
                                self.myScrapingThreadController_obj.printProgressBar(0, total_products, prefix = 'Progress:', suffix = 'Complete', length = 50)

                            for index, prod_json in enumerate(self.get_products_from_all_pages(glasses_type, total_products, brand_url_with_glasses_type)):

                                self.myScrapingThreadController_obj.create_thread(brand, glasses_type, prod_json.get('number'), prod_json.get('url'), headers)
                                if total_products and int(total_products) > 0: 
                                    self.myScrapingThreadController_obj.printProgressBar(index + 1, total_products, prefix = 'Progress:', suffix = 'Complete', length = 50)

                            # Wait for all threads to complete
                            self.myScrapingThreadController_obj.wait_for_thread_list_to_complete()
                            self.save_to_json(self.myScrapingThreadController_obj.data)
                            self.close_last_tab()

                        else: print(f'Brand url not found for {brand}')
                        end_time = datetime.now()
                        print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                        print('Duration: {}\n'.format(end_time - start_time))

                        self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                        self.print_logs('Duration: {}\n'.format(end_time - start_time))


                        ActionChains(self.browser).move_to_element(self.browser.find_element(By.CSS_SELECTOR, 'div[class="logo"]')).perform()
                        sleep(0.5)
            else: print(f'Failed to login \nURL: {store.link}\nUsername: {str(store.username)}\nPassword: {str(store.password)}')

        except Exception as e: self.print_logs(f'Exception in Keringeyewear_Scraper controller: {e}')
        finally: self.browser.quit()

    def initialize_browser(self, store: Store) -> None:
        try:
            self.browser.get(store.link)
            self.wait_until_browsing()
            self.accept_cookies()
        except Exception as e: self.print_logs(f'Exception in initialize_browser: {e}')

    def wait_until_browsing(self) -> None:
        while True:
            try:
                state = self.browser.execute_script('return document.readyState; ')
                if 'complete' == state: break
                else: sleep(0.2)
            except: pass

    def accept_cookies(self) -> None:
        try:
            self.wait_until_element_found(40, 'xpath', '//button[@id="onetrust-accept-btn-handler"]')
            sleep(3)
            self.browser.find_element(By.XPATH, '//button[@id="onetrust-accept-btn-handler"]').click()
            sleep(2)
        except Exception as e: self.print_logs(f'Exception in accept_cookies: {str(e)}')

    def get_cookie_value(self, cookie_name):
        cookie_value = ''
        try:
            for browser_cookie in self.browser.get_cookies():
                if browser_cookie['name'] == cookie_name:
                    cookie_value = browser_cookie['value']
        except Exception as e: self.print_logs(f'Exception in get_cookie_value: {e}')
        finally: return cookie_value

    def wait_until_element_found(self, wait_value: int, type: str, value: str) -> bool:
        flag = False
        try:
            locator_types = {
                'id': By.ID,
                'xpath': By.XPATH,
                'css_selector': By.CSS_SELECTOR,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME
            }

            if type in locator_types:
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((locator_types[type], value)))
                flag = True
        except: pass
        finally: return flag

    def login(self, username: str, password: str) -> bool:
        login_flag = False
        try:
            if self.wait_until_element_found(20, 'xpath', '//input[@name="j_username"]'):
                self.browser.find_element(By.XPATH, '//input[@name="j_username"]').send_keys(username)
                if self.wait_until_element_found(20, 'xpath', '//input[@name="j_password"]'):
                    self.browser.find_element(By.XPATH, '//input[@name="j_password"]').send_keys(password)
                    if self.wait_until_element_found(20, 'xpath', '//button[@name="login"]'):
                        self.browser.find_element(By.XPATH, '//button[@name="login"]').click()
                        for _ in range(0, 50):
                            if self.browser.current_url == 'https://my.keringeyewear.com/en/':
                                login_flag = True
                                break
                            else: sleep(0.3)
        except Exception as e: self.print_logs(f'Exception in login: {str(e)}')
        finally: return login_flag
    
    def wait_until_loading(self) -> None:
        while True:
            try:
                style_class = self.browser.find_element(By.XPATH, '//div[@id="spinner"]').get_attribute('style')
                if 'display: none;' in style_class: break
                else: sleep(0.3)
            except: pass

    def is_xpath_found(self, xpath: str) -> bool:
        try:
            self.browser.find_element(By.XPATH, xpath)
            return True
        except: return False

    def wait_until_xpath_found(self, xpath: str) -> bool:
        for _ in range(0, 100):
            try:
                self.browser.find_element(By.XPATH, xpath)
                return True
            except: sleep(0.5)
        return False

    def wait_until_css_selector_found(self, css_selector: str) -> bool:
        for _ in range(0, 100):
            try:
                self.browser.find_element(By.CSS_SELECTOR, css_selector)
                return True
            except: sleep(0.5)
        return False

    def open_new_tab(self, url: str) -> None:
        # open category in new tab
        self.browser.execute_script('window.open("'+str(url)+'","_blank");')
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])
        self.wait_until_browsing()
    
    def close_last_tab(self) -> None:
        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])

    def save_to_json(self, products: list[Product]) -> None:
        try:
            json_products = []
            for product in products:
                _id = ''
                if product.lens_code: _id = f"{str(product.number).strip().upper()}_{str(product.frame_code).strip().upper()}_{str(product.lens_code).strip().upper()}"
                else: _id = f"{str(product.number).strip().upper()}_{str(product.frame_code).strip().upper()}"

                json_varinats = []
                for variant in product.variants:
                    json_varinat = {
                        "_id": str(variant.sku).strip().upper().replace(' ', '_'),
                        "product_id": _id,
                        'title': str(variant.title).strip(), 
                        'sku': str(variant.sku).strip().upper(), 
                        'inventory_quantity': int(variant.inventory_quantity),
                        'found_status': int(variant.found_status),
                        'wholesale_price': float(variant.wholesale_price),
                        'listing_price': float(variant.listing_price), 
                        'barcode_or_gtin': str(variant.barcode_or_gtin).strip(),
                        'size': str(variant.size).strip().replace(' ', '')
                    }
                    json_varinats.append(json_varinat)

                
                json_product = {
                    "_id": _id,
                    'number': str(product.number).strip().upper(), 
                    'name': str(product.name).strip().title(),
                    'brand': str(product.brand).strip().title(),
                    'frame_code': str(product.frame_code).strip().upper(),
                    'lens_code': product.lens_code,
                    'type': product.type, 
                    'bridge': product.bridge,
                    'template': product.template,
                    'metafields': {
                        'for_who': str(product.metafields.for_who).strip().title(),
                        'lens_material': str(product.metafields.lens_material).strip().title(),
                        'lens_technology': str(product.metafields.lens_technology).strip().title(),
                        'lens_color': str(product.metafields.lens_color).strip().title(),
                        'frame_shape': str(product.metafields.frame_shape).strip().title(),
                        'frame_material': str(product.metafields.frame_material).strip().title(),
                        'frame_color': str(product.metafields.frame_color).strip().title(),
                        'size-bridge-template': str(product.metafields.size_bridge_template).strip(),
                        'gtin1': str(product.metafields.gtin1).strip()
                    },
                    'image': str(product.image).strip(),
                    'tags': product.tags,
                    'images_360': product.images_360,
                    'variants': json_varinats
                }
                json_products.append(json_product)
            
           
            with open(self.result_filename, 'w') as f: json.dump(json_products, f)
            
        except Exception as e: self.print_logs(f'Exception in save_to_json: {e}')
    
    def get_brand_url(self, brand: Brand) -> str:
        brand_url = ''
        try:
            for _ in range(0, 20):
                try:
                    for a_tag in self.browser.find_elements(By.CSS_SELECTOR, 'div[class*="menu-open brands"] > div[class^="col-md-2"] > a'):
                        if str(brand.name).strip().lower() == unidecode(str(a_tag.text).strip().lower()):
                            brand_url = a_tag.get_attribute("href")
                            if brand_url: break
                except: sleep(0.5)
                if brand_url: break
        except Exception as e: self.print_logs(f'Exception in get_brand_url: {e}')
        finally: return brand_url

    def get_total_products(self) -> int:
        total_products = 0
        try:
            # total_products = len(self.browser.find_elements(By.XPATH, '//div[@class="product-item space purchasable-plp set-border "]'))
            if self.wait_until_element_found(50, 'xpath', "//div[contains(text(), 'items found')]"):
                total_products = int(str(self.browser.find_element(By.XPATH, "//div[contains(text(), 'items found')]").text).strip().split(' ')[0])
        except Exception as e: self.print_logs(f'Exception in get_brand_url: {e}')
        finally: return total_products

    def get_products_from_all_pages(self, glasses_type: str, total_products: int, brand_url_with_glasses_type: str) -> list[dict]:
        products_data = self.get_products_on_first_page()
        products_data = self.get_products_on_other_pages(products_data, glasses_type, total_products, brand_url_with_glasses_type)
        return products_data

    def get_products_on_first_page(self ) -> list[dict]:
        products_data = []
        try:
            for product_div in self.browser.find_elements(By.XPATH, '//div[@class="product-item space purchasable-plp set-border "]'):
                try:
                    product_url = product_div.find_element(By.CSS_SELECTOR, 'a[class^="name"]').get_attribute('data-producturl')
                    if 'https://my.keringeyewear.com' not in product_url: product_url = f'https://my.keringeyewear.com{product_url}'
                    product_number = str(product_div.find_element(By.CSS_SELECTOR, 'a[class^="name"] > span').text).strip()
                    prod_json = { 'number': product_number, 'url': product_url }
                    if prod_json not in products_data: products_data.append(prod_json)
                except Exception as e: self.print_logs(f'Exception in product_div loop: {e}')
        except Exception as e: self.print_logs(f'Exception in get_products_on_first_page: {e}')
        finally: return products_data

    def get_products_on_other_pages(self, products_data: list[dict], glasses_type: str, total_products: int, brand_url: str) -> list[dict]:
        try:
            url = f'https://my.keringeyewear.com/en/Brands/{str(brand_url).split("?")[0].split("/")[-3]}/c/{str(brand_url).split("?")[0].split("/")[-1]}/showMore'
            page_cookies = self.get_cookies_for_next_page()
            headers = self.get_headers_for_page(page_cookies, brand_url)
            
            page = 1
            params = {}
            total_pages = int((int(total_products)-20) / 8) + 1
            if total_pages < float(int(total_products) / 8): total_pages += 1

            # while len(products_data) < int(total_products):
            while len(products_data) < int(total_products) and page <= total_pages:
                try:
                    if glasses_type == 'Sunglasses': params = { 'q': ':relevance:articleType:Sun:type:Style:brandCode:', 'type': 'Style', 'page': page, 'pageSize': 8 }
                    elif glasses_type == 'Eyeglasses': params = { 'q': ':relevance:articleType:Optical:type:Style:brandCode:', 'type': 'Style', 'page': page, 'pageSize': 8 }

                    response = requests.get(url=url, params=params, headers=headers)
                    self.print_logs(f'{url}: url, page: {page}, total_pages: {total_pages}, status_code: {response.status_code}, total_products: {total_products}, scraped_products: {len(products_data)}')
                    if response.status_code == 200:
                        page += 1
                        soup = BeautifulSoup(response.text, 'lxml')
                        for a_tag in soup.select('div[class="details brand"] > a[data-product]'):
                            product_url = a_tag.get('data-producturl')
                            if 'https://my.keringeyewear.com' not in product_url: product_url = f'https://my.keringeyewear.com{product_url}'
                            product_number = str(a_tag.text).strip()
                            prod_json = { 'number': product_number, 'url': product_url }
                            if prod_json not in products_data: products_data.append(prod_json)
                    else:
                        self.print_logs(f'{response.status_code} for {url} and params {params}')
                        if response.status_code == 404: break
                except Exception as e: self.print_logs(f'Exception in get_products_on_other_pages loop: {e}')
            self.print_logs(f'{url}: url, page: {page}, total_pages: {total_pages}, total_products: {total_products}, scraped_products: {len(products_data)}')

        except Exception as e: self.print_logs(f'Exception in get_products_on_other_pages: {e}')
        finally: return products_data

    def get_cookies_for_product(self) -> str:
        cookies = ''
        try:
            cookies = f"HYBRIS-SRV={self.get_cookie_value('HYBRIS-SRV')}; JSESSIONID={self.get_cookie_value('JSESSIONID')}; anonymous-consents={self.get_cookie_value('anonymous-consents')}; "
            cookies += f"cookie-notification={self.get_cookie_value('cookie-notification')}; ROUTE={self.get_cookie_value('ROUTE')}; ASLBSA={self.get_cookie_value('ASLBSA')}; ASLBSACORS={self.get_cookie_value('ASLBSACORS')}; "
            cookies += f"__utma={self.get_cookie_value('__utma')}; __utmc={self.get_cookie_value('__utmc')}; __utmz={self.get_cookie_value('__utmz')}; __utmt={self.get_cookie_value('__utmt')}; "
            cookies += f"OptanonAlertBoxClosed={self.get_cookie_value('OptanonAlertBoxClosed')}; _ga={self.get_cookie_value('_ga')}; _gid={self.get_cookie_value('_gid')}; securityToken={self.get_cookie_value('securityToken')}; "
            cookies += f"acceleratorSecureGUID={self.get_cookie_value('acceleratorSecureGUID')}; UPSELLsun3={self.get_cookie_value('UPSELLsun3')}: UPSELLoptical3={self.get_cookie_value('UPSELLoptical3')}; _gat_gtag_UA_72952013_2=1; "
            cookies += f"__utmb={self.get_cookie_value('__utmb')}; OptanonConsent={self.get_cookie_value('OptanonConsent')}"
        except Exception as e: self.print_logs(f'Exception in get_cookies: {e}')
        finally: return cookies

    def get_cookies_for_next_page(self) -> str:
        cookies = ''
        try:
            cookies = f"anonymous-consents={self.get_cookie_value('anonymous-consents')}; "
            cookies += f"ASLBSA={self.get_cookie_value('ASLBSA')}; "
            cookies += f"ASLBSACORS={self.get_cookie_value('ASLBSACORS')}; "
            cookies += f"cookie-notification={self.get_cookie_value('cookie-notification')}; "
            cookies += f"HYBRIS-SRV={self.get_cookie_value('HYBRIS-SRV')}; "
            cookies += f"JSESSIONID={self.get_cookie_value('JSESSIONID')}; "
            cookies += f"ROUTE={self.get_cookie_value('ROUTE')}; "
            cookies += f"__utma={self.get_cookie_value('__utma')}; "
            cookies += f"__utmc={self.get_cookie_value('__utmc')}; "
            cookies += f"__utmz={self.get_cookie_value('__utmz')}; "
            cookies += f"__utmt={self.get_cookie_value('__utmt')}; "
            cookies += f"OptanonAlertBoxClosed={self.get_cookie_value('OptanonAlertBoxClosed')}; "
            cookies += f"_ga={self.get_cookie_value('_ga')}; "
            cookies += f"_gid={self.get_cookie_value('_gid')}; "
            cookies += f"securityToken={self.get_cookie_value('securityToken')}; "
            cookies += f"UPSELL4={self.get_cookie_value('UPSELL4')}; "
            cookies += f"SERVERID={self.get_cookie_value('SERVERID')}; "
            cookies += f"__utmb={self.get_cookie_value('__utmb')}; "
            cookies += f"OptanonConsent={self.get_cookie_value('OptanonConsent')}"
        except Exception as e: self.print_logs(f'Exception in get_cookies_for_next_page: {e}')
        finally: return cookies

    def get_headers_for_product(self, cookies: str, brand_url: str) -> dict:
        return {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                # 'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'priority': 'u=0, i',
                'cookie': cookies,
                'referer': brand_url,
                # 'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.browser.execute_script('return navigator.userAgent;')
            }
    
    def get_headers_for_page(self, cookies: str, brand_url: str) -> dict:
        return {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9',
                'cookie': cookies,
                'referer': brand_url,
                'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest'
            }

    # print logs to the log file
    def print_logs(self, log: str) -> None:
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

    

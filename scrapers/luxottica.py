import math
import json
import requests
import threading
import datetime
from time import sleep
from datetime import datetime
from selenium import webdriver
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

from modules.query_processor import Query_Processor

class myScrapingThread(threading.Thread):
    def __init__(self, threadID: int, name: str, obj, varinat: dict, brand: Brand, glasses_type: str, headers: dict, tokenValue: str) -> None:
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.variant = varinat
        self.brand = brand
        self.glasses_type = glasses_type
        self.headers = headers
        self.tokenValue = tokenValue
        self.obj = obj
        self.status = 'in progress'
        pass

    def run(self):
        self.obj.get_variants(self.variant, self.brand, self.glasses_type, self.headers, self.tokenValue)
        self.status = 'completed'

    def active_threads(self):
        return threading.activeCount()


class Luxottica_Scraper:
    def __init__(self, DEBUG: bool, result_filename: str, logs_filename: str) -> None:
        self.DEBUG = DEBUG
        self.data = []
        self.result_filename = result_filename
        self.logs_filename = logs_filename
        self.thread_list = []
        self.thread_counter = 0
        self.chrome_options = Options()
        self.chrome_options.add_argument('--disable-infobars')
        self.chrome_options.add_argument("--start-maximized")
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # self.args = ["hide_console", ]
        # self.browser = webdriver.Chrome(options=self.chrome_options, service_args=self.args)
        self.browser = webdriver.Chrome(options=self.chrome_options)
        pass

    def controller(self, store: Store, query_processor: Query_Processor) -> None:
        try:
            cookies = ''
            dtPC = ''
            self.browser.get(store.link)
            self.wait_until_browsing()

            if self.login(store.link, store.username, store.password):
                sleep(10)
                for brand in store.brands:
                    
                    brand_url: str = self.get_brand_url(brand, query_processor)
                    # print(f'Brand: {brand.name}')
                    self.print_logs(f'Brand: {brand.name}')

                    if brand_url:
                        for glasses_type in brand.product_types:
                            # if glasses_type_index != 0:
                            #     self.browser.get('https://my.essilorluxottica.com/myl-it/en-GB/homepage')

                            self.browser.get(brand_url)
                            self.wait_until_browsing()
                            sleep(5)

                            if self.select_category(brand_url, glasses_type):
                                category_url = str(self.browser.current_url).strip()
                                total_products = self.get_total_products_for_brand()

                                # print(f'Total products found: {total_products} | Type: {glasses_type}')
                                self.print_logs(f'Total products found: {total_products} | Type: {glasses_type}')

                                if int(total_products) > 0:
                                    page_number = 1
                                    scraped_products = 0
                                    start_time = datetime.now()
                                    # print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                                    self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                                    self.printProgressBar(0, int(total_products), prefix = 'Progress:', suffix = 'Complete', length = 50)

                                    while int(scraped_products) != int(total_products):
                                        for product_div in self.get_product_divs_on_page():
                                            try:
                                                try:
                                                    ActionChains(self.browser).move_to_element(product_div.find_element(By.CSS_SELECTOR, 'div[class^="Tile__SeeAllContainer"] > div > button')).perform()
                                                except: pass
                                                
                                                scraped_products += 1
                                                url = str(product_div.find_element(By.CSS_SELECTOR, 'a[class^="Tile__ImageContainer"]').get_attribute('href'))
                                                identifier = str(url).split('/')[-1].strip()
                                                if not cookies: cookies = self.get_cookies_from_browser(identifier)

                                                headers = self.get_headers(cookies, url, dtPC)
                                                tokenValue = self.get_tokenValue(identifier, headers)
                                                if tokenValue:
                                                    parentCatalogEntryID = self.get_parentCatalogEntryID(tokenValue, headers)
                                                    if parentCatalogEntryID:
                                                        variants = self.get_all_variants_data(parentCatalogEntryID, headers)

                                                        for variant in variants:
                                                            self.create_thread(variant, brand,  glasses_type, headers, tokenValue)

                                            except Exception as e:
                                                if self.DEBUG: print(f'Exception in loop: {e}')
                                                self.print_logs(f'Exception in loop: {e}')

                                            if self.thread_counter >= 50:
                                                self.wait_for_thread_list_to_complete()
                                                self.save_to_json(self.data)
                                            self.printProgressBar(scraped_products, int(total_products), prefix = 'Progress:', suffix = 'Complete', length = 50)


                                        if int(scraped_products) < int(total_products):
                                            page_number += 1
                                            self.move_to_next_page(category_url, page_number)
                                            self.wait_until_element_found(40, 'css_selector', 'div[class^="PLPTitle__Section"] > p[class^="CustomText__Text"]')
                                            total_products = self.get_total_products_for_brand()
                                        else: break

                                    self.wait_for_thread_list_to_complete()
                                    self.save_to_json(self.data)

                                    end_time = datetime.now()

                                    # print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                                    # print('Duration: {}\n'.format(end_time - start_time))
                                    self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                                    self.print_logs('Duration: {}\n'.format(end_time - start_time))
                            else: print(f'Cannot find {glasses_type} for {brand.name}')

            else: print(f'Failed to login \nURL: {store.link}\nUsername: {str(store.username)}\nPassword: {str(store.password)}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in Luxottica_All_Scraper controller: {e}')
            self.print_logs(f'Exception in Luxottica_All_Scraper controller: {e}')
        finally:
            self.browser.quit()
            self.wait_for_thread_list_to_complete()
            self.save_to_json(self.data)

    def wait_until_browsing(self) -> None:
        while True:
            try:
                state = self.browser.execute_script('return document.readyState; ')
                if 'complete' == state: break
                else: sleep(0.2)
            except: pass

    def wait_until_element_found(self, wait_value: int, type: str, value: str) -> bool:
        flag = False
        try:
            if type == 'id':
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((By.ID, value)))
                flag = True
            elif type == 'xpath':
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((By.XPATH, value)))
                flag = True
            elif type == 'css_selector':
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((By.CSS_SELECTOR, value)))
                flag = True
            elif type == 'class_name':
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((By.CLASS_NAME, value)))
                flag = True
            elif type == 'tag_name':
                WebDriverWait(self.browser, wait_value).until(EC.presence_of_element_located((By.TAG_NAME, value)))
                flag = True
        except: pass
        finally: return flag

    def accept_cookies_before_login(self) -> None:
        try:
            if self.wait_until_element_found(5, 'css_selector', 'div[class^="CookiesBanner__SecondButtonWrap"] > button'):
                self.browser.find_element(By.CSS_SELECTOR, 'div[class^="CookiesBanner__SecondButtonWrap"] > button').click()
                sleep(0.3)
        except Exception as e:
            self.print_logs(f'Exception in accept_cookies_before_login: {str(e)}')
            if self.DEBUG: print(f'Exception in accept_cookies_before_login: {str(e)}')

    def accept_cookies_after_login(self) -> None:
        try:
            if self.wait_until_element_found(5, 'css_selector', 'div[class^="CookiesContent__Container"] > div > button[class$="underline"]'):
                btn = self.browser.find_element(By.CSS_SELECTOR, 'div[class^="CookiesContent__Container"] > div > button[class$="underline"]')
                ActionChains(self.browser).move_to_element(btn).click().perform()
                sleep(0.3)
        except Exception as e:
            self.print_logs(f'Exception in accept_cookies_after_login: {str(e)}')
            if self.DEBUG: print(f'Exception in accept_cookies_after_login: {str(e)}')

    def login(self, url, username: str, password: str) -> bool:
        login_flag = False
        while not login_flag:
            try:
                self.accept_cookies_before_login()
                if self.wait_until_element_found(10, 'xpath', '//input[@id="signInName"]'):
                    for _ in range(0, 30):
                        try:
                            self.browser.find_element(By.XPATH, '//input[@id="signInName"]').send_keys(username)
                            break
                        except: sleep(0.3)
                    sleep(0.2)

                    if self.wait_until_element_found(20, 'xpath', '//button[@id="continue"]'):
                        for _ in range(0, 30):
                            try:
                                self.browser.find_element(By.XPATH, '//button[@id="continue"]').click()
                                break
                            except: sleep(0.3)

                        if self.wait_until_element_found(20, 'xpath', '//input[@id="password"]'):
                            for _ in range(0, 30):
                                try:
                                    self.browser.find_element(By.XPATH, '//input[@id="password"]').send_keys(password)
                                    break
                                except: sleep(0.5)
                            sleep(0.2)
                            self.browser.find_element(By.XPATH, '//button[@id="next"]').click()
                            self.wait_until_browsing()
                            for _ in range(0, 100):
                                try:
                                    a = self.browser.find_element(By.CSS_SELECTOR, 'div[class^="AccountMenu__MenuContainer"]')
                                    if a:
                                        login_flag = True
                                        if '/myl-it/it-IT/homepage' in self.browser.current_url:
                                            self.browser.get('https://my.essilorluxottica.com/myl-it/en-GB/homepage')
                                        self.accept_cookies_after_login()
                                        break
                                    else: sleep(0.3)
                                except: sleep(0.3)
                        else: print('Password input not found')
                else: print('Email input not found')
            except Exception as e:
                self.print_logs(f'Exception in login: {str(e)}')
                if self.DEBUG: print(f'Exception in login: {str(e)}')

            if not login_flag:
                self.browser.get(url)
                self.wait_until_browsing()
        return login_flag

    def open_new_tab(self, url: str) -> None:
        # open category in new tab
        self.browser.execute_script('window.open("'+str(url)+'","_blank");')
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])
        self.wait_until_browsing()

    def select_category(self, brand_url: str, glasses_type: str) -> bool:
        category_found = False
        try:
            category_css_selector = ''
            if glasses_type == 'Sunglasses': category_css_selector = 'button[data-element-id^="Categories_sunglasses_"]'
            elif glasses_type == 'Sunglasses Kids': category_css_selector = 'button[data-element-id^="Categories_sunglasses-kids"]'
            elif glasses_type == 'Eyeglasses': category_css_selector = 'button[data-element-id^="Categories_eyeglasses_"]'
            elif glasses_type == 'Eyeglasses Kids': category_css_selector = 'button[data-element-id^="Categories_eyeglasses-kids"]'
            elif glasses_type == 'Ski & Snowboard Goggles': category_css_selector = 'button[data-element-id^="Categories_gogglesHelmets"]'

            if self.wait_until_element_found(30, 'css_selector', category_css_selector):
                category_found = True

                for _ in range(0, 100):
                    element = None
                    try:
                        element = self.browser.find_element(By.CSS_SELECTOR, category_css_selector)
                        ActionChains(self.browser).move_to_element(element).perform()
                        sleep(0.5)
                        ActionChains(self.browser).move_to_element(element).click().perform()
                        sleep(0.4)
                    except:
                        try:
                            self.browser.execute_script("arguments[0].scrollIntoView();", element)
                            sleep(0.5)
                            element.click()
                            sleep(0.4)
                        except: sleep(0.4)

                    if 'frames?PRODUCT_CATEGORY_FILTER=' in self.browser.current_url:
                        if glasses_type != 'Ski & Snowboard Goggles':
                            if glasses_type.strip().lower().replace(' ', '+') in str(self.browser.current_url).lower(): break
                            else: 
                                self.browser.get(brand_url)
                                self.wait_until_browsing()
                                sleep(5)
                        else:
                            break
                    else: sleep(0.23)

                for _ in range(0, 100):
                    try:
                        value = str(self.browser.find_element(By.CSS_SELECTOR, 'div[class^="PLPTitle__Section"] > p[class^="CustomText__Text"]').text).strip()
                        if '(' in value or ')' in value: break
                    except: sleep(0.5)

        except Exception as e:
            if self.DEBUG: print(f'Exception in select_category: {e}')
            self.print_logs((f'Exception in select_category: {e}'))
        finally: return category_found

    def get_brand_url(self, brand: Brand, query_processor: Query_Processor) -> str:
        url = ''
        try:
            url = query_processor.get_brand_url(str(brand.name).strip().lower())
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_brand_url: {e}')
            self.print_logs((f'Exception in select_category: {e}'))
        finally: return url

        # if str(brand.name).strip().lower() == 'arnette':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/arnette'
        # elif str(brand.name).strip().lower() == 'burberry':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/burberry'
        # elif str(brand.name).strip().lower() == 'bvlgari':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/bvlgari'
        # elif str(brand.name).strip().lower() == 'dolce & gabbana':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/dolce-gabbana'
        # elif str(brand.name).strip().lower() == 'ess':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/ess'
        # elif str(brand.name).strip().lower() == 'emporio armani':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/emporio-armani'
        # elif str(brand.name).strip().lower() == 'giorgio armani':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/giorgio-armani'
        # elif str(brand.name).strip().lower() == 'luxottica':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/luxottica'
        # elif str(brand.name).strip().lower() == 'michael kors':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/michael-kors'
        # elif str(brand.name).strip().lower() == 'oakley':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/oakley'
        # elif str(brand.name).strip().lower() == 'persol':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/persol'
        # elif str(brand.name).strip().lower() == 'polo ralph lauren':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/polo-ralph-lauren'
        # elif str(brand.name).strip().lower() == 'prada':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/prada'
        # elif str(brand.name).strip().lower() == 'prada linea rossa':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/prada-linea-rossa'
        # elif str(brand.name).strip().lower() == 'ralph':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/ralph'
        # elif str(brand.name).strip().lower() == 'ralph lauren':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/ralph-lauren'
        # elif str(brand.name).strip().lower() == 'ray-ban':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/ray-ban'
        # elif str(brand.name).strip().lower() == 'sferoflex':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/sferoflex'
        # elif str(brand.name).strip().lower() == 'valentino':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/valentino'
        # elif str(brand.name).strip().lower() == 'versace':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/versace'
        # elif str(brand.name).strip().lower() == 'vogue':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/vogue'
        # elif str(brand.name).strip().lower() == 'miu miu':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/miu-miu'
        # elif str(brand.name).strip().lower() == 'tiffany':
        #     url = 'https://my.essilorluxottica.com/myl-it/en-GB/preplp/tiffany'
        # return url

    def close_last_tab(self) -> None:
        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])

    def get_total_products_for_brand(self) -> int:
        total_products = 0
        try:
            for _ in range(0, 200):
                try:
                    total_sunglasses = str(self.browser.find_element(By.CSS_SELECTOR, 'div[class^="PLPTitle__Section"] > p[class^="CustomText__Text"]').text).strip()
                    if '(' in total_sunglasses:
                        # if 'Sunglasses' in total_sunglasses:
                        #     total_sunglasses = total_sunglasses.replace('Sunglasses', '').replace('(', '').replace(')', '').strip()
                        # elif 'Eyeglasses' in total_sunglasses:
                        #     total_sunglasses = total_sunglasses.replace('Eyeglasses', '').replace('(', '').replace(')', '').strip()
                        # elif 'Goggles and helmets' in total_sunglasses:
                        #     total_sunglasses = total_sunglasses.replace('Goggles and helmets', '').replace('(', '').replace(')', '').strip()
                        total_sunglasses = total_sunglasses.split('(')[-1].strip().replace(')', '').strip()
                        if total_sunglasses: total_products = int(total_sunglasses)
                        else: total_products = 0
                        break
                    else: sleep(0.3)
                except:
                    try:
                        text = str(self.browser.find_element(By.CSS_SELECTOR, 'div[class^="PLPGeneric__MainColumn"] > div > p').text).strip()
                        if 'Sorry, there are no products' in text: break
                        else: sleep(0.3)
                    except: sleep(0.3)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_total_products_and_pages: {str(e)}')
            self.print_logs(f'Exception in get_total_products_and_pages: {str(e)}')
        finally: return total_products

    def get_product_divs_on_page(self) -> list:
        product_divs = []
        for _ in range(0, 30):
            try:
                product_divs = self.browser.find_elements(By.CSS_SELECTOR, 'div[data-element-id="Tiles"] > div[class^="Tile"]')
                for product_div in product_divs:
                    product_number = str(product_div.get_attribute('data-description')).strip()
                    product_name = str(product_div.find_element(By.CSS_SELECTOR, 'div[class^="TileHeader__Header"] > div > span').text).strip()
                    total_varinats_for_product = str(product_div.find_element(By.CSS_SELECTOR, 'div[class^="Tile__ColorSizeContainer"] > div > span').text).strip()
                break
            except: sleep(0.2)
        return product_divs

    def move_to_next_page(self, brand_url: str, page_number: int) -> None:
        self.browser.get(f'{brand_url}&pageNumber={page_number}')
        self.wait_until_browsing()
        sleep(0.8)

    def save_to_json(self, products: list[Product]) -> None:
        try:
            json_products = []
            for product in products:
                product.number = str(product.number).replace('-', '/').strip()
                product.frame_code = str(product.frame_code).replace('-', '/').strip()
                product.lens_code = str(product.lens_code).replace('-', '/').strip()
                _id = ''
                if product.lens_code: _id = f"{str(product.number).strip().upper()}_{str(product.frame_code).strip().upper()}_{str(product.lens_code).strip().upper()}"
                else: _id = f"{str(product.number).strip().upper()}_{str(product.frame_code).strip().upper()}"

                json_varinats = []
                for variant in product.variants:
                    json_varinat = {
                        "_id": str(variant.sku).strip().upper().replace(' ', '_'),
                        "product_id": _id,
                        'title': str(variant.title).strip(),
                        'sku': str(variant.sku).strip().upper().replace('-', '/'),
                        'inventory_quantity': int(variant.inventory_quantity),
                        'found_status': int(variant.found_status),
                        'wholesale_price': float(variant.wholesale_price),
                        'listing_price': float(variant.listing_price),
                        'barcode_or_gtin': str(variant.barcode_or_gtin).strip(),
                        'size': str(variant.size).strip()
                    }
                    json_varinats.append(json_varinat)


                json_product = {
                    "_id": _id.replace(' ', '_'),
                    'number': str(product.number).strip().upper(),
                    'name': str(product.name).strip().title(),
                    'brand': str(product.brand).strip().title() if str(product.brand).strip().lower() != 'ray-ban' else 'Ray-ban',
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
                    'images_360': product.images_360,
                    'variants': json_varinats
                }
                json_products.append(json_product)


            with open(self.result_filename, 'w') as f: json.dump(json_products, f)

        except Exception as e:
            if self.DEBUG: print(f'Exception in save_to_json: {e}')
            self.print_logs(f'Exception in save_to_json: {e}')

    def get_cookies_from_browser(self, identifier: str) -> str:
        cookies = ''
        try:
            self.open_new_tab(f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/pages/identifier/{identifier}')
            sleep(2)
            browser_cookies = self.browser.get_cookies()

            for browser_cookie in browser_cookies:
                if browser_cookie['name'] == 'dtPC': dtPC = browser_cookie['value']
                cookies = f'{browser_cookie["name"]}={browser_cookie["value"]}; {cookies}'
            cookies = cookies.strip()[:-1]
            self.close_last_tab()
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_cookies_from_browser: {e}')
            self.print_logs(f'Exception in get_cookies_from_browser: {e}')
        finally: return cookies

    def get_variants(self, varinat: dict, brand: Brand, glasses_type: str, headers: dict, tokenValue: str):
        try:
            product = Product()
            product.brand = str(brand.name).strip()
            # product.url = f'https://my.essilorluxottica.com/myl-it/en-GB/pdp/{str(varinat["partNumber"]).replace(" ", "+").replace("_", "-").replace("/", "-").lower()}'
            product.number = str(varinat['partNumber']).strip().split('_')[0].strip()[1:]
            if str(varinat['name']).strip().upper != str(product.number).strip().upper():
                product.name = str(varinat['name']).strip()

            if str(product.name).strip() == '-': product.name = ''
            product.frame_code = str(varinat['partNumber']).strip().split('_')[-1].strip()
            # product.status = 'active'
            product.type = str(glasses_type).strip().title()

            prices = self.get_prices(varinat['uniqueID'], headers)

            # metafields = Metafields()

            properties = self.get_product_variants(varinat['uniqueID'], headers)
            if properties:
                product.metafields.frame_color = properties['frame_color']
                product.metafields.lens_color = properties['lens_color']
                product.metafields.for_who = properties['for_who']
                product.metafields.lens_material = properties['lens_material']
                product.metafields.frame_shape = properties['frame_shape']
                product.metafields.frame_material = properties['frame_material']
                product.metafields.lens_technology = properties['lens_technology']
                product.image = properties['img_url']


                sizes = properties['sizes']

                for size in sizes:
                    if str(size['size']).strip():
                        if not product.bridge:
                            try: product.bridge = str(size['size']).strip().split('-')[1].strip()
                            except: pass
                        if not product.template:
                            try: product.template = str(size['size']).strip().split('-')[-1].strip()
                            except: pass

                barcodes, product_sizes = [], []

                variants: list[Variant] = []
                for size in sizes:
                    variant = Variant()
                    variant.title = size['title']
                    variant.sku = f'{product.number} {product.frame_code} {variant.title}'
                    variant.inventory_quantity = size['inventory_quantity']
                    variant.found_status = 1
                    variant.barcode_or_gtin = size['UPC']
                    variant.size = str(size['size']).strip().replace(' ', '')
                    barcodes.append(size['UPC'])
                    product_sizes.append(variant.size)
                    for price in prices:
                        try:
                            if str(price['wholesale_price']).strip(): variant.wholesale_price = float(price['wholesale_price'])
                            else: variant.wholesale_price = 0.0
                        except: pass
                        try:
                            if str(price['listing_price']).strip(): variant.listing_price = float(price['listing_price'])
                            else: variant.listing_price = 0.0
                        except: pass
                    variants.append(variant)

                product.variants = variants

                product.metafields.size_bridge_template = ', '.join(product_sizes)
                product.metafields.gtin1 = ', '.join(barcodes)


                # for image360 in self.get_360_images(varinat['uniqueID'], headers):
                #     if image360 not in metafields.img_360_urls:
                #         metafields.img_360_urls = image360
                product.images_360 = self.get_360_images(varinat['uniqueID'], headers)
                if not product.images_360: product.images_360 = self.get_images(varinat['uniqueID'], headers)
                # product.metafields = metafields

                self.data.append(product)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_variants: {e}')
            self.print_logs(f'Exception in get_variants: {e}')

    def get_headers(self, cookie: str, referer: str, dtpc: str) -> dict:
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cookie': cookie,
            'referer': referer,
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
            'x-dtpc': dtpc
        }

    def get_tokenValue(self, identifier: str, headers: dict):
        tokenValue = ''
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/pages/identifier/{identifier}'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                if 'contents' in json_data['data']:
                    id = str(int(json_data['data']['contents'][0]['id']))
                    tokenValue = json_data['data']['contents'][0]['tokenValue']
                else: print(json_data['data'], identifier)
            else: print(f'Status code: {response.status_code} for id and tokenValue {response.text} {response.headers}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_tokenValue: {e}')
            self.print_logs(f'Exception in get_tokenValue: {e}')
        finally: return tokenValue

    def get_parentCatalogEntryID(self, tokenValue: str, headers: dict) -> str:
        parentCatalogEntryID = ''
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/variants/{tokenValue}'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                parentCatalogEntryID = json_data['data']['catalogEntryView'][0]['parentCatalogEntryID']
            else: print(f'Status code: {response.status_code} for parentCatalogEntryID')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_parentCatalogEntryID: {e}')
            self.print_logs(f'Exception in get_parentCatalogEntryID: {e}')
        finally: return parentCatalogEntryID

    def get_all_variants_data(self, parentCatalogEntryID: str, headers: str) -> list[dict]:
        variants = []
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/{parentCatalogEntryID}/variants'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                # print(json_data['data']['catalogEntryView'])
                for index, variant in enumerate(json_data['data']['catalogEntryView'][0]['variants']):
                    try:
                        name = ''
                        partNumber = variant['partNumber']
                        uniqueID = variant['uniqueID']
                        try: name = variant['name']
                        except: pass
                        # sizes, colors, lens_properties, lens_colors = [], [], [], []
                        # for attribute in variant['attributes']:
                        #     if attribute['identifier'] == 'DL_SIZE_CODE':
                        #         for value in attribute['values']:
                        #             size = value['value']
                        #             sizes.append(size)
                        #     elif attribute['identifier'] == 'FRONT_COLOR_DESCRIPTION':
                        #         for value in attribute['values']:
                        #             color = value['value']
                        #             colors.append(color)
                        #     elif attribute['identifier'] == 'LENS_PROPERTIES':
                        #         for value in attribute['values']:
                        #             lens_property = value['value']
                        #             lens_properties.append(lens_property)
                        #     elif attribute['identifier'] == 'LENS_COLOR_DESCRIPTION':
                        #         for value in attribute['values']:
                        #             lens_color = value['value']
                        #             lens_colors.append(lens_color)

                        variants.append({'sequence': (index+1), 'partNumber': partNumber, 'name': name, 'uniqueID': uniqueID})
                    except: pass
            else: print(f'Status code: {response.status_code} for get_all_variants_data')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_all_variants_data: {e}')
            self.print_logs(f'Exception in get_all_variants_data: {e}')
        finally: return variants

    def get_product_variants(self, uniqueID: str, headers: dict) -> dict:
        properties = {}
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/variants/{uniqueID}'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                frame_color, lens_color, for_who, lens_material, frame_shape, frame_material, lens_technology = '', '', '', '', '', '', ''
                img_url = ''
                try: img_url = f"{str(json_data['data']['catalogEntryView'][0]['fullImage']).strip()}?impolicy=MYL_EYE&wid=600"
                except: 
                    try: img_url = f"{str(json_data['data']['catalogEntryView'][0]['fullImageRaw']).strip()}?impolicy=MYL_EYE&wid=600"
                    except: pass
                for attribute in json_data['data']['catalogEntryView'][0]['attributes']:
                    values = []
                    if attribute['identifier'] == 'FRONT_COLOR_DESCRIPTION':
                        for value in attribute['values']: values.append(value['value'])
                        frame_color = ', '.join(values)
                    elif attribute['identifier'] == 'LENS_COLOR_DESCRIPTION':
                        for value in attribute['values']: values.append(value['value'])
                        lens_color = ', '.join(values)
                    elif attribute['identifier'] == 'GENDER':
                        for value in attribute['values']: values.append(value['value'])
                        for_who = ', '.join(values)
                    elif attribute['identifier'] == 'LENS_MATERIAL':
                        for value in attribute['values']: values.append(value['value'])
                        lens_material = ', '.join(values)
                    elif attribute['identifier'] == 'FACE_SHAPE':
                        for value in attribute['values']: values.append(value['value'])
                        frame_shape = ', '.join(values)
                    elif attribute['identifier'] == 'FRAME_MATERIAL':
                        for value in attribute['values']: values.append(value['value'])
                        frame_material = ', '.join(values)
                    elif attribute['identifier'] == 'PHOTOCHROMIC':
                        if attribute['values'][0]['value'] == 'TRUE':
                            if lens_technology: lens_technology += str(' PHOTOCHROMIC').title()
                            else: lens_technology = str('PHOTOCHROMIC').title()
                    elif attribute['identifier'] == 'POLARIZED':
                        if attribute['values'][0]['value'] == 'TRUE':
                            if lens_technology: lens_technology += str(' POLARIZED').title()
                            else: lens_technology = str('POLARIZED').title()

                if not str(lens_technology).strip():
                    for attribute in json_data['data']['catalogEntryView'][0]['attributes']:
                        if attribute['identifier'] == 'LENS_COLORING_PERCEIVED':
                            lens_technology = str(attribute['values'][0]['value']).strip()

                ids = []
                sizes_without_q = []
                for sKU in json_data['data']['catalogEntryView'][0]['sKUs']:
                    BRIDGE, SIZE, TEMPLE = '', '', ''
                    uniqueID = str(sKU['uniqueID'])
                    title = str(sKU['partNumber']).strip()[-2:]
                    upc = str(sKU['upc'])
                    ids.append(uniqueID)
                    for attribute in sKU['attributes']:
                        if attribute['identifier'] == 'BRIDGE_WIDTH':
                            BRIDGE = attribute['values'][0]['value']
                        elif attribute['identifier'] == 'FRAME_SIZE':
                            SIZE = attribute['values'][0]['value']
                        elif attribute['identifier'] == 'TEMPLE_LENGTH':
                            TEMPLE = attribute['values'][0]['value']

                    sizes_without_q.append({'uniqueID': uniqueID, 'title': title, 'UPC': upc, 'size': f'{BRIDGE}-{SIZE}-{TEMPLE}'})

                sizes = []
                json_response = self.check_availability('%2C'.join(ids), headers)
                for json_res in json_response:
                    productId = json_res['productId']
                    for size_without_q in sizes_without_q:
                        if productId == size_without_q['uniqueID']:
                            inventory_quantity = 0
                            # if json_res['inventoryStatus'] == 'Available': inventory_quantity = 5
                            try:
                                if int(float(json_res['availableQuantity'])) > 0: inventory_quantity = 5
                            except: self.print_logs(f"{size_without_q['UPC']} inventory quantity is {json_res['availableQuantity']}")
                            sizes.append(
                                {
                                    'title': size_without_q['title'],
                                    'inventory_quantity': inventory_quantity,
                                    "UPC": size_without_q['UPC'],
                                    "size": size_without_q['size']
                                }
                            )

                properties = {
                    'img_url': img_url,
                    'frame_color': frame_color,
                    'lens_color': lens_color,
                    'for_who': for_who,
                    'lens_material': lens_material,
                    'frame_shape': frame_shape,
                    'frame_material': frame_material,
                    'lens_technology': lens_technology,
                    'sizes': sizes
                }
            else: print(f'Status code: {response.status_code} for id and tokenValue')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_product_variants: {e}')
            self.print_logs(f'Exception in get_product_variants: {e}')
        finally: return properties

    def check_availability(self, payload: str, headers: dict) -> list[dict]:
        json_data = {}
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/availability?productId={payload}'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                json_data = json_data['data']
                json_data = json_data['doorInventoryAvailability'][0]['inventoryAvailability']
        except Exception as e:
            if self.DEBUG: print(f'Exception in check_availability: {e}')
            self.print_logs(f'Exception in check_availability: {e}')
        finally: return json_data

    def get_360_images(self, tokenValue: str, headers: dict) -> list[str]:
        image_360_urls = []
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/variants/{tokenValue}/attachments?type=PHOTO_360'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                if 'attachments' in json_data['data']['catalogEntryView'][0]:
                    for attachment in json_data['data']['catalogEntryView'][0]['attachments']:
                        image_360_url = str(attachment['attachmentAssetPath']).strip()
                        # if '?impolicy=MYL_EYE&wid=688' not in image_360_url:
                        #     image_360_url = f'{image_360_url}?impolicy=MYL_EYE&wid=688'
                        if image_360_url not in image_360_urls: image_360_urls.append(image_360_url)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_360_images: {e}')
            self.print_logs(f'Exception in get_360_images: {e}')
        finally: return image_360_urls

    def get_images(self, tokenValue: str, headers: dict) -> list[str]:
        image_urls = []
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/variants/{tokenValue}/attachments?type=PHOTO'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                if 'attachments' in json_data['data']['catalogEntryView'][0]:
                    for attachment in json_data['data']['catalogEntryView'][0]['attachments']:
                        image_360_url = str(attachment['attachmentAssetPath']).strip()
                        # if '?impolicy=MYL_EYE&wid=688' not in image_360_url:
                        #     image_360_url = f'{image_360_url}?impolicy=MYL_EYE&wid=688'
                        if image_360_url not in image_urls: image_urls.append(image_360_url)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_images: {e}')
            self.print_logs(f'Exception in get_images: {e}')
        finally: return image_urls

    def get_prices(self, tokenValue: str, headers: dict) -> list[str]:
        prices = []
        try:
            url = f'https://my.essilorluxottica.com/fo-bff/api/priv/v1/myl-it/en-GB/products/prices?productId={tokenValue}'
            response = self.get_response(url, headers)
            if response and response.status_code == 200:
                json_data = json.loads(response.text)
                for data in json_data['data']:
                    wholesale_price, listing_price = '', ''
                    try: wholesale_price = float(data[tokenValue]['OPT'][0]['price']['value'])
                    except: pass
                    try: listing_price = float(data[tokenValue]['PUB'][0]['price']['value'])
                    except: pass
                    prices.append({'wholesale_price': wholesale_price, 'listing_price': listing_price})
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_prices: {e}')
            self.print_logs(f'Exception in get_prices: {e}')
        finally: return prices

    def get_response(self, url: str, headers: dict):
        response = None
        for _ in range(0, 20):
            try:
                response = requests.get(url=url, headers=headers, timeout=25)
                if response.status_code == 200: break
                else: sleep(1)
            except: sleep(0.8)
        if response and response.status_code != 200: self.print_logs(f'{_} {response.status_code} for {url}')
        return response

    def printProgressBar(self, iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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

    # print logs to the log file
    def print_logs(self, log: str) -> None:
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

    def create_thread(self, varinat: dict, brand: Brand, glasses_type: str, headers: dict, tokenValue: str) -> None:
        thread_name = "Thread-"+str(self.thread_counter)
        self.thread_list.append(myScrapingThread(self.thread_counter, thread_name, self, varinat, brand,  glasses_type, headers, tokenValue))
        self.thread_list[self.thread_counter].start()
        self.thread_counter += 1

    def is_thread_list_complted(self) -> bool:
        for obj in self.thread_list:
            if obj.status == "in progress":
                return False
        return True

    def wait_for_thread_list_to_complete(self) -> None:
        while True:
            result = self.is_thread_list_complted()
            if result:
                self.thread_counter = 0
                self.thread_list.clear()
                break
            else: sleep(1)

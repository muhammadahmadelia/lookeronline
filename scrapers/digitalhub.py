
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

class myScrapingThread(threading.Thread):
    def __init__(self, threadID: int, name: str, obj, username: str, brand: Brand, product_number: str, glasses_type: str, headers: dict) -> None:
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.username = username
        self.brand = brand
        self.product_number = product_number
        self.glasses_type = glasses_type
        self.headers = headers
        self.obj = obj
        self.status = 'in progress'
        pass

    def run(self):
        self.obj.scrape_product(self.username, self.brand, self.product_number, self.glasses_type, self.headers)
        self.status = 'completed'

    def active_threads(self):
        return threading.activeCount()



class Digitalhub_Scraper:
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

    def controller(self, store: Store) -> None:
        try:
            cookies, fs_token = '', ''

            self.browser.get(store.link)
            self.wait_until_browsing()

            if self.login(store.username, store.password):
                self.browser.get('https://digitalhub.marcolin.com/shop')
                self.wait_until_browsing()

                if self.wait_until_element_found(20, 'xpath', '//div[@id="mCSB_1_container"]'):

                    for brand in store.brands:
                        # brand: Brand = brand_with_type['brand']
                        # print(f'Brand: {brand.name}')
                        self.print_logs(f'Brand: {brand.name}')

                        for glasses_type in brand.product_types:

                            brand_url = self.get_brand_url(brand, glasses_type)
                            self.open_new_tab(brand_url)
                            self.wait_until_browsing()
                            start_time = datetime.now()

                            if self.wait_until_element_found(90, 'xpath', '//div[@class="row mt-4 list grid-divider"]/div'):
                                total_products = self.get_total_products()
                                scraped_products = 0
                                
                                # print(f'Type: {glasses_type} | Total products: {total_products}')
                                # print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                                self.print_logs(f'Type: {glasses_type} | Total products: {total_products}')
                                self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                                self.printProgressBar(scraped_products, total_products, prefix = 'Progress:', suffix = 'Complete', length = 50)
                                while True:

                                    for product_data in self.get_all_products_from_page():
                                        product_number = str(product_data['number']).strip().upper()
                                        product_url = str(product_data['url']).strip()
                                        

                                        if not cookies: cookies = self.get_cookies()
                                        if not fs_token: fs_token = self.get_fs_token()
                                        headers = self.get_headers(fs_token, cookies, product_url)

                                        # self.scrape_product(store.username, brand, product_number, glasses_type, headers)
                                        self.create_thread(store.username, brand, product_number, glasses_type, headers)
                                        if self.thread_counter >= 50: 
                                            self.wait_for_thread_list_to_complete()
                                            self.save_to_json(self.data)
                                        scraped_products += 1

                                        self.printProgressBar(scraped_products, total_products, prefix = 'Progress:', suffix = 'Complete', length = 50)
                                    
                                    if self.is_next_page(): self.move_to_next_page()
                                    else: break

                            self.wait_for_thread_list_to_complete()
                            self.save_to_json(self.data)
                            end_time = datetime.now()
                            
                            # print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                            # print('Duration: {}\n'.format(end_time - start_time))

                            self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                            self.print_logs('Duration: {}\n'.format(end_time - start_time))
                            
                            self.close_last_tab()

            else: print(f'Failed to login \nURL: {store.link}\nUsername: {str(store.username)}\nPassword: {str(store.password)}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in Keringeyewear_Scraper controller: {e}')
            self.print_logs(f'Exception in Keringeyewear_Scraper controller: {e}')
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

    def login(self, username: str, password: str) -> bool:
        login_flag = False
        try:
            if self.wait_until_element_found(20, 'xpath', '//input[@id="user-name"]'):
                self.browser.find_element(By.XPATH, '//input[@id="user-name"]').send_keys(username)
                self.browser.find_element(By.XPATH, '//input[@id="password"]').send_keys(password)
                try:
                    button = WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]')))
                    button.click()

                    WebDriverWait(self.browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="welcome-msg my-5"] > h3')))
                    login_flag = True
                except Exception as e: 
                    self.print_logs(str(e))
                    if self.DEBUG: print(str(e))
                    else: pass
        except Exception as e:
            self.print_logs(f'Exception in login: {str(e)}')
            if self.DEBUG: print(f'Exception in login: {str(e)}')
            else: pass
        finally: return login_flag

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

    def get_brand_url(self, brand: Brand, glasses_type: str) -> str:
        brand_url = ''
        try:
            div_tags = self.browser.find_element(By.XPATH, '//div[@id="mCSB_1_container"]').find_elements(By.XPATH, './/div[@class="brand-box col-2"]')
            xpath_glasses_type = ''
            if glasses_type == 'Sunglasses':
                xpath_glasses_type = ".//a[contains(text(), 'Sun')]"
            elif glasses_type == 'Eyeglasses':
                xpath_glasses_type = ".//a[contains(text(), 'Optical')]"
            for div_tag in div_tags:
                href = div_tag.find_element(By.XPATH, xpath_glasses_type).get_attribute('href')
                if f'codeLine1={str(brand.code).strip().upper()}' in href:
                    brand_url = f'{href}&limit=80'

        except Exception as e:
            self.print_logs(f'Exception in get_brand_url: {str(e)}')
            if self.DEBUG: print(f'Exception in get_brand_url: {str(e)}')
            else: pass
        finally: return brand_url

    def open_new_tab(self, url: str) -> None:
        # open category in new tab
        self.browser.execute_script('window.open("'+str(url)+'","_blank");')
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])
        self.wait_until_browsing()
    
    def close_last_tab(self) -> None:
        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[len(self.browser.window_handles) - 1])
    
    def is_next_page(self) -> bool:
        next_page_flag = False
        try:
            next_span_style = self.browser.find_element(By.XPATH, '//span[@class="next"]').get_attribute('style')
            if ': hidden;' not in next_span_style: next_page_flag = True
        except Exception as e:
            self.print_logs(f'Exception in is_next_page: {str(e)}')
            if self.DEBUG: print(f'Exception in is_next_page: {str(e)}')
            else: pass
        finally: return next_page_flag

    def move_to_next_page(self) -> None:
        try:
            current_page_number = str(self.browser.find_element(By.XPATH, '//span[@class="current"]').text).strip()
            next_page_span = self.browser.find_element(By.XPATH, '//span[@class="next"]')
            # ActionChains(self.browser).move_to_element(next_page_span).perform()
            ActionChains(self.browser).move_to_element(next_page_span).click().perform()
            self.wait_for_next_page_to_load(current_page_number)
        except Exception as e:
            self.print_logs(f'Exception in move_to_next_page: {str(e)}')
            if self.DEBUG: print(f'Exception in move_to_next_page: {str(e)}')
            else: pass

    def wait_for_next_page_to_load(self, current_page_number: str) -> None:
        for _ in range(0, 100):
            try:
                next_page_number = str(self.browser.find_element(By.XPATH, '//span[@class="current"]').text).strip()
                if int(next_page_number) > int(current_page_number): 
                    for _ in range(0, 30):
                        try:
                            for div_tag in self.browser.find_elements(By.XPATH, '//div[@class="row mt-4 list grid-divider"]/div'):
                                div_tag.find_element(By.XPATH, './/p[@class="model-name"]').text
                            break
                        except: sleep(0.3)
                    break
            except: sleep(0.3)
 
    def get_total_products(self) -> int:
        total_products = 0
        try:
            total_products = int(str(self.browser.find_element(By.XPATH, '//div[@class="row mt-4 results"]/div').text).strip().split(' ')[0])
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_total_products: {e}')
            self.print_logs(f'Exception in get_total_products: {e}')
        finally: return total_products

    def get_all_products_from_page(self) -> list[dict]:
        products_on_page = []
        try:
            for _ in range(0, 30):
                products_on_page = []
                try:
                    for div_tag in self.browser.find_elements(By.XPATH, '//div[@class="row mt-4 list grid-divider"]/div'): 
                        ActionChains(self.browser).move_to_element(div_tag).perform()
                        product_url, product_number = '', ''

                        product_url = div_tag.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        text = str(div_tag.find_element(By.XPATH, './/p[@class="model-name"]').text).strip()
                        product_number = str(text.split(' ')[0]).strip()
                        
                        json_data = {
                            'number': product_number,
                            'url': product_url
                        }
                        if json_data not in products_on_page: products_on_page.append(json_data)
                    break
                except: sleep(0.3)
        except Exception as e:
            self.print_logs(f'Exception in get_all_products_from_page: {str(e)}')
            if self.DEBUG: print(f'Exception in get_all_products_from_page: {str(e)}')
            else: pass
        finally: return products_on_page

    def scrape_product(self, username: str, brand: Brand, product_number: str, glasses_type: str, headers: dict) -> None:
        try:
            url = f'https://digitalhub.marcolin.com/api/model?codeSalesOrg=IA01&soldCode={username}&shipCode=&idLine={str(brand.code).upper()}&idCode={product_number}&spareParts=null'

            response = self.make_request(url, headers)
            if response.status_code == 200:
                json_data = json.loads(response.text)
                product_name = str(json_data['data']['name']).strip().replace(str(product_number).strip().upper(), '').strip()
                frame_codes = []

                for json_product in json_data['data']['products']:
                    if str(json_product['colorCode']).strip().upper() not in frame_codes:
                        product = Product()
            
                        # product.url = str(headers['Referer']).strip().split('&prod=')[0] + f'&prod={json_product["idCode"]}'
                        try:
                            product.brand = str(brand.name).strip()
                            product.number = str(json_product['codLevel1']).strip().upper().replace('-', '/')
                            product.name = product_name
                            product.frame_code = str(json_product['colorCode']).strip().upper()
                            frame_codes.append(product.frame_code)
                            
                            colorDescription = str(json_product['colorDescription']).strip().split(' - ')[-1].strip().split(' / ')
                            if len(colorDescription) == 1: product.metafields.frame_color = colorDescription[0].strip().title()
                            elif len(colorDescription) == 2:
                                product.metafields.frame_color = colorDescription[0].strip().title()
                                product.metafields.lens_color = colorDescription[1].strip().title()
                            
                            product.type = glasses_type
                        except Exception as e:
                            self.print_logs(f'Exception in getting product data: {e}')
                            if self.DEBUG: print(f'Exception in getting product data: {e}')
                        # product.status = 'active'
                        barcodes, sizes = [], []
                        
                        try:
                            variants = []
                            for json_product2 in json_data['data']['products']:
                                if str(json_product2['colorCode']).strip().upper() == product.frame_code:
                                    variant = Variant()
                                    # variant.position = len(product.variants) + 1
                                    variant.title = str(json_product2['sizeDescription']).strip()
                                    variant.sku = f'{product.number} {product.frame_code} {variant.title}'
                                    if json_product2['aux']['availabilityColor'] == 2: variant.inventory_quantity = 5
                                    else: variant.inventory_quantity = 0
                                    variant.found_status = 1
                                    variant.wholesale_price = format(int(json_product2['price']), '.2f')
                                    variant.listing_price = format(int(json_product2['publicPrice']), '.2f')
                                    variant.barcode_or_gtin = str(json_product2['barcode']).strip()
                                    variant.size = f'{variant.title}-{json_product2["aux"]["rodLength"]}-{json_product2["aux"]["noseLength"]}'.strip().replace(' ', '')
                                    variants.append(variant)
                                    
                                    barcodes.append(variant.barcode_or_gtin)
                                    sizes.append(variant.size)
                            product.variants = variants
                        except Exception as e:
                            self.print_logs(f'Exception in getting product variant data: {e}')
                            if self.DEBUG: print(f'Exception in getting product variant data: {e}')
                        
                        try:
                            if not product.bridge: 
                                for size in sizes:
                                    product.bridge = str(size).strip().split('-')[1].strip()
                                    break
                        except: pass

                        try:
                            if not product.template: 
                                for size in sizes:
                                    product.template = str(size).strip().split('-')[-1].strip()
                                    break
                        except: pass
                        
                        try:

                            product.metafields.for_who = str(json_product['aux']['genderDesc']).strip().title()
                            if product.metafields.for_who == 'Male': product.metafields.for_who = 'Men'
                            elif product.metafields.for_who == 'Female': product.metafields.for_who = 'Women'

                            product.metafields.size_bridge_template = ', '.join(sizes)

                            product.metafields.lens_technology = str(json_product['aux']['typeLensesDesc']).strip().title()

                            product.metafields.frame_material = str(json_product['aux']['productGroupDesc']).strip().title()
                            product.metafields.frame_shape = str(json_product['aux']['formDesc']).strip().title()
                            product.metafields.gtin1 = ', '.join(barcodes)

                            if str(json_product['image']).strip() != "None":
                                product.image = str(json_product['image']).strip().replace('\/', '\\')

                            images_360_urls: list[str] = []
                            for image360 in json_product['images360']:
                                if f"{product.number.replace('/', '-')}_{product.frame_code.replace('/', '-')}_" in image360:
                                    images_360_urls.append(str(image360).strip().replace('\/', '/'))
                            if images_360_urls:
                                front_image = images_360_urls.pop(-1)
                                images_360_urls.insert(0, front_image)
                            product.images_360 = images_360_urls

                        except Exception as e:
                            self.print_logs(f'Exception in getting product meta data: {e}')
                            if self.DEBUG: print(f'Exception in getting product meta data: {e}')
                        

                        self.data.append(product)
            else: self.print_logs(f'{response.status_code} for {url}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in scrape_product_data: {e}')
            self.print_logs(f'Exception in scrape_product_data: {e}')

    def get_fs_token(self) -> str:
        fs_token = ''
        try:
            fs_token = self.browser.execute_script('return window.localStorage.getItem(arguments[0]);', 'fs_token')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_fs_token: {e}')
            self.print_logs(f'Exception in get_fs_token: {e}')
        finally: return fs_token

    def get_cookies(self) -> str:
        cookies = ''
        try:
            browser_cookies = self.browser.get_cookies()
            for browser_cookie in browser_cookies:
                if browser_cookie["name"] == 'php-console-server':
                    cookies = f'{browser_cookie["name"]}={browser_cookie["value"]}; _gat_UA-153573784-1=1; {cookies}'
                else: cookies = f'{browser_cookie["name"]}={browser_cookie["value"]}; {cookies}'
            cookies = cookies.strip()[:-1]
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_cookies: {e}')
            self.print_logs(f'Exception in get_cookies: {e}')
        finally: return cookies

    def get_headers(self, fs_token: str, cookies: str, referer_url: str) -> dict:
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': f'Bearer {fs_token}',
            'Connection': 'keep-alive',
            'Cookie': cookies,
            'Host': 'digitalhub.marcolin.com',
            'Referer': referer_url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        }
    
    def make_request(self, url, headers):
        response = ''
        for _ in range(0, 10):
            try:
                response = requests.get(url=url, headers=headers, timeout=20)
                if response.status_code == 200: break
                else: self.print_logs(f'{response.status_code} for {url}')
            except requests.exceptions.ReadTimeout: sleep(1)
            except requests.exceptions.ConnectTimeout: sleep(1)
            except Exception as e: 
                self.print_logs(f'{e} for {url}')
                sleep(1)
        return response

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
                    'images_360': product.images_360,
                    'variants': json_varinats
                }
                json_products.append(json_product)
            
           
            with open(self.result_filename, 'w') as f: json.dump(json_products, f)
            
        except Exception as e:
            if self.DEBUG: print(f'Exception in save_to_json: {e}')
            self.print_logs(f'Exception in save_to_json: {e}')
    
    # print logs to the log file
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

    def create_thread(self, username: str, brand: Brand, product_number: str, glasses_type: str, headers: dict) -> None:
        thread_name = "Thread-"+str(self.thread_counter)
        self.thread_list.append(myScrapingThread(self.thread_counter, thread_name, self, username, brand, product_number, glasses_type, headers))
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


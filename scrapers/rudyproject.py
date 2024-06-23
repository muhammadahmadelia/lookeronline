
import json
import requests
import datetime
from time import sleep
from datetime import datetime
from bs4 import BeautifulSoup
from models.store import Store
from models.brand import Brand
from models.product import Product
from models.metafields import Metafields
from models.variant import Variant

import threading

# class myScrapingThread(threading.Thread):
#     def __init__(self, threadID: int, name: str, obj, brand: Brand, glasses_type: str, product_url: str, page_url: str) -> None:
#         threading.Thread.__init__(self)
#         self.threadID = threadID
#         self.name = name
#         self.brand = brand
#         self.glasses_type = glasses_type
#         self.product_url = product_url
#         self.page_url = page_url
#         self.obj = obj
#         self.status = 'in progress'
#         pass

#     def run(self):
#         self.obj.get_product_variants_data(self.brand, self.glasses_type, self.product_url, self.page_url)
#         self.status = 'completed'

#     def active_threads(self):
#         return threading.activeCount()


class Rudyproject_Scraper:
    def __init__(self, DEBUG: bool, result_filename: str, logs_filename : str) -> None:
        self.DEBUG = DEBUG
        self.result_filename = result_filename
        self.logs_filename = logs_filename
        self.logs = []
        self.thread_list = []
        self.thread_counter = 0
        self.data = []
        pass
    
    def controller(self, store: Store):
        try:
            product_urls = list()
            print("Getting all product URL's from Sunglasses category\n")
            for sub_category in self.get_all_sub_category_urls(store):
                # sub_category_name = sub_category.get('sub_category_name')
                sub_category_url = sub_category.get('sub_category_url')
                product_urls += self.get_all_product_urls_from_category_page(sub_category_url)
                product_urls = list(dict.fromkeys(product_urls))
                
            start_time = datetime.now()
            print(f'Type: Sunglasses | Total products: {len(product_urls)}')
            print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

            self.print_logs(f'Type: Sunglasses | Total products: {len(product_urls)}')
            self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
            if len(product_urls) > 0:
                self.printProgressBar(0, len(product_urls), prefix = 'Progress:', suffix = 'Complete', length = 50)

            for index, product_url in enumerate(product_urls):
                self.create_thread(product_url)
                if len(self.thread_list) > 20:                   
                    self.wait_for_thread_list_to_complete()
                # self.get_product_details(product_url)
                self.printProgressBar(index + 1, len(product_urls), prefix = 'Progress:', suffix = 'Complete', length = 50)
                
            end_time = datetime.now()
            print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
            print('Duration: {}\n'.format(end_time - start_time))

            self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
            self.print_logs('Duration: {}\n'.format(end_time - start_time))

        except Exception as e:
            self.print_logs(f'Exception in Rudyproject_Scraper controller: {e}')
            if self.DEBUG: print(f'Exception in Rudyproject_Scraper controller: {e}')
            else: pass
        finally: 
            self.wait_for_thread_list_to_complete()
            self.save_to_json(self.data)

    def get_headers(self, referer: str) -> dict:
        return {
            'authority': 'safilo.my.site.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'referer': referer,
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
    
    def get_all_sub_category_urls(self, store: Store) -> list[dict]:
        sub_categories: list[dict] = list() 
        try:
            response = requests.get(url=store.link, headers=self.get_headers(store.link))
            if response.status_code == 200:
                doc_tree = html.fromstring(response.text)
                for a_tag in doc_tree.xpath('//div[@id="block-views-block-menu-sports-block-eyewear"]')[0].xpath('.//li/a'):
                    sub_category_name = a_tag.xpath('./text()')[0]
                    sub_category_url = 'https://www.rudyproject.com{}'.format(a_tag.xpath('./@href')[0])
                    new_sub_category = { 'sub_category_name': sub_category_name, 'sub_category_url': sub_category_url }
                    if new_sub_category not in sub_categories:
                        sub_categories.append(new_sub_category)
            else: self.print_logs(f'{response.status_code} for {store.link}')
        except Exception as e:
            self.print_logs(f'Exception in get_all_sub_category_urls: {str(e)}')
            if self.DEBUG: print(f'Exception in get_all_sub_category_urls: {str(e)}')
            else: pass 
        finally: return sub_categories

    def get_all_product_urls_from_category_page(self, sub_category_url: str) -> list[str]:
        product_urls: list[str] = list()
        try:
            response = requests.get(url=sub_category_url, headers=self.get_headers(sub_category_url))
            if response.status_code == 200:
                doc_tree = html.fromstring(response.text)
                for a_tag in doc_tree.xpath('//div[@id="block-rp-theme-views-block-variations-catalog-block"]')[0].xpath('.//a[@class="text-black"]'):
                    product_url = 'https://www.rudyproject.com{}'.format(str(a_tag.xpath('./@href')[0]).strip())
                    if product_url not in product_urls:
                        product_urls.append(product_url)
                product_urls += self.get_products_from_next_pages(sub_category_url, response.text)
            else: self.print_logs(f'{response.status_code} for {sub_category_url}')
        except Exception as e:
            self.print_logs(f'Exception in get_all_product_urls_from_category_page: {str(e)}')
            if self.DEBUG: print(f'Exception in get_all_product_urls_from_category_page: {str(e)}')
            else: pass
        finally: 
            product_urls = list(dict.fromkeys(product_urls))
            return product_urls

    def get_products_from_next_pages(self, url: str, response_text: str):
        product_urls: list[str] = list()
        try:
            doc_tree = html.fromstring(response_text)
            while doc_tree.xpath('//a[@rel="next"]'):
                next_page_link = doc_tree.xpath('//a[@rel="next"]/@href')[0]
                next_page_url = '{}{}'.format(url, next_page_link)

                response = requests.get(url=next_page_url, headers=self.get_headers(next_page_url))
                if response.status_code == 200:
                    doc_tree = html.fromstring(response.text)
                    for a_tag in doc_tree.xpath('//div[@id="block-rp-theme-views-block-variations-catalog-block"]')[0].xpath('.//a[@class="text-black"]'):
                        product_url = 'https://www.rudyproject.com{}'.format(a_tag.xpath('./@href')[0])
                        product_urls.append(product_url)

                else: 
                    self.print_logs(f'{response.status_code} for {next_page_url}')
                    break

        except Exception as e:
            self.print_logs(f'Exception in get_products_from_next_pages: {str(e)}')
            if self.DEBUG: print(f'Exception in get_products_from_next_pages: {str(e)}')
            else: pass
        finally: return product_urls

    def get_product_details(self, product_url: str):
        try:
            response = requests.get(url=product_url, headers=self.get_headers(product_url))
            if response.status_code == 200:
                doc_tree = html.fromstring(response.text)

                product = Product()
                product.name = doc_tree.xpath('//div[contains(@class, "variants-item") and contains(@class, "active")]')[0].xpath('.//img/@alt')[0]
                product.brand = 'Rudy Project'
                
                product.url = product_url
                
                image_urls = list()

                for src in doc_tree.xpath(f'//img[@alt="{str(product.name).strip()}" and @class="img-fluid"]/@src'):
                    image_url = f'https://www.rudyproject.com{str(src).strip()}'
                    if image_url not in image_urls:
                        image_urls.append(image_url)
                
                if image_urls: product.image = image_urls[0]
                
                product.metafields.for_who = 'Unisex'
                try: product.metafields.frame_color = doc_tree.xpath('//div[contains(@class, "variation_attribute_frame_color")]/div[contains(@class, "item")]/text()')[0]
                except: pass
                try: product.metafields.lens_color = doc_tree.xpath('//div[contains(@class, "variation_attribute_lens_color")]/div[contains(@class, "item")]/text()')[0]
                except: pass
                try: product.metafields.lens_material = doc_tree.xpath('//div[contains(@class, "variation_attribute_lens")]/div[contains(@class, "item")]/text()')[0]
                except: pass

                variant = Variant()
                try: variant.sku = doc_tree.xpath('//div[contains(@class, "variation_field_sku")]/div[contains(@class, "item")]/text()')[0]
                except: pass
                try: variant.listing_price = str(doc_tree.xpath('//span[contains(@class, "variation_price")]/text()')[0]).strip().replace('€', '')
                except: pass
                product.add_single_variant(variant)

                self.data.append(product)
                self.save_to_json(self.data)

        except Exception as e:
            self.print_logs(f'Exception in get_product_details: {str(e)}')
            if self.DEBUG: print(f'Exception in get_product_details: {str(e)}')
            else: pass


    # def controller(self, store: Store) -> None:
    #     try:
    #         for brand in store.brands:
    #             # brand: Brand = brand_with_type['brand']
    #             print(f'Brand: {brand.name}')
    #             self.print_logs(f'Brand: {brand.name}')

    #             for glasses_type in brand.product_types:
    #                 print(f'Scraping Type: {glasses_type}')
    #                 self.print_logs(f'Scraping Type: {glasses_type}')

    #                 scraped_products = 0
    #                 total_products = 0
    #                 start_time = datetime.now()
    #                 print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
    #                 self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

    #                 for url in self.get_urls_for_type(glasses_type):
    #                     page_url = url
    #                     total_products = 0
    #                     while True:
    #                         response = self.make_request(page_url, store.link)

    #                         if response and response.status_code == 200:
    #                             products_data = self.get_products_data(response)
    #                             total_products += len(products_data)

    #                             for product_name, product_link in products_data:
    #                                 scraped_products += 1
    #                                 # self.get_product_variants_data(brand, glasses_type, product_link, page_url)
    #                                 self.create_thread(brand, glasses_type, product_link, page_url)

    #                             next_page_url = self.get_next_page_url(response.text)
    #                             if next_page_url: page_url = next_page_url
    #                             else: break

    #                         else: self.print_logs(f'Failed to get url {url}')

    #                     self.wait_for_thread_list_to_complete()
    #                     self.save_to_json(self.data)
                    
    #                 end_time = datetime.now()
    #                 print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
    #                 print(f'Total products scraped: {scraped_products}')                    
    #                 print('Duration: {}\n'.format(end_time - start_time))

    #                 self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
    #                 self.print_logs(f'Total products scraped: {scraped_products}')                    
    #                 self.print_logs('Duration: {}\n'.format(end_time - start_time))
    #     except Exception as e:
    #         self.print_logs(f'Exception in Rudyproject_Scraper controller: {e}')
    #         if self.DEBUG: print(f'Exception in Rudyproject_Scraper controller: {e}')
    #     finally:
    #         self.wait_for_thread_list_to_complete()
    #         self.save_to_json(self.data)

    # def get_urls_for_type(self, glasses_type: str) -> list[str]:
    #     urls = []
    #     try:
    #         if glasses_type == 'Sunglasses':
    #             urls = ['https://www.rudyproject.com/it/en/products/performance-eyewear.html', 'https://www.rudyproject.com/it/en/products/active-lifestyle-eyewear.html']
    #             glasses_type = 'Sunglasses'
    #         elif glasses_type == 'Ski & Snowboard Goggles':
    #             urls = ['https://www.rudyproject.com/it/en/products/snow-mx.html']
    #             glasses_type = 'Ski & Snowboard Goggles'
    #         elif glasses_type == 'Eyeglasses':
    #             urls = ['https://www.rudyproject.com/it/en/products/rxoptical/models.html']
    #             glasses_type = 'Eyeglasses'
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_urls_for_type: {e}')
    #         if self.DEBUG: print(f'Exception in get_urls_for_type: {e}')
    #     finally: return urls
    
    # def make_request(self, url: str, referer_url: str):
    #     response = ''
    #     try:
    #         headers = self.get_headers(referer_url)
    #         for _ in range(0, 10):
    #             try:
    #                 response = requests.get(url=url, headers=headers)
    #                 break
    #             except: sleep(0.5)
    #     except Exception as e:
    #         self.print_logs(f'Exception in make_request: {e}')
    #         if self.DEBUG: print(f'Exception in make_request: {e}')
    #     finally: return response

    # def get_headers(self, referer_url: str) -> dict:
    #     return {
    #         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    #         'accept-encoding': 'gzip, deflate, br',
    #         'accept-language': 'en-US,en;q=0.9',
    #         'cache-control': 'max-age=0',
    #         'referer': referer_url,
    #         'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
    #         'sec-ch-ua-mobile': '?0',
    #         'sec-ch-ua-platform': '"Windows"',
    #         'sec-fetch-dest': 'document',
    #         'sec-fetch-mode': 'navigate',
    #         'sec-fetch-site': 'same-origin',
    #         'sec-fetch-user': '?1',
    #         'upgrade-insecure-requests': '1' }

    # def get_products_data(self, response) -> list[str]:
    #     products = []
    #     try:
    #         soup = BeautifulSoup(response.text, 'lxml')
    #         for div in soup.select('div#ctl00_CPH_Content_Panel_List > div'):
    #             link = str(div.select_one('a[id$="Link_Detail"]').get('href'))
    #             if 'code=' in link:
    #                 product_name = str(div.find('p', {'class': 'box-prodotto__title title--xsmall title'}).text).strip()
    #                 product_link = F'https://www.rudyproject.com{link}'
    #                 products.append([product_name, product_link])
    #             else:
    #                 response_2 = self.make_request(f'https://www.rudyproject.com{link}', 'https://www.rudyproject.com')
    #                 if response_2.status_code == 200:
    #                     soup_2 = BeautifulSoup(response_2.text, 'lxml')
    #                     for div in soup_2.select('div#ctl00_CPH_Content_Panel_List > div'):
    #                         link = str(div.select_one('a[id$="Link_Detail"]').get('href'))
    #                         if 'code=' in link:
    #                             product_name = str(div.find('p', {'class': 'box-prodotto__title title--xsmall title'}).text).strip()
    #                             product_link = F'https://www.rudyproject.com{link}'
    #                             products.append([product_name, product_link])
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_products_data: {str(e)}')
    #         if self.DEBUG: print(f'Exception in get_products_data: {str(e)}')
    #         else: pass
    #     finally: return products

    # def get_next_page_url(self, response_text: str) -> str:
    #     next_page_url = ''
    #     try:
    #         soup = BeautifulSoup(response_text, 'lxml')
    #         value = soup.select('div.pagination > ul > li')[-2].find('a').get('href')
    #         if value: next_page_url = 'https://www.rudyproject.com' + str(value)
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_next_page_url: {e}')
    #         if self.DEBUG: print(f'Exception in get_next_page_url: {e}')
    #     finally: return next_page_url

    # def get_product_variations(self, soup, product: Product):
    #     sku, price, availablity, img_url = '', '', '', ''
    #     try:
    #         try:
    #             sku = str(soup.select_one('div[class$="align-center-small mb-small-2"]').text).strip()
    #         except Exception as e:
    #             self.print_logs(f'Exception in getting variant sku: {str(e)}')
    #             if self.DEBUG: print(f'Exception in getting variant sku: {str(e)}')
    #             else: pass

    #         try:
    #             price = str(soup.select_one('div[class="price"]').text).replace('€', '').replace(',', '.').strip() if soup.select_one('div[class="price"]') else ''
    #         except Exception as e:
    #             self.print_logs(f'Exception in getting variant price: {str(e)}')
    #             if self.DEBUG: print(f'Exception in getting variant price: {str(e)}')
    #             else: pass

    #         try:
    #             availability_btn = soup.select_one('a[id$="Button_Cart"]')
    #             if availability_btn: availablity = 'Active'
    #             else: availablity = 'Draft'
    #         except Exception as e:
    #             self.print_logs(f'Exception in getting availability: {str(e)}')
    #             if self.DEBUG: print(f'Exception in getting availability: {str(e)}')
    #             else: pass
    #             availablity = 'Draft'

    #         try:
    #             img_url = 'https://www.rudyproject.com' + str(soup.select_one('a[data-fancybox="images"]').get('href'))
    #         except Exception as e:
    #             self.print_logs(f'Exception in getting variant img_url: {str(e)}')
    #             if self.DEBUG: print(f'Exception in getting variant img_url: {str(e)}')
    #             else: pass

    #         try:
    #             images_360 = [] 
    #             for a_tag in soup.select('div[class^="product-slider__gallery"] > div[class="swiper-wrapper"] > div > a'):
    #                 images_360.append(f'https://www.rudyproject.com{a_tag.get("href")}')
    #             product.images_360 = images_360
    #         except Exception as e:
    #             self.print_logs(f'Exception in getting variant img_360_url: {str(e)}')
    #             if self.DEBUG: print(f'Exception in getting variant img_360_url: {str(e)}')
    #             else: pass 

    #     except Exception as e:
    #         self.print_logs(f'Exception in get_product_variations: {str(e)}')
    #         if self.DEBUG: print(f'Exception in get_product_variations: {str(e)}')
    #         else: pass  
    #     finally: return sku, price, availablity, img_url

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
                        # 'title': str(variant.title).strip(), 
                        'sku': str(variant.sku).strip().upper(), 
                        'inventory_quantity': int(variant.inventory_quantity),
                        'found_status': int(variant.found_status),
                        'wholesale_price': float(variant.wholesale_price) if str(variant.wholesale_price).strip() else 0.0,
                        'listing_price': float(variant.listing_price) if str(variant.listing_price).strip() else 0.0, 
                        'barcode_or_gtin': str(variant.barcode_or_gtin).strip(),
                        'size': str(variant.size).strip()
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

    def create_thread(self, brand: Brand, glasses_type: str, product_url: str, page_url: str):
        thread_name = "Thread-"+str(self.thread_counter)
        self.thread_list.append(myScrapingThread(self.thread_counter, thread_name, self, brand, glasses_type, product_url, page_url))
        self.thread_list[self.thread_counter].start()
        self.thread_counter += 1

    def is_thread_list_complted(self):
        for obj in self.thread_list:
            if obj.status == "in progress":
                return False
        return True

    def wait_for_thread_list_to_complete(self):
        while True:
            result = self.is_thread_list_complted()
            if result: 
                self.thread_counter = 0
                self.thread_list.clear()
                break
            else: sleep(1)

    # def get_product_variants_data(self, brand: Brand, glasses_type: str, product_url: str, page_url: str) -> None:
    #     try:
    #         product_response = self.make_request(product_url, page_url)
    #         if product_response.status_code == 200:
    #             soup = BeautifulSoup(product_response.text, 'lxml')

    #             gender, size = self.get_gender_and_size(soup)
    #             all_varinat_skus = self.get_all_variants_skus(soup, product_url)

    #             model_skus = []
    #             flag = True
    #             while flag:
    #                 product = Product()
    #                 product.brand = brand.name
    #                 product.type = glasses_type
    #                 # product.status = 'active'
    #                 # product.url = product_url

    #                 metafields = Metafields()
    #                 metafields.for_who = str(gender).strip().title()
    #                 metafields.size_bridge_template = str(size).strip()

    #                 try:
    #                     value = str(soup.select_one('strong[class="text--black"]').text).strip().title()
    #                     if ' +' in str(value).strip(): value = str(value).replace(' +', '+')
    #                     product.name = str(value).strip().title()
    #                     value2 = str(soup.select_one('h1[class^="title"]').text).strip().title()
    #                     if value2 not in product.name: product.name = f'{value2} {product.name}'

    #                     # if ' +' in str(value).strip(): value = str(value).replace(' +', '+')
    #                     # if str(product.name).strip().lower() in str(value).strip().lower():
    #                     #     value = str(value).lower().replace(str(product.name).lower(), '').strip()
                        
    #                     if str('Impactx Photochromic 2').strip().lower() in value.lower() or str('Impactx 2').strip().lower() in value.lower(): 
    #                         metafields.lens_technology = 'Impactx Photochromic 2'
    #                         split_value = ''
    #                         if str('Impactx Photochromic 2').strip().lower() in str(value).strip().lower(): split_value = 'Impactx Photochromic 2'
    #                         elif str('Impactx 2').strip().lower() in str(value).strip().lower(): split_value = 'Impactx 2'
    #                         if split_value:
    #                             values = str(value).lower().split(str(split_value).strip().lower())
    #                             if len(values) == 2:
    #                                 metafields.frame_color = str(values[0]).strip().title()
    #                                 metafields.lens_color = str(values[1]).strip().title()
    #                     elif str('Rp Optics').strip().lower() in value.lower(): 
    #                         metafields.lens_technology = 'Rp Optics'
    #                         if str(metafields.lens_technology).strip().lower() in str(value).strip().lower():
    #                             values = str(value).lower().split(str(metafields.lens_technology).strip().lower())
    #                             if len(values) == 2:
    #                                 metafields.frame_color = str(values[0]).strip().title()
    #                                 metafields.lens_color = str(values[1]).strip().title()
    #                     elif str('Pol. 3Fx').strip().lower() in value.lower() or str('Polar 3FX').strip().lower() in value.lower(): 
    #                         metafields.lens_technology = 'Polarized'
    #                         split_value = ''
    #                         if str('Pol. 3Fx').strip().lower() in str(value).strip().lower(): split_value = 'Pol. 3Fx'
    #                         elif str('Polar 3FX').strip().lower() in str(value).strip().lower(): split_value = 'Polar 3FX'
    #                         if split_value:
    #                             values = str(value).lower().split(str(split_value).strip().lower())
    #                             if len(values) == 2:
    #                                 metafields.frame_color = str(values[0]).strip().title()
    #                                 metafields.lens_color = str(values[1]).strip().title()
    #                     else:
    #                         metafields.lens_technology = 'Rp Optics' 
    #                         if '-' in value:
    #                             values = value.split('-')
    #                             metafields.frame_color = values[0].strip()
    #                             metafields.lens_color = values[1].strip()
    #                         else: metafields.frame_color = value

    #                     if len(metafields.frame_color) > 0 and str(metafields.frame_color).strip()[-1] == '-': metafields.frame_color = metafields.frame_color[0:-1]
                    
    #                 except Exception as e:
    #                     self.print_logs(f'Exception in getting product full name: {str(e)}')
    #                     if self.DEBUG: print(f'Exception in getting product full name: {str(e)}')
    #                     else: pass


    #                 sku, price, availablity, product.image = self.get_product_variations(soup, product)
    #                 product.number = str(sku).strip().upper()


    #                 variant = Variant()
    #                 # variant.position = 1
    #                 if '\u00ac' in metafields.size_bridge_template: metafields.size_bridge_template = str(metafields.size_bridge_template).replace('\u00ac', '-').strip()
    #                 if metafields.size_bridge_template:
    #                     variant.size = metafields.size_bridge_template
    #                     # if '#' in metafields.size_bridge_template: 
    #                     #     variant.title = str(metafields.size_bridge_template).split('#')[0].strip()
    #                 variant.sku = sku
    #                 variant.listing_price = price
    #                 variant.found_status = 1
    #                 if availablity == 'Active': variant.inventory_quantity = 5
    #                 else: variant.inventory_quantity = 0

    #                 if '+' in metafields.frame_color:
    #                     metafields.frame_color = str(metafields.frame_color).split('+')[-1].strip()

    #                 product.metafields = metafields
    #                 product.add_single_variant(variant)

    #                 model_skus.append(sku)

    #                 self.data.append(product)
    #                 flag = False

    #                 for variation_sku in all_varinat_skus:
    #                     if variation_sku not in model_skus:
    #                         next_variant_url = f"{str(product_url).split('=')[0]}={variation_sku}"
    #                         product_url = next_variant_url
    #                         product_response = self.make_request(next_variant_url, product_url)
    #                         if product_response.status_code == 200:
    #                             soup = BeautifulSoup(product_response.text, 'lxml')
    #                             flag = True
    #                             break

    #         else: self.print_logs(f'Failed to get url {product_url}')
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_product_variants_data: {e}')
    #         if self.DEBUG: print(f'Exception in get_product_variants_data: {e}') 

    # def get_gender_and_size(self, soup: BeautifulSoup):
    #     gender, size = '', ''
    #     try:
    #         for li in soup.select('ul[class="product-detail__list"] > li'):
    #             label = li.select_one('span[class="product-detail__list-label"]').text
    #             value = li.select_one('span[class="product-detail__list-content"]').text
    #             if str(label).strip().lower() == 'gender':
    #                 if str(value).strip().lower() == 'w': gender = 'WOMEN'
    #                 else: gender = value
    #             elif str(label).strip().lower() == 'dimension': size = value
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_gender_and_size: {str(e)}')
    #         if self.DEBUG: print(f'Exception in get_gender_and_size: {str(e)}')
    #         else: pass
    #     finally: return gender, size

    # def get_all_variants_skus(self, soup: BeautifulSoup, product_url: str) -> list[str]:
    #     all_varinat_skus = []
    #     try:
    #         divs = soup.select('div[class="button-select__item"]')
    #         if len(divs) > 0:
    #             for div in soup.select('div[class="button-select__item"]'):
    #                 variation_sku = div.get('variant-code')
    #                 if variation_sku not in all_varinat_skus: all_varinat_skus.append(variation_sku)
    #             variation_sku = str(product_url).split('=')[-1].strip()
    #             if variation_sku not in all_varinat_skus: all_varinat_skus.append(variation_sku)
    #         else: 
    #             variation_sku = str(product_url).split('=')[-1].strip()
    #             if variation_sku not in all_varinat_skus: all_varinat_skus.append(variation_sku)
    #     except Exception as e:
    #         self.print_logs(f'Exception in get_gender_and_size: {str(e)}')
    #         if self.DEBUG: print(f'Exception in get_gender_and_size: {str(e)}')
    #         else: pass
    #     finally: return all_varinat_skus

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
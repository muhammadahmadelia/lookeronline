import json
import requests

from time import sleep
from urllib.parse import quote

from modules.files_reader import Files_Reader

class Shopify_Processor:
    def __init__(self, DEBUG: bool, config_file: str, logs_filename: str) -> None:
        self.DEBUG: bool = DEBUG
        self.config_file: str = config_file
        self.URL: str = ''
        self.session = requests.session()
        self.location_id: str = ''
        self.logs_filename = logs_filename
        self.headers = {'Accept': 'application/json'}
        pass

    # get shopify store id
    def get_store_url(self) -> None:
        try:
            # reading config file
            file_reader = Files_Reader(self.DEBUG)
            json_data = file_reader.read_json_file(self.config_file)

            API_KEY, PASSWORD, shop_name, Version = json_data[0]['API Key'], json_data[0]['Admin API Access token'], json_data[0]['store name'], json_data[0]['Version']
            self.URL = f'https://{API_KEY}:{PASSWORD}@{shop_name}.myshopify.com/admin/api/{Version}/'
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_store_url: {str(e)}')
            self.print_logs(f'Exception in get_store_url: {str(e)}')

     # shopify stuff
    
    ### product ###
    # get all products count from shopify against vendor name
    def get_count_of_products_by_vendor(self, vendor_name: str, product_type: str = '') -> list[dict]:
        count = -1
        try:
            endpoint = f'products/count.json?vendor={quote(vendor_name)}'
            if str(product_type).strip(): endpoint = f'{endpoint}&product_type={quote(product_type)}'
            while count == -1:
                try:
                    response = self.session.get(url=(self.URL + endpoint), headers=self.headers)
                    if response.status_code == 200:
                        json_data = json.loads(response.text)
                        count = json_data['count']
                    elif response.status_code == 429: sleep(1)
                    else: print(f'{response.status_code} found in getting count of collection products {response.text}')
                except requests.exceptions.ConnectionError: sleep(0.5)
                except : pass
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_count_of_products_by_vendor: {str(e)}')
            self.print_logs(f'Exception in get_count_of_products_by_vendor: {str(e)}')
        finally: return count

    # get all products from shopify against vendor name
    def get_products_by_vendor(self, vendor_name: str, product_type: str = '') -> list[dict]:
        products = []
        try:
            endpoint = f'products.json?limit=250&vendor={quote(vendor_name)}'
            if str(product_type).strip(): endpoint = f'{endpoint}&product_type={quote(product_type)}'
            url =  self.URL + endpoint
            while True:
                response = ''
                while True:
                    try:
                        response = self.session.get(url=url, headers=self.headers)
                        if response.status_code == 200:
                            json_data = json.loads(response.text)
                            products += list(json_data['products'])
                            break
                        elif response.status_code == 429: sleep(1)
                        else: 
                            self.print_logs(f'{response.status_code} found in getting products by vendor')
                            sleep(1)
                    except requests.exceptions.ConnectionError: sleep(0.5)
                    except: pass
                try:
                    page_info = ''
                    link = str(response.headers['Link']).strip()
                    if 'rel="next"' in link:
                        if len(link.split(';')) == 2: page_info = str(link).split(';')[0][1:-1]
                        elif len(link.split(';')) == 3:
                            page_info = str(link).split(';')[-2]
                            page_info = page_info.split(',')[-1].strip()[1:-1]
                        page_info = page_info.split('page_info=')[-1]
                        url = self.URL + f'products.json?limit=250&page_info=' + page_info
                    else: break
                except: break

        except Exception as e:
            if self.DEBUG: print(f'Exception in get_products_by_vendor: {str(e)}')
            self.print_logs(f'Exception in get_products_by_vendor: {str(e)}')
        finally: return products
    
    # get product from shopify against product id
    def get_product_by_id(self, product_id: str) -> dict:
        shopify_product = {}
        try:
            flag = False
            endpoint = f'products/{product_id}.json'
            while not flag:
                try:
                    response = self.session.get(url=(self.URL + endpoint), headers=self.headers)
                    if response.status_code == 200: 
                        shopify_product = json.loads(response.text)
                        flag = True
                    elif response.status_code == 429: sleep(0.1)
                    elif response.status_code == 404: break
                    else: 
                        self.print_logs(f'{response.status_code} found in getting product', response.text)
                        sleep(1)
                except requests.exceptions.ConnectionError: sleep(0.5)
                except Exception as e: self.print_logs(f'Exception in get_product_from_shopify loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_product: {e}')
            self.print_logs(f'Exception in get_product: {e}')
        finally: return shopify_product

    # # update product fields
    def update_product(self, product_json: dict):
        update_flag = False
        try:
            endpoint = f'products/{product_json["product"]["id"]}.json'
            counter = 0
            while not update_flag:
                try:
                    response = self.session.put(url=(self.URL + endpoint), json=product_json)
                    if response.status_code == 200: update_flag = True                
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        self.print_logs(f'{response.status_code} found in updating {product_json}')
                        sleep(1)
                    counter += 1
                    if counter == 10: break
                except requests.exceptions.ConnectionError: sleep(0.5)
                except: pass
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_product: {e}')
            self.print_logs(f'Exception in update_product: {e}')
        finally: return update_flag

    # update product image against product id
    def set_product_image(self, product_id: str, json_value: dict) -> bool:
        updation_flag = False
        try:
            endpoint = f'products/{product_id}/images.json'
            counter = 0
            while not updation_flag:
                try:
                    response = self.session.post(url=(self.URL + endpoint), json=json_value, headers=self.headers)
                    if response.status_code == 200: updation_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 4: 
                            self.print_logs(f'Failed to add image for product: {product_id} {response.text}')
                            break
                except requests.exceptions.ConnectionError: sleep(0.5)
                except Exception as e: self.print_logs(f'Exception in update_product_image loop: {e}') 
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_product_image: {str(e)}')
            self.print_logs(f'Exception in update_product_image: {str(e)}')
        return updation_flag

    # delete product image against product id and image id
    def delete_product_image(self, product_id: str, image_id: str) -> bool:
        updation_flag = False
        try:
            endpoint = f'products/{product_id}/images/{image_id}.json'
            counter = 0
            while not updation_flag:
                try:
                    response = self.session.delete(url=(self.URL + endpoint))
                    if response.status_code == 200: updation_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'Failed to delete image to product: {product_id}')
                            break
                except requests.exceptions.ConnectionError: sleep(0.5)
                except Exception as e: self.print_logs(f'Exception in update_product_image loop: {e}') 
        except Exception as e:
            if self.DEBUG: print(f'Exception in delete_product_image: {str(e)}')
            self.print_logs(f'Exception in delete_product_image: {str(e)}')
        return updation_flag
    
    # update product image alt text against image id
    def update_product_image_alt_text(self, product_id: str, image_id: str, alt: str, product_title: str) -> bool:
        updation_flag = False
        try:
            endpoint = f'products/{product_id}/images/{image_id}.json'
            json_value = {"image": {"id": image_id, "alt": alt}}
            counter = 0
            while not updation_flag:
                try:
                    response = self.session.put(url=(self.URL + endpoint), json=json_value)
                    if response.status_code == 200: updation_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'Failed to update alt text of image: {product_title} status code: {response.status_code}')
                            break
                except requests.exceptions.ConnectionError: sleep(0.5)
                except Exception as e: self.print_logs(f'Exception in update_product_image_alt_text loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_product_image_alt_text: {str(e)}')
            self.print_logs(f'Exception in update_product_image_alt_text: {str(e)}')
        return updation_flag
    
    # insert new product
    def insert_product(self, new_product_json: dict) -> dict:
        json_data = {}
        try:
            endpoint = 'products.json'
            flag = False
            while not flag:
                try:
                    response = self.session.post(url=(self.URL + endpoint), json=new_product_json)
                    if response.status_code == 201 or response.status_code == 200:
                        json_data = response.json() # json.loads(response.text)
                        flag = True
                    elif response.status_code == 429 or response.status_code == 430: sleep(1)
                    else: 
                        self.print_logs(f'{response.status_code} found by inserting product to shopify: {new_product_json["title"]} Text: {response.text}')
                        break
                except requests.exceptions.ConnectionError: sleep(1)
                except Exception as e: 
                    self.print_logs(f'Exception in insert_product loop: {e} {new_product_json}')
                    break
            
        except Exception as e:
            if self.DEBUG: print(f'Exception in insert_product: {str(e)}')
            self.print_logs(f'Exception in insert_product: {str(e)}')
        finally: return json_data

    ## metafields ##
    # get product metafileds
    def get_product_metafields(self, product_id: str) -> dict:
        shopify_product_metafields = {}
        try:
            flag = False
            endpoint = f'products/{product_id}/metafields.json'
            while not flag:
                try:
                    response = self.session.get(url=(self.URL + endpoint), headers=self.headers)
                    if response.status_code == 200: 
                        shopify_product_metafields = json.loads(response.text)
                        flag = True
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        self.print_logs(f'{response.status_code} found in getting product metafields', response.text)
                        sleep(1)
                except requests.exceptions.ConnectionError: sleep(0.5)
                except Exception as e: self.print_logs(f'Exception in get_product_metafields_from_shopify loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_product_metafields: {e}')
            self.print_logs(f'Exception in get_product_metafields: {e}')
        finally: return shopify_product_metafields

    # set new metafields against product id
    def set_metafields_for_product(self, product_id: str, metafield: dict) -> bool:
        metafield_flag = False
        try:
            endpoint = f'products/{product_id}/metafields.json'
            json_data = {"metafield":  metafield}
            counter = 0
            while not metafield_flag:
                try:
                    response = self.session.post(url=(self.URL + endpoint), json=json_data)
                    if response.status_code == 201: metafield_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} in adding product metafield {json_data} {response.text}')
                            break
                except requests.exceptions.ConnectionError: sleep(1)
                except Exception as e: self.print_logs(f'Exception in set_metafields_for_product loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in set_metafields_for_product: {str(e)}')
            self.print_logs(f'Exception in set_metafields_for_product: {str(e)}')
        finally: return metafield_flag

    # update product metafield against metafield id
    def update_metafield(self, json_value: dict) -> bool:
        updation_flag = False
        try:
            endpoint = f'metafields/{json_value["metafield"]["id"]}.json'
            # json_value = {"metafield": {"id": metafield_id, "value": frame_material, "type": "single_line_text_field"}}
            counter = 0
            while not updation_flag:
                response = self.session.put(url=(self.URL + endpoint), json=json_value)
                if response.status_code == 200: updation_flag = True
                elif response.status_code == 429: sleep(1)
                else: 
                    sleep(1)
                    counter += 1
                    if counter == 10: 
                        self.print_logs(f'Failed to update {json_value} metafield for: {json_value["metafield"]["id"]}')
                        break
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_frame_material_metafield: {str(e)}')
            self.print_logs(f'Exception in update_frame_material_metafield: {str(e)}')
        return updation_flag

    # set country code against inventory item id
    def set_country_code(self, inventory_item_id: str) -> bool:
        country_code_flag = False
        try:
            endpoint = f'inventory_items/{inventory_item_id}.json'
            json_data = {"inventory_item": {"country_code_of_origin": "IT"}}
            counter = 0
            while not country_code_flag:
                try:
                    response = self.session.put(url=(self.URL + endpoint), json=json_data)
                    if response.status_code == 200: country_code_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} in adding country code')
                            break
                except requests.exceptions.ConnectionError: pass
                except Exception as e: self.print_logs(f'Exception in set_country_code loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in set_country_code: {str(e)}')
            self.print_logs(f'Exception in set_country_code: {str(e)}')
        finally: return country_code_flag

    ## variant ##
    # update variant against id
    def update_variant(self, json_value: str) -> bool:
        updation_flag = False
        try:
            endpoint = f'variants/{json_value["variant"]["id"]}.json'
            counter = 0
            while not updation_flag:
                try:
                    response = self.session.put(url=(self.URL + endpoint), json=json_value)
                    if response.status_code == 200: updation_flag = True
                    elif response.status_code == 429: sleep(1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'Failed to update {json_value["variant"]}. Code: {response.status_code}')
                            break
                except requests.exceptions.ConnectionError: sleep(1)
                except Exception as e: self.print_logs(f'Exception in update_variant loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_variant: {str(e)}')
            self.print_logs(f'Exception in update_variant: {str(e)}')
        return updation_flag
    
    # get new adjusted quantity with respect to new qunatity
    def get_adjusted_inventory_level(self, new_quantity: int, old_quantity: int) -> int:
        adjusted_qunatity = 0
        try:
            while (int(old_quantity) + int(adjusted_qunatity)) != int(new_quantity):
                if int(old_quantity) > int(new_quantity): adjusted_qunatity -= 1
                elif int(old_quantity) < int(new_quantity): adjusted_qunatity += 1

            
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_adjusted_inventory_level: {str(e)}')
            self.print_logs(f'Exception in get_adjusted_inventory_level: {str(e)}')
        finally: return adjusted_qunatity

    # get the location id of the inventory
    def get_inventory_level(self, inventory_item_id: str) -> str:
        location_id = ''
        try:
            endpoint = f'inventory_levels.json?inventory_item_ids={inventory_item_id}'
            counter = 0
            while not location_id:
                try:
                    response = self.session.get(url=(self.URL + endpoint), headers=self.headers)
                    if response.status_code == 200: 
                        json_data = json.loads(response.text)
                        inventory_levels = json_data['inventory_levels']
                        location_id = inventory_levels[0]['location_id']
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} getting inventory level')
                            break
                except requests.exceptions.ConnectionError: pass
                except Exception as e: self.print_logs(f'Exception in get_inventory_level loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_inventory_level: {str(e)}')
            self.print_logs(f'Exception in get_inventory_level: {str(e)}')
        finally: return location_id

    # get the location id without inventory item id
    def get_inventory_level_no_id(self):
        location_id = ''
        try:
            endpoint = f'locations.json'
            counter = 0
            while not location_id:
                try:
                    response = self.session.get(url=(self.URL + endpoint), headers=self.headers)
                    if response.status_code == 200: 
                        json_data = json.loads(response.text)
                        inventory_levels = json_data['locations']
                        location_id = inventory_levels[0]['id']
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} getting inventory level')
                            break
                except requests.exceptions.ConnectionError: pass
                except Exception as e: self.print_logs(f'Exception in get_inventory_level_no_id loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_inventory_level: {str(e)}')
            self.print_logs(f'Exception in get_inventory_level: {str(e)}')
        finally: return location_id

    # update variant inventory_quantity against variant id
    def update_variant_inventory_quantity(self, inventory_item_id: str, inventory_quantity: int) -> bool:
        updation_flag = False
        try:
            if not self.location_id: self.location_id = self.get_inventory_level_no_id()
            if not self.location_id: self.location_id = self.get_inventory_level(inventory_item_id)
            endpoint = f'inventory_levels/adjust.json'
            json_data = {"location_id": self.location_id, "inventory_item_id": int(inventory_item_id), "available_adjustment": inventory_quantity}
            counter = 0
            while not updation_flag:
                try:
                    response = self.session.post(url=(self.URL + endpoint), json=json_data)
                    if response.status_code == 200:
                        updation_flag = True
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} found in updating inventory quantity of variant: {inventory_item_id} {json_data}')
                            break
                except requests.exceptions.ConnectionError: pass
                except Exception as e: self.print_logs(f'Exception in update_variant_inventory_quantity loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_inventory_item: {str(e)}')
            self.print_logs(f'Exception in update_inventory_item: {str(e)}')
        finally: return updation_flag

    # insert new variant
    def insert_variant(self, product_id: str, json_single_variant: dict):
        json_data = {}
        try:
            if not self.location_id: self.location_id = self.get_inventory_level_no_id()

            endpoint = f'products/{product_id}/variants.json'
            flag = False
            counter = 0
            while not flag:
                try:
                    response = self.session.post(url=(self.URL + endpoint), json=json_single_variant)
                    if response.status_code == 201 or response.status_code == 200:
                        json_data = response.json() # json.loads(response.text)
                        flag = True
                    elif response.status_code == 429: sleep(1)
                    elif response.status_code == 422:
                        self.print_logs(f'{response.status_code} {response.text} found by inserting variant {json_single_variant}')
                        break
                    else:
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} {response.text} found by inserting variant {json_single_variant}')
                            break
                except requests.exceptions.ConnectionError: pass
                except Exception as e: 
                    self.print_logs(f'Exception in insert_variant loop: {e} {json_single_variant}')
                    break
        except Exception as e:
            if self.DEBUG: print(f'Exception in insert_variant: {str(e)}')
            self.print_logs(f'Exception in insert_variant: {str(e)}')
        finally: return json_data

    # update product option name against option id
    def update_product_options(self, product_id: str, option_id: str, option_name: str) -> bool:
        update_flag = False
        try:
            endpoint = f'products/{product_id}.json'
            json = { "product": { "id": product_id, "options": {"id": option_id, "name": option_name} } }
            counter = 0
            while not update_flag:
                try:
                    response = self.session.put(url=(self.URL + endpoint), json=json)
                    if response.status_code == 200: update_flag = True                
                    elif response.status_code == 429: sleep(0.1)
                    else: 
                        sleep(1)
                        counter += 1
                        if counter == 10: 
                            self.print_logs(f'{response.status_code} found in updating product option')
                            break
                except requests.exceptions.ConnectionError: sleep(1)
                except Exception as e: self.print_logs(f'Exception in update_product_options loop: {e}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_product_options: {e}')
            self.print_logs(f'Exception in update_product_options: {e}')
        finally: return update_flag

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass
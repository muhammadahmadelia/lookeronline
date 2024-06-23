import os
import json
import glob
from datetime import datetime

from modules.query_processor import Query_Processor

from models.store import Store
from models.product import Product
from models.variant import Variant

class Safilo_Mongodb:
    def __init__(self, DEBUG: bool, results_foldername: str, logs_filename: str, query_processor: Query_Processor) -> None:
        self.DEBUG: bool = DEBUG
        self.results_foldername = results_foldername
        self.logs_filename = logs_filename
        self.query_processor = query_processor
        pass

    def controller(self, store: Store) -> None:
        try:
            print('Updating database...')
            self.print_logs('Updating database...')

            for brand in store.brands:

                for product_type in brand.product_types:
                    print(f'Brand: {brand.name} | Type: {product_type}')
                    self.print_logs(f'Brand: {brand.name} | Type: {product_type}')

                    # read products of specifc brand and specific type from json file
                    scraped_products = self.read_data_from_json_file(brand.name, product_type)

                    if len(scraped_products) > 0:
                        # get products of specifc brand and type from database
                        db_products = self.get_products(brand.name, product_type)
                        print(f'Scraped Products: {len(scraped_products)} | Database Products: {len(db_products)}')
                        self.print_logs(f'Scraped Products: {len(scraped_products)} | Database Products: {len(db_products)}')

                        start_time = datetime.now()
                        print(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                        self.print_logs(f'Start Time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')

                        # update all variants found status and inventory qunatity 0
                        products_ids = [db_product.id for db_product in db_products]
                        self.query_processor.update_variants({'product_id': {'$in': products_ids}}, {'$set': {'found_status': 0, 'inventory_quantity': 0}})

                        self.printProgressBar(0, len(scraped_products), prefix = 'Progress:', suffix = 'Complete', length = 50)
                        
                        for index, scraped_product in enumerate(scraped_products):
                            self.printProgressBar((index + 1), len(scraped_products), prefix = 'Progress:', suffix = 'Complete', length = 50)
                            # matching scraped product with database products
                            # return type is integer if matched and None if not matched
                            matched_product_index = next((i for i, db_product in enumerate(db_products) if scraped_product.id == db_product.id), None)
                            
                            if matched_product_index != None:
                                # pop the matched index product from list of database products
                                matched_db_product = db_products.pop(matched_product_index)
                                
                                self.check_product_feilds(scraped_product, matched_db_product)

                                for scraped_variant in scraped_product.variants:
                                    # matching scraped product variant with matched database product variants
                                    # return type is integer if matched and None if not matched
                                    matched_variant_index = next((i for i, db_variant in enumerate(matched_db_product.variants) if scraped_variant.id == db_variant.id), None)
                                    
                                    if matched_variant_index != None:
                                        # pop the matched index variant from list of database product variants
                                        matched_db_variant = matched_db_product.variants.pop(matched_variant_index)
                                        self.check_variant_fields(scraped_variant, matched_db_variant)
                                    
                                    else: 
                                        # adding new variant of this product to the database
                                        self.add_new_variant(scraped_variant, matched_db_product.id)
                            else: 
                                # adding new product of this brand and type to the database
                                self.add_new_product(scraped_product)

                        end_time = datetime.now()
                        print(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                        print('Duration: {}\n'.format(end_time - start_time))
                        print()

                        self.print_logs(f'End Time: {end_time.strftime("%A, %d %b %Y %I:%M:%S %p")}')
                        self.print_logs('Duration: {}\n\n'.format(end_time - start_time))
                    else: self.print_logs(f'Failed to read values from {self.results_foldername} for {brand.name} | {product_type}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in Safilo_Mongodb: controller: {e}')
            self.print_logs(f'Exception in Safilo_Mongodb: controller: {e}')

    # read latest file from results folder and return products of specific brand name and type
    def read_data_from_json_file(self, brand_name: str, product_type: str) -> list[Product]:
        products: list[Product] = []
        try:
            files = glob.glob(f'{self.results_foldername}*.json')
            if files:
                latest_file = max(files, key=os.path.getctime)
                
                f = open(latest_file)
                json_data = json.loads(f.read())
                f.close()

                for json_d in json_data:
                    if str(json_d['brand']).strip().lower() == str(brand_name).strip().lower() and str(json_d['type']).strip().lower() == str(product_type).strip().lower():
                        product = Product()
                        product.id = str(json_d['_id']).strip().replace('-', '/')
                        product.number = str(json_d['number']).strip().upper()
                        product.name = str(json_d['name']).strip().upper()
                        product.brand = str(json_d['brand']).strip()
                        product.frame_code = str(json_d['frame_code']).strip().upper().replace('-', '/')
                        product.lens_code = str(json_d['lens_code']).strip().upper().replace('-', '/')
                        product.type = str(json_d['type']).strip().title()
                        product.bridge = str(json_d['bridge']).strip()
                        product.template = str(json_d['template']).strip()
                        product.image = str(json_d['image']).strip()
                        product.url = str(json_d['url']).strip()
                        product.images_360 = json_d['images_360']

                        product.metafields.for_who = str(json_d['metafields']['for_who']).strip().title()
                        product.metafields.lens_material = str(json_d['metafields']['lens_material']).strip().title()
                        product.metafields.lens_technology = str(json_d['metafields']['lens_technology']).strip().title()
                        product.metafields.lens_color = str(json_d['metafields']['lens_color']).strip().title()
                        product.metafields.frame_shape = str(json_d['metafields']['frame_shape']).strip().title()
                        product.metafields.frame_material = str(json_d['metafields']['frame_material']).strip().title()
                        product.metafields.frame_color = str(json_d['metafields']['frame_color']).strip().title()
                        product.metafields.size_bridge_template = str(json_d['metafields']['size-bridge-template']).strip()
                        product.metafields.gtin1 = str(json_d['metafields']['gtin1']).strip()
                        
                        variants = []
                        for json_variant in json_d['variants']:
                            variant = Variant()
                            variant.id = str(json_variant['_id']).strip().replace('-', '/')
                            variant.product_id = str(json_variant['product_id']).strip().replace('-', '/')
                            variant.title = str(json_variant['title']).strip()
                            variant.sku = str(json_variant['sku']).strip().upper().replace('-', '/')
                            variant.inventory_quantity = int(json_variant['inventory_quantity'])
                            variant.found_status = int(json_variant['found_status'])
                            variant.wholesale_price = float(json_variant['wholesale_price'])
                            variant.listing_price = float(json_variant['listing_price'])
                            variant.barcode_or_gtin = str(json_variant['barcode_or_gtin']).strip()
                            variant.size = str(json_variant['size']).strip()
                            variants.append(variant)
                        product.variants = variants 
                        products.append(product)

                
        except Exception as e:
            self.print_logs(f'Exception in read_data_from_json_file: {str(e)}')
            if self.DEBUG: print(f'Exception in read_data_from_json_file: {e}')
            else: pass
        finally: return products

    # get products from database of specific brand and type
    def get_products(self, brand_name: str, product_type: str) -> list[Product]:
        products: list[Product] = []
        try:
            # for p_json in query_processor.get_products_by_brand(brand.name):
            for p_json in self.query_processor.get_all_product_details_by_brand_name(brand_name, product_type):
                product = Product()
                product.id = str(p_json['_id']).strip()
                product.number = str(p_json['number']).strip()
                product.name = str(p_json['name']).strip()
                product.brand = str(p_json['brand']).strip()
                product.frame_code = str(p_json['frame_code']).strip()
                product.lens_code = str(p_json['lens_code']).strip()
                product.type = str(p_json['type']).strip()
                product.bridge = str(p_json['bridge']).strip()
                product.template = str(p_json['template']).strip()
                product.url = str(p_json['url']).strip()
                product.shopify_id = str(p_json['shopify_id']).strip()
                product.metafields.for_who = str(p_json['metafields']['for_who']).strip()
                product.metafields.lens_material = str(p_json['metafields']['lens_material']).strip()
                product.metafields.lens_technology = str(p_json['metafields']['lens_technology']).strip()
                product.metafields.lens_color = str(p_json['metafields']['lens_color']).strip()
                product.metafields.frame_shape = str(p_json['metafields']['frame_shape']).strip()
                product.metafields.frame_material = str(p_json['metafields']['frame_material']).strip()
                product.metafields.frame_color = str(p_json['metafields']['frame_color']).strip()
                product.metafields.size_bridge_template = str(p_json['metafields']['size-bridge-template']).strip()
                product.metafields.gtin1 = str(p_json['metafields']['gtin1']).strip()
                product.image = str(p_json['image']).strip() if product.image else ''
                product.images_360 = p_json['images_360'] if p_json['images_360'] else []

                variants: list[Variant] = []
                # for v_json in query_processor.get_variants_by_product_id(product.id):
                for v_json in p_json['variants']:
                    variant = Variant()
                    variant.id = str(v_json['_id']).strip()
                    variant.product_id = str(v_json['product_id']).strip()
                    variant.title = str(v_json['title']).strip()
                    variant.sku = str(v_json['sku']).strip()
                    variant.inventory_quantity = int(v_json['inventory_quantity'])
                    variant.found_status = int(v_json['found_status'])
                    variant.wholesale_price = float(v_json['wholesale_price'])
                    variant.listing_price = float(v_json['listing_price'])
                    variant.barcode_or_gtin = str(v_json['barcode_or_gtin']).strip()
                    variant.shopify_id = str(v_json['shopify_id']).strip()
                    variant.inventory_item_id = str(v_json['inventory_item_id']).strip()
                    variant.size = str(v_json['size']).strip()
                    variants.append(variant)

                product.variants = variants

                products.append(product)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_products: {e}')
            self.print_logs(f'Exception in get_products: {e}')
        finally: return products

    # check database product fields with scraped product fields and update new values to database
    def check_product_feilds(self, scraped_product: Product, matched_db_product: Product) -> None:
        try:
            update_values_dict = {}
            if scraped_product.name and scraped_product.name != matched_db_product.name:
                update_values_dict['name'] = scraped_product.name

            if scraped_product.bridge and scraped_product.bridge != matched_db_product.bridge:
                update_values_dict['bridge'] = scraped_product.bridge
            
            if scraped_product.template and scraped_product.template != matched_db_product.template:
                update_values_dict['template'] = scraped_product.template

            if scraped_product.image and scraped_product.image != matched_db_product.image:
                update_values_dict['image'] = scraped_product.image

            if scraped_product.url and scraped_product.url != matched_db_product.url:
                update_values_dict['url'] = scraped_product.url

            if scraped_product.images_360 and len(scraped_product.images_360) != 0 and scraped_product.images_360 != matched_db_product.images_360:
                update_values_dict['images_360'] = scraped_product.images_360

            if scraped_product.metafields.for_who and scraped_product.metafields.for_who != matched_db_product.metafields.for_who:
                update_values_dict['metafields.for_who'] = scraped_product.metafields.for_who

            if scraped_product.metafields.lens_material and scraped_product.metafields.lens_material != matched_db_product.metafields.lens_material:
                update_values_dict['metafields.lens_material'] = scraped_product.metafields.lens_material

            if scraped_product.metafields.lens_technology and scraped_product.metafields.lens_technology != matched_db_product.metafields.lens_technology:
                update_values_dict['metafields.lens_technology'] = scraped_product.metafields.lens_technology

            if scraped_product.metafields.lens_color and scraped_product.metafields.lens_color != matched_db_product.metafields.lens_color:
                update_values_dict['metafields.lens_color'] = scraped_product.metafields.lens_color

            if scraped_product.metafields.frame_shape and scraped_product.metafields.frame_shape != matched_db_product.metafields.frame_shape:
                update_values_dict['metafields.frame_shape'] = scraped_product.metafields.frame_shape

            if scraped_product.metafields.frame_material and scraped_product.metafields.frame_material != matched_db_product.metafields.frame_material:
                update_values_dict['metafields.frame_material'] = scraped_product.metafields.frame_material

            if scraped_product.metafields.frame_color and scraped_product.metafields.frame_color != matched_db_product.metafields.frame_color:
                update_values_dict['metafields.frame_color'] = scraped_product.metafields.frame_color

            if scraped_product.metafields.size_bridge_template and scraped_product.metafields.size_bridge_template != matched_db_product.metafields.size_bridge_template:
                update_values_dict['metafields.size-bridge-template'] = scraped_product.metafields.size_bridge_template

            if scraped_product.metafields.gtin1 and scraped_product.metafields.gtin1 != matched_db_product.metafields.gtin1:
                update_values_dict['metafields.gtin1'] = scraped_product.metafields.gtin1

            if update_values_dict: self.query_processor.update_product({"_id": matched_db_product.id}, {"$set": update_values_dict})
        except Exception as e:
            if self.DEBUG: print(f'Exception in check_product_feilds: {e}')
            self.print_logs(f'Exception in check_product_feilds: {e} {matched_db_product}')

    # check database variant fields with scraped variant fields and update new values to database
    def check_variant_fields(self, scraped_variant: Variant, matched_db_variant: Variant) -> None:
        
        try:
            update_values_dict = {}
            update_values_dict['found_status'] = 1
                
            if scraped_variant.inventory_quantity != 0:
                update_values_dict['inventory_quantity'] = scraped_variant.inventory_quantity

            if scraped_variant.wholesale_price != 0.0 and scraped_variant.wholesale_price != matched_db_variant.wholesale_price:
                update_values_dict['wholesale_price'] = scraped_variant.wholesale_price

            if scraped_variant.listing_price != 0.0 and scraped_variant.listing_price != matched_db_variant.listing_price:
                update_values_dict['listing_price'] = scraped_variant.listing_price

            if scraped_variant.barcode_or_gtin and scraped_variant.barcode_or_gtin != matched_db_variant.barcode_or_gtin: 
                update_values_dict['barcode_or_gtin'] = scraped_variant.barcode_or_gtin

            if scraped_variant.size and scraped_variant.size != matched_db_variant.size: 
                update_values_dict['size'] = scraped_variant.size

            if update_values_dict: self.query_processor.update_variant({"_id": matched_db_variant.id}, {"$set": update_values_dict})
        except Exception as e:
            if self.DEBUG: print(f'Exception in check_variant_fields: {e}')
            self.print_logs(f'Exception in check_variant_fields: {e}')

    # add new product to the database
    def add_new_product(self, product: Product) -> None:
        try:
            # first add new product to shopify then to database
            json_product = {
                "_id": product.id,
                'number': product.number,
                'name': product.name,
                'brand': product.brand,
                'frame_code': product.frame_code,
                'lens_code': product.lens_code,
                'type': product.type,
                'bridge': product.bridge,
                'template': product.template,
                'url': product.url,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                'shopify_id': product.shopify_id,
                'metafields': {
                    'for_who': product.metafields.for_who,
                    'lens_material': product.metafields.lens_material,
                    'lens_technology': product.metafields.lens_technology,
                    'lens_color': product.metafields.lens_color,
                    'frame_shape': product.metafields.frame_shape,
                    'frame_material': product.metafields.frame_material,
                    'frame_color': product.metafields.frame_color,
                    'size-bridge-template': product.metafields.size_bridge_template,
                    'gtin1': product.metafields.gtin1
                },
                'image': product.image,
                'images_360': product.images_360
            }

            new_json_product = self.query_processor.insert_product(json_product)
            
            if new_json_product:
                # self.print_logs(f'New product added _id {new_json_product.inserted_id}')
                for variant in product.variants:
                    self.add_new_variant(variant, product.id)
        
        except Exception as e:
            if self.DEBUG: print(f'Exception in add_new_product: {e}')
            self.print_logs(f'Exception in add_new_product: {e}')

    # add new variant to the database against specific product id
    def add_new_variant(self, variant: Variant, product_id: str) -> None:
        try:
            json_variant = {
                '_id': variant.id,
                'product_id': product_id,
                'title': variant.title,
                'sku': variant.sku,
                'inventory_quantity': variant.inventory_quantity,
                'found_status': variant.found_status,
                'wholesale_price': variant.wholesale_price,
                'listing_price': variant.listing_price,
                'barcode_or_gtin': variant.barcode_or_gtin,
                'size': variant.size,
                'shopify_id': variant.shopify_id,
                'inventory_item_id': variant.inventory_item_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            new_json_variant = self.query_processor.insert_variant(json_variant)
            # if new_json_variant:
            #     self.print_logs(f'New variant added _id {new_json_variant.inserted_id}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in add_new_variant: {e}')
            self.print_logs(f'Exception in add_new_variant: {e}')

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

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

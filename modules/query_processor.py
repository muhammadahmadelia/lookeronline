from datetime import datetime
from models.store import Store
from models.brand import Brand
from models.product import Product
from models.metafields import Metafields
from models.variant import Variant

from modules.files_reader import Files_Reader
import pymongo
from urllib.parse import quote_plus
import certifi
ca = certifi.where()

class Query_Processor:
    def __init__(self, DEBUG: bool, config_file: str, database_name: str):
        self.DEBUG: bool = DEBUG
        self.config_file: str = config_file
        self.database_name: str = database_name
        self.logs_filename: str = ''
        self.db_client = None
        pass

    def get_db_client(self):
        try:
            if not self.db_client:
                # reading connection file
                file_reader = Files_Reader(self.DEBUG)
                json_data = file_reader.read_json_file(self.config_file)
                URI = "mongodb+srv://%s:%s@%s/?retryWrites=true&w=majority" % (
                    quote_plus(json_data[0]['mongodb']['username']), 
                    quote_plus(json_data[0]['mongodb']['password']), 
                    json_data[0]['mongodb']['host']
                )
                while True:
                    try:
                        # Replace <connection-string> with your actual connection string
                        self.db_client = pymongo.MongoClient(URI, tlsCAFile=ca)
                        self.db_client.lookeronline.command('ping')
                        break
                    except Exception as e: pass
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_connection_string: {e}')
            self.print_logs(f'Exception in get_connection_string: {e}')
    
    # # store
    # get all stores from database
    def get_stores(self) -> list[Store]:
        stores: list[Store] = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client.lookeronline
            for result in db.stores.find({}):
                store = Store()
                store.name = result['name']
                store.link = result['link']
                store.username = result['username']
                store.password = result['password']
                stores.append(store)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_stores: {e}')
            self.print_logs(f'Exception in get_stores: {e}')
        finally: return stores

    # get store from database against name
    def get_store_by_name(self, name: str) -> Store:
        store = Store()
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client.lookeronline
            result = db.stores.find_one({'name': name}) 
            store.name = result['name']
            store.link = result['link']
            store.username = result['username']
            store.password = result['password']
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_store_by_name: {e}')
            self.print_logs(f'Exception in get_store_by_name: {e}')
        finally: return store

    # # brand
    # get all brands from database
    def get_brands(self) -> list[Brand]:
        brands = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]

            for result in db.brands.find({}):
                brand = Brand()
                brand.name = result['name']
                brand.code = result['code']
                brand.product_types = result['types']
                brands.append(brand)
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_brands: {e}')
            self.print_logs(f'Exception in get_brands: {e}')
        finally: return brands
    
    #get brand url
    def get_brand_url(self, brand_name: str) -> str:
        url: str = ''
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            brand = db.brands_url.find_one({'brand': brand_name})
            url = brand['url']
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_brand_url: {e}')
            self.print_logs(f'Exception in get_brand_url: {e}')
        finally: return url

    # products
    # get all products from database against brand_id
    def get_products_by_brand(self, brand_name: str) -> list[dict]:
        products: list[dict] = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            products = list(db.products.find({'brand': brand_name}))
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_products_by_brand: {e}')
            self.print_logs(f'Exception in get_products_by_brand: {e}')
        finally: return products

    def get_products_by_brand_and_type(self, brand_name: str, type: str) -> list[dict]:
        products: list[dict] = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            products = list(db.products.find({'brand': brand_name, 'type': type}))
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_products_by_brand_and_type: {e}')
            self.print_logs(f'Exception in get_products_by_brand_and_type: {e}')
        finally: return products

    def get_all_product_details_by_brand_name(self, brand_name: str, product_type: str) -> list[dict]:
        products: list[dict] = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            products = list(
                db.products.aggregate(
                    [
                        { "$lookup": { "from": "variants", "localField": "_id", "foreignField": "product_id", "as": "variants" } },
                        { "$match": { "brand": brand_name, "type": product_type } }
                    ]
                )
            )
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_products: {e}')
            self.print_logs(f'Exception in get_products: {e}')
        finally: return products

    # update product fields against query
    def update_product(self, query: dict, new_values: dict) -> None:
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            db.products.update_one(query, new_values)
            # result = db.products.update_one(query, new_values)
            # print("Matched count:", result.matched_count)
            # print("Modified count:", result.modified_count)
            # print("Upserted ID:", result.upserted_id)
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_product: {e}')
            self.print_logs(f'Exception in update_product: {e}')

    # insert product
    def insert_product(self, json_product: dict) -> dict:
        product: dict = {}
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            product = db.products.insert_one(json_product)
        except Exception as e:
            if self.DEBUG: print(f'Exception in insert_product: {e}')
            self.print_logs(f'Exception in insert_product: {e}')
        finally: return product

    # variants
    # get all variants from database against product_id
    def get_variants_by_product_id(self, product_id: str) -> list[dict]:
        variants: list[dict] = []
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            variants = list(db.variants.find({'product_id': product_id}))
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_variants_by_product_id: {e}')
            self.print_logs(f'Exception in get_variants_by_product_id: {e}')
        finally: return variants

    # update variant fields against query
    def update_variant(self, query: dict, new_values: dict) -> None:
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            db.variants.update_one(query, new_values)
            # result = db.products.update_one(query, new_values)
            # print("Matched count:", result.matched_count)
            # print("Modified count:", result.modified_count)
            # print("Upserted ID:", result.upserted_id)
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_variant: {e}')
            self.print_logs(f'Exception in update_variant: {e}')

     # update variant fields against query
    
    def update_variants(self, query: dict, new_values: dict) -> None:
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            db.variants.update_many(query, new_values)
            # result = db.products.update_one(query, new_values)
            # print("Matched count:", result.matched_count)
            # print("Modified count:", result.modified_count)
            # print("Upserted ID:", result.upserted_id)
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_variants: {e}')
            self.print_logs(f'Exception in update_variants: {e}')

    # insert new variant
    def insert_variant(self, json_variant: dict) -> dict:
        variant: dict = {}
        try:
            if not self.db_client: self.get_db_client()
            db = self.db_client[self.database_name]
            variant = db.variants.insert_one(json_variant)
        except Exception as e:
            if self.DEBUG: print(f'Exception in insert_variant: {e}')
            self.print_logs(f'Exception in insert_variant: {e}')
        finally: return variant

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

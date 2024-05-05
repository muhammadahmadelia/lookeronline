import os
import sys
import json
import glob
import datetime
from datetime import datetime
import chromedriver_autoinstaller
import pandas as pd

import smtplib
# from email.message import EmailMessage
import ssl
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

from models.store import Store
# from models.brand import Brand
# from models.product import Product
# from models.variant import Variant
# from models.metafields import Metafields

from modules.query_processor import Query_Processor
from modules.files_reader import Files_Reader


from scrapers.digitalhub import Digitalhub_Scraper
from scrapers.safilo import Safilo_Scraper
from scrapers.keringeyewear import Keringeyewear_Scraper
# from scrapers.rudyproject import Rudyproject_Scraper
from scrapers.luxottica import Luxottica_Scraper

from database.digitalhub import Digitalhub_Mongodb
from database.safilo import Safilo_Mongodb
from database.keringeyewear import Keringeyewear_Mongodb
# from database.rudyproject import Rudyproject_Mongodb
from database.luxottica import Luxottica_Mongodb

from shopifycode.shopify_updater import Shopify_Updater

class Scraping_Controller:
    def __init__(self, DEBUG: bool, path: str) -> None:
        self.DEBUG = DEBUG
        self.store: Store = None
        self.path: str = path
        self.config_file: str = f'{self.path}/files/config.json'
        self.results_foldername: str = ''
        self.logs_folder_path: str = ''
        self.result_filename: str = ''
        self.logs_filename: str = ''
        self.log_files: list[str] = []
        pass
    
    def main_controller(self) -> None:
        try:
            
            # getting all stores from database
            query_processor = Query_Processor(self.DEBUG, self.config_file, '')
            stores = query_processor.get_stores()

            for store in stores:
                self.store = store
                if self.store.name in ['Digitalhub', 'Keringeyewear', 'Safilo', 'Luxottica']:
                # if self.store.name in ['Keringeyewear']:
                    query_processor.database_name = str(self.store.name).lower()

                    self.logs_folder_path = f'{self.path}/Logs/{self.store.name}/'
                    if not os.path.exists('Logs'): os.makedirs('Logs')
                    if not os.path.exists(self.logs_folder_path): os.makedirs(self.logs_folder_path)
                    self.create_logs_filename()

                    query_processor.logs_filename = self.logs_filename

                    # getting all brands of store from database
                    self.store.brands = query_processor.get_brands()

                    if self.store.brands:
                        self.results_foldername = f'{self.path}/scraped_data/{self.store.name}/'
                        
                        if not os.path.exists('scraped_data'): os.makedirs('scraped_data')
                        if not os.path.exists(self.results_foldername): os.makedirs(self.results_foldername)
                        self.remove_extra_scraped_files()
                        self.create_result_filename()

                        print('\n')
                        if self.logs_filename not in self.log_files: self.log_files.append(self.logs_filename)

                        if self.store.name in ['Digitalhub', 'Safilo', 'Keringeyewear', 'Luxottica']:
                            # download chromedriver.exe with same version and get its path
                            # chromedriver_autoinstaller.install(self.path)
                            if self.store.name == 'Digitalhub': Digitalhub_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                            elif self.store.name == 'Safilo': Safilo_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                            elif self.store.name == 'Keringeyewear': Keringeyewear_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                            elif self.store.name == 'Luxottica': Luxottica_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store, query_processor)
                        # elif self.store.name == 'Rudyproject': Rudyproject_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)


                        if self.store.name == 'Digitalhub': Digitalhub_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                        elif self.store.name == 'Safilo': Safilo_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                        elif self.store.name == 'Keringeyewear': Keringeyewear_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                        # elif self.store.name == 'Rudyproject': Rudyproject_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                        elif self.store.name == 'Luxottica': Luxottica_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)

                        
                    else: print('No brand selected to scrape and update')
            
        except Exception as e:
            if self.DEBUG: print(f'Exception in multiple_stores_controller: {e}')
            self.print_logs(f'Exception in multiple_stores_controller: {e}')
        finally: return self.log_files
    # create logs filename
    def create_logs_filename(self) -> None:
        try:
            scrape_time = datetime.now().strftime('%d-%m-%Y %H-%M-%S')
            self.logs_filename = f'{self.logs_folder_path}Logs {scrape_time}.txt'
        except Exception as e:
            self.print_logs(f'Exception in create_logs_filename: {str(e)}')
            if self.DEBUG: print(f'Exception in create_logs_filename: {e}')
            else: pass

    # create result filename
    def create_result_filename(self) -> None:
        try:
            # if not self.result_filename:
            scrape_time = datetime.now().strftime('%d-%m-%Y %H-%M-%S')
            self.result_filename = f'{self.results_foldername}Results {scrape_time}.json'
        except Exception as e:
            self.print_logs(f'Exception in create_result_filename: {str(e)}')
            if self.DEBUG: print(f'Exception in create_result_filename: {e}')
            else: pass

    # remove extra scraped files and keep latest 6 files 
    def remove_extra_scraped_files(self) -> None:
        try:
            files = glob.glob(f'{self.results_foldername}*.json')
            while len(files) > 1:
                oldest_file = min(files, key=os.path.getctime)
                os.remove(oldest_file)
                files = glob.glob(f'{self.results_foldername}*.json')

            files = glob.glob(f'{self.logs_folder_path}*.txt')
            while len(files) > 1:
                oldest_file = min(files, key=os.path.getctime)
                os.remove(oldest_file)
                files = glob.glob(f'{self.logs_folder_path}*.txt')
        except Exception as e:
            self.print_logs(f'Exception in remove_extra_scraped_files: {str(e)}')
            if self.DEBUG: print(f'Exception in remove_extra_scraped_files: {e}')
            else: pass

    # get store of user choice
    def get_store_to_update(self, stores: list[Store]) -> Store:
        selected_store = None
        try:
            print('\nSelect any store to update:')
            for store_index, store in enumerate(stores):
                print(store_index + 1, store.name)

            while True:
                store_choice = 0
                try:
                    store_choice = int(input('Choice: '))
                    if store_choice and store_choice <= len(stores):
                            selected_store = stores[int(str(store_choice).strip()) - 1]
                            break
                    else: print(f'Please enter number from 1 to {len(stores)}')
                except: print(f'Please enter number from 1 to {len(stores)}')
        except Exception as e:
            if self.DEBUG: print(f'Exception in get_store_to_update: {e}')
            else: pass
        finally: return selected_store

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

    
class Shopify_Controller:
    def __init__(self, DEBUG: bool, path: str) -> None:
        self.DEBUG = DEBUG
        self.store: Store = None
        self.path: str = path
        self.config_file: str = f'{self.path}/files/config.json'
        self.logs_folder_path: str = ''
        self.logs_filename: str = ''
        self.result_files: list[str] = []
        pass

    def update_inventory_controller(self, log_files: list[str]) -> None:
        try:
            
            # getting all stores from database
            query_processor = Query_Processor(self.DEBUG, self.config_file, '')
            stores = query_processor.get_stores()

            for store in stores:
                self.store = store
                if self.store.name in ['Digitalhub', 'Keringeyewear', 'Safilo', 'Luxottica']:
                # if self.store.name in ['Safilo']:
                    query_processor.database_name = str(self.store.name).lower()
                    # self.logs_folder_path = f'{self.path}/Logs/{self.store.name}/'
                    

                    for log_file in log_files:
                        if '.txt' in log_file and f'Logs\\{self.store.name}\\' in log_file:
                            self.logs_filename = log_file
                            break
                    
                    # getting all brands of store from database
                    self.store.brands = query_processor.get_brands()
                    if self.store.brands:
                        
                        # new_list = []
                        # for brand in self.store.brands:
                        #     if brand.name == 'Fossil':
                        #         new_list.append(brand)
                        #         break
                        # self.store.brands = new_list
                        
                        shopify_obj = Shopify_Updater(self.DEBUG, self.store, self.config_file, query_processor, self.logs_filename)
                        shopify_obj.update_inventory_controller()
                        self.create_excel_file(shopify_obj)
                    else: print('No brand selected to scrape and update') 
        except Exception as e:
            if self.DEBUG: print(f'Exception in update_inventory_controller: {e}')
            else: pass
        finally: return self.result_files

    # remove extra log files and keep latest 6 files 
    def remove_extra_log_files(self) -> None:
        try:
            files = glob.glob(f'{self.logs_folder_path}*.txt')
            while len(files) > 4:
                oldest_file = min(files, key=os.path.getctime)
                os.remove(oldest_file)
                files = glob.glob(f'{self.logs_folder_path}*.txt')
        except Exception as e:
            self.print_logs(f'Exception in remove_extra_log_files: {str(e)}')
            if self.DEBUG: print(f'Exception in remove_extra_log_files: {e}')
            else: pass

    # create logs filename
    def create_logs_filename(self) -> None:
        try:
            scrape_time = datetime.now().strftime('%d-%m-%Y %H-%M-%S')
            self.logs_filename = f'{self.logs_folder_path}Logs {scrape_time}.txt'
        except Exception as e:
            self.print_logs(f'Exception in create_logs_filename: {str(e)}')
            if self.DEBUG: print(f'Exception in create_logs_filename: {e}')
            else: pass

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass

    # create excel file of results
    def create_excel_file(self, shopify_obj: Shopify_Updater):
        try:
            data = []
            path = 'Results/'
            if not os.path.exists('Results'): os.makedirs('Results')

            filename = f'{path}{self.store.name} {datetime.now().strftime("%d-%m-%Y")} Results.xlsx'
            if filename not in self.result_files: self.result_files.append(filename)

            data.append( 
                (
                    'Brands and types', {
                    "Brand": [brand.name for brand in self.store.brands], 
                    "Types": [', '.join(brand.product_types) for brand in self.store.brands]
                    } 
                ) 
            )
            if shopify_obj.new_products:
                new_products_tuple = (
                    'New Products', {
                        'Title' : [sublist[0] for sublist in shopify_obj.new_products], 
                        'Vendor' : [sublist[1] for sublist in shopify_obj.new_products], 
                        'Product Type' : [sublist[2] for sublist in shopify_obj.new_products], 
                        'Variant SKU' : [sublist[3] for sublist in shopify_obj.new_products], 
                        'Price' : [sublist[4] for sublist in shopify_obj.new_products], 
                        'Inventory Quantity' : [sublist[5] for sublist in shopify_obj.new_products]
                    }
                )
                data.append(new_products_tuple)
            if shopify_obj.new_variants:
                new_variants_tuple = (
                    'New Variants', {
                        'Vendor' : [sublist[0] for sublist in shopify_obj.new_variants], 
                        'Product Type' : [sublist[1] for sublist in shopify_obj.new_variants], 
                        'Variant SKU' : [sublist[2] for sublist in shopify_obj.new_variants], 
                        'Price' : [sublist[3] for sublist in shopify_obj.new_variants],
                        'Inventory Quantity' : [sublist[4] for sublist in shopify_obj.new_variants]
                    }
                )
                data.append(new_variants_tuple)
            if shopify_obj.updated_variants:
                found_variants_tuple = (
                    'Found Variants', {
                        'Vendor' : [sublist[0] for sublist in shopify_obj.updated_variants], 
                        'Product Type' : [sublist[1] for sublist in shopify_obj.updated_variants],
                        'Variant SKU' : [sublist[2] for sublist in shopify_obj.updated_variants],
                        'Price' : [sublist[3] for sublist in shopify_obj.updated_variants],
                        'Compare At Price' : [sublist[4] for sublist in shopify_obj.updated_variants],
                        'Inventory Quantity' : [sublist[5] for sublist in shopify_obj.updated_variants]
                    }
                )
                data.append(found_variants_tuple)
            if shopify_obj.not_found_variants:
                not_found_variants_tuple = (
                    'Not found Variants', {
                        'Vendor' : [sublist[0] for sublist in shopify_obj.not_found_variants], 
                        'Product Type' : [sublist[1] for sublist in shopify_obj.not_found_variants],
                        'Variant SKU' : [sublist[2] for sublist in shopify_obj.not_found_variants],
                        'Price' : [sublist[3] for sublist in shopify_obj.not_found_variants],
                        'Compare At Price' : [sublist[4] for sublist in shopify_obj.not_found_variants],
                        'Inventory Quantity' : [sublist[5] for sublist in shopify_obj.not_found_variants]
                    }
                )
                data.append(not_found_variants_tuple)

            if data:
                writer = pd.ExcelWriter(filename, engine='xlsxwriter')
                for sheet_name, sheet_data in data:
                    df = pd.DataFrame(sheet_data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                writer.close()
        except Exception as e:
            self.print_logs(f'Exception in create_excel: {str(e)}')
            if self.DEBUG: print(f'Exception in create_excel: {e}')
            else: pass


# send email
def send_mail(send_from, from_pass, send_to, subject, text, files=None):
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)


    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(send_from, from_pass)
        smtp.sendmail(send_from, send_to, msg.as_string())

def get_latest_log_files(DEBUG: bool) -> list[str]:
    log_files: list[str] = []
    try:
        for folder_name in glob.glob('Logs/*'):
            files = glob.glob(f'{folder_name}/*.txt')
            if files:
                log_files.append(max(files, key=os.path.getctime))
    except Exception as e:
        if DEBUG: print(f'Exception in get_latest_log_files: {e}')
    finally: return log_files

DEBUG = True
try:
    pathofpyfolder = os.path.realpath(sys.argv[0])
    # get path of Exe folder
    path = pathofpyfolder.replace(pathofpyfolder.split('\\')[-1], '')
    
    if '.exe' in pathofpyfolder.split('\\')[-1]: DEBUG = False
    obj = Scraping_Controller(DEBUG, path)
    obj.main_controller()

    log_files = get_latest_log_files(DEBUG)
    
    obj = Shopify_Controller(DEBUG, path)
    result_files = obj.update_inventory_controller(log_files)
    if result_files:
        file_reader = Files_Reader(DEBUG)
        json_data = file_reader.read_json_file(obj.config_file)
        start_time = datetime.now()
        subject = f'Scraper time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}'
        # sending log files
        try: send_mail(json_data[0]['email']['from'], json_data[0]['email']['pass'], json_data[0]['email']['logs_to'], subject, '', log_files)
        except Exception as e: print(str(e))
        # sending result files
        files = [result_file for result_file in result_files]
        for results_to in json_data[0]['email']['results_to']:
            send_mail(json_data[0]['email']['from'], json_data[0]['email']['pass'], results_to, subject, '', files)
except Exception as e:
    if DEBUG: print('Exception: '+str(e))
    else: pass
import os
import sys
import json
import glob
import datetime
from datetime import datetime
import chromedriver_autoinstaller
import pandas as pd

import smtplib
from email.message import EmailMessage
import ssl
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

from models.store import Store
from models.brand import Brand
from models.product import Product
from models.variant import Variant
from models.metafields import Metafields

from modules.query_processor import Query_Processor
from modules.files_reader import Files_Reader


from scrapers.digitalhub import Digitalhub_Scraper
from scrapers.safilo import Safilo_Scraper
from scrapers.keringeyewear import Keringeyewear_Scraper
from scrapers.rudyproject import Rudyproject_Scraper
from scrapers.luxottica import Luxottica_Scraper

from database.digitalhub import Digitalhub_Mongodb
from database.safilo import Safilo_Mongodb
from database.keringeyewear import Keringeyewear_Mongodb
from database.rudyproject import Rudyproject_Mongodb
from database.luxottica import Luxottica_Mongodb

class Controller:
    def __init__(self, DEBUG: bool, path: str) -> None:
        self.DEBUG = DEBUG
        self.store: Store = None
        self.path: str = path
        self.config_file: str = f'{self.path}/files/config.json'
        self.results_foldername: str = ''
        self.logs_folder_path: str = ''
        self.result_filename: str = ''
        self.logs_filename: str = ''
        pass
    
    def main_controller(self) -> None:
        try:
            log_files = list()
            # getting all stores from database
            query_processor = Query_Processor(self.DEBUG, self.config_file, '')
            stores = query_processor.get_stores()

            for store in stores:
                self.store = store
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
                    if self.logs_filename not in log_files: log_files.append(self.logs_filename)

                    if self.store.name in ['Digitalhub', 'Safilo', 'Keringeyewear', 'Luxottica']:
                        # download chromedriver.exe with same version and get its path
                        chromedriver_autoinstaller.install(self.path)
                        if self.store.name == 'Digitalhub': Digitalhub_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                        elif self.store.name == 'Safilo': Safilo_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                        elif self.store.name == 'Keringeyewear': Keringeyewear_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)
                        elif self.store.name == 'Luxottica': Luxottica_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store, query_processor)
                    elif self.store.name == 'Rudyproject': Rudyproject_Scraper(self.DEBUG, self.result_filename, self.logs_filename).controller(self.store)


                    if self.store.name == 'Digitalhub': Digitalhub_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                    elif self.store.name == 'Safilo': Safilo_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                    elif self.store.name == 'Keringeyewear': Keringeyewear_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                    elif self.store.name == 'Rudyproject': Rudyproject_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)
                    elif self.store.name == 'Luxottica': Luxottica_Mongodb(self.DEBUG, self.results_foldername, self.logs_filename, query_processor).controller(self.store)

                    
                else: print('No brand selected to scrape and update')
            if log_files:
                file_reader = Files_Reader(self.DEBUG)
                json_data = file_reader.read_json_file(self.config_file)
                start_time = datetime.now()
                subject = f'Scraper time: {start_time.strftime("%A, %d %b %Y %I:%M:%S %p")}'
                files = [logs_file for logs_file in log_files]
                self.send_mail(json_data[0]['email']['from'], json_data[0]['email']['pass'], json_data[0]['email']['to'], subject, '', files)
        except Exception as e:
            if self.DEBUG: print(f'Exception in multiple_stores_controller: {e}')
            self.print_logs(f'Exception in multiple_stores_controller: {e}')

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
            while len(files) > 2:
                oldest_file = min(files, key=os.path.getctime)
                os.remove(oldest_file)
                files = glob.glob(f'{self.results_foldername}*.json')

            files = glob.glob(f'{self.logs_folder_path}*.txt')
            while len(files) > 2:
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

    # send email
    def send_mail(self, send_from, from_pass, send_to, subject, text, files=None):
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

DEBUG = True
try:
    pathofpyfolder = os.path.realpath(sys.argv[0])
    # get path of Exe folder
    path = pathofpyfolder.replace(pathofpyfolder.split('\\')[-1], '')
    
    if '.exe' in pathofpyfolder.split('\\')[-1]: DEBUG = False
    Controller(DEBUG, path).main_controller()
    
except Exception as e:
    if DEBUG: print('Exception: '+str(e))
    else: pass
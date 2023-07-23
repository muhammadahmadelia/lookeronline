import json
import pandas as pd

class Files_Reader:
    def __init__(self, DEBUG: bool) -> None:
        self.DEBUG = DEBUG
        pass

    def read_text_file(self, filename: str) -> str:
        text = ''
        try:
            with open(filename, 'r') as conn_string:
                text = conn_string.read()
        except Exception as e:
            if self.DEBUG: print(f'Exception in read_text_file: {e}')
            else: pass
        finally: return text
        
    def read_csv_file(self, filename: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(filename)
            return df
        except Exception as e:
            if self.DEBUG: print('Exception in reading csv file: '+ str(e))
            else: pass

    def read_json_file(self, filename: str) -> list[dict]:
        json_data = []
        try:
            f = open(filename)
            json_data = json.loads(f.read())
            f.close()
        except Exception as e:
            if self.DEBUG: print('Exception in reading_json_file: '+ str(e))
            else: pass
        finally: return json_data

import os
import base64
import requests
from time import sleep
from PIL import Image
from io import BytesIO

from models.brand import Brand
from models.product import Product

from modules.files_reader import Files_Reader

from shopifycode.shopify_processor import Shopify_Processor

class Utils:
    def __init__(self, DEBUG: bool, logs_filename: str) -> None:
        self.DEBUG: bool = DEBUG
        self.logs_filename: str = logs_filename
        pass

    def get_templates_folder_path(self, store_name: str) -> str:
        template_folder_path = ''
        try:
            if store_name == 'Digitalhub': template_folder_path = 'templates/Digitalhub/'
            elif store_name == 'Safilo': template_folder_path = 'templates/Safilo/'
            elif store_name == 'Keringeyewear': template_folder_path = 'templates/Keringeyewear/'
            elif store_name == 'Derigo': template_folder_path = 'templates/Derigo/'
            elif store_name == 'Luxottica': template_folder_path = 'templates/Luxottica/'
        except Exception as e:
            self.print_logs(f'Exception in get_templates_folder_path: {e}')
            if self.DEBUG: print(f'Exception in get_templates_folder_path: {e}')
            else: pass
        finally: return template_folder_path

    # get product template path 
    def get_template_path(self, field: str, brand: Brand, product: Product, template_file_path: str) -> str:
        template_path = ''
        try:
            if field == 'Product Title': template_path = f'{template_file_path}{brand.name}/{product.type}/title.txt'
            elif field == 'Product Description': template_path = f'{template_file_path}{brand.name}/{product.type}/product_description.txt'
            elif field == 'Meta Title': template_path = f'{template_file_path}{brand.name}/{product.type}/meta_title.txt'
            elif field == 'Meta Description': template_path = f'{template_file_path}{brand.name}/{product.type}/meta_description.txt'
            elif field == 'Image Description': template_path = f'{template_file_path}{brand.name}/{product.type}/image_description.txt'
            
        except Exception as e:
            self.print_logs(f'Exception in get_template_path: {e}')
            if self.DEBUG: print(f'Exception in get_template_path: {e}')
        finally: return template_path

    # get product description template
    def get_template(self, path: str) -> str:
        template = ''
        try:
            if os.path.exists(path):
                file_reader = Files_Reader(self.DEBUG)
                template = file_reader.read_text_file(path)
        except Exception as e:
            self.print_logs(f'Exception in get_template: {e}')
            if self.DEBUG: print(f'Exception in get_template: {e}')
            else: pass
        finally: return template
    
    # get original text from template
    def get_original_text(self, template: str, brand: Brand, product: Product) -> str:
        try:
            template = self.check_and_replace_text('{brand.name}', brand.name, template)
            template = self.check_and_replace_text('{product.number}', product.number, template)
            template = self.check_and_replace_text('{product.name}', product.name, template)
            template = self.check_and_replace_text('{product.frame_code}', product.frame_code, template)
            template = self.check_and_replace_text('{product.frame_color}', product.metafields.frame_color, template)
            template = self.check_and_replace_text('{product.lens_code}', product.lens_code, template)
            template = self.check_and_replace_text('{product.lens_color}', product.metafields.lens_color, template)
            template = self.check_and_replace_text('{product.type}', product.type, template)

            # Metafields
            template = self.check_and_replace_text('{product.metafields.for_who}', product.metafields.for_who, template)
            template = self.check_and_replace_text('{product.metafields.lens_material}', product.metafields.lens_material, template)
            template = self.check_and_replace_text('{product.metafields.lens_technology}', product.metafields.lens_technology, template)
            template = self.check_and_replace_text('{product.metafields.frame_material}', product.metafields.frame_material, template)
            template = self.check_and_replace_text('{product.metafields.frame_shape}', product.metafields.frame_shape, template)

        except Exception as e:
            self.print_logs(f'Exception in get_original_text: {e}')
            if self.DEBUG: print(f'Exception in get_original_text: {e}')
            else: pass
        finally: return template
        
    def check_and_replace_text(self, text: str, value: str, template: str) -> str:
        try:
            if str(text).strip().upper() in template: 
                if str(text).strip().lower() == '{product.metafields.for_who}' and str(value).strip().lower() == 'unisex':
                    template = str(template).replace(str(text).strip().upper(), 'MEN and WOMEN')
                else: template = str(template).replace(str(text).strip().upper(), str(value).strip().upper())
            elif str(text).strip().title() in template: 
                if str(text).strip().lower() == '{product.metafields.for_who}' and str(value).strip().lower() == 'unisex':
                    template = str(template).replace(str(text).strip().title(), 'Men and Women')
                else: template = str(template).replace(str(text).strip().title(), str(value).strip().title())
            elif str(text).strip().lower() in template: 
                if str(text).strip().lower() == '{product.metafields.for_who}' and str(value).strip().lower() == 'unisex':
                    template = str(template).replace(str(text).strip().lower(), 'men and women')
                else: template = str(template).replace(str(text).strip().lower(), str(value).strip().lower())

            template = str(template).replace('  ', ' ').strip()
        except Exception as e:
            self.print_logs(f'Exception in check_and_replace_text: {e}')
            if self.DEBUG: print(f'Exception in check_and_replace_text: {e}')
            else: pass
        finally: return template

    # create product title
    def create_product_title(self, brand: Brand, product: Product, template_file_path: str) -> str:
        title = ''
        try:
            title_template_path = self.get_template_path('Product Title', brand, product, template_file_path)
            title_template = self.get_template(title_template_path)
            if title_template:
                title = self.get_original_text(title_template, brand, product)
            
            else:
                if str(brand.name).strip(): title += f'{str(brand.name).strip().title()}'
                if str(product.name).strip(): title += f' {str(product.name).strip().upper()}'
                if str(product.number).strip(): title += f' {str(product.number).strip().upper()}'
                if str(product.frame_code).strip(): title += f' {str(product.frame_code).strip().upper()}'

                title = str(title).strip()
                if '  ' in title: title = str(title).strip().replace('  ', ' ')
                if str(title).strip()[-1] == '-': title = str(title)[:-1].strip()
        except Exception as e:
            self.print_logs(f'Exception in create_product_title: {e}')
            if self.DEBUG: print(f'Exception in create_product_title: {e}')
            else: pass
        finally: return title

    # create product description
    def create_product_description(self, brand: Brand, product: Product, template_file_path: str) -> str:
        product_description = ''
        try:
            product_description_template_path = self.get_template_path('Product Description', brand, product, template_file_path)
            product_description_template = self.get_template(product_description_template_path)
            product_description = self.get_original_text(product_description_template, brand, product)
        except Exception as e:
            self.print_logs(f'Exception in create_product_description: {e}')
            if self.DEBUG: print(f'Exception in create_product_description: {e}')
        finally: return product_description

    # create product meta title
    def create_product_meta_title(self, brand: Brand, product: Product, template_file_path: str) -> str:
        meta_title = ''
        try:
            meta_title_template_path = self.get_template_path('Meta Title', brand, product, template_file_path)
            meta_title_template = self.get_template(meta_title_template_path)
            meta_title_template = str(meta_title_template).split('|')[0]
            meta_title = self.get_original_text(meta_title_template, brand, product)

            if meta_title:
                meta_title = str(meta_title).replace('  ', ' ').strip()
                if '| LookerOnline' not in meta_title: meta_title = '{} | LookerOnline'.format(meta_title)
                # if len(f'{meta_title} | LookerOnline') > 60: meta_title = f'{meta_title} | LO'
                # else: meta_title = f'{meta_title} | LookerOnline'
                # if len(meta_title) > 60: meta_title = str(meta_title).replace('| LookerOnline', '| LO')
                # else: meta_title = str(meta_title).replace('| LO', '| LookerOnline')
        except Exception as e:
            self.print_logs(f'Exception in create_product_meta_title: {e}')
            if self.DEBUG: print(f'Exception in create_product_meta_title: {e}')
        finally: return meta_title

    # create product meta description
    def create_product_meta_description(self, brand: Brand, product: Product, template_file_path: str) -> str:
        meta_description = ''
        try:
            meta_description_template_path = self.get_template_path('Meta Description', brand, product, template_file_path)
            meta_description_template = self.get_template(meta_description_template_path)
            meta_description = self.get_original_text(meta_description_template, brand, product)

            if meta_description:
                meta_description = str(meta_description).replace('  ', ' ').replace('âœ“', '✓').strip()
        except Exception as e:
            self.print_logs(f'Exception in create_product_meta_description: {e}')
            if self.DEBUG: print(f'Exception in create_product_meta_description: {e}')
        finally: return meta_description

    # create product image description
    def create_product_image_description(self, brand: Brand, product: Product, template_file_path: str) -> str:
        image_description = ''
        try:
            image_description_template_path = self.get_template_path('Image Description', brand, product, template_file_path)
            image_description_template = self.get_template(image_description_template_path)
            image_description = self.get_original_text(image_description_template, brand, product)
        except Exception as e:
            self.print_logs(f'Exception in create_product_image_description: {e}')
            if self.DEBUG: print(f'Exception in create_product_image_description: {e}')
        finally: return image_description

    # get product tags whcih are not on shopify
    def get_product_tags(self, brand: Brand, product: Product, shopify_product_tags: list[str]) -> list[str]:
        tags = []
        try:
            if str(brand.name).strip() and str(brand.name).strip() not in shopify_product_tags: tags.append(str(brand.name).strip())
            if str(product.number).strip() and str(product.number).strip().upper() not in shopify_product_tags: tags.append(str(product.number).strip().upper())
            if str(product.name).strip() and str(product.name).strip().upper() not in shopify_product_tags: tags.append(str(product.name).strip().upper())
            if str(product.frame_code).strip() and str(product.frame_code).strip().upper() not in shopify_product_tags: tags.append(str(product.frame_code).strip().upper())
            if str(product.lens_code).strip() and str(product.lens_code).strip().upper() not in shopify_product_tags: tags.append(str(product.lens_code).strip().upper())
            if str(product.type).strip() and str(product.type).strip() not in shopify_product_tags: tags.append(str(product.type).strip())
            if str(product.metafields.for_who).strip():
                if str(product.metafields.for_who).strip().lower() == 'unisex':
                    if 'Men'  not in shopify_product_tags: tags.append('Men')
                    if 'Women'  not in shopify_product_tags: tags.append('Women')
                else:
                    if str(product.metafields.for_who).strip() not in shopify_product_tags: 
                        tags.append(str(product.metafields.for_who).strip())
            if str(product.metafields.lens_material).strip() and str(product.metafields.lens_material).strip() not in shopify_product_tags: tags.append(str(product.metafields.lens_material).strip())
            if str(product.metafields.lens_technology).strip() and str(product.metafields.lens_technology).strip() not in shopify_product_tags: tags.append(str(product.metafields.lens_technology).strip())
            if str(product.metafields.frame_shape).strip() and str(product.metafields.frame_shape).strip() not in shopify_product_tags: tags.append(str(product.metafields.frame_shape).strip())
            if str(product.metafields.frame_material).strip() and str(product.metafields.frame_material).strip() not in shopify_product_tags: tags.append(str(product.metafields.frame_material).strip())
        except Exception as e:
            self.print_logs(f'Exception in get_product_tags: {e}')
            if self.DEBUG: print(f'Exception in get_product_tags: {e}')
            else: pass
        finally: return tags

    # def create_productsize_gtin1_metafields(self, database_product: Product, shopify_variants: list[dict]) -> list[str]:
    #     product_size_metafield, gtin1_metafield = '', ''
    #     try:
    #         product_size_metafield_list, gtin1_metafield_list = [], []
    #         # getting product_sizes and gtin1 from database variants by matching them with shopify variants in sequence
    #         for shopify_variant in shopify_variants:
    #             matched_database_variant = next((database_variant for database_variant in database_product.variants if str(database_variant.shopify_id).strip() == str(shopify_variant['id']).strip()), None)
    #             if matched_database_variant:
    #                 if matched_database_variant.barcode_or_gtin: gtin1_metafield_list.append(matched_database_variant.barcode_or_gtin)
    #                 if matched_database_variant.size: product_size_metafield_list.append(matched_database_variant.size)
                
    #         # converting product_size and gtin1 list to string
            
    #         if gtin1_metafield_list: gtin1_metafield = ', '.join(gtin1_metafield_list)
    #         if product_size_metafield_list: product_size_metafield = ', '.join(product_size_metafield_list)
    #     except Exception as e: 
    #         self.print_logs(f'Exception in create_productsize_gtin1_metafields: {e}')
    #         if self.DEBUG: print(f'Exception in create_productsize_gtin1_metafields: {e}')
    #         else: pass
    #     finally: return [product_size_metafield, gtin1_metafield]

    # get new product metafields for the product
    def get_new_product_metafeilds(self, brand: Brand, product: Product,template_file_path: str) -> list[dict]:
        metafields = []
        try:
            meta_title = self.create_product_meta_title(brand, product, template_file_path)
            meta_description = self.create_product_meta_description(brand, product, template_file_path)
            if str(product.metafields.for_who).strip(): 
                metafields.append(self.get_new_metafield_by_key('for_who', product.metafields.for_who, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('per_chi', product.metafields.for_who, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, "namespace": "my_fields", "key": "for_who", "value": str(product.metafields.for_who).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, "namespace": "italian", "key": "per_chi", "value": str(product.metafields.for_who).strip(), "type": "single_line_text_field"})
            if str(product.metafields.frame_color).strip():
                metafields.append(self.get_new_metafield_by_key('frame_color', product.metafields.frame_color, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('colore_della_montatura', product.metafields.frame_color, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'frame_color', "value": str(product.metafields.frame_color).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'colore_della_montatura', "value": str(product.metafields.frame_color).strip(), "type": "single_line_text_field"})
            if str(product.metafields.frame_material).strip(): 
                metafields.append(self.get_new_metafield_by_key('frame_material', product.metafields.frame_material, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('materiale_della_montatura', product.metafields.frame_material, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'frame_material', "value": str(product.metafields.frame_material).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'materiale_della_montatura', "value": str(product.metafields.frame_material).strip(), "type": "single_line_text_field"})
            if str(product.metafields.frame_shape).strip(): 
                metafields.append(self.get_new_metafield_by_key('frame_shape', product.metafields.frame_shape, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('forma', product.metafields.frame_shape, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'frame_shape', "value": str(product.metafields.frame_shape).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'forma', "value": str(product.metafields.frame_shape).strip(), "type": "single_line_text_field"})
            if str(product.metafields.lens_color).strip(): 
                metafields.append(self.get_new_metafield_by_key('lens_color', product.metafields.lens_color, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('colore_della_lente', product.metafields.lens_color, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'lens_color', "value": str(product.metafields.lens_color).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'colore_della_lente', "value": str(product.metafields.lens_color).strip(), "type": "single_line_text_field"})
            if str(product.metafields.lens_material).strip(): 
                metafields.append(self.get_new_metafield_by_key('lens_material', product.metafields.lens_material, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('materiale_della_lente', product.metafields.lens_material, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'lens_material', "value": str(product.metafields.lens_material).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'materiale_della_lente', "value": str(product.metafields.lens_material).strip(), "type": "single_line_text_field"})
            if str(product.metafields.lens_technology).strip(): 
                metafields.append(self.get_new_metafield_by_key('lens_technology', product.metafields.lens_technology, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('tecnologia_della_lente', product.metafields.lens_technology, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'lens_technology', "value": str(product.metafields.lens_technology).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'tecnologia_della_lente', "value": str(product.metafields.lens_technology).strip(), "type": "single_line_text_field"})
            if str(product.metafields.size_bridge_template).strip(): 
                metafields.append(self.get_new_metafield_by_key('product_size', product.metafields.size_bridge_template, product.shopify_id))
                metafields.append(self.get_new_metafield_by_key('calibro_ponte_asta', product.metafields.size_bridge_template, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'product_size', "value": str(product.metafields.size_bridge_template).strip(), "type": "single_line_text_field"})
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'italian', 'key': 'calibro_ponte_asta', "value": str(product.metafields.size_bridge_template).strip(), "type": "single_line_text_field"})
            if str(product.metafields.gtin1).strip(): 
                metafields.append(self.get_new_metafield_by_key('gtin1', product.metafields.gtin1, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'my_fields', 'key': 'gtin1', "value": str(product.metafields.gtin1).strip(), "type": "single_line_text_field"})
            if str(meta_title).strip(): 
                metafields.append(self.get_new_metafield_by_key('title_tag', meta_title, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'global', 'key': 'title_tag', "value": str(meta_title).strip(), "type": "single_line_text_field"}) 
            if str(meta_description).strip(): 
                metafields.append(self.get_new_metafield_by_key('description_tag', meta_description, product.shopify_id))
                # metafields.append({"product_id": product.shopify_id, 'namespace': 'global', 'key': 'description_tag', "value": str(meta_description).strip(), "type": "single_line_text_field"})
            
        except Exception as e: 
            self.print_logs(f'Exception in get_new_product_metafeilds: {e}')
            if self.DEBUG: print(f'Exception in get_new_product_metafeilds: {e}')
            else: pass
        finally: return metafields

    def get_new_metafield_by_key(self, key: str, value: str, product_id: str) -> dict:
        if key == 'for_who': return {"product_id": product_id, "namespace": "my_fields", "key": "for_who", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'frame_color': return {"product_id": product_id, "namespace": "my_fields", "key": "frame_color", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'frame_material': return {"product_id": product_id, "namespace": "my_fields", "key": "frame_material", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'frame_shape': return {"product_id": product_id, "namespace": "my_fields", "key": "frame_shape", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'lens_color': return {"product_id": product_id, "namespace": "my_fields", "key": "lens_color", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'lens_material': return {"product_id": product_id, "namespace": "my_fields", "key": "lens_material", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'lens_technology': return {"product_id": product_id, "namespace": "my_fields", "key": "lens_technology", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'product_size': return {"product_id": product_id, "namespace": "my_fields", "key": "product_size", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'gtin1': return {"product_id": product_id, "namespace": "my_fields", "key": "gtin1", "value": str(value).strip(), "type": "single_line_text_field"}

        if key == 'per_chi': return {"product_id": product_id, "namespace": "italian", "key": "per_chi", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'colore_della_montatura': return {"product_id": product_id, "namespace": "italian", "key": "colore_della_montatura", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'materiale_della_montatura': return {"product_id": product_id, "namespace": "italian", "key": "materiale_della_montatura", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'forma': return {"product_id": product_id, "namespace": "italian", "key": "forma", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'colore_della_lente': return {"product_id": product_id, "namespace": "italian", "key": "colore_della_lente", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'materiale_della_lente': return {"product_id": product_id, "namespace": "italian", "key": "materiale_della_lente", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'tecnologia_della_lente': return {"product_id": product_id, "namespace": "italian", "key": "tecnologia_della_lente", "value": str(value).strip(), "type": "single_line_text_field"}
        elif key == 'calibro_ponte_asta': return {"product_id": product_id, "namespace": "italian", "key": "calibro_ponte_asta", "value": str(value).strip(), "type": "single_line_text_field"}
        
        if key == 'title_tag': return {"product_id": product_id, 'namespace': 'global', 'key': 'title_tag', "value": str(value).strip(), "type": "single_line_text_field"}
        if key == 'description_tag': return {"product_id": product_id, 'namespace': 'global', 'key': 'description_tag', "value": str(value).strip(), "type": "single_line_text_field"}
    
    # add 360 images to the product on shopify
    def add_product_360_images(self, store_name: str, product: Product, image_description: str, shopify_processor: Shopify_Processor) -> None:
        try:
            if str(store_name).strip().title() == 'Digitalhub':
                img_360_urls = product.images_360

                if '_08.' in img_360_urls[-1]:
                    last_image = img_360_urls.pop(-1)
                    img_360_urls.insert(0, last_image)

                for index, image_360_url in enumerate(img_360_urls):
                    image_filename = ''
                    image_filename = str(image_360_url).strip().split('/')[-1].strip()
                    if image_filename:
                        image_attachment = self.download_image(image_360_url)
                        if image_attachment:
                            # save downloaded image
                            # with open(image_filename, 'wb') as f: f.write(image_attachment)
                            image_file = BytesIO(image_attachment)
                            # crop image to the correct size
                            cropped_image = self.crop_downloaded_image(image_file)
                            if cropped_image:
                                cropped_image_bytes = BytesIO()
                                cropped_image.save(cropped_image_bytes, format='JPEG')
                                cropped_image_bytes.seek(0)
                                cropped_image_base64 = base64.b64encode(cropped_image_bytes.read()).decode('utf-8')
                            # open croped image
                            # f = open(image_filename, 'rb')
                            # image_attachment = base64.b64encode(f.read())
                            # f.close()

                                json_value = {"image": {"position": index + 1, "attachment": cropped_image_base64, "filename": image_filename, "alt": image_description}}
                                shopify_processor.set_product_image(product.shopify_id, json_value)
                            # delete downloaded image
                            # os.remove(image_filename)
            elif str(store_name).strip().title() == 'Safilo':
                for index, image_360_url in enumerate(product.images_360):
                    image_filename = ''
                    image_360_url = str(image_360_url).strip()
                    image_filename = f'{str(image_description).replace(" ", "_")}__{index + 1}.jpg'
                    if image_filename:
                        json_value = {"image": {"position": index + 1, "src": image_360_url, "filename": image_filename, "alt": image_description}}
                        shopify_processor.set_product_image(product.shopify_id, json_value)
            elif str(store_name).strip().title() in ['Keringeyewear', 'Derigo']:
                for index, image_360_url in enumerate(product.images_360):
                    image_filename = f"{str(image_description).strip().replace(' ', '_')}.png"
                    json_value = {"image": {"position": index + 1, "src": image_360_url, "filename": image_filename, "alt": image_description}}
                    shopify_processor.set_product_image(product.shopify_id, json_value)
                
                for index, image_360_url in enumerate(img_360_urls):
                    image_filename = ''
                    image_filename = str(image_360_url).strip().split('/')[-1].strip()
                    if image_filename:
                        json_value = {"image": {"position": index + 1, "src": image_360_url, "filename": image_filename, "alt": image_description}}
                        if not shopify_processor.set_product_image(product.shopify_id, json_value):
                            self.print_logs(f'Failed to upload image {image_360_url} for {product.id}')
            elif str(store_name).strip().title() == 'Luxottica':
                for index, image_360_url in enumerate(product.images_360):
                    image_360_url = str(image_360_url).strip()
                    if '?impolicy=' in image_360_url: image_360_url = str(image_360_url).split('?impolicy=')[0].strip()
                    
                    image_filename = image_360_url.split('/')[-1].strip()

                    if '?' in image_filename: image_filename = str(image_filename).split('?')[0].strip()
                    if image_filename[0] == '0': image_filename = image_filename[1:]

                    if image_filename:
                        json_value = {"image": {"position": index + 1, "src": image_360_url, "filename": image_filename, "alt": image_description}}
                        if not shopify_processor.set_product_image(product.shopify_id, json_value):
                            self.print_logs(f'Failed to upload image {image_360_url} for {product.id}')
                            # image_attachment = self.download_image(image_360_url)
                            # if image_attachment:
                            #     # save downloaded image
                            #     with open(image_filename, 'wb') as f: f.write(image_attachment)
                            #     # open croped image
                            #     f = open(image_filename, 'rb')
                            #     image_attachment = base64.b64encode(f.read())
                            #     f.close()
                                
                            #     json_value = {"image": {"position": index + 1, "attachment": image_attachment.decode('utf-8'), "filename": image_filename, "alt": image_description}}
                            #     shopify_processor.set_product_image(product.shopify_id, json_value)
                            #     # delete downloaded image
                            #     os.remove(image_filename)
                            # else: self.print_logs(f'')
        except Exception as e:
            self.print_logs(f'Exception in add_product_360_images: {e}')
            if self.DEBUG: print(f'Excepption in add_product_360_images: {e}')
            else: pass
    
    # check spin image tag for product
    def check_product_spin_tag(self, num_images: int, tags_str: str) -> str:
        tags = []
        try:
            # Split the tags_str into a list of tags
            tags = tags_str.split(",")
            
            # Check if the spinimages tag is already present in the tags list
            spin_tag_present = any(str(tag).strip().startswith("spinimages=") for tag in tags)
            
            if spin_tag_present:
                exact_spin_tag_present = False
                for tag in tags:
                    if f'spinimages={num_images}' == str(tag).strip(): 
                        exact_spin_tag_present = True
                        break
                if not exact_spin_tag_present: tags.append(f'spinimages={num_images}')

                duplicate_tags = []
                for tag in tags:
                    if str(tag).strip().startswith('spinimages') and str(tag).strip() != f'spinimages={num_images}':
                        duplicate_tags.append(tag)

                if duplicate_tags:
                    tags = [string for string in tags if string not in duplicate_tags]
            else: tags.append(f'spinimages={num_images}')
            
            if tags == tags_str.split(','): tags = []
        except Exception as e:
            self.print_logs(f'Exception in check_product_spin_tag: {e}')
            if self.DEBUG: print(f'Excepption in check_product_spin_tag: {e}')
            else: pass
        finally: return ",".join(tags)
    
    # remove spin tag from tags
    def remove_spin_tag(self, tags: str):
        new_tags = []
        try:
            for tag in str(tags).split(','):
                if 'spinimages' not in str(tag).strip().lower():
                    new_tags.append(str(tag).strip())
        except Exception as e:
            self.print_logs(f'Exception in remove_spin_tag: {e}')
            if self.DEBUG: print(f'Excepption in remove_spin_tag: {e}')
            else: pass
        finally: return ', '.join(new_tags)

    # add product image to the shopify
    def add_product_image(self, store_name: str, product: Product, image_description: str, shopify_processor: Shopify_Processor) -> None:
        try:
            if str(store_name).strip().title() == 'Digitalhub': print('Digitalhub')
            elif str(store_name).strip().title() == 'Safilo': print('Safilo')
            elif str(store_name).strip().title() == 'Keringeyewear': print('Keringeyewear')
            elif str(store_name).strip().title() in ['Luxottica', 'Derigo']:
                image = str(product.image).strip()
                if '?impolicy=' in image: image = str(image).split('?impolicy=')[0].strip()
                
                image_filename = image.split('/')[-1].strip()
                if '?' in image_filename: image_filename = str(image_filename).split('?')[0].strip()
                if image_filename[0] == '0': image_filename = image_filename[1:]
                
                if image_filename:
                    json_value = {"image": {"position": 1, "src": image, "filename": image_filename, "alt": image_description}}
                    shopify_processor.set_product_image(product.shopify_id, json_value)
            # image_attachment = shopify_processor.download_image(str(product.image).strip())
            # if image_attachment:
            #     image_attachment = base64.b64encode(image_attachment)
            #     image_filename = str(product.image).strip().split('/')[-1].strip()
            #     json_value = {"image": {"position": 1, "attachment": image_attachment.decode('utf-8'), "filename": image_filename, "alt": image_description}}
            #     if not shopify_processor.update_product_image(product.shopify_id, json_value):
            #         self.print_logs(f'Failed to update product: {product.shopify_id} image')
            # else: self.print_logs(f'Failed to download image for {product.number} {product.frame_code}')
        except Exception as e:
            self.print_logs(f'Exception in add_product_image: {e}')
            if self.DEBUG: print(f'Excepption in add_product_image: {e}')
            else: pass

    # print logs to the log file
    def print_logs(self, log: str):
        try:
            with open(self.logs_filename, 'a') as f:
                f.write(f'\n{log}')
        except: pass


    def crop_downloaded_image(self, image_file):
        cropped_image = None
        try:
            im = Image.open(image_file)
            width, height = im.size   # Get dimensions
            new_width = 1680
            new_height = 1020
            left = (width - new_width)/2
            top = (height - new_height)/2
            right = (width + new_width)/2
            bottom = (height + new_height)/2
            cropped_image = im.crop((left, top, right, bottom))
            # try:
            #     im.save(filename)
            # except:
            #     rgb_im = im.convert('RGB')
            #     rgb_im.save(filename)
        except Exception as e:
            if self.DEBUG: print(f'Exception in crop_downloaded_image: {e}')
            self.print_logs(f'Exception in crop_downloaded_image: {e}')
        finally: return cropped_image
    # this function will download image from the given url
    def download_image(self, url: str):
        image_attachment = ''
        try:
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-Encoding': 'gzip, deflate, br',
                'accept-Language': 'en-US,en;q=0.9',
                'cache-Control': 'max-age=0',
                'sec-ch-ua': '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'Sec-Fetch-User': '?1',
                'upgrade-insecure-requests': '1',
            }
            
            for _ in range(0, 20):
                try:
                    response = requests.get(url=url)
                    if response.status_code == 200:
                        # image_attachment = base64.b64encode(response.content)
                        image_attachment = response.content
                        break
                    elif response.status_code == 404: 
                        self.print_logs(f'404 in downloading this image {url}')
                        break
                    else: 
                        self.print_logs(f'{response.status_code} found for downloading image')
                        sleep(1)
                except: pass
        except Exception as e:
            if self.DEBUG: print(f'Exception in download_image: {str(e)}')
            self.print_logs(f'Exception in download_image: {str(e)}')
        finally: return image_attachment

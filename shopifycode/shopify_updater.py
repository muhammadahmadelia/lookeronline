from models.store import Store
from models.brand import Brand
from models.product import Product
from models.variant import Variant

from modules.utils import Utils
from modules.query_processor import Query_Processor

from shopifycode.shopify_processor import Shopify_Processor

class Shopify_Updater:
    def __init__(self, DEBUG: bool, store: Store, config_file: str, query_processor: Query_Processor, logs_filename: str) -> None:
        self.DEBUG: bool = DEBUG
        self.store: Store = store
        self.config_file: str = config_file
        self.template_file_path = ''
        self.new_products: list[str] = []
        self.new_variants: list[str] = []
        self.updated_variants: list[str] = []
        self.not_found_variants: list[str] = []
        self.query_processor = query_processor
        self.logs_filename = logs_filename
        self.utils = Utils(self.DEBUG, self.logs_filename)
        pass
    
    # updates inventory of products
    def update_inventory_controller(self) -> None:
        try:
            self.template_file_path = self.utils.get_templates_folder_path(str(self.store.name).strip().title())
            
            shopify_processor = Shopify_Processor(self.DEBUG, self.config_file, self.logs_filename)
            shopify_processor.get_store_url()
            
            print(f'\nUpdating product inventory for {str(self.store.name).strip().title()}')
            self.print_logs(f'\nUpdating product inventory for {str(self.store.name).strip().title()}')

            new_products_counter = 0

            for brand in self.store.brands:
                # if brand.name == 'Police': # this line to replace
                template_suffix = ''
                print(f'\nBrand: {brand.name}')
                self.print_logs(f'\nBrand: {brand.name}')
                
                brand.products = self.query_processor.get_complete_products_by_brand(brand.name)
                print(f'No. of Products in database: {len(brand.products)}')
                self.print_logs(f'No. of Products in database: {len(brand.products)}')

                products_count = shopify_processor.get_count_of_products_by_vendor(brand.name)
                print(f'No. of Products in shopify: {products_count}')
                self.print_logs(f'No. of Products in shopify: {products_count}')

                self.printProgressBar(0, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)
                shopify_products = shopify_processor.get_products_by_vendor(brand.name)

                if products_count == len(shopify_products):
                    for database_product_index, database_product in enumerate(brand.products):
                        self.printProgressBar(database_product_index + 1, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)
                        
                        
                        if database_product.shopify_id:
                            # get matched product between shopify products nad database product by shopify id
                            # return type is integer if matched and None if not matched
                            matched_shopify_product_index = next((i for i, shopify_product in enumerate(shopify_products) if str(database_product.shopify_id) == str(shopify_product['id'])), None)
                            if matched_shopify_product_index != None:
                                # pop the matched index product from list of shopify products
                                matched_shopify_product = shopify_products.pop(matched_shopify_product_index)
                                # check if Outlet tag is not in shopify product tags
                                if 'Outlet' not in matched_shopify_product['tags'] and 'available now' not in matched_shopify_product['tags']:
                                    if matched_shopify_product['template_suffix'] and not template_suffix: template_suffix = matched_shopify_product['template_suffix']
                                    # update product type if not matched
                                    if str(database_product.type).strip().lower() != str(matched_shopify_product['product_type']).strip().lower():
                                        shopify_processor.update_product({ "product": { "id": database_product.shopify_id, "product_type": str(database_product.type).strip() } })
                                    
                                    for database_variant in database_product.variants:
                                        if database_variant.shopify_id:
                                            # get matched variant between shopify product variants and database product variants by shopify id
                                            # return type is integer if matched and None if not matched
                                            matched_shopify_variant_index = next((i for i, shopify_variant in enumerate(matched_shopify_product['variants']) if str(shopify_variant['id']) == str(database_variant.shopify_id)), None)
                                            if matched_shopify_variant_index != None:
                                                # pop the matched index variant from list of shopify product variants
                                                matched_shopify_variant = matched_shopify_product['variants'].pop(matched_shopify_variant_index)
                                                # check variants fields and update those which are not matched
                                                self.check_product_variant(database_variant, database_product, matched_shopify_variant, shopify_processor)

                                            else: 
                                                self.print_logs(f'{database_variant.id} variant not found on shopify store')
                                                for shopify_variant in matched_shopify_product['variants']:
                                                    self.print_logs(f"S_V_ID: {shopify_variant.get('id')} | S_V_SKU: {shopify_variant.get('sku')}")
                                        else: 
                                            self.add_new_variant(database_variant, database_product, shopify_processor)
                                    
                                # else: self.print_logs(f'Outlet tag found for {database_product.id}')
                            
                            else: self.print_logs(f'{database_product.id} product not found on shopify store')
                        else: 
                            new_products_counter += 1
                            self.add_new_product(database_product, brand, template_suffix, shopify_processor)

                            if new_products_counter == 10:
                                new_products_counter = 0
                                shopify_processor = Shopify_Processor(self.DEBUG, self.config_file, self.logs_filename)
                                shopify_processor.get_store_url()


                    # for shopify_product in shopify_products:
                    #     if 'Outlet' not in shopify_product['tags']:
                    #         self.print_logs(f'{shopify_product["title"]} not in database')
                else: self.print_logs(f'Failed to get {products_count} products from shopify')

                shopify_processor = Shopify_Processor(self.DEBUG, self.config_file, self.logs_filename)
                shopify_processor.get_store_url()
        except Exception as e:
            self.print_logs(f'Exception in update_inventory_controller controller: {e}')
            if self.DEBUG: print(f'Exception in update_inventory_controller controller: {e}')
            else: pass

    # # update product fields like product title, description, images and tags
    # def update_product(self, field_to_update: str) -> None:
    #     try:
    #         self.template_file_path = self.utils.get_templates_folder_path(str(self.store.name).strip().title())
            
    #         shopify_processor = Shopify_Processor(self.DEBUG, self.config_file, self.logs_filename)
    #         shopify_processor.get_store_url()
            
    #         print(f'\nUpdating product fields for {str(self.store.name).strip().title()}')

    #         for brand in self.store.brands:
    #             for product_type in brand.product_types:
    #                 print(f'\nBrand: {brand.name} | Product type: {product_type}')

    #                 brand.products = self.query_processor.get_complete_products_by_brand_and_type(brand.name, product_type)
    #                 print(f'No. of Products in database: {len(brand.products)}')

    #                 products_count = shopify_processor.get_count_of_products_by_vendor(brand.name, product_type)
    #                 print(f'No. of Products in shopify: {products_count}')

    #                 shopify_products = shopify_processor.get_products_by_vendor(brand.name, product_type)

    #                 if products_count == len(shopify_products):
    #                     self.printProgressBar(0, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)

    #                     for database_product_index, database_product in enumerate(brand.products):
    #                         self.printProgressBar(database_product_index + 1, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)

    #                         if database_product.shopify_id:
    #                             # get matched product between shopify products nad database product by shopify id
    #                             # return type is integer if matched and None if not matched
    #                             matched_shopify_product_index = next((i for i, shopify_product in enumerate(shopify_products) if str(database_product.shopify_id) == str(shopify_product['id'])), None)
    #                             if matched_shopify_product_index != None:
    #                                 # pop the matched index product from list of shopify products
    #                                 matched_shopify_product = shopify_products.pop(matched_shopify_product_index)
    #                                 # check if Outlet tag is not in shopify product tags
    #                                 if 'Outlet' not in matched_shopify_product['tags']:
    #                                     if field_to_update == 'Update Product Title and Description':
    #                                         product_title = self.utils.create_product_title(brand, database_product, self.template_file_path)
    #                                         product_description = self.utils.create_product_description(brand, database_product, self.template_file_path)
    #                                         update_fields = {}

    #                                         if str(matched_shopify_product['title']).strip() != product_title:
    #                                             update_fields['title'] = product_title

    #                                         if str(matched_shopify_product['body_html']).strip() != product_description:
    #                                             update_fields['body_html'] = product_description
                                            
    #                                         if update_fields:
    #                                             update_fields['id'] = matched_shopify_product['id']
    #                                             shopify_processor.update_product({'product': update_fields})
    #                                     elif field_to_update == 'Update Product Images':
    #                                         if len(matched_shopify_product['images']) == 0 and database_product.images_360 or database_product.image:
    #                                             self.print_logs(f"Setting images for {matched_shopify_product['title']} images: 0")
    #                                             self.set_product_images(brand, database_product, matched_shopify_product['title'], shopify_processor)
    #                                         else:
    #                                             if database_product.images_360 and len(matched_shopify_product['images']) < len(database_product.images_360):
    #                                                 self.print_logs(f"Setting images for {matched_shopify_product['title']} images on shopify: {len(matched_shopify_product['images'])} In database: {len(database_product.images_360)}")
    #                                                 for product_image in matched_shopify_product['images']:
    #                                                     shopify_processor.delete_product_image(product_image['product_id'], product_image['id'])
    #                                                 self.set_product_images(brand, database_product, matched_shopify_product['title'], shopify_processor)
    #                                     elif field_to_update == 'Update Product Tags':
    #                                         if len(matched_shopify_product['images']) == 0 or len(matched_shopify_product['images']) == 1 and 'spinimages' in matched_shopify_product['tags']:
    #                                             new_tags = self.utils.remove_spin_tag(matched_shopify_product['tags'])
    #                                             if new_tags:
    #                                                 shopify_processor.update_product({ "product": { "id": matched_shopify_product['id'], "tags": new_tags } })
    #                                         else:
    #                                             if len(matched_shopify_product['images']) > 1:
    #                                                 new_tags = self.utils.check_product_spin_tag(len(matched_shopify_product['images']), matched_shopify_product['tags'])
    #                                                 if new_tags: 
    #                                                     shopify_processor.update_product({ "product": { "id": matched_shopify_product['id'], "tags": new_tags } })
    #                 else: print(f'Failed to get {products_count} products from shopify')

    #     except Exception as e:
    #         self.print_logs(f'Exception in update_product_title_and_description controller: {e}')
    #         if self.DEBUG: print(f'Exception in update_product_title_and_description controller: {e}')
    #         else: pass

    # # update product metafields
    # def update_product_metafields(self) -> None:
    #     try:
    #         self.template_file_path = self.utils.get_templates_folder_path(str(self.store.name).strip().title())
            
    #         shopify_processor = Shopify_Processor(self.DEBUG, self.config_file, self.logs_filename)
    #         shopify_processor.get_store_url()
            
    #         print(f'\nUpdating product metafields for {str(self.store.name).strip().title()}')

    #         for brand in self.store.brands:
    #             for product_type in brand.product_types:
    #                 print(f'\nBrand: {brand.name} | Product type: {product_type}')

    #                 brand.products = self.query_processor.get_complete_products_by_brand_and_type(brand.name, product_type)
    #                 print(f'No. of Products in database: {len(brand.products)}')

    #                 self.printProgressBar(0, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)

    #                 for database_product_index, database_product in enumerate(brand.products):
    #                     self.printProgressBar(database_product_index + 1, len(brand.products), prefix = 'Progress:', suffix = 'Complete', length = 50)
    #                     shopify_metafields = shopify_processor.get_product_metafields(database_product.shopify_id)
    #                     if shopify_metafields:
    #                         meta_title = self.utils.create_product_meta_title(brand, database_product, self.template_file_path)
                            
    #                         meta_description = self.utils.create_product_meta_description(brand, database_product, self.template_file_path)
    #                         # if str(database_product.metafields.for_who).strip():
    #                         #     self.check_metafields_value(shopify_metafields, 'for_who', database_product.metafields.for_who, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'per_chi', database_product.metafields.for_who, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.frame_color).strip():
    #                         #     self.check_metafields_value(shopify_metafields, 'frame_color', database_product.metafields.frame_color, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'colore_della_montatura', database_product.metafields.frame_color, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.frame_material).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'frame_material', database_product.metafields.frame_material, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'materiale_della_montatura', database_product.metafields.frame_material, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.frame_shape).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'frame_shape', database_product.metafields.frame_shape, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'forma', database_product.metafields.frame_shape, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.lens_color).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'lens_color', database_product.metafields.lens_color, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'colore_della_lente', database_product.metafields.lens_color, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.lens_material).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'lens_material', database_product.metafields.lens_material, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'materiale_della_lente', database_product.metafields.lens_material, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.lens_technology).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'lens_technology', database_product.metafields.lens_technology, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'tecnologia_della_lente', database_product.metafields.lens_technology, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.size_bridge_template).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'product_size', database_product.metafields.size_bridge_template, database_product.shopify_id, shopify_processor)
    #                         #     self.check_metafields_value(shopify_metafields, 'calibro_ponte_asta', database_product.metafields.size_bridge_template, database_product.shopify_id, shopify_processor)
    #                         # if str(database_product.metafields.gtin1).strip(): 
    #                         #     self.check_metafields_value(shopify_metafields, 'gtin1', database_product.metafields.gtin1, database_product.shopify_id, shopify_processor)
    #                         if str(meta_title).strip(): 
    #                             self.check_metafields_value(shopify_metafields, 'title_tag', meta_title, database_product.shopify_id, shopify_processor)
    #                         if str(meta_description).strip(): 
    #                             self.check_metafields_value(shopify_metafields, 'description_tag', meta_description, database_product.shopify_id, shopify_processor)
            
    #     except Exception as e:
    #         self.print_logs(f'Exception in update_product_metafields: {e}')
    #         if self.DEBUG: print(f'Exception in update_product_metafields: {e}')
    #         else: pass
    
    # check product variant and update them if needed
    def check_product_variant(self, variant: Variant, product: Product, shopify_variant: dict, shopify_processor: Shopify_Processor) -> None:
        try:
            update_fields = {}                
            if str(variant.title).strip():
                if len(product.variants) == 1:
                    if 'Default Title' != shopify_variant['title']:
                        update_fields['option1'] = 'Default Title'
                        # if not shopify_processor.update_variant({"variant": {"id": variant.shopify_id, "option1": "Default Title"}}):
                        #     self.print_logs(f'Failed to update variant title for: {variant.id}')
                else:    
                    if variant.title != shopify_variant['title']:
                        update_fields['option1'] = variant.title
                        # if not shopify_processor.update_variant({"variant": {"id": variant.shopify_id, "option1": variant.title}}):
                        #     self.print_logs(f'Failed to update variant title for: {variant.id}')

            if str(variant.sku).strip() and str(variant.sku).strip() != str(shopify_variant['sku']).strip():
                update_fields['sku'] = variant.sku
                # if not shopify_processor.update_variant({"variant": {"id": variant.shopify_id, "sku": variant.sku}}):
                #     self.print_logs(f'Failed to update variant sku of product: {variant.id}')

            if variant.listing_price:
                if not shopify_variant['compare_at_price'] or float(variant.listing_price) != float(shopify_variant['compare_at_price']):
                    update_fields['compare_at_price'] = variant.listing_price
                    # if not shopify_processor.update_variant({"variant": {"id": variant.shopify_id, "compare_at_price": variant.listing_price}}):
                    #     self.print_logs(f'Failed to update variant price of product: {variant.id}')

            if str(variant.barcode_or_gtin).strip() and str(variant.barcode_or_gtin).strip() != str(shopify_variant['barcode']).strip():
                update_fields['barcode'] = variant.barcode_or_gtin
                # if not shopify_processor.update_variant({"variant": {"id": variant.shopify_id, "barcode": variant.barcode_or_gtin}}):
                #     self.print_logs(f'Failed to update variant barcode of product: {variant.id}')

            if shopify_variant['inventory_management'] and shopify_variant['inventory_management'] == 'shopify':
                if int(variant.inventory_quantity) != int(shopify_variant['inventory_quantity']):
                    adjusted_qunatity = shopify_processor.get_adjusted_inventory_level(int(variant.inventory_quantity), int(shopify_variant['inventory_quantity']))
                    if variant.inventory_item_id:
                        if not shopify_processor.update_variant_inventory_quantity(variant.inventory_item_id, adjusted_qunatity):
                            self.print_logs(f'Failed to update variant inventory quantity of product: {variant.id}')
                    else: self.print_logs(f"inventory_item_id not found for {variant.id} from database")
            else: update_fields['inventory_management'] = 'shopify'

            if not bool(shopify_variant['taxable']):
                update_fields['taxable'] = True

            if update_fields:
                update_fields['id'] = variant.shopify_id
                json_value = {"variant": update_fields}
                if not shopify_processor.update_variant(json_value):
                    self.print_logs(f'Failed to update {json_value} for: {variant.shopify_id}')

            if bool(variant.found_status): self.updated_variants.append([product.brand, product.type, variant.sku, shopify_variant['price'], variant.listing_price, variant.inventory_quantity])
            else: self.not_found_variants.append([product.brand, product.type, variant.sku, shopify_variant['price'], variant.listing_price, 0])
            
        except Exception as e:
            if self.DEBUG: print(f'Exception in check_product_variant: {e}')
            self.print_logs(f'Exception in check_product_variant: {e}')
    
    # add new product variant to the shopify store
    def add_new_variant(self, variant: Variant, product: Product, shopify_processor: Shopify_Processor) -> None:
        try:
            self.print_logs(f'Adding variant: {variant.sku}')
            new_variant_json = self.get_new_variant_json(len(product.variants), variant)
            new_variant_json['position'] = len(product.variants)
            new_variant_json['product_id'] = int(product.shopify_id)
            new_variant_json = {'variant': new_variant_json}
            # inserting new variant to the shopify store
            json_data = shopify_processor.insert_variant(product.shopify_id, new_variant_json)
            if json_data:
                # updating shopify_id and inventory_item_id of variant in database
                # get shopify id from inserted variant response
                variant.shopify_id = str(json_data['variant']['id']).strip()
                # update shopify id to the database against variant id
                self.query_processor.update_variant({"_id": variant.id}, {"$set": {"shopify_id": variant.shopify_id}})
                # get inventory item id from inserted variant response
                variant.inventory_item_id = str(json_data['variant']['inventory_item_id']).strip()
                # update inventory item id to the database against variant id
                self.query_processor.update_variant({"_id": variant.id}, {"$set": {"inventory_item_id": variant.inventory_item_id}})
                # set inventory qunatity against inventory item id
                shopify_processor.update_variant_inventory_quantity(variant.inventory_item_id, variant.inventory_quantity)
                # set country code against inventory item id
                shopify_processor.set_country_code(variant.inventory_item_id)

                again_shopify_product = shopify_processor.get_product_by_id(product.shopify_id)
                for shopify_variant in again_shopify_product['product']['variants']:
                    for v in product.variants:
                        if str(v.shopify_id).strip() == str(shopify_variant['id']).strip():
                            if str(v.title).strip() != str(shopify_variant['title']).strip():
                                if not shopify_processor.update_variant({"variant": {"id": v.shopify_id, "option1": v.title}}):
                                    self.print_logs(f'Failed to update variant title of product: {variant.product_id}')

                self.set_product_options(product, again_shopify_product['product']['options'], shopify_processor)

                self.new_variants.append([product.brand, product.type, variant.sku, variant.listing_price, variant.inventory_quantity])
        except Exception as e:
            self.print_logs(f'Exception in add_new_variant: {e}')
            if self.DEBUG: print(f'Exception in add_new_variant: {e}')
            else: pass

    # get new variant json for insertion in shopify
    def get_new_variant_json(self, no_of_variants: int, variant: Variant) -> dict:
        new_variant_json = {}
        try:
            title = ''
            if no_of_variants == 1: title = 'Default Title'
            else: title = variant.title
            if str(variant.listing_price).strip() == '': variant.listing_price = '0.00'
            
            new_variant_json = {
                "option1": str(title), 
                "price": str(variant.listing_price), 
                "sku": str(variant.sku), 
                "compare_at_price": str(variant.listing_price),
                "taxable": True,
                "barcode": str(variant.barcode_or_gtin),
                "grams": 500, 
                "weight": '0.5', 
                "weight_unit": 'kg',
                "inventory_management": "shopify"
            }
        except Exception as e: 
            self.print_logs(f'Exception in get_new_variant_json: {e}')
            if self.DEBUG: print(f'Exception in get_new_variant_json: {e}')
            else: pass
        finally: return new_variant_json
    
    def check_metafields_value(self, shopify_metafields: list[dict], key: str, value: str, product_id: str, shopify_processor: Shopify_Processor):
        try:
            
            shopify_matched_metafield = next((shopify_metafield for shopify_metafield in shopify_metafields['metafields'] if shopify_metafield['key'] == key), None)
            if shopify_matched_metafield:
                if str(shopify_matched_metafield['value']).strip() != str(value).strip():
                    json_value = {"metafield": {"id": shopify_matched_metafield['id'], "value": str(value).strip(), "type": "single_line_text_field"}}
                    if not shopify_processor.update_metafield(json_value): self.print_logs(f'Failed to update {json_value} for product: {product_id}')
            else:
                json_value = self.utils.get_new_metafield_by_key(key, value, product_id)
                if json_value: shopify_processor.set_metafields_for_product(product_id, json_value)
        except Exception as e:
            self.print_logs(f'Exception in check_metafields_value: {e}')
            if self.DEBUG: print(f'Exception in check_metafields_value: {e}')
            else: pass

    def set_metafields_for_new_variant(self, database_product: Product, shopify_variants: list[dict], shopify_processor: Shopify_Processor) -> None:
        try:
            # product_size_metafield, gtin1_metafield = self.utils.create_productsize_gtin1_metafields(database_product, shopify_variants)

            if database_product.metafields.size_bridge_template or database_product.metafields.gtin1:
                shopify_metafields = shopify_processor.get_product_metafields(database_product.shopify_id)
                if shopify_metafields:
                    if database_product.metafields.size_bridge_template:
                        self.check_metafields_value(shopify_metafields, 'product_size', database_product.metafields.size_bridge_template, database_product.shopify_id, shopify_processor)
                        self.check_metafields_value(shopify_metafields, 'calibro_ponte_asta', database_product.metafields.size_bridge_template, database_product.shopify_id, shopify_processor)
                        # shopify_matched_metafield = next((shopify_metafield for shopify_metafield in shopify_metafields['metafields'] if shopify_metafield['key'] == 'product_size'), None)
                        # # checking for product_size metafield
                        # if shopify_matched_metafield:
                            
                        #     if str(shopify_matched_metafield['value']).strip() != str(database_product.metafields.size_bridge_template).strip():
                        #         json_value = {"metafield": {"id": shopify_matched_metafield['id'], "value": str(product_size_metafield).strip(), "type": "single_line_text_field"}}
                        #         if not shopify_processor.update_metafield(json_value): self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')
                        # # checking for calibro_ponte_asta metafield
                        # shopify_matched_metafield = next((shopify_metafield for shopify_metafield in shopify_metafields['metafields'] if shopify_metafield['key'] == 'calibro_ponte_asta'), None)
                        # if shopify_matched_metafield:
                        #     if str(shopify_matched_metafield['value']).strip() != str(database_product.metafields.size_bridge_template).strip():
                        #             json_value = {"metafield": {"id": shopify_matched_metafield['id'], "value": str(product_size_metafield).strip(), "type": "single_line_text_field"}}
                        #             if not shopify_processor.update_metafield(json_value): self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')
                    if database_product.metafields.gtin1:
                        self.check_metafields_value(shopify_metafields, 'gtin1', database_product.metafields.gtin1, database_product.shopify_id, shopify_processor)
                        # # checking for gtin1 metafield
                        # shopify_matched_metafield = next((shopify_metafield for shopify_metafield in shopify_metafields['metafields'] if shopify_metafield['key'] == 'gtin1'), None)
                        # if shopify_matched_metafield:
                        #     if str(shopify_matched_metafield['value']).strip() != str(product_size_metafield).strip():
                        #             json_value = {"metafield": {"id": shopify_matched_metafield['id'], "value": str(product_size_metafield).strip(), "type": "single_line_text_field"}}
                        #             if not shopify_processor.update_metafield(json_value): self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')
                    
                    
                    # for shopify_metafield in shopify_metafields['metafields']:
                    #     if product_size_metafield:
                            
                    #         if shopify_metafield['key'] == 'product_size':
                    #             if str(shopify_metafield['value']).strip() != str(product_size_metafield).strip():
                    #                 json_value = {"metafield": {"id": shopify_metafield['id'], "value": str(product_size_metafield).strip(), "type": "single_line_text_field"}}
                    #                 if not shopify_processor.update_metafield(json_value):
                    #                     self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')
                    #         elif shopify_metafield['key'] == 'calibro_ponte_asta':
                    #             if str(shopify_metafield['value']).strip() != str(product_size_metafield).strip():
                    #                 json_value = {"metafield": {"id": shopify_metafield['id'], "value": str(product_size_metafield).strip(), "type": "single_line_text_field"}}
                    #                 if not shopify_processor.update_metafield(json_value):
                    #                     self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')
                    #     if gtin1_metafield:
                    #         if shopify_metafield['key'] == 'gtin1':
                    #             if str(shopify_metafield['value']).strip() != str(gtin1_metafield).strip():
                    #                 json_value = {"metafield": {"id": shopify_metafield['id'], "value": str(gtin1_metafield).strip(), "type": "single_line_text_field"}}
                    #                 if not shopify_processor.update_metafield(json_value):
                    #                     self.print_logs(f'Failed to update {json_value} for product: {database_product.id}')

        except Exception as e: 
            self.print_logs(f'Exception in set_metafields_for_new_variant: {e}')
            if self.DEBUG: print(f'Exception in set_metafields_for_new_variant: {e}')
            else: pass
    
    # add new product to the shopify store
    def add_new_product(self, product: Product, brand: Brand, template_suffix: str, shopify_processor: Shopify_Processor) -> None:
        try:
            # creating title for product
            product_title = self.utils.create_product_title(brand, product, self.template_file_path)
            self.print_logs(f'Adding product: {product_title}')
            
            # get product description for new product
            product_description = self.utils.create_product_description(brand, product, self.template_file_path)

            # get tags for new product
            tags = self.utils.get_product_tags(brand, product, [])
            tags.insert(0, 'New')

            # get new variant json and store them in list
            new_variants_json: list[dict] = []
            for index, variant in enumerate(product.variants):
                new_variant_json = self.get_new_variant_json(len(product.variants), variant)
                if new_variant_json: new_variants_json.append(new_variant_json)
            
            # get new product json
            new_product_json = self.get_new_product_json(product_title, product_description, brand.name, product.type, ', '.join(tags), new_variants_json, template_suffix)
            if new_product_json:
                json_data, response_text = shopify_processor.insert_product(new_product_json)
                if json_data:
                    # get shopify id from inserted product response
                    product.shopify_id = str(json_data['product']['id']).strip()
                    # update shopify id to the database against product id
                    self.query_processor.update_product({"_id": product.id}, {"$set": {"shopify_id": product.shopify_id}})
                    # get metafields for new product
                    new_metafields = self.utils.get_new_product_metafeilds(brand, product, self.template_file_path)
                    for new_metafield in new_metafields:
                        shopify_processor.set_metafields_for_product(product.shopify_id, new_metafield)

                    for shopify_variant in json_data['product']['variants']:
                        
                        for variant in product.variants:
                            if str(shopify_variant['sku']).strip() == str(variant.sku).strip():
                                new_entry = [product_title, product.brand, product.type, shopify_variant['sku'], shopify_variant['price'], variant.inventory_quantity]
                                if new_entry not in self.new_products: self.new_products.append(new_entry)
                                # get shopify id from inserted variant response
                                variant.shopify_id = str(shopify_variant['id']).strip()
                                # update shopify id to the database against variant id
                                self.query_processor.update_variant({"_id": variant.id}, {"$set": {"shopify_id": variant.shopify_id}})
                                # get inventory item id from inserted variant response
                                variant.inventory_item_id = str(shopify_variant['inventory_item_id']).strip()
                                # update inventory item id to the database against variant id
                                self.query_processor.update_variant({"_id": variant.id}, {"$set": {"inventory_item_id": variant.inventory_item_id}})
                                # set inventory qunatity against inventory item id
                                shopify_processor.update_variant_inventory_quantity(variant.inventory_item_id, variant.inventory_quantity)
                                # set country code against inventory item id
                                shopify_processor.set_country_code(variant.inventory_item_id)
                    
                    self.set_product_options(product, json_data['product']['options'], shopify_processor)
                    self.set_product_images(brand, product, product_title, shopify_processor)
                    # self.set_image_360_tag(', '.join(tags), product.shopify_id, shopify_processor)
                    json_product = shopify_processor.get_product_by_id(product.shopify_id)
                    if json_product:
                        no_of_images = len(json_product['product']['images'])
                        if no_of_images > 1:
                            tags = json_product['product']['tags']
                            tags += f', spinimages={no_of_images}'
                            tags = str(tags).strip()
                            shopify_processor.update_product({ "product": { "id": product.shopify_id, "tags": tags } })
                else:
                    self.print_logs(f'Get this while adding product: {response_text}')
        except Exception as e: 
            self.print_logs(f'Exception in add_new_product: {e}')
            if self.DEBUG: print(f'Exception in add_new_product: {e}')
            else: pass
    
    # update product options to Size if variants are more than 1
    def set_product_options(self, product: Product, shopify_product_options: list[dict], shopify_processor: Shopify_Processor) -> None:
        try:
            if len(product.variants) > 1 and shopify_product_options:
                for option in shopify_product_options:
                    if option['name'] == 'Title':
                        shopify_processor.update_product_options(option['product_id'], option['id'], 'Size')
        except Exception as e: 
            self.print_logs(f'Exception in set_product_options: {e}')
            if self.DEBUG: print(f'Exception in set_product_options: {e}')
            else: pass

    # set product images if there is no image
    def set_product_images(self, brand: Brand, product: Product, product_title: str, shopify_processor: Shopify_Processor) -> None:
        try:
            if product.image or product.images_360:
                # create image description for product
                image_description = self.utils.create_product_image_description(brand, product, self.template_file_path)
                if not image_description: image_description = product_title
                if product.images_360:
                    # adding 360 images to product
                    self.print_logs(f'Adding product images for {product.id}')
                    self.utils.add_product_360_images(self.store.name, product, image_description, shopify_processor)
                elif product.image: 
                    print('Adding product image')
                    self.utils.add_product_image(self.store.name ,product, image_description, shopify_processor)
        except Exception as e: 
            self.print_logs(f'Exception in set_product_images: {e}')
            if self.DEBUG: print(f'Exception in set_product_images: {e}')
            else: pass 

    # get new product json for insertion in shopify
    def get_new_product_json(self, product_title: str, product_description: str, brand_name: str, product_type: str, tags: list[str], product_variants: list[dict],template_suffix: str) -> dict:
        new_product_json = {}
        try:
            new_product_json = {
                "product": {
                    "title": product_title,
                    "body_html": product_description,
                    "vendor": brand_name,
                    "product_type": product_type,
                    "template_suffix": template_suffix, 
                    "status": 'active', 
                    "published_scope": "web", 
                    "tags": tags,
                    "variants": product_variants
                }
            }
        except Exception as e: 
            self.print_logs(f'Exception in get_new_product_json: {e}')
            if self.DEBUG: print(f'Exception in get_new_product_json: {e}')
            else: pass
        finally: return new_product_json

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
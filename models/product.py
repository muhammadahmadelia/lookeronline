from models.metafields import Metafields
from models.variant import Variant

class Product:
    def __init__(self) -> None:
        self.__id: str = ''
        self.__number: str = ''
        self.__name: str = ''
        self.__brand: str = ''
        self.__frame_code: str = ''
        self.__lens_code: str = ''
        self.__type: str = ''
        self.__bridge: str = ''
        self.__template: str = ''
        self.__shopify_id: str = ''
        self.__metafields: Metafields = Metafields()
        self.__image: str = ''
        self.__images_360: list[str] = []
        self.__variants: list[Variant] = []
        pass
    
    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(self, id: str):
        self.__id = id

    @property
    def number(self) -> str:
        return self.__number

    @number.setter
    def number(self, number: str):
        self.__number = number

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def brand(self) -> str:
        return self.__brand

    @brand.setter
    def brand(self, brand: str):
        self.__brand = brand

    @property
    def frame_code(self) -> str:
        return self.__frame_code

    @frame_code.setter
    def frame_code(self, frame_code: str):
        self.__frame_code = frame_code

    @property
    def lens_code(self) -> str:
        return self.__lens_code

    @lens_code.setter
    def lens_code(self, lens_code: str):
        self.__lens_code = lens_code

    @property
    def type(self) -> str:
        return self.__type

    @type.setter
    def type(self, type: str):
        self.__type = type

    @property
    def bridge(self) -> str:
        return self.__bridge

    @bridge.setter
    def bridge(self, bridge: str):
        self.__bridge = bridge

    @property
    def template(self) -> str:
        return self.__template

    @template.setter
    def template(self, template: str):
        self.__template = template

    @property
    def shopify_id(self) -> str:
        return self.__shopify_id

    @shopify_id.setter
    def shopify_id(self, shopify_id: str):
        self.__shopify_id = shopify_id

    @property
    def metafields(self) -> Metafields:
        return self.__metafields

    @metafields.setter
    def metafields(self, metafields: Metafields):
        self.__metafields = metafields

    @property
    def image(self) -> str:
        return self.__image

    @image.setter
    def image(self, image: str):
        self.__image = image

    @property
    def images_360(self) -> list[str]:
        return self.__images_360

    @images_360.setter
    def images_360(self, images_360: list[str]):
        self.__images_360 = images_360

    @property
    def variants(self) -> list[Variant]:
        return self.__variants

    @variants.setter
    def variants(self, variants: list[Variant]):
        self.__variants = variants

    def add_single_variant(self, variant: Variant) -> None:
        self.__variants.append(variant)


    
    
    

    
    
    

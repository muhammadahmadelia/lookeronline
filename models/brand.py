from models.product import Product


class Brand:
    def __init__(self) -> None:
        # self.__id = 0
        # self.__store_id = 0
        self.__name: str = ''
        self.__code: str = ''
        self.__product_types: list[str] = []
        self.__products: list[Product] = []
        pass

    # @property
    # def id(self) -> int:
    #     return self.__id

    # @id.setter
    # def id(self, id: int):
    #     self.__id = id

    # @property
    # def store_id(self) -> int:
    #     return self.__store_id

    # @store_id.setter
    # def store_id(self, store_id: int):
    #     self.__store_id = store_id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def code(self) -> str:
        return self.__code

    @code.setter
    def code(self, code: int):
        self.__code = code

    @property
    def product_types(self) -> list[str]:
        return self.__product_types

    @product_types.setter
    def product_types(self, product_types: list[str]):
        self.__product_types = product_types

    @property
    def products(self) -> list[Product]:
        return self.__products

    @products.setter
    def products(self, products: list[Product]):
        self.__products = products

    # def empty_products(self):
    #     self.__products = []
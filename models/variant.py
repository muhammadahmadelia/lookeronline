class Variant:
    def __init__(self) -> None:
        self.__id: str = ''
        self.__product_id: str = ''
        self.__title: str = ''
        self.__sku: str = ''
        self.__inventory_quantity: int = 0
        self.__found_status: int = 1
        self.__wholesale_price: float = 0.00
        self.__listing_price: float = 0.00
        self.__barcode_or_gtin: str = ''
        self.__size: str = ''
        self.__shopify_id: str = ''
        self.__inventory_item_id: str = ''
        pass

    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(self, id: str):
        self.__id = id

    @property
    def product_id(self) -> str:
        return self.__product_id

    @product_id.setter
    def product_id(self, product_id: str):
        self.__product_id = product_id

    @property
    def title(self) -> str:
        return self.__title

    @title.setter
    def title(self, title: str):
        self.__title = title

    @property
    def sku(self) -> str:
        return self.__sku

    @sku.setter
    def sku(self, sku: str):
        self.__sku = sku

    @property
    def inventory_quantity(self) -> int:
        return self.__inventory_quantity

    @inventory_quantity.setter
    def inventory_quantity(self, inventory_quantity: int):
        self.__inventory_quantity = inventory_quantity

    @property
    def found_status(self) -> int:
        return self.__found_status

    @found_status.setter
    def found_status(self, found_status: int):
        self.__found_status = found_status

    @property
    def wholesale_price(self) -> float:
        return self.__wholesale_price

    @wholesale_price.setter
    def wholesale_price(self, wholesale_price: float):
        self.__wholesale_price = wholesale_price

    @property
    def listing_price(self) -> float:
        return self.__listing_price

    @listing_price.setter
    def listing_price(self, listing_price: float):
        self.__listing_price = listing_price

    @property
    def barcode_or_gtin(self) -> str:
        return self.__barcode_or_gtin

    @barcode_or_gtin.setter
    def barcode_or_gtin(self, barcode_or_gtin: str):
        self.__barcode_or_gtin = barcode_or_gtin

    @property
    def size(self) -> str:
        return self.__size

    @size.setter
    def size(self, size: str):
        self.__size = size

    @property
    def shopify_id(self) -> str:
        return self.__shopify_id

    @shopify_id.setter
    def shopify_id(self, shopify_id: str):
        self.__shopify_id = shopify_id

    @property
    def inventory_item_id(self) -> str:
        return self.__inventory_item_id

    @inventory_item_id.setter
    def inventory_item_id(self, inventory_item_id: str):
        self.__inventory_item_id = inventory_item_id

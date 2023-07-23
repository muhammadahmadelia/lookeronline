from models.brand import Brand

class Store:
    def __init__(self) -> None:
        self.__name: str = ''
        self.__link: str = ''
        self.__username: str = ''
        self.__password: str = ''
        self.__brands: list[Brand] = []
        pass

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def link(self) -> str:
        return self.__link

    @link.setter
    def link(self, link: str):
        self.__link = link

    @property
    def username(self) -> str:
        return self.__username

    @username.setter
    def username(self, username: str):
        self.__username = username

    @property
    def password(self) -> str:
        return self.__password

    @password.setter
    def password(self, password: str):
        self.__password = password

    @property
    def brands(self) -> list[Brand]:
        return self.__brands

    @brands.setter
    def brands(self, brands: list[Brand]):
        self.__brands = brands
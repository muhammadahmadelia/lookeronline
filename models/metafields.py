class Metafields:
    def __init__(self) -> None:
        self.__for_who: str = ''
        self.__lens_material: str = ''
        self.__lens_technology: str = ''
        self.__lens_color: str = ''
        self.__frame_shape: str = ''
        self.__frame_material: str = ''
        self.__frame_color: str = ''
        self.__size_bridge_template: str = ''
        self.__gtin1: str = ''
        pass

    @property
    def for_who(self) -> str:
        return self.__for_who

    @for_who.setter
    def for_who(self, for_who: str):
        self.__for_who = for_who
    
    @property
    def lens_material(self) -> str:
        return self.__lens_material

    @lens_material.setter
    def lens_material(self, lens_material: str):
        self.__lens_material = lens_material

    @property
    def lens_technology(self) -> str:
        return self.__lens_technology

    @lens_technology.setter
    def lens_technology(self, lens_technology: str):
        self.__lens_technology = lens_technology

    @property
    def lens_color(self) -> str:
        return self.__lens_color

    @lens_color.setter
    def lens_color(self, lens_color: str):
        self.__lens_color = lens_color

    @property
    def frame_shape(self) -> str:
        return self.__frame_shape

    @frame_shape.setter
    def frame_shape(self, frame_shape: str):
        self.__frame_shape = frame_shape

    @property
    def frame_material(self) -> str:
        return self.__frame_material

    @frame_material.setter
    def frame_material(self, frame_material: str):
        self.__frame_material = frame_material

    @property
    def frame_color(self) -> str:
        return self.__frame_color

    @frame_color.setter
    def frame_color(self, frame_color: str):
        self.__frame_color = frame_color

    @property
    def size_bridge_template(self) -> str:
        return self.__size_bridge_template
    
    @size_bridge_template.setter
    def size_bridge_template(self, size_bridge_template: str):
        self.__size_bridge_template = size_bridge_template
    
    @property
    def gtin1(self) -> str:
        return self.__gtin1

    @gtin1.setter
    def gtin1(self, gtin1: str):
        self.__gtin1 = gtin1

    




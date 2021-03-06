class PagingBar:
    """
    '''一个可以翻页的分页, 支持1~10页'''

    上一页◂➀۰➁۰➌۰➃۰➄▸下一页

    Attributes:
        pgamt (int): 总页数
        crtpg (int): 当前页码
    """

    __hollowsymbols = '➀➁➂➃➄➅➆➇➈➉'
    __solidsymbols = '➊➋➌➍➎➏➐➑➒➓'

    def __init__(self, pgamt: int = 3):
        """
        生成初始页码为1的分页栏

        Args:
            pgamt (int, optional): 页面数量，最大支持10页. Defaults to 3.
        """
        assert pgamt <= 10, '分页栏最大支持10页'
        self.pgamt = pgamt
        self.crtpg = 1
        serial = '۰'.join(self.__hollowsymbols[:self.pgamt])
        self.__template = self.bar = '上一页◂' + serial + '▸下一页' 
        self.turnpage(1)

    def __str__(self) -> str:
        return self.bar

    def turnpage(self, pgnumber: int) -> str:
        """
        翻到指定页面

        Args:
            pgnumber (int): 指定的页码

        Returns:
            str: 当前分页栏字符串
        """
        self.crtpg = pgnumber
        self.bar = self.__template.replace(self.__hollowsymbols[self.crtpg-1], self.__solidsymbols[self.crtpg-1])
        if self.crtpg == 1:
            self.bar = self.bar.replace('上一页', '‖')
        if self.crtpg == self.pgamt:
            self.bar = self.bar.replace('下一页', '‖')
        return self.bar

    def pgup(self) -> str:
        if self.crtpg != 1:
            self.crtpg -= 1
            self.turnpage(self.crtpg)
        return self.bar

    def pgdn(self) -> str:
        if self.crtpg != self.pgamt:
            self.crtpg += 1
            self.turnpage(self.crtpg)
        return self.bar


if __name__ == "__main__":
    pg = PagingBar(5)
    print(pg.pgdn())
    print(pg.pgup())
    print(pg.turnpage(4))
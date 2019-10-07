import pytz
import requests
from bs4 import BeautifulSoup
from datetime import datetime


# 中英對照表
board2url_table = {
    "八卦": "Gossiping",
    "表特": "Beauty"
}


class InvlaidUrlError(Exception):
    pass


class Board:
    '''
    PTT 板的資訊
    - board_name : 板名
    - board_url : 板的網址
    - domain_url : PTT 主網址
    '''

    def __init__(self, board_name):

        if board_name not in board2url_table.keys():
            raise KeyError(f"{board_name} is not in board2url table!")

        self._board_name = board_name
        self._domain = 'https://www.ptt.cc'

    @property
    def url(self):
        board_url = board2url_table[self._board_name]
        return f'{self._domain}/bbs/{board_url}/index.html'

    @property
    def board_name(self):
        return self._board_name

    @property
    def domain(self):
        return self._domain


class PTTBasicCrawler:
    """
        功能:
        ----------
        爬蟲基本功能

        參數:
        ----------
        - board_name : 目標的版名
        - today_date : 今日日期
        - min_push_count : 最少推文數

        屬性:
        ----------
        - board : 目標板的資訊
        - session : 網路資訊
        - today_date : 今日日期
        - min_push_count : 最少推文數

        注意
        ----------
        記得實做 `get_articles`
    """

    def __init__(self, board_name: str, today_date: str, min_push_count: int = 0):

        self.board = Board(board_name)
        self.session = self._create_session()
        self.today_date = today_date
        self.min_push_count = min_push_count

    def _create_session(self) -> requests.Session:
        """
        功能
        ----------
        使用 session cookie 解決點選已滿18歲按鈕

        回傳
        ----------
        已設定好的 session
        """

        session = requests.Session()
        session.cookies.set('over18', '1')
        return session

    def get_web_page(self, url: str, **kwargs) -> str:
        """
        功能
        ----------
        抓取目標網頁內容


        參數:
        ----------
        - url : 目標網址
        - **kwargs : 其他設定


        回傳
        ----------
        目標網頁內容
        """
        res = self.session.get(url, **kwargs)

        if res.status_code != 200:
            raise InvlaidUrlError(f"{res.url} is invalid url!")

        return res.text

    def get_and_parse(self, url: str, **kwargs) -> BeautifulSoup:
        """
        功能
        ----------
        抓取目標網頁內容，並使用 `BeautifulSoup` 解析

        參數:
        ----------
        - url : 目標網址
        - **kwargs : 其他設定

        回傳
        ----------
        解析後成果
        """

        html_content = self.get_web_page(url, **kwargs)
        soup = BeautifulSoup(html_content, 'lxml')

        return soup

    def get_article_date(self, article) -> str:
        """
        功能
        ----------
        搜尋文章日期

        參數:
        ----------
        - article :
            - type : bs4.element.Tag
            - 文章元素

        回傳
        ----------
        文章日期
        """

        return article.find('div', class_='date').text.strip()

    def get_push_count(self, article) -> int:
        """
        功能
        ----------
        搜尋文章推文數

        參數:
        ----------
        - article :
            - type : bs4.element.Tag
            - 文章元素

        回傳
        ----------
        文章推文數
        """

        push_str = article.find('div', class_='nrec').text
        push_count = 0

        try:
            push_count = int(push_str)
        except ValueError:
            if push_str == '爆':
                push_count = 100
            elif push_str.startswith('X'):
                push_count = -10
            elif not push_str:
                push_count = 0

        return push_count

    def is_article_exist(self, article) -> bool:
        """
        功能
        ----------
        以有沒有超連結來判斷文章是否存在

        參數:
        ----------
        - article :
            - type : bs4.element.Tag
            - 文章元素

        回傳
        ----------
        文章推文數
        """

        return article.find("a")

    def get_pre_page_link(self, html_content: BeautifulSoup) -> str:
        """
        功能
        ----------
        搜尋下一頁的連結

        參數:
        ----------
        - html_content : 已解析的網頁內容

        回傳
        ----------
        下一頁連結
        """

        link = html_content.find(
            'div', class_='btn-group btn-group-paging').find_all('a', class_="btn")[1]['href']

        return self.board.domain + link

    def get_articles(self):
        raise NotImplementedError()


class PTTGossipingCrawler(PTTBasicCrawler):
    '''
    八卦板爬蟲

    屬性
    ----
        - max_page_size: 最大篇數
    '''

    def __init__(self, today_date: str, min_push_count: int = 0):

        board_name = "八卦"

        super().__init__(board_name, today_date, min_push_count)
        self.max_page_size = 5

    def _get_current_page_articles(self, url: str) -> tuple:
        """
        功能
        ----------
        取得`當前`頁面符合條件的文章

        參數:
        ----------
        - url : 目標網址

        回傳
        ----------
        一個 list 保存符合條件的文章資訊

        - title
        - link
        - 推文數
        - 日期

        """
        current_page_result_articles = []  # 保存符合條件的文章資訊

        html_content = self.get_and_parse(url)  # 取得已解析的網頁內容

        pre_page_link = self.get_pre_page_link(html_content)  # 搜尋上一頁連結

        current_page_all_articles = html_content.find_all(
            'div', class_='r-ent')  # 搜尋文章區塊們

        # 一個一個取得網頁資訊
        for article in current_page_all_articles:

            push_count = self.get_push_count(article)
            article_date = self.get_article_date(article)

            # 如果 推文少於設定值 -> 略過
            if push_count < self.min_push_count:
                continue

            # 如果 文章不存在 -> 略過
            if not self.is_article_exist(article):
                continue

            # 如果超過日期 -> 跳出

            if article_date != self.today_date:
                return current_page_result_articles, pre_page_link, article_date

            link = self.board.domain + article.find('a')['href']  # 取得文章連結
            title = article.find('a').text  # 取得文章標題

            # 建立表格，一一對應
            article_info = {
                'title': title,
                'date': article_date,
                'link': link,
                'push_count': push_count
            }

            current_page_result_articles.append(article_info)  # 加入結果 list

        return current_page_result_articles, pre_page_link, article_date

    def get_articles(self):

        result = []

        # 處理第一頁
        articles, prepage_link, _ = self._get_current_page_articles(
            self.board.url)

        article_date = self.today_date

        # 處理第二頁開始，直到日期不一樣
        while article_date == self.today_date and len(result) < self.max_page_size:
            result += articles

            articles, prepage_link, article_date = self._get_current_page_articles(
                prepage_link)

        return result[:self.max_page_size]


if __name__ == "__main__":

    # 設定時區
    time_zone = pytz.timezone("Asia/Taipei")

    # 取得日期
    today_date = datetime.now(time_zone).strftime("%m/%d").lstrip("0")

    print("today is ", today_date)

    result = PTTGossipingCrawler(today_date, min_push_count=30).get_articles()

    for r in result:
        print(r)

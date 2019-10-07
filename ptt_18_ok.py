import requests
from ptt import Board

board = Board("八卦")
session = requests.session()
session.cookies.set('over18', '1')  # 設定cookie 一直向 server 回答滿 18 歲了 !​
res = session.get(board.url)

print(res.text)

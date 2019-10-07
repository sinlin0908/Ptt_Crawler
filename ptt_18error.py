import requests
from ptt import Board

board = Board("八卦")
res = requests.get(board.url)

print(res.text)

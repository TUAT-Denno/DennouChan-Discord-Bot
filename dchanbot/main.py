import sys

import os
from os.path import join, dirname
from dotenv import load_dotenv

from bot import DChanBot

# .envファイルに記述されている環境変数を読み込む
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(
    dotenv_path = dotenv_path,
    verbose = True
)

def main() -> int:
    # ボット起動
    bot = DChanBot(token = os.environ.get("DBOT_CONFIG_DIR"))
    bot.run()   # <- ブロッキングするので必ず最後に呼ぶこと！

    return 0

if __name__ == '__main__':
    sys.exit(main())

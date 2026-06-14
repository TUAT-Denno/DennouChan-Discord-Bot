from .acct import Acct
from bot import DChanBot

# Pycordがこのモジュールを読み込むために必要
def setup(bot : DChanBot):
    bot.add_cog(Acct(bot))

import logging
from pathlib import Path

import discord
from pydantic import BaseModel

from .config import Config
from .config_registory import ConfigRegistry

logger = logging.getLogger("dchanbot.bot")

class BotConfig(BaseModel):
    discord_token : str = "SET_YOUR_DISCORD_BOT_TOKEN_HERE"

class DChanBot(discord.AutoShardedBot):
    def __init__(self, confdir : Path):
        self._confdir = confdir

        self._confregistory = ConfigRegistry()
        
        # 設定の読み込み
        self._config = Config(
            filename= confdir / "dchanbot.json",
            schema = BotConfig
        )
        self._config.load()
        self.register_cog_config(self._config)
        
        # Botが利用するイベントの設定
        # DChanBotはpresences, members以外に関連した全てのイベントを受け取ることができる
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents = intents)

        print("Starting bot...")

    async def on_ready(self):
        print(f"Hello! I'm {self.user.name}!!")
        print(f"ID: {self.user.id}")

        self._load_cogs()
        await self._update_presence() 

    async def _update_presence(self):
        await self.change_presence(
            activity = discord.Game(name = '農工ライフ')
        )

    def run(self):
        token = self._config.data.discord_token
        super().run(token = token)

    async def close(self):
        self._confregistory.save_all()  # 設定の保存
        await super().close()

    def register_cog_config(self, conf : Config):
        self._confregistory.register(conf)

    # Bot実行に必要なモジュール（cogsフォルダの中にあるもの）を読み込む
    def _load_cogs(self):
        ret = self.load_extensions(
            "cogs.greeting",
            store = True    # store=Trueとすると、ロードエラー時にクリティカルになる
        )

import logging
import asyncio
from pathlib import Path

import discord
from pydantic import BaseModel

from core.file_model_registory import FileModelRegistry

logger = logging.getLogger("dchanbot.bot")

class BotConfig(BaseModel):
    discord_token : str = "SET_YOUR_DISCORD_BOT_TOKEN_HERE",

class DChanBot(discord.AutoShardedBot):
    def __init__(self, confdir : Path, datadir : Path):
        self._confregistory = FileModelRegistry(rootdir = confdir)
        self._dataregistory = FileModelRegistry(rootdir = datadir)
        
        # 設定の読み込み
        self._config = self._confregistory.load(
            name = "dchanbot",
            schema = BotConfig
        )

        # Botが利用するイベントの設定
        # DChanBotはpresences, members以外に関連した全てのイベントを受け取ることができる
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents = intents)

        print("Starting bot...")

    async def on_ready(self):
        print(f"Hello! I'm {self.user.name}!!")
        print(f"ID: {self.user.id}")

        for guild in self.guilds:
            print(f"Installed in: {guild.name} - {guild.id}")

        await self.sync_commands(force = True)

        await self._update_presence()

    async def _update_presence(self):
        await self.change_presence(
            activity = discord.Game(name = '農工ライフ')
        )

    def run(self):
        self._load_cogs()

        token = self._config.data.discord_token
        super().run(token = token)

    async def close(self):
        print("Shutting down bot...")

        # Cogに終了時の処理をさせる
        for cog in self.cogs.values():
            if hasattr(cog, "on_shutdown"):
                routine = getattr(cog, "on_shutdown")
                if asyncio.iscoroutinefunction(routine):
                    #try:
                        await routine()
                    #except Exception as e:
                    #    print(f"{cog.__class__.__name__}.on_shutdown() failed: {e}")

        self._dataregistory.save_all()  # データファイルの保存
        self._confregistory.save_all()  # 設定の保存

        await super().close()

    # Bot実行に必要なモジュール（cogsフォルダの中にあるもの）を読み込む
    def _load_cogs(self):
        extensions = [
            'cogs.greeting',
            'cogs.schednotifier',
            'cogs.chat'
        ]

        for ext in extensions:
            try:
                self.load_extension(
                    name = ext,
                    store = True    # store=Trueとすると、ロードエラー時にクリティカルになる
                )
            except Exception as e:
                print(f"Error loading extensions[{ext}]: {e}")

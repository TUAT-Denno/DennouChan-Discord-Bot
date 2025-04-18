import logging

import discord


logger = logging.getLogger("dchanbot.bot")


class DChanBot(discord.AutoShardedBot):
    def __init__(self, token : str):
        self._token = token
        
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

    # Bot実行に必要なモジュール（cogsフォルダの中にあるもの）を読み込む
    def _load_cogs(self):
        ret = self.load_extensions(
            "cogs.greeting",
            store = True    # store=Trueとすると、ロードエラー時にクリティカルになる
        )

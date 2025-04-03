import discord
from discord.ext import commands

from bot import DChanBot

class Greeting(commands.Cog):
    def __init__(self, bot : DChanBot):
        self._bot = bot

        print("The Greeting Cog is loaded!!")

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        print("The Greeting Cog is now ready.")

    @commands.Cog.listener(name = "on_message")
    async def on_message(self, message : discord.Message):
        # ボットからのメッセージは無視
        if message.author.bot is True:
            return

        # 以下の条件を満たす場合、無視
        #  ・テキスト/ニュースチャンネル/公開スレッド/DMからのMSGでない
        #  ・NSFWに設定されているチャンネルからのMSG
        if(message.channel.type == discord.ChannelType.text or
           message.channel.type == discord.ChannelType.news or
           message.channel.type == discord.ChannelType.public_thread):
            if message.channel.is_nsfw():
                await message.channel.send(content="すけべな所で話しかけないでください！！")
                return
        else:
            if (message.channel.type != discord.ChannelType.private):
                return

        if(message.type != discord.MessageType.default and
           message.type != discord.MessageType.reply):
            return

        if self._bot.user.mentioned_in(message):  # メンションされたか？
            await self._say_hello(message)

    async def _say_hello(self, message : discord.Message):
        msg_content = message.clean_content or ""
        if msg_content == "":
            return

        greetings = [
            "おはよう",
            "おはようございます",
            "こんにちは",
            "こんにちわ",
            "こんばんは",
            "こんばんわ",
            "おやすみ",
            "おやすみなさい",
            "おはこんばんにちは",
            "ごきげんよう"
        ]
        for g in greetings:
            if g in msg_content:
                reply = f"{message.author.mention}さん、{g}"
                await message.channel.send(
                    content = reply,
                    reference = message
                )

# Pycordがこのモジュールを読み込むために必要
def setup(bot : DChanBot):
    bot.add_cog(Greeting(bot))

import discord
from discord.ext import commands, tasks

from bot import DChanBot
from core.chat.qdrant_db import QdrantDB
from core.chat.summarizer import Summarizer
from core.chat.encryptor import TextEncryptor

class DiscordMessageCollector(commands.Cog):
    def __init__(
        self,
        bot : DChanBot,
        db : QdrantDB,
        summarizer : Summarizer,
        encryptor : TextEncryptor
    ):
        self._bot = bot

        self._db = db
        self._summarizer = summarizer
        self._encryptor = encryptor

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        print("The DiscordMessageCollector is now ready.")

    @commands.Cog.listener(name = "on_message")
    async def on_message(self, message : discord.Message):
        # ボットからのメッセージは無視
        if message.author.bot is True:
            return

        # 以下の条件を満たす場合、無視
        #  ・テキスト/ニュースチャンネル/公開スレッド/DMからのMSGでない
        #  ・NSFWに設定されているチャンネルからのMSG
        allowed_ch_types = {
            discord.ChannelType.text,
            discord.ChannelType.news,
            discord.ChannelType.public_thread,
            discord.ChannelType.private  # DMチャンネル
        }
        if message.channel.type not in allowed_ch_types:
            return
        
        if message.channel.type in {discord.ChannelType.text, discord.ChannelType.news, discord.ChannelType.public_thread}:
            if message.channel.is_nsfw():
                return

        # 通常のメッセージ・返信以外は無視
        if(message.type != discord.MessageType.default and
           message.type != discord.MessageType.reply):
            return

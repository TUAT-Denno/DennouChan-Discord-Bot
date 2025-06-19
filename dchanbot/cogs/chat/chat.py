import logging

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from pydantic import BaseModel

from bot import DChanBot
from core.chat.chat_instance import ChatInstances

# 設定用の構造体
class ChatCogConfig(BaseModel):
    google_api_key : str = "YOUR_GOOGLE_API_KEY"


class CharChat(commands.Cog):
    def __init__(self, bot : DChanBot):
        print("Chat Cog is now loaded")

        self._bot = bot

        # 設定の読み込み
        self._config = self._bot._confregistory.load(
            name = "chat",
            schema = ChatCogConfig,
            subdir = "chat"
        )

        self._instances = ChatInstances(
            api_key = self._config.data.google_api_key,
            data_dir = self._bot._dataregistory._rootdir / "chat"
        )

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        print("Chat Cog is now ready")

    #
    #   メッセージ投稿時の処理
    #     メッセージ中にBotに対するメンションがあれば返答する
    #
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
                await message.channel.send("NSFWチャンネルでは返答できません")
                return

        # 通常のメッセージ・返信以外は無視
        if(message.type != discord.MessageType.default and
           message.type != discord.MessageType.reply):
            return

        if self._bot.user.mentioned_in(message):  # メンションされたか？
            async with message.channel.typing():
                session_id = self._get_session_id(message)

                response = await self._instances.chat(session_id, message.content)

                await message.channel.send(
                    content = response,
                    reference = message
                )

    async def on_shutdown(self):
        print("Shutting down Chat Cog...")

        await self._instances.save_all_session()

    def _get_session_id(self, message : discord.Message) -> str:
        if message.channel.type is discord.ChannelType.private:
            return f"session_u{message.author.id}"
        else:
            return f"session_g{message.guild.id}"

    #
    # コマンドの実装
    #

    chatcmds = SlashCommandGroup(
        name = "chat",
        description = "チャット機能関連のコマンドです",
    )

    @chatcmds.command(name = "stat", description = "チャットの統計データを表示します")
    async def show_stat(
        self,
        ctx : discord.ApplicationContext
    ):
        if ctx.channel.type is discord.ChannelType.private:
            session_id = f"session_u{ctx.author.id}"
        else:
            session_id = f"session_g{ctx.guild.id}"

        stat = self._instances.get_statistic(session_id)
        msg = (
            f"チャット回数：{stat.chat_count}回\n\n"
            f"トークン使用量\n"
            f"入力：{stat.tokusage.input_tokens}トークン\n"
            f"出力：{stat.tokusage.output_tokens}トークン\n"
            f"総計：{stat.tokusage.total_tokens}トークン\n"
        )
        await ctx.respond(msg)

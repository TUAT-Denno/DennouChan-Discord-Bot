import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from pydantic import BaseModel

from bot import DChanBot

class AcctCogConfig(BaseModel):
    acct_form_url : str = "SET_YOUR_ACCT_FORM_URL_HERE"

class Acct(commands.Cog):
    acctcmds = SlashCommandGroup(
        name = "acct",
        description = "会計関連コマンド",
    )

    def __init__(self, bot : DChanBot):
        self._bot = bot

        # Load configuration
        self._config = self._bot._confregistory.load(
            name = "acct",
            schema = AcctCogConfig,
            subdir = "acct"
        )

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        print("Acct is now ready")

    @acctcmds.command(name = "form", description = "会計フォームのURLを返します")
    async def form(self, ctx: discord.ApplicationContext):
        form_url = self._config.acct_form_url
        if not form_url or form_url == "SET_YOUR_ACCT_FORM_URL_HERE":
            await ctx.respond(
                "会計フォームURLが未設定です。管理者は `acct.json` の "
                "`acct_form_url` を設定してください。",
                ephemeral = True
            )
            return

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label = "会計フォームを開く", url = form_url)
        )

        await ctx.respond(
            "会計報告フォームはこちらです。\n"
            "領収書画像・用途・金額を確認してから提出してください。",
            view = view,
            ephemeral = True
        )

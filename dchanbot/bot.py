"""The main module for Dennou-Chan Discord Bot
"""

import logging
import asyncio
from pathlib import Path

import discord
from pydantic import BaseModel

from core.file_model_registory import FileModelRegistry

logger = logging.getLogger("dchanbot.bot")

class BotConfig(BaseModel):
    """Configuration schema for DChanBot

    Attribute:
        discord_token (str): The bot token used for authentication with Discord API
    """
    discord_token : str = "SET_YOUR_DISCORD_BOT_TOKEN_HERE",

class DChanBot(discord.AutoShardedBot):
    """The main bot class for Dennou-Chan Discord Bot

    DChanBot is a Discord bot implementation using Pycord's AutoShardedBot.
    It loads configuration from JSON files, manages bot lifecycle, 
    and dynamically loads extensions (cogs).

    Attributes:
        _confregistory (FileModelRegistry): Registry for configuration files.
        _dataregistory (FileModelRegistry): Registry for persistent data files.
        _config (BotConfig): Bot configuration object.
    """

    def __init__(self, confdir : Path, datadir : Path):
        """Initialize the bot.

        Args:
            confdir (Path): Directory where configuration files are stored.
            datadir (Path): Directory where runtime data is stored.
        """
        self._confregistory = FileModelRegistry(rootdir = confdir)
        self._dataregistory = FileModelRegistry(rootdir = datadir)
        
        # Load configuration
        self._config = self._confregistory.load(
            name = "dchanbot",
            schema = BotConfig
        )

        # Set up bot intents
        # DChanBot listens to all events except presences and members
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents = intents)

        print("Starting bot...")

    async def on_ready(self):
        """Event handler for when the bot is ready."""
        print(f"Hello! I'm {self.user.name}!!")
        print(f"ID: {self.user.id}")

        for guild in self.guilds:
            print(f"Installed in: {guild.name} - {guild.id}")

        await self.sync_commands(force = True)

        await self._update_presence()

    async def _update_presence(self):
        """Updates the bot's presence (status)."""
        await self.change_presence(
            activity = discord.Game(name = '農工ライフ')
        )

    def run(self):
        """Runs the bot after loading all extensions."""
        self._load_cogs()

        token = self._config.data.discord_token
        super().run(token = token)

    async def close(self):
        """Gracefully shuts down the bot and saves data/config files."""
        print("Shutting down bot...")

        # Call shutdown hooks in each cog if defined
        for cog in self.cogs.values():
            if hasattr(cog, "on_shutdown"):
                routine = getattr(cog, "on_shutdown")
                if asyncio.iscoroutinefunction(routine):
                    #try:
                        await routine()
                    #except Exception as e:
                    #    print(f"{cog.__class__.__name__}.on_shutdown() failed: {e}")

        self._dataregistory.save_all()  # Save runtime data files
        self._confregistory.save_all()  # Save configuration files

        await super().close()

    def _load_cogs(self):
        """Loads required cogs (extensions) for bot functionality."""
        extensions = [
            'cogs.schednotifier',
            'cogs.chat'
        ]

        for ext in extensions:
            try:
                self.load_extension(
                    name = ext,
                    store = True    # If store=True, failure to load raises a critical error
                )
            except Exception as e:
                print(f"Error loading extensions[{ext}]: {e}")

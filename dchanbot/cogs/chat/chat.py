import logging

import discord
from discord.ext import commands, tasks
from discord.commands import SlashCommandGroup

from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI

from bot import DChanBot
from core.chat.chat_instance import ChatInstance, ChatRequest, ChatResponse


logger = logging.getLogger(__name__)

class ChatCogConfig(BaseModel):
    """Configuration schema for the Chat Cog"""
    google_api_key : str = "YOUR_GOOGLE_API_KEY"


class CharChat(commands.Cog):
    """A Discord cog for chatbot functionality using mentions and slash commands"""

    def __init__(self, bot : DChanBot):
        """Initializes the Chat Cog."""
        logger.info("Chat Cog is now loaded")

        self._bot = bot

        # Load chat configuration
        self._config = self._bot._confregistory.load(
            name = "chat",
            schema = ChatCogConfig,
            subdir = "chat"
        )

        # Prepare LLM for chat
        self._llm = ChatGoogleGenerativeAI(
            model = "gemini-3.5-flash",
            api_key = self._config.google_api_key
        )

        # Initialize chat instance manager
        self._instances = ChatInstance(model = self._llm)

        # Start periodic execution routines
        # self.loop_save_chat_sessions.start()

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        """Triggered when the bot is fully ready."""
        logger.info("Chat Cog is now ready")

    @commands.Cog.listener(name = "on_message")
    async def on_message(self, message : discord.Message):
        """Responds to messages that mention the bot, if the context is appropriate.

        Args:
            message (discord.Message): Incoming message to evaluate.
        """
        # Ignore messages from other bots
        if message.author.bot is True:
            return

        # Only allow specific channel types
        allowed_ch_types = {
            discord.ChannelType.text,
            discord.ChannelType.news,
            discord.ChannelType.public_thread,
            discord.ChannelType.private  # DMs
        }
        if message.channel.type not in allowed_ch_types:
            return
        
        # Skip NSFW channels
        if message.channel.type in {discord.ChannelType.text, discord.ChannelType.news, discord.ChannelType.public_thread}:
            if message.channel.is_nsfw():
                await message.channel.send("NSFWチャンネルでは返答できません")
                return

        # Ignore messages that are not default or replies
        if(message.type != discord.MessageType.default and
           message.type != discord.MessageType.reply):
            return

        # Respond if bot is mentioned OR in DM channel
        if (
            message.channel.type == discord.ChannelType.private
            or self._bot.user.mentioned_in(message)
        ):
            async with message.channel.typing():
                # session_id = self._get_session_id(message)
                req = ChatRequest(
                    content = message.content
                )
                response = await self._instances.chat(req)

                await message.channel.send(
                    content = response.content,
                    reference = message if message.channel.type != discord.ChannelType.private else None
                )

    async def on_shutdown(self):
        """Called during bot shutdown to persist session data."""
        logger.info("Shutting down Chat Cog...")

        # self.loop_save_chat_sessions.stop()

    def _get_session_id(self, message : discord.Message) -> str:
        """Generates a session ID based on message context.

        Args:
            message (discord.Message): The incoming message.

        Returns:
            str: A session ID string.
        """
        if message.channel.type is discord.ChannelType.private:
            return f"session_u{message.author.id}"
        else:
            return f"session_g{message.guild.id}"

    #
    # Implementation of commands
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
        """Displays chat statistics and token usage for the current session.

        Args:
            ctx (discord.ApplicationContext): The command context.
        """
        pass


    #
    # Implementation of periodic execution routines
    #

    @tasks.loop(hours = 1)
    async def loop_save_chat_sessions(self):
        """Periodically saves all active chat sessions to disk.

        This task runs once every hour to flush and summarize all in-memory
        chat histories and persist usage statistics. It helps ensure that
        recent conversation data is not lost in the event of an unexpected shutdown.
        """
        pass

import logging

from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord.commands import SlashCommandGroup

from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI

from bot import DChanBot
from core.chat.chat_service import ChatService, ChatRequest, ChatResponse, ConversationSource
from core.chat.prompt_manager import PromptManager
from core.chat.conversation_repository import InMemoryConversationRepository


logger = logging.getLogger(__name__)


def build_conversation_id(
    *,
    user_id: str,
    guild_id: str | None,
    channel_id: str | None,
) -> str:
    if guild_id is None:
        return f"discord:dm:user:{user_id}"

    if channel_id is None:
        raise ValueError(
            "channel_id is required for guild conversations"
        )

    return (
        f"discord:guild:{guild_id}"
        f":channel:{channel_id}"
        f":user:{user_id}"
    )

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

        self._prompt_manager = PromptManager(
            Path(__file__).parent / "prompts"
        )

        self._conversation_repository = (
            InMemoryConversationRepository()
        )

        # Initialize chat service
        self._service = ChatService(
            model = self._llm,
            prompt_manager = self._prompt_manager,
            conversation_repository=self._conversation_repository
        )

        # Start periodic execution routines
        # self.loop_save_chat_sessions.start()

    def _create_chat_request(self, message: discord.Message) -> ChatRequest:
        user_id = str(message.author.id)

        if message.guild is None:
            return ChatRequest(
                conversation_id = build_conversation_id(
                    user_id = user_id,
                    guild_id = None,
                    channel_id = None,
                ),
                content = message.content,
                user_id = user_id,
                source = ConversationSource.DM,
            )

        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)

        return ChatRequest(
            conversation_id = build_conversation_id(
                user_id = user_id,
                guild_id = guild_id,
                channel_id = channel_id,
            ),
            content = message.content,
            user_id = user_id,
            source = ConversationSource.GUILD,
            guild_id = guild_id,
            channel_id = channel_id,
        )

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

        if message.guild is None:
            request = ChatRequest(
                conversation_id = build_conversation_id(
                    user_id = str(message.author.id),
                    guild_id = None,
                    channel_id = None,
                ),
                content = message.content,
                user_id = str(message.author.id),
                source = ConversationSource.DM,
            )
        else:
            request = ChatRequest(
                conversation_id = build_conversation_id(
                    user_id = str(message.author.id),
                    guild_id = str(message.guild.id),
                    channel_id = str(message.channel.id),
                ),
                content = message.content,
                user_id = str(message.author.id),
                source = ConversationSource.GUILD,
                guild_id = str(message.guild.id),
                channel_id = str(message.channel.id),
            )

        # Respond if bot is mentioned OR in DM channel
        if (
            message.channel.type == discord.ChannelType.private
            or self._bot.user.mentioned_in(message)
        ):
            async with message.channel.typing():
                # session_id = self._get_session_id(message)
                response = await self._service.chat(request)

                await message.channel.send(
                    content = response.content,
                    reference = message if message.channel.type != discord.ChannelType.private else None
                )

    async def on_shutdown(self):
        """Called during bot shutdown to persist session data."""
        logger.info("Shutting down Chat Cog...")

        # self.loop_save_chat_sessions.stop()

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

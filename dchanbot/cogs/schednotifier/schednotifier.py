from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo   # from Python 3.9
import logging
from pathlib import Path
from typing import Dict

import discord
from discord.ext import commands, tasks
from discord.commands import Option, SlashCommandGroup
from pydantic import BaseModel

from bot import DChanBot
from .gcalendar import GCalenderClient


class SchedCogConfForGuild(BaseModel):
    """Guild-specific configuration for the schedule notifier cog."""
    calendar_id : str = ""
    channel_id : int = -1

class SchedCogConfig(BaseModel):
    """Global configuration schema for the schedule notifier cog."""
    client_secret_path : str = ""
    reflesh_token_path : str = ""
    guilds_conf : Dict[str, SchedCogConfForGuild] = {}  # "guild_id" : "config"


logger = logging.getLogger("dchanbot.cogs.schednotifier")


class SchedNotifier(commands.Cog):
    """Cog for notifying Discord servers of upcoming Google Calendar events."""

    schedcmds = SlashCommandGroup(
        name = "sched",
        description = "スケジュール通知関連のコマンドです",
    )

    def __init__(self, bot : DChanBot):
        """Initializes the schedule notifier cog."""
        self._bot = bot

        print("SchedNotifier is now loaded")

        # Load configuration
        self._config = self._bot._confregistory.load(
            name = "schednotifier",
            schema = SchedCogConfig,
            subdir = "schednotifier"
        )

        # Prepare Calendar API client
        clisecret_path = self._config.data.client_secret_path
        reftoken_path = self._config.data.reflesh_token_path

        self._apiclient = GCalenderClient()
        self._apiclient.authorize(
            reflesh_token_path = Path(reftoken_path),
            client_secrets_path = Path(clisecret_path)
        )

        if self._apiclient.build() is False:
            logger.critical("Failed to build Calendar API client")
            return

        self.loop_notify_today_schedule.start()
        self.loop_notify_tomorrow_schedule.start()

    @commands.Cog.listener(name = "on_ready")
    async def on_ready(self):
        """Fired when the cog is fully ready."""
        print("SchedNotifier is now ready")

    #
    # Implementation of commands
    #

    @schedcmds.command(name = "set-calid", description = "カレンダーIDの設定をします")
    async def set_calendar_id(
        self,
        ctx : discord.ApplicationContext,
        newid : Option(str, "新しいカレンダーID")
    ):
        """Sets the Google Calendar ID for the current guild."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("管理者専用のコマンドです。", ephemeral = True)
            return
        
        self._set_calendar_id(newid, ctx.guild)
        await ctx.respond(f"カレンダーIDを{newid}に設定しました。")

    @schedcmds.command(name = "set-channel", description = "スケジュールの投稿先を設定します")
    async def set_channel(
        self,
        ctx : discord.ApplicationContext,
        channel : Option(discord.TextChannel, "投稿先のチャンネル")
    ):
        """Sets the channel where schedule messages will be posted."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("管理者専用のコマンドです。", ephemeral = True)
            return
        
        self._set_channel(channel.id, ctx.guild)
        await ctx.respond(f"スケジュールの送信先チャンネルを{channel.name}（ID：{channel.id}）に設定しました。")

    @schedcmds.command(name = "set-this-channel", description = "このチャンネルをスケジュールの投稿先に設定します")
    async def set_this_channel(
        self,
        ctx : discord.ApplicationContext
    ):
        """Sets the current channel as the target for schedule posts."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("管理者専用のコマンドです。", ephemeral = True)
            return
        
        channel = ctx.channel
        if channel.type not in (discord.ChannelType.text, discord.ChannelType.news, discord.ChannelType.public_thread):
            await ctx.respond(f"このチャンネルは投稿先に設定できません。\nテキスト・ニュース・公開スレッドにのみ対応しています。")
            return

        self._set_channel(channel.id, ctx.guild)
        await ctx.respond(f"スケジュールの送信先チャンネルを{channel.name}（ID：{channel.id}）に設定しました。")

    @schedcmds.command(name = "today", description = "今日のスケジュールをお知らせします")
    async def notify_today_schedule(
        self,
        ctx : discord.ApplicationContext
    ):
        """Sends today's schedule to the user via slash command."""
        await ctx.response.defer()

        today = datetime.now(ZoneInfo("Asia/Tokyo"))
        end = today + timedelta(days=1)

        # Retrieves today's events
        events = self._get_events(
            from_date = today,
            to_date = end,
            guild_id = ctx.guild.id
        )
        if not events:  # No events
            await ctx.followup.send("今日の予定は設定されていません")
            return

        msg = self._generate_schedmsg_from_eventlist(
            events = events,
            time = today,
            istoday = True
        )

        await ctx.followup.send(content = msg)

    @schedcmds.command(name = "tomorrow", description = "明日のスケジュールをお知らせします")
    async def notify_tomorrow_schedule(
        self,
        ctx : discord.ApplicationContext
    ):
        """Sends tomorrow's schedule to the user via slash command."""
        await ctx.response.defer()

        tomorrow = datetime.now(ZoneInfo("Asia/Tokyo")) + timedelta(days=1)
        end = tomorrow + timedelta(days=1)

        # Retrieves tomorrow's events
        events = self._get_events(
            from_date = tomorrow,
            to_date = end,
            guild_id = ctx.guild.id
        )
        if not events:  # No events
            await ctx.followup.send("明日の予定は設定されていません")
            return

        msg = self._generate_schedmsg_from_eventlist(
            events = events,
            time = tomorrow,
            istoday = False
        )

        await ctx.followup.send(content = msg)

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """Handles errors in application commands."""
        if isinstance(error, commands.NotOwner):
            await ctx.respond("このコマンドは実行できません！")
        else:
            print(error)
            raise error

    #
    # Implementation of periodic execution routines
    #

    today_time = time(hour=6, minute=0, tzinfo=ZoneInfo("Asia/Tokyo"))
    tomorrow_time = time(hour=22, minute=57, tzinfo=ZoneInfo("Asia/Tokyo"))

    @tasks.loop(time = today_time)
    async def loop_notify_today_schedule(self):
        """Loop that posts today's schedule to configured channels every morning."""
        if self._apiclient.is_enable() is False:
            return
        
        today = datetime.now(ZoneInfo("Asia/Tokyo"))
        end = today + timedelta(days=1)

        guilds_conf = self._config.data.guilds_conf
        for guild_id, conf in guilds_conf.items():
            calendarid = conf.calendar_id
            channelid = conf.channel_id
            if calendarid == "":
                continue
            if channelid == -1:
                continue

            channel = self._bot.get_channel(channelid)
            if channel is None:
                continue

            # Retrieves events
            events = self._apiclient.list_events(
                calendarId = calendarid,
                timeMin = datetime(today.year, today.month, today.day, 00, 00),
                timeMax = datetime(end.year, end.month, end.day, 00, 00)
            )
            if not events:  # No events
                continue
            
            msg = self._generate_schedmsg_from_eventlist(
                events = events,
                time = today,
                istoday = True
            )

            # Post to Discord
            await channel.send(msg)

    @tasks.loop(time=tomorrow_time)
    async def loop_notify_tomorrow_schedule(self):
        """Loop that posts tomorrow's schedule every night."""
        if self._apiclient.is_enable() is False:
            return
        
        tomorrow = datetime.now(ZoneInfo("Asia/Tokyo")) + timedelta(days=1)
        end = tomorrow + timedelta(days=1)

        guilds_conf = self._config.data.guilds_conf
        for guild_id, conf in guilds_conf.items():
            calendarid = conf.calendar_id
            channelid = conf.channel_id
            if calendarid == "":
                continue
            if channelid == -1:
                continue

            channel = self._bot.get_channel(channelid)
            if channel is None:
                continue
        
            # Retrieves events
            events = self._apiclient.list_events(
                calendarId = calendarid,
                timeMin = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 00, 00),
                timeMax = datetime(end.year, end.month, end.day, 00, 00)
            )
            if not events:  # No events
                return
            
            msg = self._generate_schedmsg_from_eventlist(
                events = events,
                time = tomorrow,
                istoday = False
            )

            # Post to Discord
            await channel.send(msg)

    #
    # Internal functions
    #

    def _get_events(
        self,
        from_date : datetime,
        to_date : datetime,
        guild_id : int
    ) -> list:
        """Retrieves calendar events for a guild between two dates."""
        if self._apiclient.is_enable() is False:
            return []
        
        guilds_conf = self._config.data.guilds_conf
        guild_id_str = str(guild_id)
        if guild_id_str not in guilds_conf.keys():
            return []

        calendar_id = guilds_conf[guild_id_str].calendar_id
        if calendar_id == "":
            return []

        return self._apiclient.list_events(
            calendarId = calendar_id,
            timeMin = datetime(from_date.year, from_date.month, from_date.day, 00, 00),
            timeMax = datetime(to_date.year, to_date.month, to_date.day, 00, 00)
        )

    def _generate_schedmsg_from_eventlist(
        self,
        events : list,
        time : datetime,
        istoday : bool
    ) -> str:
        """Generates a formatted schedule message from event data."""
        weekdays_ja = ['月', '火', '水', '木', '金', '土', '日']
        msg = "## {} {}の予定\n".format(
            "今日" if istoday else "明日",
            time.strftime("%Y/%m/%d") + f"（{weekdays_ja[time.weekday()]}）"
        )

        def _get_duration() -> str:
            start = evt['start'].get('dateTime', evt['start'].get('date'))
            end = evt['end'].get('dateTime', evt['end'].get('date'))

            if start is end:
                return "終日"
            
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            return f"{start_dt.hour:02}:{start_dt.minute:02} ～ {end_dt.hour:02}:{end_dt.minute:02}"

        for evt in events:
            duration = _get_duration()
            summary = evt.get('summary', 'なにかの予定')

            msg += f"### {summary}   {duration}\n"
            if 'description' in evt:
                msg += f"{evt['description']}\n"
            if 'location' in evt:
                msg += f"場所：{evt['location']}\n"
            msg += '\n'
        
        return msg

    def _set_calendar_id(self, calid : str, guild : discord.Guild):
        """Sets the calendar ID for a given guild."""
        if guild is None:
            return

        guilds_conf = self._config.data.guilds_conf
        guild_id_str = str(guild.id)
        if guild_id_str in guilds_conf.keys():
            conf = guilds_conf[guild_id_str]
            conf.calendar_id = calid
        else:
            guilds_conf[guild_id_str] = SchedCogConfForGuild(
                calendar_id = calid
            )

    def _set_channel(self, channelId : int, guild : discord.Guild):
        """Sets the notification channel for a given guild."""
        if guild is None:
            return
        
        guilds_conf = self._config.data.guilds_conf
        guild_id_str = str(guild.id)
        if guild_id_str in guilds_conf.keys():
            conf = guilds_conf[guild_id_str]
            conf.channel_id = channelId
        else:
            guilds_conf[guild_id_str] = SchedCogConfForGuild(
                channel_id = channelId
            )

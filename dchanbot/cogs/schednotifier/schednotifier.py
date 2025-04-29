from datetime import datetime, timedelta
from zoneinfo import ZoneInfo   # from Python 3.9
from pathlib import Path
import logging

import discord
from discord.ext import commands, tasks

from bot import DChanBot
from .gcalendar import GCalenderClient


logger = logging.getLogger("dchanbot.cogs.schednotifier")


class SchedNotifier(commands.Cog):
    def __init__(self, bot : DChanBot):
        self._bot = bot

        self._apiclient = GCalenderClient()
        self._apiclient.authorize(
            reflesh_token_path = Path(""),
            client_secrets_path = Path("")
        )
        if self._apiclient.build() is False:
            logger.critical("Failed to build Calendar API client")
            return

        # 定期実行するルーチンの起動
        self.notify_today_schedule.start()
        self.notify_tomorrow_schedule.start()

        logger.info("SchedNotifier is now ready.")

    def unload(self):
        self.notify_today_schedule.stop()
        self.notify_tomorrow_schedule.stop()

    # 本日のスケジュールを投稿するルーチン
    @tasks.loop(time=datetime(hour=6, minute=0, tzinfo=ZoneInfo("Asia/Tokyo")))
    async def notify_today_schedule(self):
        if self._apiclient.is_enable() is False:
            return

        today = datetime.today()
        end = today + timedelta(days=1)

        # イベント取得
        events = self._apiclient.list_events(
            calendarId = "",
            timeMin = datetime(today.year, today.month, today.day, 00, 00),
            timeMax = datetime(end.year, end.month, end.day, 00, 00)
        )
        if not events:  # イベントがない
            return
        
        # 投稿文を作成
        msg = self._generate_schedmsg_from_eventlist(
            events = events,
            time = today,
            istoday = True
        )

        # 投稿

    # 明日のスケジュールを投稿するルーチン
    @tasks.loop(time=datetime(hour=23, minute=0, tzinfo=ZoneInfo("Asia/Tokyo")))
    async def notify_tomorrow_schedule(self):
        if self._apiclient.is_enable() is False:
            return
        
        tomorrow = datetime.today() + timedelta(days=1)
        end = tomorrow + timedelta(days=1)
        
        # イベント取得
        events = self._apiclient.list_events(
            calendarId = "",
            timeMin = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 00, 00),
            timeMax = datetime(end.year, end.month, end.day, 00, 00)
        )
        if not events:  # イベントがない
            return
        
        # 投稿文を作成
        msg = self._generate_schedmsg_from_eventlist(
            events = events,
            time = tomorrow,
            istoday = False
        )

        # 投稿



    def _generate_schedmsg_from_eventlist(
        self,
        events : list,
        time : datetime,
        istoday : bool
    ) -> str:
        weekdays_ja = ['日', '月', '火', '水', '木', '金', '土']
        msg = "{} {}の予定をお知らせします\n".format(
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
            return "{}:{} ～ {}:{}".format(
                start_dt.hour, start_dt.minute,
                end_dt.hour, end_dt.minute
            )

        for evt in events:
            duration = _get_duration()
            summary = evt.get('summary', 'なにかの予定')

            msg += f"・{summary} {duration}\n"
            if 'description' in evt:
                msg += f"  詳細：{evt['description']}\n"
            if 'location' in evt:
                msg += f"  場所：{evt['location']}\n"
            msg += '\n'
        
        return msg

from datetime import datetime, timezone
from zoneinfo import ZoneInfo   # from Python 3.9
from pathlib import Path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger("dchanbot.cogs.schednotifier.gcalendar")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class GCalenderClient:
    def __init__(self):
        self._creds = None
        self._service = None

    #
    # APIを叩ける状態かどうか
    #
    def is_enable(self) -> bool:
        return self._service is not None

    #
    # Google Calendar APIを使うための認証処理を行う
    #
    def authorize(
        self,
        reflesh_token_path : Path,
        client_secrets_path : Path
    ):
        if self._creds is not None:
            return
        
        # 1. すでにリフレッシュトークンを記録したファイルがある場合、
        #    それを読み込む
        if reflesh_token_path.exists():
            self._creds = Credentials.from_authorized_user_file(
                filename = str(reflesh_token_path),
                scopes = SCOPES
            )

        # 2. 1で失敗 or ファイルがない場合、認証処理を行う
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file = str(client_secrets_path),
                    scopes = SCOPES
                )
                self._creds = flow.run_local_server(port=0)

            # トークンを保存
            with reflesh_token_path.open(mode="w") as token:
                token.write(self._creds.to_json())
        
    def build(self) -> bool:
        if self._creds is not None:
            self._service = build("calendar", "v3", credentials=self._creds)
        return (self._service is not None)
    
    #
    # 指定された範囲のイベントのリストを取得する
    #   calendarId - カレンダーID
    #   timeMin - フィルタするイベントの終了時間の下限
    #   timeMax - フィルタするイベントの開始時間の上限
    #
    def list_events(
        self, 
        calendarId : str,
        timeMin : datetime,
        timeMax : datetime
    ) -> list:
        if self._service is None:
            return ""

        if timeMin >= timeMax:
            raise ValueError("dateMin must be less than dateMax")

        try:
            # APIを叩く
            event_result = self._service.events().list(
                calendarId = calendarId,
                orderBy = "startTime",      # イベント開始時刻順にソートする
                singleEvents = True,
                maxResults = 100,           # とりま100件まで取得
                timeMin = self._to_utc_string(timeMin),
                timeMax = self._to_utc_string(timeMax)
            ).execute()
            events = event_result.get('items', [])
        except HttpError as e:
            logger.error(f"HttpError: {e}")
            return None

        return events

    #
    # datetimeオブジェクトをUTC時間の文字列に変換する
    #   例： 2025-01-01T06:00:00Z
    #
    def _to_utc_string(self, time : datetime) -> str:
        dtutc = None

        # タイムゾーンをUTCに変換
        # timeがタイムゾーン情報を持っていない場合、もともとUTCであったとみなす
        if time.tzinfo is None:
            dtutc = time.replace(tzinfo = timezone.utc)
        else:
            dtutc = time.astimezone(ZoneInfo("UTC"))
        
        # Google APIは末尾が"Z"のものをUTC時刻として処理する
        return dtutc.strftime('%Y-%m-%dT%H:%M:%SZ')

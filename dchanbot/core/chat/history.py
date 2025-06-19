from typing import List
from pathlib import Path
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory

import aiosqlite

from .summarizer import Summarizer

class ChatHistory(BaseChatMessageHistory):
    def __init__(
        self,
        session_id : str,
        db_path    : Path,
        summarizer : Summarizer,
        max_recent : int = 20,          # LRUキャッシュの数
        summarize_threshold : int = 100 # 要約処理のトリガーメッセージ件数
    ):
        self._session_id = session_id
        
        self._db_path    = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._summarizer = summarizer
        self._max_recent = max_recent
        self._summarize_threshold = summarize_threshold

        self._messages : List[BaseMessage] = []  # チャットMSGのメモリキャッシュ
        self._db_initialized = False

    @property
    def messages(self) -> List[BaseMessage]:
        return self._messges
    
    async def aget_messages(self) -> List[BaseMessage]:
        return self._messages

    def add_messages(self, messages : List[BaseMessage]) -> None:
        self._messages.extend(messages)

    async def aadd_messages(self, messages: List[BaseMessage]) -> None:
        self._messages.extend(messages)

    def clear(self) -> None:
        self._messages.clear()

    async def aclear(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM chat_history WHERE session_id = ?",
                (self._session_id,)
            )
            await db.commit()

        self._messages.clear()
    
    async def load_all_messages(self) -> None:
        await self._ensure_db()

        self._messages.clear()
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT role, content, timestamp FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC",
                (self._session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                for role, content, ts in rows:
                    cls = HumanMessage if role == "Human" else AIMessage
                    self._messages.append(
                        cls(content=content, additional_kwargs={"timestamp": ts})
                    )

    async def flush_to_db(self):
        await self._ensure_db()

        async with aiosqlite.connect(self._db_path) as db:
            for msg in self._messages:
                # DiscordのMSGの投稿日時が格納されていれば、それをtimestampに変換
                ts_raw = msg.additional_kwargs.get("timestamp", 0.0)
                timestamp = ts_raw.timestamp() if isinstance(ts_raw, datetime) else ts_raw

                await db.execute(
                    "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (
                        self._session_id,
                        "Human" if isinstance(msg, HumanMessage) else "AI",
                        msg.content,
                        timestamp,
                    )
                )
                await db.commit()

        await self.summarize_if_necessary()
    
    async def _ensure_db(self):
        if  self._db_initialized:
            return

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL
                )
            """)
            await db.commit()
        self._db_initialized = True

    async def summarize_if_necessary(self):
        if self._summarizer is None:
            return

        if len(self._messages) - self._max_recent > self._summarize_threshold:
            # 最新のmax_recent件数分は、保持する
            recents = self._messages[-self.max_recent:]

            # 残りの古いMSGを要約する
            # 要約したメッセージのtimestampはこの時点での時刻とする
            olds = self._messages[:-self._max_recent]
            summary = await self.summarize_messages(olds)
            summary_ts = datetime().now().timestamp()
            summarized_msg = AIMessage(
                content = summary,
                additional_kwargs = {
                    "timestamp" : summary_ts
                }
            )

            self._messages = [summarized_msg] + recents

            async with aiosqlite.connect(self._db_path) as db:
                # DBから古いメッセージをtimestampで特定して削除
                for msg in olds:
                    ts_raw = msg.additional_kwargs.get("timestamp", 0.0)
                    timestamp = ts_raw.timestamp() if isinstance(ts_raw, datetime) else ts_raw
                    await db.execute(
                        "DELETE FROM chat_history WHERE session_id = ? AND timestamp = ?",
                        (self._session_id, timestamp,)
                    )
                
                # 要約したものをDBに保存
                await db.execute(
                    "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (self._session_id, "AI", summarized_msg.content, summary_ts,)
                )
                await db.commit()

    async def summarize_messages(self, messages : List[BaseMessage]) -> str:
        if self._summarizer is not None:
            msgs = "\n".join(
                f"{m.type}: {m.content}" for m in messages if hasattr(m, "content")
            )
            summary = await self._summarizer.summarize(msgs)
            return summary
        
        return ""

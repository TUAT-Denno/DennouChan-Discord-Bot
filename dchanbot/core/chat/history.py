import asyncio
from typing import List
from pathlib import Path
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory

import aiosqlite

from .summarizer import Summarizer

class ChatHistory(BaseChatMessageHistory):
    """Asynchronous chat history manager with summarization and SQLite persistence.

    Stores and retrieves chat messages for a given session, optionally summarizing
    older messages to reduce memory and storage usage.
    """

    def __init__(
        self,
        session_id : str,
        db_path    : Path,
        summarizer : Summarizer,
        max_recent : int = 20,
        summarize_threshold : int = 100
    ):
        """Initializes a new ChatHistory instance.

        Args:
            session_id (str): Unique identifier for the chat session.
            db_path (Path): Path to the SQLite database for storing messages.
            summarizer (Summarizer): Summarizer to use for compressing chat history.
            max_recent (int, optional): Number of recent messages to retain. Defaults to 20.
            summarize_threshold (int, optional): Number of old messages to trigger summarization. Defaults to 100.
        """
        self._session_id = session_id
        
        self._db_path    = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._summarizer = summarizer
        self._max_recent = max_recent
        self._summarize_threshold = summarize_threshold

        self._messages : List[BaseMessage] = []
        self._db_initialized = False

        self._db_lock = asyncio.Lock()

    @property
    def messages(self) -> List[BaseMessage]:
        """Gets the current in-memory messages.

        Returns:
            List[BaseMessage]: The list of cached chat messages.
        """
        return self._messges
    
    async def aget_messages(self) -> List[BaseMessage]:
        """Asynchronously retrieves cached messages.

        Returns:
            List[BaseMessage]: The list of cached chat messages.
        """
        return self._messages

    def add_messages(self, messages : List[BaseMessage]) -> None:
        """Adds a list of messages to the in-memory cache.

        Args:
            messages (List[BaseMessage]): Messages to append.
        """
        self._messages.extend(messages)

    async def aadd_messages(self, messages: List[BaseMessage]) -> None:
        """Asynchronously adds messages to the in-memory cache.

        Args:
            messages (List[BaseMessage]): Messages to append.
        """
        self._messages.extend(messages)

    def clear(self) -> None:
        """Clears all messages from the in-memory cache."""
        self._messages.clear()

    async def aclear(self) -> None:
        """Asynchronously clears all messages from both the in-memory cache and the database."""
        async with self._db_lock:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "DELETE FROM chat_history WHERE session_id = ?",
                    (self._session_id,)
                )
                await db.commit()

        self._messages.clear()
    
    async def load_all_messages(self) -> None:
        """Loads all messages from the database into memory."""
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
        """Flushes all in-memory messages to the SQLite database."""
        await self._ensure_db()

        async with self._db_lock:
            async with aiosqlite.connect(self._db_path) as db:
                for msg in self._messages:
                    # If the Discord message's timestamp is stored, convert it to a float timestamp
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

    async def _ensure_db(self):
        """Ensures that the database and table exist, creating them if needed."""
        if  self._db_initialized:
            return

        async with self._db_lock:
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
        """Summarizes older messages if the number of old messages exceeds the threshold.

        Retains only the most recent messages and a single AI-generated summary.
        """
        if self._summarizer is None:
            return

        if len(self._messages) - self._max_recent > self._summarize_threshold:
            # Keep only the most recent `max_recent` messages
            recents = self._messages[-self.max_recent:]

            # Summarize the remaining older messages
            # Use the current time as the timestamp for the summarized message
            olds = self._messages[:-self._max_recent]
            summary = await self._summarize_messages(olds)
            summary_ts = datetime().now().timestamp()
            summarized_msg = AIMessage(
                content = summary,
                additional_kwargs = {
                    "timestamp" : summary_ts
                }
            )

            self._messages = [summarized_msg] + recents

            async with self._db_lock:
                async with aiosqlite.connect(self._db_path) as db:
                    # Delete old messages from the database using their timestamps
                    for msg in olds:
                        ts_raw = msg.additional_kwargs.get("timestamp", 0.0)
                        timestamp = ts_raw.timestamp() if isinstance(ts_raw, datetime) else ts_raw
                        await db.execute(
                            "DELETE FROM chat_history WHERE session_id = ? AND timestamp = ?",
                            (self._session_id, timestamp,)
                        )
                    
                    # Save the summarized message to the database
                    await db.execute(
                        "INSERT INTO chat_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                        (self._session_id, "AI", summarized_msg.content, summary_ts,)
                    )
                    await db.commit()

    async def _summarize_messages(self, messages : List[BaseMessage]) -> str:
        """Summarizes a list of messages using the configured summarizer.

        Args:
            messages (List[BaseMessage]): Messages to summarize.

        Returns:
            str: Summary text generated by the summarizer.
        """
        if self._summarizer is not None:
            msgs = "\n".join(
                f"{m.type}: {m.content}" for m in messages if hasattr(m, "content")
            )
            summary = await self._summarizer.summarize(msgs)
            return summary
        
        return ""

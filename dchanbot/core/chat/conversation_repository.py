import logging

from collections.abc import Sequence

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage


logger = logging.getLogger(__name__)


class InMemoryConversationRepository:
    def __init__(self):
        self._histories: dict[str, InMemoryChatMessageHistory] = {}

    def _get_or_create_history(self, conversation_id: str) -> InMemoryChatMessageHistory:
        history = self._histories.get(conversation_id)
        if history is None:
            history = InMemoryChatMessageHistory()
            self._histories[conversation_id] = history

        return history
    
    async def load_messages(
        self,
        conversation_id: str
    ) -> list[BaseMessage]:
        history = self._get_or_create_history(conversation_id)

        messages = await history.aget_messages()

        return list(messages)

    async def append_messages(
        self,
        conversation_id: str,
        messages: Sequence[BaseMessage],
    ) -> None:
        history = self._get_or_create_history(conversation_id)
        await history.aadd_messages(messages)

    async def clear_messages(
        self,
        conversation_id: str,
    ) -> None:
        history = self._histories.get(conversation_id)

        if history is None:
            return

        await history.aclear()
        del self._histories[conversation_id]


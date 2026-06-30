from collections.abc import Sequence
from typing import Protocol

from langchain_core.messages import BaseMessage

class ConversationRepository(Protocol):
    async def load_messages(
        self,
        conversation_id: str,
    ) -> list[BaseMessage]:
        ...

    async def append_messages(
        self,
        conversation_id: str,
        messages: Sequence[BaseMessage],
    ) -> None:
        ...

    async def clear_messages(
        self,
        conversation_id: str,
    ) -> None:
        ...

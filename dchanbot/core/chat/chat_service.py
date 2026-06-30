import logging

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict, Annotated

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from core.chat.prompt_manager import PromptManager
from core.chat.conversation_repository import InMemoryConversationRepository


logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    conversation_id: str
    request_content: str

    messages: Annotated[list[BaseMessage], add_messages]
    new_messages: Annotated[list[BaseMessage], add_messages]


class ConversationSource(StrEnum):
    DM = "dm"
    GUILD = "guild"

@dataclass(frozen=True)
class ChatRequest:
    conversation_id: str
    content: str
    user_id: str
    source: ConversationSource
    guild_id: str | None = None
    channel_id: str | None = None

    def __post_init__(self) -> None:
        if not self.conversation_id:
            raise ValueError("conversation_id must not be empty")

        if not self.user_id:
            raise ValueError("user_id must not be empty")

        if self.source is ConversationSource.DM:
            if self.guild_id is not None:
                raise ValueError(
                    "guild_id must be None for DM conversations"
                )
            
            if self.channel_id is not None:
                raise ValueError(
                    "channel_id must be None for DM conversations"
                )

        elif self.source is ConversationSource.GUILD:
            if self.guild_id is None:
                raise ValueError(
                    "guild_id is required for guild conversations"
                )

            if self.channel_id is None:
                raise ValueError(
                    "channel_id is required for guild conversations"
                )

@dataclass(frozen = True)
class ChatResponse:
    content: str

class ChatService:
    def __init__(
        self,
        model: BaseChatModel,
        prompt_manager: PromptManager,
        conversation_repository: InMemoryConversationRepository
    ):
        self._model = model
        self._prompt_manager = prompt_manager
        self._conversation_repository = conversation_repository

        graph_builder = StateGraph(ChatState)

        # Add nodes
        graph_builder.add_node("prepare", self._prepare)
        graph_builder.add_node("generate", self._generate)
        graph_builder.add_node("save", self._save)

        # Add edges to connect nodes
        graph_builder.add_edge(START, "prepare")
        graph_builder.add_edge("prepare", "generate")
        graph_builder.add_edge("generate", "save")
        graph_builder.add_edge("save", END)

        # Compile the graph
        self._graph = graph_builder.compile()

    async def _prepare(self, state: ChatState) -> dict:
        prompt = self._prompt_manager.get("denno_chan")
        history = await self._conversation_repository.load_messages(state["conversation_id"])
        user_message = HumanMessage(content = state["request_content"])

        return {
            "messages": [
                SystemMessage(content = prompt.system_prompt),
                *history,
                user_message,
            ],
            "new_messages": [
                user_message,
            ]
        }

    async def _generate(self, state: ChatState) -> dict:
        logger.debug(
            "Invoking model with messages: %s",
            [type(message).__name__ for message in state["messages"]],
        )

        response = await self._model.ainvoke(state["messages"])

        return {
            "messages": [response],
            "new_messages": [response],
        }

    async def _save(self, state: ChatState) -> dict:
        await self._conversation_repository.append_messages(
            conversation_id = state["conversation_id"],
            messages = state["new_messages"],
        )

        return {}

    async def chat(self, request : ChatRequest) -> ChatResponse:
        result = await self._graph.ainvoke(
            {
                "conversation_id": request.conversation_id,
                "request_content": request.content,
                "messages": [],
                "new_messages": [],
            }
        )

        message = result["messages"][-1]

        logger.debug(
            "AI response: type=%s content=%r blocks=%r",
            type(message).__name__,
            message.content,
            message.content_blocks,
        )

        content = message.text
        if not isinstance(content, str):
            raise TypeError(
                f"Expected string response content, got {type(content).__name__}"
            )

        return ChatResponse(content=content)
